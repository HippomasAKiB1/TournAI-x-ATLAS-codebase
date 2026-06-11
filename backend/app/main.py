import os
import json
import sys
import math
import secrets
import hashlib
import datetime
import asyncio
import requests
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta
from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks, status, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add project root directory to Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.adaptive.pipeline_trigger import trigger_adaptive_update
from backend.app.db.session import engine, Base, get_db, SessionLocal
from backend.app.db import crud, schemas, auth
from backend.app.db.models import User, Match, UserPrediction

# Celery Dual-Mode Configuration
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"
if USE_CELERY:
    try:
        from backend.app.tasks.celery import run_adaptive_pipeline_task
        print("Celery backend queue enabled.")
    except ImportError:
        print("WARNING: Celery tasks module not found. Falling back to BackgroundTasks.")
        USE_CELERY = False

# Cookie Hashing & SameSite settings for Production
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TournAI × ATLAS REST Backend",
    description="Live prediction, tournament simulation, and adaptive learning API",
    version="1.0.0"
)

async def poll_football_data_loop():
    """
    Periodically syncs matches from football-data.org and updates live scores/results.
    """
    await asyncio.sleep(10) # Wait for startup migrations to complete
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "b9bbbeb96e0d4a96b9595580bf6362ad")
    headers = {"X-Auth-Token": api_key}
    
    print(f"[Live Polling] Starting football-data.org background polling service with key: {api_key[:4]}...{api_key[-4:]}")
    
    # 1. Sync external match IDs on startup
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches?season=2026"
        def fetch_fixtures():
            return requests.get(url, headers=headers, timeout=12)
            
        print(f"[Live Polling] Fetching fixtures from: {url}")
        res = await asyncio.to_thread(fetch_fixtures)
        if res.status_code == 200:
            data = res.json()
            api_matches = data.get("matches", [])
            print(f"[Live Polling] Received {len(api_matches)} matches from football-data.org")
            
            db = SessionLocal()
            try:
                synced_count = 0
                for api_m in api_matches:
                    home_name = api_m["homeTeam"]["name"]
                    away_name = api_m["awayTeam"]["name"]
                    utc_date = api_m.get("utcDate")
                    api_id = api_m["id"]
                    
                    local_match = db.query(Match).filter(
                        (func.lower(Match.home_team) == home_name.lower()) & 
                        (func.lower(Match.away_team) == away_name.lower())
                    ).first()
                    
                    if not local_match:
                        def clean_team_name(name):
                            name = name.lower()
                            if "united states" in name or "usa" in name:
                                return "usa"
                            if "saudi arabia" in name:
                                return "saudi arabia"
                            return name
                        
                        all_matches = db.query(Match).all()
                        for m in all_matches:
                            if clean_team_name(m.home_team) == clean_team_name(home_name) and clean_team_name(m.away_team) == clean_team_name(away_name):
                                local_match = m
                                break
                                
                    if local_match:
                        local_match.external_match_id = api_id
                        local_match.kickoff_utc = utc_date
                        synced_count += 1
                db.commit()
                print(f"[Live Polling] Successfully linked {synced_count} matches in local database.")
            except Exception as e:
                db.rollback()
                print(f"[Live Polling] Database error during initial sync: {e}")
            finally:
                db.close()
        else:
            print(f"[Live Polling] Failed to fetch matches on startup. Status code: {res.status_code}, Msg: {res.text}")
    except Exception as e:
        print(f"[Live Polling] Error during initial sync execution: {e}")
        
    # 2. Polling loop
    while True:
        try:
            # Poll LIVE matches
            url_live = "https://api.football-data.org/v4/competitions/WC/matches?status=LIVE"
            def fetch_live():
                return requests.get(url_live, headers=headers, timeout=10)
                
            res_live = await asyncio.to_thread(fetch_live)
            if res_live.status_code == 200:
                live_matches = res_live.json().get("matches", [])
                if live_matches:
                    db = SessionLocal()
                    try:
                        for api_m in live_matches:
                            api_id = api_m["id"]
                            score = api_m.get("score", {})
                            h_score = score.get("fullTime", {}).get("home") or score.get("regularTime", {}).get("home") or 0
                            a_score = score.get("fullTime", {}).get("away") or score.get("regularTime", {}).get("away") or 0
                            
                            local_m = db.query(Match).filter(Match.external_match_id == api_id).first()
                            if local_m:
                                local_m.home_score = h_score
                                local_m.away_score = a_score
                                local_m.status = "LIVE"
                                db.commit()
                                print(f"[Live Polling] Updated LIVE score: {local_m.home_team} {h_score} - {a_score} {local_m.away_team}")
                    except Exception as e:
                        db.rollback()
                        print(f"[Live Polling] DB Error updating live score: {e}")
                    finally:
                        db.close()
            
            # Poll FINISHED matches
            url_finished = "https://api.football-data.org/v4/competitions/WC/matches?status=FINISHED"
            def fetch_finished():
                return requests.get(url_finished, headers=headers, timeout=10)
                
            res_fin = await asyncio.to_thread(fetch_finished)
            if res_fin.status_code == 200:
                finished_matches = res_fin.json().get("matches", [])
                if finished_matches:
                    db = SessionLocal()
                    try:
                        for api_m in finished_matches:
                            api_id = api_m["id"]
                            score = api_m.get("score", {})
                            h_score = score.get("fullTime", {}).get("home")
                            a_score = score.get("fullTime", {}).get("away")
                            
                            local_m = db.query(Match).filter(Match.external_match_id == api_id).first()
                            if local_m and local_m.status != "completed" and h_score is not None and a_score is not None:
                                print(f"[Live Polling] Match finished: {local_m.home_team} vs {local_m.away_team} ({h_score}-{a_score})")
                                local_m.status = "completed"
                                local_m.home_score = h_score
                                local_m.away_score = a_score
                                db.commit()
                                
                                if USE_CELERY:
                                    run_adaptive_pipeline_task.delay(
                                        local_m.home_team,
                                        local_m.away_team,
                                        h_score,
                                        a_score,
                                        local_m.stage
                                    )
                                else:
                                    asyncio.create_task(asyncio.to_thread(
                                        trigger_adaptive_update,
                                        home_team=local_m.home_team,
                                        away_team=local_m.away_team,
                                        home_score=h_score,
                                        away_score=a_score,
                                        stage=local_m.stage
                                    ))
                    except Exception as e:
                        db.rollback()
                        print(f"[Live Polling] DB Error updating finished match: {e}")
                    finally:
                        db.close()
        except Exception as e:
            print(f"[Live Polling] Exception in loop: {e}")
            
        await asyncio.sleep(60)

