import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from ..data.loader import load_train_ready_data, DEFAULT_DATA_DIR
from ..data.preprocessor import ATLASPreprocessor
from ..models.feature_engineering import engineer_features, FINAL_FEATURES
from ..models.trainer import ATLASModelTrainer

ROOT = Path(__file__).resolve().parents[2]
MOD_DIR = ROOT / "output" / "models"
TRAIN_DATA_PATH = DEFAULT_DATA_DIR / "atlas_train_ready_final.csv"
FIXTURES_FEATS_PATH = DEFAULT_DATA_DIR / "wc2026_fixture_features.csv"

def append_match_to_training_set(
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    stage: str = "Group Stage"
):
    """
    Look up the fixture features from wc2026_fixture_features.csv and append 
    two rows (home and away perspectives) to the training dataset.
    """
    df_train = pd.read_csv(TRAIN_DATA_PATH)
    df_fixtures = pd.read_csv(FIXTURES_FEATS_PATH)
    
    # Try to find the pre-computed fixture row
    fixture_row = df_fixtures[
        (df_fixtures['home_team'].str.lower() == home_team.lower()) &
        (df_fixtures['away_team'].str.lower() == away_team.lower())
    ]
    
    if len(fixture_row) == 0:
        # Fallback search regardless of home/away ordering
        fixture_row = df_fixtures[
            ((df_fixtures['home_team'].str.lower() == home_team.lower()) & (df_fixtures['away_team'].str.lower() == away_team.lower())) |
            ((df_fixtures['home_team'].str.lower() == away_team.lower()) & (df_fixtures['away_team'].str.lower() == home_team.lower()))
        ]
        
    if len(fixture_row) == 0:
        raise ValueError(f"No fixture found in wc2026_fixture_features.csv for {home_team} vs {away_team}")
        
    feat = fixture_row.iloc[0]
    next_match_id = int(df_train['match_id'].max() + 1)
    
    # 1. Home perspective row
    home_result = 'Win' if home_score > away_score else 'Loss' if home_score < away_score else 'Draw'
    home_result_code = 2 if home_score > away_score else 0 if home_score < away_score else 1
    
    row_home = {
        'match_id': next_match_id,
        'year': 2026,
        'stage': stage,
        'stage_numeric': 1 if stage == "Group Stage" else 2,
        'is_knockout': 0 if stage == "Group Stage" else 1,
        'date': feat.get('date', '2026-06-12'),
        'venue': feat.get('city', 'Host Venue'),
        'team': home_team,
        'opponent': away_team,
        'is_home': 1,
        'team_confederation': 'UEFA', # fallback
        'opp_confederation': 'UEFA', # fallback
        'same_confederation': 0,
        'is_host': int(feat.get('home_host_nation', 0)),
        'opp_is_host': int(feat.get('away_host_nation', 0)),
        'neutral_venue': 1 if int(feat.get('home_host_nation', 0)) == 0 and int(feat.get('away_host_nation', 0)) == 0 else 0,
        'team_elo': float(feat.get('home_current_elo', 1500.0)),
        'opp_elo': float(feat.get('away_current_elo', 1500.0)),
        'elo_diff': float(feat.get('elo_diff', 0.0)),
        'elo_win_prob': float(feat.get('home_elo_win_prob', 0.5)),
        'form_5': float(feat.get('home_form_10', 0.5)),
        'opp_form_5': float(feat.get('away_form_10', 0.5)),
        'form_diff': float(feat.get('form_diff', 0.0)),
        'goals_scored_form5': float(feat.get('home_goals_scored_form10', 1.0)) / 2.0,
        'goals_conceded_form5': float(feat.get('home_goals_conceded_form10', 1.0)) / 2.0,
        'opp_goals_scored_form5': float(feat.get('away_goals_scored_form10', 1.0)) / 2.0,
        'wc_appearances': float(feat.get('home_wc_appearances', 0)),
        'opp_wc_appearances': float(feat.get('away_wc_appearances', 0)),
        'wc_wins': float(feat.get('home_wc_wins', 0)),
        'opp_wc_wins': float(feat.get('away_wc_wins', 0)),
        'wc_finals': float(feat.get('home_wc_finals', 0)),
        'opp_wc_finals': float(feat.get('away_wc_finals', 0)),
        'wc_semis': float(feat.get('home_wc_semis', 0)),
        'opp_wc_semis': float(feat.get('away_wc_semis', 0)),
        'wc_avg_goals': 0.0,
        'h2h_winrate': 0.5,
        'h2h_matches': 0,
        'rest_days': 4.0,
        'opp_rest_days': 4.0,
        'rest_days_adv': 0.0,
        'tournament_match_num': int(feat.get('fixture_id', 1)),
        'goals_scored': home_score,
        'goals_conceded': away_score,
        'goal_diff': home_score - away_score,
        'result': home_result,
        'result_code': home_result_code,
        'split': 'train',
        'data_tier': 'tier2'
    }
    
    # 2. Away perspective row
    away_result = 'Win' if away_score > home_score else 'Loss' if away_score < home_score else 'Draw'
    away_result_code = 2 if away_score > home_score else 0 if away_score < home_score else 1
    
    row_away = {
        'match_id': next_match_id,
        'year': 2026,
        'stage': stage,
        'stage_numeric': 1 if stage == "Group Stage" else 2,
        'is_knockout': 0 if stage == "Group Stage" else 1,
        'date': feat.get('date', '2026-06-12'),
        'venue': feat.get('city', 'Host Venue'),
        'team': away_team,
        'opponent': home_team,
        'is_home': 0,
        'team_confederation': 'UEFA',
        'opp_confederation': 'UEFA',
        'same_confederation': 0,
        'is_host': int(feat.get('away_host_nation', 0)),
        'opp_is_host': int(feat.get('home_host_nation', 0)),
        'neutral_venue': 1 if int(feat.get('home_host_nation', 0)) == 0 and int(feat.get('away_host_nation', 0)) == 0 else 0,
        'team_elo': float(feat.get('away_current_elo', 1500.0)),
        'opp_elo': float(feat.get('home_current_elo', 1500.0)),
        'elo_diff': -float(feat.get('elo_diff', 0.0)),
        'elo_win_prob': 1.0 - float(feat.get('home_elo_win_prob', 0.5)),
        'form_5': float(feat.get('away_form_10', 0.5)),
        'opp_form_5': float(feat.get('home_form_10', 0.5)),
        'form_diff': -float(feat.get('form_diff', 0.0)),
        'goals_scored_form5': float(feat.get('away_goals_scored_form10', 1.0)) / 2.0,
        'goals_conceded_form5': float(feat.get('away_goals_conceded_form10', 1.0)) / 2.0,
        'opp_goals_scored_form5': float(feat.get('home_goals_scored_form10', 1.0)) / 2.0,
        'wc_appearances': float(feat.get('away_wc_appearances', 0)),
        'opp_wc_appearances': float(feat.get('home_wc_appearances', 0)),
        'wc_wins': float(feat.get('away_wc_wins', 0)),
        'opp_wc_wins': float(feat.get('home_wc_wins', 0)),
        'wc_finals': float(feat.get('away_wc_finals', 0)),
        'opp_wc_finals': float(feat.get('home_wc_finals', 0)),
        'wc_semis': float(feat.get('away_wc_semis', 0)),
        'opp_wc_semis': float(feat.get('home_wc_semis', 0)),
        'wc_avg_goals': 0.0,
        'h2h_winrate': 0.5,
        'h2h_matches': 0,
        'rest_days': 4.0,
        'opp_rest_days': 4.0,
        'rest_days_adv': 0.0,
        'tournament_match_num': int(feat.get('fixture_id', 1)),
        'goals_scored': away_score,
        'goals_conceded': home_score,
        'goal_diff': away_score - home_score,
        'result': away_result,
        'result_code': away_result_code,
        'split': 'train',
        'data_tier': 'tier2'
    }
    
    # Fill remaining columns in both perspective rows
    for col in df_train.columns:
        if col not in row_home:
            row_home[col] = 0.0
        if col not in row_away:
            row_away[col] = 0.0
            
    df_train = pd.concat([df_train, pd.DataFrame([row_home]), pd.DataFrame([row_away])], ignore_index=True)
    df_train.to_csv(TRAIN_DATA_PATH, index=False)
    print(f"  [OK] Appended match {next_match_id} ({home_team} vs {away_team}) to training dataset.")

def execute_model_retraining(random_state: int = 42):
    """Refit the preprocessing scaling and retrain the full models suite."""
    df_train = load_train_ready_data()
    df_train_engineered = engineer_features(df_train)
    
    train_mask = df_train_engineered['split'] == 'train'
    
    # Fit preprocessor
    preprocessor = ATLASPreprocessor()
    preprocessor.fit(df_train_engineered[train_mask], FINAL_FEATURES)
    preprocessor.save(MOD_DIR / "preprocessor.pkl")
    
    # Get feature arrays
    X_train = df_train_engineered.loc[train_mask, FINAL_FEATURES].values
    X_train_scaled = preprocessor.transform(df_train_engineered[train_mask])
    y_train = df_train_engineered.loc[train_mask, 'result_code'].values.astype(int)
    
    # Train models
    print("  Starting incremental Voting Ensemble retraining...")
    trainer = ATLASModelTrainer(random_state=random_state)
    trainer.train_and_cross_validate(X_train, y_train, X_train_scaled, n_splits=5)
    trainer.save_models(MOD_DIR)
    
    print("  [OK] Model retraining completed and models exported.")
