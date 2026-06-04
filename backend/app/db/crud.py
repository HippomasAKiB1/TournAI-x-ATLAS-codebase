from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import User, Match, UserPrediction
from .schemas import UserCreate, MatchCreate, UserPredictionCreate
from .auth import get_password_hash

# User CRUD
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    hashed_pwd = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Match CRUD
def get_match(db: Session, match_id: int):
    return db.query(Match).filter(Match.id == match_id).first()

def get_matches(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Match).offset(skip).limit(limit).all()

def create_match(db: Session, match: MatchCreate):
    db_match = Match(
        home_team=match.home_team,
        away_team=match.away_team,
        home_score=match.home_score,
        away_score=match.away_score,
        stage=match.stage,
        status=match.status,
        date=match.date
    )
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

# User Prediction CRUD
def create_user_prediction(db: Session, prediction: UserPredictionCreate, user_id: int):
    # Check if user already predicted this match, if so update it
    existing = db.query(UserPrediction).filter(
        UserPrediction.user_id == user_id,
        UserPrediction.match_id == prediction.match_id
    ).first()
    
    if existing:
        existing.predicted_home_score = prediction.predicted_home_score
        existing.predicted_away_score = prediction.predicted_away_score
        db.commit()
        db.refresh(existing)
        return existing
        
    db_pred = UserPrediction(
        user_id=user_id,
        match_id=prediction.match_id,
        predicted_home_score=prediction.predicted_home_score,
        predicted_away_score=prediction.predicted_away_score
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)
    return db_pred

def get_user_predictions(db: Session, user_id: int):
    return db.query(UserPrediction).filter(UserPrediction.user_id == user_id).all()

def get_global_leaderboard(db: Session, limit: int = 100):
    """Calculate the global prediction competition leaderboard ranked by points earned."""
    results = db.query(
        User.username,
        func.count(UserPrediction.id).label("total_predictions"),
        func.sum(UserPrediction.points_earned).label("total_points")
    ).join(
        UserPrediction, User.id == UserPrediction.user_id, isouter=True
    ).group_by(
        User.id
    ).order_by(
        func.sum(UserPrediction.points_earned).desc(),
        func.count(UserPrediction.id).desc()
    ).limit(limit).all()
    
    return [
        {
            "username": r[0],
            "total_predictions": r[1],
            "total_points": r[2] if r[2] is not None else 0
        }
        for r in results
    ]