@app.on_event("startup")
def startup_event():
    # Database migrations to safely add external_match_id and kickoff_utc
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE matches ADD COLUMN external_match_id INTEGER"))
                conn.commit()
                print("Migration: Added external_match_id to matches table.")
            except Exception:
                pass # Ignore if column already exists
            try:
                conn.execute(text("ALTER TABLE matches ADD COLUMN kickoff_utc VARCHAR"))
                conn.commit()
                print("Migration: Added kickoff_utc to matches table.")
            except Exception:
                pass # Ignore if column already exists
    except Exception as e:
        print(f"Migration error: {e}")

    db = SessionLocal()
    try:
        if db.query(Match).count() == 0:
            print("Populating database matches table from predictions.json...")
            predictions_path = FRONTEND_DATA_DIR / "predictions.json"
            if predictions_path.exists():
                with open(predictions_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    fixtures = data.get("predictions", [])
                    for fxt in fixtures:
                        match = Match(
                            id=fxt["fixture_id"],
                            home_team=fxt["home_team"],
                            away_team=fxt["away_team"],
                            date=fxt["date"],
                            stage="Group Stage",
                            status="scheduled"
                        )
                        db.add(match)
                db.commit()
                print(f"Successfully populated {len(fixtures)} matches in the database.")
            else:
                print(f"WARNING: predictions.json not found at {predictions_path}. Could not populate database.")
    except Exception as e:
        print(f"Error during database matches pre-population: {e}")
        db.rollback()
    finally:
        db.close()

    # Start live polling service in background
    loop = asyncio.get_event_loop()
    loop.create_task(poll_football_data_loop())

# CORS configuration to allow local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths configuration
ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DATA_DIR = ROOT / "frontend" / "public" / "data"

class MatchIngestPayload(BaseModel):
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    stage: str = "Group Stage"

class PredictPayload(BaseModel):
    home_team: str
    away_team: str

# Load Helper
def load_sanitized_json(filename: str) -> Dict[str, Any]:
    file_path = FRONTEND_DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file {filename} not found.")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse {filename}: {str(e)}")

# Pipeline Status Tracking State
PIPELINE_STATUS = {
    "status": "idle",
    "last_run_time": None,
    "error": None
}

def calculate_poisson_score(elo_diff: float, avg_diff: float) -> tuple[int, int, float]:
    """Dynamically compute lambda goals parameter and find the highest joint probability score line."""
    # Base goals is 1.35. Elo difference and Average Squad Impact difference adjusts expected goals
    lambda_home = 1.35 + (elo_diff / 500.0) + (avg_diff / 15.0)
    lambda_away = 1.35 - (elo_diff / 500.0) - (avg_diff / 15.0)
    
    # Cap parameters between 0.3 and 5.0
    lambda_home = max(0.3, min(5.0, lambda_home))
    lambda_away = max(0.3, min(5.0, lambda_away))
    
    best_prob = -1.0
    best_score = (0, 0)
    
    # Iterate from 0 to 5 goals
    for gh in range(6):
        prob_h = (lambda_home ** gh) * math.exp(-lambda_home) / math.factorial(gh)
        for ga in range(6):
            prob_a = (lambda_away ** ga) * math.exp(-lambda_away) / math.factorial(ga)
            joint_prob = prob_h * prob_a
            if joint_prob > best_prob:
                best_prob = joint_prob
                best_score = (gh, ga)
                
    return best_score[0], best_score[1], round(best_prob, 4)

def calculate_entropy_confidence(p_home: float, p_draw: float, p_away: float) -> float:
    """Calculate the normalized Shannon entropy confidence of the match outcome distribution."""
    total = p_home + p_draw + p_away
    if total <= 0.0:
        return 0.3333
    p1 = p_home / total
    p2 = p_draw / total
    p3 = p_away / total
    
    entropy = 0.0
    for p in [p1, p2, p3]:
        if p > 0.0:
            entropy -= p * math.log2(p)
            
    # Max entropy for a 3-outcome problem is log2(3) = 1.5849625
    max_entropy = math.log2(3.0)
    confidence = 1.0 - (entropy / max_entropy)
    return round(max(0.0, min(1.0, confidence)), 4)

# ============================================================================
# 1. CORE ATLAS ML DATA ENDPOINTS
# ============================================================================

