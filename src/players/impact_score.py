import pandas as pd
import numpy as np

def calculate_player_impact_scores(df_players_squad: pd.DataFrame) -> pd.DataFrame:
    """Calculate the composite Player Impact Score (0-100) for all squad players."""
    df_ps = df_players_squad.copy()
    
    # Advanced stats used for rating
    impact_weights = {
        'xg_p90': 0.20,
        'goals_p90': 0.15,
        'key_passes_p90': 0.15,
        'interceptions_p90': 0.10,
        'prog_carries_p90': 0.10,
        'pass_accuracy': 0.10,
        'dribble_success': 0.05,
        'recent_minutes': 0.15,
    }
    
    # Convert parameters to numeric and fill missing values with 0
    for col in impact_weights:
        if col in df_ps.columns:
            df_ps[col] = pd.to_numeric(df_ps[col], errors='coerce').fillna(0.0)
            
    # Normalize each feature to a 0-100 scale
    normalized = pd.DataFrame()
    for col, weight in impact_weights.items():
        if col in df_ps.columns:
            vals = df_ps[col]
            min_val = vals.min()
            max_val = vals.max()
            if max_val > min_val:
                normalized[col] = (vals - min_val) / (max_val - min_val) * 100.0
            else:
                normalized[col] = 50.0  # default fallback
                
    # Calculate weighted impact score
    df_ps['impact_score'] = 0.0
    for col, weight in impact_weights.items():
        if col in normalized.columns:
            df_ps['impact_score'] += normalized[col] * weight
            
    # Scale final score to exactly 0-100 range
    max_score = df_ps['impact_score'].max()
    if max_score > 0:
        df_ps['impact_score'] = (df_ps['impact_score'] / max_score * 100.0).round(1)
        
    return df_ps
