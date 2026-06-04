import numpy as np
import pandas as pd

# Core features available for all historical match tiers
CORE_FEATURES = [
    'elo_diff', 'elo_win_prob', 'form_diff',
    'is_knockout', 'stage_numeric',
    'is_home', 'is_host', 'opp_is_host', 'neutral_venue',
    'same_confederation',
    'wc_appearances', 'opp_wc_appearances',
    'wc_wins', 'opp_wc_wins',
    'wc_finals', 'opp_wc_finals',
    'wc_semis', 'opp_wc_semis',
    'wc_avg_goals',
    'h2h_winrate', 'h2h_matches',
    'form_5', 'opp_form_5',
    'goals_scored_form5', 'goals_conceded_form5', 'opp_goals_scored_form5',
    'rest_days', 'opp_rest_days', 'rest_days_adv',
    'tournament_match_num',
]

# Advanced stats available only for 2018+2022 World Cup matches (tier2)
ADVANCED_FEATURES = [
    'tourn_matches_played', 'tourn_goals_for', 'tourn_goals_against',
    'tourn_goal_diff', 'tourn_wins', 'tourn_winrate', 'tourn_goals_per_match',
]

# Squad metrics available for recent squads and World Cup 2026 squads
SQUAD_FEATURES = [
    'squad_xg_per_match', 'squad_goals_per_match', 'squad_shots_per_match',
    'squad_key_passes_per_match', 'squad_interceptions_per_match',
    'squad_dribbles_per_match', 'squad_squad_pass_accuracy',
    'opp_squad_xg_per_match', 'opp_squad_goals_per_match', 'opp_squad_shots_per_match',
    'opp_squad_key_passes_per_match', 'opp_squad_interceptions_per_match',
    'opp_squad_dribbles_per_match', 'opp_squad_squad_pass_accuracy',
]

# Demographic profiles
DEMO_FEATURES = [
    'squad_avg_age', 'opp_squad_avg_age', 'age_diff',
    'avg_club_prestige', 'max_club_prestige',
    'opp_avg_club_prestige', 'opp_max_club_prestige',
    'club_prestige_diff',
]

# Confederation codes
CONF_FEATURES = ['team_conf_code', 'opp_conf_code']

# Interaction features engineered from individual base features
INTERACTION_FEATURES = [
    'elo_x_knockout', 'form_x_stage', 'elo_x_host',
    'squad_quality_diff', 'experience_diff', 'pedigree_diff'
]

# Candidate base features
ALL_CANDIDATE_FEATURES = CORE_FEATURES + ADVANCED_FEATURES + SQUAD_FEATURES + DEMO_FEATURES + CONF_FEATURES

# Consolidated final features list used for modeling
FINAL_FEATURES = ALL_CANDIDATE_FEATURES + INTERACTION_FEATURES

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer interaction and differential features on top of a loaded DataFrame."""
    df_engineered = df.copy()
    
    # Elo × Knockout stage interaction
    if 'elo_diff' in df_engineered.columns and 'is_knockout' in df_engineered.columns:
        df_engineered['elo_x_knockout'] = df_engineered['elo_diff'] * df_engineered['is_knockout']
    else:
        df_engineered['elo_x_knockout'] = 0.0
        
    # Form × Stage progression interaction
    if 'form_diff' in df_engineered.columns and 'stage_numeric' in df_engineered.columns:
        df_engineered['form_x_stage'] = df_engineered['form_diff'] * df_engineered['stage_numeric']
    else:
        df_engineered['form_x_stage'] = 0.0
        
    # Elo × Host nation advantage interaction
    if 'elo_diff' in df_engineered.columns and 'is_host' in df_engineered.columns:
        df_engineered['elo_x_host'] = df_engineered['elo_diff'] * df_engineered['is_host']
    else:
        df_engineered['elo_x_host'] = 0.0
        
    # Squad quality difference
    squad_xg = df_engineered.get('squad_xg_per_match', 0.0)
    opp_squad_xg = df_engineered.get('opp_squad_xg_per_match', 0.0)
    df_engineered['squad_quality_diff'] = squad_xg - opp_squad_xg
    
    # World Cup experience differential
    wc_app = df_engineered.get('wc_appearances', 0.0)
    opp_wc_app = df_engineered.get('opp_wc_appearances', 0.0)
    df_engineered['experience_diff'] = wc_app - opp_wc_app
    
    # World Cup historical pedigree (titles) differential
    wc_wins = df_engineered.get('wc_wins', 0.0)
    opp_wc_wins = df_engineered.get('opp_wc_wins', 0.0)
    df_engineered['pedigree_diff'] = wc_wins - opp_wc_wins
    
    # Ensure all interaction features are numeric and NaNs are filled with 0.0
    for col in INTERACTION_FEATURES:
        if col in df_engineered.columns:
            df_engineered[col] = df_engineered[col].fillna(0.0)
            
    # Clean column matching
    for col in ALL_CANDIDATE_FEATURES:
        if col not in df_engineered.columns:
            df_engineered[col] = 0.0
            
    return df_engineered