@app.get("/api/predictions")
async def get_predictions():
    data = load_sanitized_json("predictions.json")
    predictions_list = data.get("predictions", [])
    
    # Load player/squad data to look up ELO and squad impact averages
    players_data = load_sanitized_json("players.json")
    team_strengths = players_data.get("team_strength", [])
    team_strength_map = {t["team"].lower(): t for t in team_strengths}
    
    enriched_predictions = []
    for pred in predictions_list:
        home_team = pred.get("home_team", "")
        away_team = pred.get("away_team", "")
        
        home_str = team_strength_map.get(home_team.lower())
        away_str = team_strength_map.get(away_team.lower())
        
        elo_home = home_str.get("current_elo") if home_str else 1600.0
        elo_away = away_str.get("current_elo") if away_str else 1600.0
        # If elo is None, fallback to 1600
        if elo_home is None: elo_home = 1600.0
        if elo_away is None: elo_away = 1600.0
        elo_diff = elo_home - elo_away
        
        avg_home = home_str.get("avg_impact") if home_str else 50.0
        avg_away = away_str.get("avg_impact") if away_str else 50.0
        if avg_home is None: avg_home = 50.0
        if avg_away is None: avg_away = 50.0
        avg_diff = avg_home - avg_away
        
        # Calculate Poisson score prediction
        predicted_home_goals, predicted_away_goals, poisson_joint_prob = calculate_poisson_score(elo_diff, avg_diff)
        
        # Calculate confidence from the ensemble win/draw/loss probabilities
        p_home = pred.get("ensemble_home_win") or pred.get("home_win_prob") or 0.33
        p_draw = pred.get("ensemble_draw") or pred.get("draw_prob") or 0.33
        p_away = pred.get("ensemble_away_win") or pred.get("away_win_prob") or 0.33
        
        confidence = calculate_entropy_confidence(p_home, p_draw, p_away)
        
        # Check for upset alert (if lower-Elo team has > 30% win probability)
        is_upset = False
        if elo_diff > 0 and p_away > 0.30:
            is_upset = True
        elif elo_diff < 0 and p_home > 0.30:
            is_upset = True
            
        enriched_pred = {
            **pred,
            "predicted_home_goals": predicted_home_goals,
            "predicted_away_goals": predicted_away_goals,
            "poisson_joint_prob": poisson_joint_prob,
            "confidence": confidence,
            "upset_alert": is_upset
        }
        enriched_predictions.append(enriched_pred)
        
    data["predictions"] = enriched_predictions
    return data

@app.get("/api/simulations")
async def get_simulations():
    return load_sanitized_json("simulations.json")

@app.get("/api/players")
async def get_players():
    return load_sanitized_json("players.json")

@app.get("/api/explanations")
async def get_explanations():
    return load_sanitized_json("explanations.json")

@app.get("/api/model_comparison")
async def get_model_comparison():
    return load_sanitized_json("model_comparison.json")

@app.get("/api/group_standings")
async def get_group_standings():
    return load_sanitized_json("group_standings.json")

@app.get("/api/injuries")
async def get_injuries():
    return load_sanitized_json("injuries.json")


