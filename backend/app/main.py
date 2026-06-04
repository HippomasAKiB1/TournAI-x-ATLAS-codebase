import os
import json
import sys
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

# ============================================================================
# 1. CORE ATLAS ML DATA ENDPOINTS
# ============================================================================

@app.get("/api/predictions")
async def get_predictions():
    return load_sanitized_json("predictions.json")

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
    avg_away = away_str.get("avg_impact") or 50.0
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
        "confidence": max(home_win_prob, away_win_prob, draw_prob_final),
        "elo_diff": elo_diff,
        "reasons": [squad_quality_narrative, elo_diff_narrative, form_narrative]
    }

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
            trigger_adaptive_update,
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
