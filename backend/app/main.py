import os
import json
import sys
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta
from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks, status
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

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TournAI × ATLAS REST Backend",
    description="Live prediction, tournament simulation, and adaptive learning API",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
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
    
    if match:
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
        
    # Trigger trigger_adaptive_update in a background task or Celery queue
    if USE_CELERY:
        run_adaptive_pipeline_task.delay(
            payload.home_team,
            payload.away_team,
            payload.home_score,
            payload.away_score,
            payload.stage
        )
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
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    return {"access_token": access_token, "token_type": "bearer"}

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