@app.get("/api/sse/pipeline")
async def sse_pipeline_updates(request: Request):
    """
    Server-Sent Events endpoint to stream pipeline completion events.
    Frontend connects to this to automatically refresh data when simulations complete.
    """
    async def event_generator():
        # Check initial timestamp
        last_timestamp = None
        predictions_path = FRONTEND_DATA_DIR / "predictions.json"
        
        if predictions_path.exists():
            try:
                mtime = os.path.getmtime(predictions_path)
                last_timestamp = mtime
            except Exception:
                pass
                
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
                
            await asyncio.sleep(2)
            
            # Check current modification time
            if predictions_path.exists():
                try:
                    mtime = os.path.getmtime(predictions_path)
                    if last_timestamp is None:
                        last_timestamp = mtime
                    elif mtime > last_timestamp:
                        last_timestamp = mtime
                        # Read generated_at from file
                        with open(predictions_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            gen_at = data.get("generated_at", "")
                        yield f"data: {json.dumps({'event': 'pipeline_complete', 'generated_at': gen_at})}\n\n"
                except Exception:
                    # Ignore temporary read issues during writes
                    pass
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/predict")
async def predict_custom_match(payload: PredictPayload):
    """
    Perform a dynamic custom H2H prediction based on team ratings and average squad impact values.
    """
    players_data = load_sanitized_json("players.json")
    team_strengths = players_data.get("team_strength", [])
    
    home_str = next((t for t in team_strengths if t["team"].lower() == payload.home_team.lower()), None)
    away_str = next((t for t in team_strengths if t["team"].lower() == payload.away_team.lower()), None)
    
    if not home_str or not away_str:
        raise HTTPException(status_code=400, detail="One or both teams not found in squad rating profiles.")
        
    elo_home = home_str.get("current_elo") or 1600.0
    elo_away = away_str.get("current_elo") or 1600.0
    elo_diff = elo_home - elo_away
    
    avg_home = home_str.get("avg_impact") or 50.0
    away_avg_val = away_str.get("avg_impact")
    avg_away = away_avg_val if away_avg_val is not None else 50.0
    avg_diff = avg_home - avg_away
    
    # Adjusted Elo difference based on squad impact averages
    elo_diff_adj = elo_diff + (avg_diff * 12.0)
    
    # Win probability
    win_prob_home = 1.0 / (1.0 + 10.0 ** (-elo_diff_adj / 400.0))
    
    # Draw probability scales down with larger differences
    diff_magnitude = abs(elo_diff_adj)
    draw_prob = max(0.12, 0.28 - (diff_magnitude / 3000.0))
    
    raw_home_prob = win_prob_home * (1.0 - draw_prob)
    raw_away_prob = (1.0 - win_prob_home) * (1.0 - draw_prob)
    
    total = raw_home_prob + raw_away_prob + draw_prob
    home_win_prob = round(raw_home_prob / total, 4)
    away_win_prob = round(raw_away_prob / total, 4)
    draw_prob_final = round(draw_prob / total, 4)
    
    predicted_result = "Draw"
    if home_win_prob > away_win_prob and home_win_prob > draw_prob_final:
        predicted_result = "Home Win"
    elif away_win_prob > home_win_prob and away_win_prob > draw_prob_final:
        predicted_result = "Away Win"
        
    # Calculate Poisson scoreline
    predicted_home_goals, predicted_away_goals = calculate_poisson_score(elo_diff, avg_diff)
    
    # Calculate normalized entropy confidence
    confidence = calculate_entropy_confidence(home_win_prob, draw_prob_final, away_win_prob)
    
    # Upset Alert
    is_upset = False
    if elo_diff > 0 and away_win_prob > 0.30:
        is_upset = True
    elif elo_diff < 0 and home_win_prob > 0.30:
        is_upset = True
      
    # Generate custom explanations
    elo_diff_narrative = (
        f"Higher Elo rating (+{round(elo_diff)} pts) increases win chance by {round(abs(elo_diff) / 20.0, 1)}%"
        if elo_diff > 0 else
        f"Lower Elo rating (-{round(abs(elo_diff))} pts) decreases win chance by {round(abs(elo_diff) / 20.0, 1)}%"
    )
    squad_quality_narrative = (
        f"Superior player squad quality (+{round(avg_diff, 1)} average impact) increases win chance by {round(avg_diff * 2.5, 1)}%"
        if avg_diff > 0 else
        f"Weaker player squad quality (-{round(abs(avg_diff), 1)} average impact) decreases win chance by {round(abs(avg_diff) * 2.5, 1)}%"
    )
    form_home = home_str.get("form_10") or 0.5
    form_away = away_str.get("form_10") or 0.5
    form_diff = form_home - form_away
    form_narrative = (
        f"Better recent tournament momentum (+{round(form_diff * 100)}%) increases win chance by {round(form_diff * 25.0, 1)}%"
        if form_diff > 0 else
        f"Poorer recent tournament momentum (-{round(abs(form_diff) * 100)}%) decreases win chance by {round(abs(form_diff) * 25.0, 1)}%"
    )
    
    return {
        "home_win_prob": home_win_prob,
        "away_win_prob": away_win_prob,
        "draw_prob": draw_prob_final,
        "predicted_result": predicted_result,
        "predicted_home_goals": predicted_home_goals,
        "predicted_away_goals": predicted_away_goals,
        "confidence": confidence,
        "elo_diff": elo_diff,
        "upset_alert": is_upset,
        "reasons": [squad_quality_narrative, elo_diff_narrative, form_narrative]
    }

def run_pipeline_in_background(
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    stage: str
):
    global PIPELINE_STATUS
    PIPELINE_STATUS["status"] = "running"
    try:
        from datetime import datetime
        trigger_adaptive_update(
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            stage=stage
        )
        PIPELINE_STATUS["status"] = "idle"
        PIPELINE_STATUS["last_run_time"] = datetime.now().isoformat()
        PIPELINE_STATUS["error"] = None
    except Exception as e:
        PIPELINE_STATUS["status"] = "idle"
        PIPELINE_STATUS["error"] = str(e)
        print(f"Error in background pipeline: {e}")

# ============================================================================
# 2. ADAPTIVE INGESTION ENDPOINT
# ============================================================================

@app.post("/api/ingest")
async def ingest_match(
    payload: MatchIngestPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_atlas_key: Optional[str] = Header(None)
):
    """
    Secure endpoint to ingest a finished match result and trigger ELO updates, 
    model retraining, bracket simulations, and JSON exports in the background.
    """
    expected_key = os.getenv("ATLAS_SECRET_KEY", "atlas-admin-secret-key-2026")
    if x_atlas_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid X-ATLAS-KEY authentication header.")
        
    # 1. Update match record in DB
    match = db.query(Match).filter(
        func.lower(Match.home_team) == payload.home_team.lower(),
        func.lower(Match.away_team) == payload.away_team.lower()
    ).first()
    
    is_already_completed = False
    
    if match:
        # Idempotency check: if score is identical, skip running pipeline
        if match.status == "completed" and match.home_score == payload.home_score and match.away_score == payload.away_score:
            is_already_completed = True
        else:
            match.status = "completed"
            match.home_score = payload.home_score
            match.away_score = payload.away_score
            
            # 2. Score predictions for this match
            predictions = db.query(UserPrediction).filter(UserPrediction.match_id == match.id).all()
            for pred in predictions:
                # Exact score = 3 pts
                if pred.predicted_home_score == payload.home_score and pred.predicted_away_score == payload.away_score:
                    pred.points_earned = 3
                # Correct outcome = 1 pt
                elif (
                    (pred.predicted_home_score > pred.predicted_away_score and payload.home_score > payload.away_score) or
                    (pred.predicted_home_score < pred.predicted_away_score and payload.home_score < payload.away_score) or
                    (pred.predicted_home_score == pred.predicted_away_score and payload.home_score == payload.away_score)
                ):
                    pred.points_earned = 1
                else:
                    pred.points_earned = 0
            db.commit()
    else:
        # If match not in pre-populated list, we can create one as completed
        match = Match(
            home_team=payload.home_team,
            away_team=payload.away_team,
            home_score=payload.home_score,
            away_score=payload.away_score,
            stage=payload.stage,
            status="completed"
        )
        db.add(match)
        db.commit()
        
    if is_already_completed:
        return {
            "status": "already_processed",
            "message": f"Match result for {payload.home_team} vs {payload.away_team} ({payload.home_score}-{payload.away_score}) has already been ingested."
        }
        
    # Trigger trigger_adaptive_update in a background task or Celery queue
    if USE_CELERY:
        task = run_adaptive_pipeline_task.delay(
            payload.home_team,
            payload.away_team,
            payload.home_score,
            payload.away_score,
            payload.stage
        )
        return {
            "status": "update_queued",
            "task_id": task.id,
            "message": f"Adaptive learning and tournament re-simulation triggered in Celery queue (Task: {task.id}) for {payload.home_team} vs {payload.away_team}."
        }
    else:
        background_tasks.add_task(
            run_pipeline_in_background,
            payload.home_team,
            payload.away_team,
            payload.home_score,
            payload.away_score,
            payload.stage
        )
        return {
            "status": "update_queued",
            "message": f"Adaptive learning and tournament re-simulation triggered in the background for {payload.home_team} vs {payload.away_team}."
        }

@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Retrieve the status and last completion time of the adaptive pipeline."""
    return PIPELINE_STATUS

@app.get("/api/latest_shift")
async def get_latest_shift():
    """Safe retrieval of the latest tournament shift narrative to avoid frontend 404 errors."""
    file_path = FRONTEND_DATA_DIR / "latest_shift.json"
    if not file_path.exists():
        return {
            "shift_narrative": "No matches have been ingested yet. All 72 group stage matches are currently simulated baselines. Use the Live Ingestion Control panel below to ingest actual scores and see real-time probability shifts!"
        }
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"shift_narrative": f"Error loading narrative: {str(e)}"}

@app.post("/api/reset")
async def reset_database(db: Session = Depends(get_db)):
    """Resets all matches back to 'scheduled' with null scores, and deletes custom ELO narratives."""
    try:
        # Reset matches status and scores
        db.query(Match).update({
            Match.home_score: None,
            Match.away_score: None,
            Match.status: "scheduled",
            Match.kickoff_utc: None
        })
        db.commit()
        
        # Remove latest_shift.json to clear the narrative shift
        file_path = FRONTEND_DATA_DIR / "latest_shift.json"
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Error removing latest_shift.json: {e}")
                
        # Reset pipeline status
        global PIPELINE_STATUS
        PIPELINE_STATUS = {"status": "idle", "last_run_time": None, "error": None}
        
        return {"message": "Database and simulation states reset successfully to pre-tournament baseline."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {str(e)}")


@app.get("/api/live")
async def get_live_match(db: Session = Depends(get_db)):
    """
    Returns the current live match in the database, 
    or a mock live match (Morocco vs Portugal 1-1, 63') as a fallback.
    """
    live_match = db.query(Match).filter(Match.status == "LIVE").first()
    if live_match:
        try:
            pred_data = load_sanitized_json("predictions.json")
            preds = pred_data.get("predictions", [])
            h2h_pred = next((p for p in preds if p["home_team"].lower() == live_match.home_team.lower() and p["away_team"].lower() == live_match.away_team.lower()), None)
            probs = {
                "home_win_prob": h2h_pred.get("home_win_prob") if h2h_pred else 0.38,
                "draw_prob": h2h_pred.get("draw_prob") if h2h_pred else 0.28,
                "away_win_prob": h2h_pred.get("away_win_prob") if h2h_pred else 0.34
            }
        except Exception:
            probs = {"home_win_prob": 0.38, "draw_prob": 0.28, "away_win_prob": 0.34}
            
        return {
            "id": live_match.id,
            "home_team": live_match.home_team,
            "away_team": live_match.away_team,
            "home_score": live_match.home_score if live_match.home_score is not None else 0,
            "away_score": live_match.away_score if live_match.away_score is not None else 0,
            "minute": 74,
            "status": "LIVE",
            "possession_home": 52,
            "possession_away": 48,
            "stage": live_match.stage,
            "kickoff_utc": live_match.kickoff_utc,
            **probs
        }
    
    return {
        "id": 9999,
        "home_team": "Morocco",
        "away_team": "Portugal",
        "home_score": 1,
        "away_score": 1,
        "minute": 63,
        "status": "LIVE",
        "possession_home": 54,
        "possession_away": 46,
        "stage": "Quarter-Finals",
        "kickoff_utc": "2026-06-09T14:00:00Z",
        "home_win_prob": 0.35,
        "draw_prob": 0.30,
        "away_win_prob": 0.35
    }

@app.get("/api/fixtures")
async def get_fixtures(date: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns all match fixtures. If a date is provided, filters matches for that date.
    """
    query = db.query(Match)
    if date:
        query = query.filter(Match.date == date)
    matches = query.order_by(Match.id).all()
    
    result = []
    try:
        pred_data = load_sanitized_json("predictions.json")
        preds = pred_data.get("predictions", [])
        pred_map = {(p["home_team"].lower(), p["away_team"].lower()): p for p in preds}
    except Exception:
        pred_map = {}
        
    for m in matches:
        p_data = pred_map.get((m.home_team.lower(), m.away_team.lower()))
        result.append({
            "id": m.id,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "stage": m.stage,
            "status": m.status,
            "date": m.date,
            "kickoff_utc": m.kickoff_utc,
            "home_win_prob": p_data.get("home_win_prob") if p_data else 0.33,
            "draw_prob": p_data.get("draw_prob") if p_data else 0.33,
            "away_win_prob": p_data.get("away_win_prob") if p_data else 0.34
        })
    return result

@app.get("/api/players/featured")
async def get_featured_players():
    """
    Returns 3 featured players by sorting the top 50 players by impact score, ensuring Hakimi is in.
    """
    try:
        players_data = load_sanitized_json("players.json")
        top50 = players_data.get("top50", [])
        sorted_players = sorted(top50, key=lambda x: x.get("impact_score", 0.0), reverse=True)
        featured = []
        hakimi = next((p for p in sorted_players if "hakimi" in p["player_name"].lower()), None)
        if hakimi:
            featured.append(hakimi)
            
        for p in sorted_players:
            if p not in featured:
                featured.append(p)
            if len(featured) == 3:
                break
        return featured
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load featured players: {str(e)}")

@app.get("/api/squads/{team_name}")
async def get_squad_by_team(team_name: str):
    """
    Parses wc2026_player_squad.csv, resolves positions dynamically,
    calculates dynamic impact score, and selects a projected starting XI.
    """
    csv_path = ROOT / "Dataset" / "wc2026_player_squad.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="wc2026_player_squad.csv squad dataset not found.")
        
    squad = []
    try:
        raw_players = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["team"].lower() == team_name.lower():
                    raw_players.append(row)
                    
        if not raw_players:
            raise HTTPException(status_code=404, detail=f"No squad data found for team: {team_name}")
            
        gks_list = [
            "martínez", "martinez", "bono", "bounou", "costa", "maignan", "pickford", "simon", "raya", "casteels", 
            "ter stegen", "neuer", "livaković", "livakovic", "vargas", "turner", "onana", "pentz", "viscarra",
            "ederson", "alisson", "oblak", "szczęsny", "szczesny", "sommer", "kobel", "donnarumma", "vicario",
            "meret", "flekken", "verbruggen", "bijlow", "patrício", "patricio", "sa", "lloris", "areola", "samba",
            "ramsdale", "henderson", "olsen", "hermansen", "schmeichel", "gulácsi", "gulacsi", "dibusz", "strakosha",
            "berisha", "kastrati", "stankovic", "belec", "gunn", "clark", "mccrorie", "dubravka", "rodak",
            "ravalico", "krejci", "stanek", "kovar", "jaros", "pentz", "lindner", "hedl", "valese", "gallese",
            "crépeau", "crepeau", "clair", "niță", "nita", "târnovanu", "tarnovanu", "moldovan", "rochet",
            "mele", "israel", "cáceda", "caceda", "romero", "malagón", "malagon", "gonzález", "gonzalez",
            "padilla", "mvogo", "kahric", "mejía", "mejia", "mosquera", "stanković", "allison", "oblen", "horvath"
        ]
        
        processed_players = []
        for row in raw_players:
            goals = float(row.get("goals_p90") or 0.0)
            xg = float(row.get("xg_p90") or 0.0)
            key_passes = float(row.get("key_passes_p90") or 0.0)
            interceptions = float(row.get("interceptions_p90") or 0.0)
            prog_carries = float(row.get("prog_carries_p90") or 0.0)
            pass_acc = float(row.get("pass_accuracy") or 0.0)
            mv = float(row.get("market_value_M_proxy") or 5.0)
            age = int(float(row["age_2026"])) if row.get("age_2026") else 26
            
            player_name = row["player_name"]
            
            raw_impact = 40.0 + (mv * 1.2) + (goals * 15.0) + (key_passes * 8.0) + (interceptions * 10.0)
            impact = min(99.9, max(30.0, raw_impact))
            
            processed_players.append({
                "player_name": player_name,
                "team": row["team"],
                "impact_score": round(impact, 1),
                "xg_p90": round(xg, 4),
                "goals_p90": round(goals, 4),
                "key_passes_p90": round(key_passes, 4),
                "interceptions_p90": round(interceptions, 4),
                "prog_carries_p90": round(prog_carries, 4),
                "pass_accuracy": round(pass_acc, 4),
                "market_value_m": mv,
                "age": age,
                "injury_status": row.get("injury_status") or "Available",
                "injury_notes": row.get("injury_notes") or ""
            })
            
        gks = []
        for p in processed_players:
            name_lower = p["player_name"].lower()
            if any(gk in name_lower for gk in gks_list):
                gks.append(p)
                
        if not gks:
            sorted_by_outfield = sorted(processed_players, key=lambda x: x["interceptions_p90"] + x["goals_p90"] + x["key_passes_p90"] + x["prog_carries_p90"])
            gks.append(sorted_by_outfield[0])
            
        gk_names = {p["player_name"] for p in gks}
        outfield_players = [p for p in processed_players if p["player_name"] not in gk_names]
        
        outfield_players.sort(key=lambda x: x["interceptions_p90"], reverse=True)
        defs = outfield_players[:6]
        def_names = {p["player_name"] for p in defs}
        
        remaining_outfield = [p for p in outfield_players if p["player_name"] not in def_names]
        remaining_outfield.sort(key=lambda x: x["goals_p90"] + x["xg_p90"], reverse=True)
        fwds = remaining_outfield[:5]
        fwd_names = {p["player_name"] for p in fwds}
        
        for p in processed_players:
            if p["player_name"] in gk_names:
                p["position"] = "GK"
            elif p["player_name"] in def_names:
                p["position"] = "DEF"
            elif p["player_name"] in fwd_names:
                p["position"] = "FWD"
            else:
                p["position"] = "MID"
                
        squad = processed_players
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse squad file: {str(e)}")
        
    if not squad:
        raise HTTPException(status_code=404, detail=f"No squad data found for team: {team_name}")
        
    try:
        players_data = load_sanitized_json("players.json")
        top50 = players_data.get("top50", [])
        top50_map = {p["player_name"].lower(): p["impact_score"] for p in top50}
        for p in squad:
            name_lower = p["player_name"].lower()
            if name_lower in top50_map:
                p["impact_score"] = top50_map[name_lower]
    except Exception:
        pass
        
    squad.sort(key=lambda x: x["impact_score"], reverse=True)
    
    gks = [p for p in squad if p["position"] == "GK"]
    defs = [p for p in squad if p["position"] == "DEF"]
    mids = [p for p in squad if p["position"] == "MID"]
    fwds = [p for p in squad if p["position"] == "FWD"]
    
    projected_xi = []
    if gks:
        projected_xi.append(gks[0])
    projected_xi.extend(defs[:4])
    projected_xi.extend(mids[:3])
    projected_xi.extend(fwds[:3])
    
    if len(projected_xi) < 11:
        num_gk_needed = 1 - len([p for p in projected_xi if p["position"] == "GK"])
        num_def_needed = 4 - len([p for p in projected_xi if p["position"] == "DEF"])
        num_mid_needed = 3 - len([p for p in projected_xi if p["position"] == "MID"])
        num_fwd_needed = 3 - len([p for p in projected_xi if p["position"] == "FWD"])
        
        remaining_squad = [p for p in squad if p not in projected_xi]
        for p in remaining_squad:
            if len(projected_xi) == 11:
                break
            p_copy = dict(p)
            if num_gk_needed > 0:
                p_copy["position"] = "GK"
                num_gk_needed -= 1
            elif num_def_needed > 0:
                p_copy["position"] = "DEF"
                num_def_needed -= 1
            elif num_mid_needed > 0:
                p_copy["position"] = "MID"
                num_mid_needed -= 1
            elif num_fwd_needed > 0:
                p_copy["position"] = "FWD"
                num_fwd_needed -= 1
            projected_xi.append(p_copy)
            
    return {
        "team": team_name,
        "squad": squad,
        "projected_xi": projected_xi
    }

# ============================================================================
# 3. USER AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    db_email = crud.get_user_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered.")
    db_username = crud.get_user_by_username(db, username=user.username)
    if db_username:
        raise HTTPException(status_code=400, detail="Username already taken.")
    return crud.create_user(db=db, user=user)

@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Aquire OAuth2 token for user authentication."""
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Generate secure HTTP-only refresh token
    refresh_token = secrets.token_urlsafe(32)
    crud.create_db_refresh_token(db, token=refresh_token, user_id=user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 3600, # 7 days
        expires=7 * 24 * 3600,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/refresh")
def refresh_access_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing.")
        
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    db_token = crud.get_refresh_token_by_hash(db, token_hash=token_hash)
    
    if not db_token or db_token.revoked or db_token.expires_at < datetime.datetime.utcnow():
        if db_token:
            crud.revoke_all_user_refresh_tokens(db, user_id=db_token.user_id)
        raise HTTPException(status_code=401, detail="Invalid, expired or revoked refresh token.")
        
    user = crud.get_user(db, user_id=db_token.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    # Rotate refresh token: revoke old one, generate new one
    db_token.revoked = True
    db.commit()
    
    new_refresh_token = secrets.token_urlsafe(32)
    crud.create_db_refresh_token(db, token=new_refresh_token, user_id=user.id)
    
    new_access_token = auth.create_access_token(data={"sub": user.username})
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=7 * 24 * 3600,
        expires=7 * 24 * 3600,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "username": user.username
    }


@app.post("/api/auth/logout")
def logout_user(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        crud.revoke_refresh_token(db, token=refresh_token)
    response.delete_cookie(
        "refresh_token",
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return {"status": "success", "message": "Successfully logged out."}


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_user_me(current_user: User = Depends(auth.get_current_user)):
    """Fetch current user profile data."""
    return current_user


# ============================================================================
# 4. FAN PREDICTIONS & LEADERBOARD ENDPOINTS
# ============================================================================

@app.post("/api/predictions/submit", response_model=schemas.UserPredictionResponse)
def submit_prediction(
    prediction: schemas.UserPredictionCreate,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Submit or edit a user's match score forecast."""
    return crud.create_user_prediction(db=db, prediction=prediction, user_id=current_user.id)

@app.get("/api/predictions/my", response_model=List[schemas.UserPredictionResponse])
def get_my_predictions(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all match forecasts submitted by the active user."""
    return crud.get_user_predictions(db=db, user_id=current_user.id)

@app.get("/api/competition/leaderboard", response_model=List[schemas.LeaderboardRow])
def get_leaderboard(db: Session = Depends(get_db)):
    """Fetch the global prediction competition leaderboard rankings."""
    return crud.get_global_leaderboard(db=db)

@app.get("/api/matches", response_model=List[schemas.MatchResponse])
def get_db_matches(db: Session = Depends(get_db)):
    """Retrieve all match fixtures from the database ordered by fixture ID."""
    return db.query(Match).order_by(Match.id).all()

class WhatIfPayload(BaseModel):
    team: str
    strength_drop_pct: float
    player_name: Optional[str] = None

@app.get("/api/tracker/bracket")
async def get_bracket_probabilities():
    """Retrieve advancement probabilities for all slots in the knockout bracket."""
    return load_sanitized_json("bracket.json")

@app.get("/api/tracker/qualification")
async def get_qualification_probabilities():
    """Retrieve group qualification probabilities for each team."""
    return load_sanitized_json("qualification.json")

@app.post("/api/simulate/whatif")
async def simulate_whatif(payload: WhatIfPayload):
    """
    Run a fast 1,000 Monte Carlo simulation run after adjusting a team's strength 
    due to an injury or scenario, returning the before-and-after probabilities.
    """
    try:
        # Load baseline simulations
        base_sim = load_sanitized_json("simulations.json")
        base_results = base_sim.get("results", [])
        
        # Load predictions and standings
        predictions_data = load_sanitized_json("predictions.json")
        fixtures_list = predictions_data.get("predictions", [])
        
        # Load team ELOs
        players_data = load_sanitized_json("players.json")
        team_strengths = players_data.get("team_strength", [])
        team_elos = {t["team"]: (t["current_elo"] or 1600.0) for t in team_strengths}
        
        # Reconstruct groups
        groups = {}
        standings_data = load_sanitized_json("group_standings.json")
        for group_name, teams in standings_data.items():
            groups[group_name.replace("Group ", "")] = [t["Team"] for t in teams]
            
        all_teams = []
        for g_teams in groups.values():
            all_teams.extend(g_teams)
        all_teams = sorted(list(set(all_teams)))
        
        # Build fixture probs lookup and adjust them for the injured team
        fixture_probs_lookup = {}
        adj_factor = 1.0 - (payload.strength_drop_pct / 100.0)
        adj_factor = max(0.5, min(1.0, adj_factor))
        
        for pred in fixtures_list:
            home = pred["home_team"]
            away = pred["away_team"]
            p_away = pred.get("ensemble_away_win") or pred.get("away_win_prob") or 0.33
            p_draw = pred.get("ensemble_draw") or pred.get("draw_prob") or 0.33
            p_home = pred.get("ensemble_home_win") or pred.get("home_win_prob") or 0.33
            
            # If home is the injured team, reduce home win probability
            if home.lower() == payload.team.lower():
                diff = p_home * (1.0 - adj_factor)
                p_home = p_home * adj_factor
                p_away = p_away + diff * 0.7
                p_draw = p_draw + diff * 0.3
            # If away is the injured team, reduce away win probability
            elif away.lower() == payload.team.lower():
                diff = p_away * (1.0 - adj_factor)
                p_away = p_away * adj_factor
                p_home = p_home + diff * 0.7
                p_draw = p_draw + diff * 0.3
                
            # Normalize probabilities
            tot = p_home + p_draw + p_away
            if tot > 0:
                p_home /= tot
                p_draw /= tot
                p_away /= tot
                
            fixture_probs_lookup[(home, away)] = [p_away, p_draw, p_home]
            
        # Reconstruct ELOs, adjust for injured team
        if payload.team in team_elos:
            team_elos[payload.team] *= adj_factor
            
        # Run 1,000 simulations
        from src.simulation.monte_carlo import ATLASMonteCarloSimulator
        simulator = ATLASMonteCarloSimulator(groups, fixture_probs_lookup, team_elos, all_teams)
        df_sim = simulator.run_simulations(n_simulations=1000, show_progress=False)
        
        # Format results
        results_list = df_sim.to_dict('records')
        
        # Compare before and after for the target team
        base_target = next((t for t in base_results if t["Team"].lower() == payload.team.lower()), None)
        new_target = next((t for t in results_list if t["Team"].lower() == payload.team.lower()), None)
        
        comparison = {}
        if base_target and new_target:
            before_r16 = base_target.get("Round of 16 %", 0.0)
            after_r16 = new_target.get("Round of 16 %", 0.0)
            before_champ = base_target.get("Champion %", 0.0)
            after_champ = new_target.get("Champion %", 0.0)
            
            player = payload.player_name or "Key player"
            narrative = (
                f"{player}'s absence reduces {payload.team}'s squad strength by {payload.strength_drop_pct:.1f}%. "
                f"As a result, their probability of reaching the Round of 16 drops from {before_r16:.1f}% to {after_r16:.1f}%, "
                f"and their overall title chances fall from {before_champ:.1f}% to {after_champ:.1f}%."
            )
            
            comparison = {
                "team": payload.team,
                "strength_drop_pct": payload.strength_drop_pct,
                "player_name": payload.player_name,
                "before": {
                    "champion": before_champ,
                    "finalist": base_target.get("Finalist %", 0.0),
                    "semi_final": base_target.get("Semi-Final %", 0.0),
                    "quarter_final": base_target.get("Quarter-Final %", 0.0),
                    "r16": before_r16
                },
                "after": {
                    "champion": after_champ,
                    "finalist": new_target.get("Finalist %", 0.0),
                    "semi_final": new_target.get("Semi-Final %", 0.0),
                    "quarter_final": new_target.get("Quarter-Final %", 0.0),
                    "r16": after_r16
                },
                "narrative": narrative
            }
            
        return {
            "status": "success",
            "comparison": comparison,
            "results": results_list[:12]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")
