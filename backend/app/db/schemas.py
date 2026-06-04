from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Match Schemas
class MatchBase(BaseModel):
    home_team: str
    away_team: str
    stage: str = "Group Stage"
    date: Optional[str] = None

class MatchCreate(MatchBase):
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "scheduled"

class MatchResponse(MatchBase):
    id: int
    home_score: Optional[int]
    away_score: Optional[int]
    status: str

    class Config:
        from_attributes = True

# User Prediction Schemas
class UserPredictionBase(BaseModel):
    match_id: int
    predicted_home_score: int
    predicted_away_score: int

class UserPredictionCreate(UserPredictionBase):
    pass

class UserPredictionResponse(UserPredictionBase):
    id: int
    user_id: int
    points_earned: int

    class Config:
        from_attributes = True

# Leaderboard Schemas
class LeaderboardRow(BaseModel):
    username: str
    total_predictions: int
    total_points: int
