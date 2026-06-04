import numpy as np
import pandas as pd
from ..models.predictor import ATLASPredictor
from ..models.feature_engineering import FINAL_FEATURES

def build_wc2026_features_df(df_fixture_feats: pd.DataFrame) -> pd.DataFrame:
    """Map raw WC 2026 fixture features to model-compatible features."""
    df_mapped = pd.DataFrame(index=df_fixture_feats.index)
    
    # Core Elo & form
    df_mapped['elo_diff'] = df_fixture_feats['elo_diff'].fillna(0.0)
    df_mapped['elo_win_prob'] = df_fixture_feats['home_elo_win_prob'].fillna(0.5)
    df_mapped['form_diff'] = df_fixture_feats['form_diff'].fillna(0.0)
    
    # Stage config (Group Stage = 1, not Knockout)
    df_mapped['is_knockout'] = 0
    df_mapped['stage_numeric'] = 1
    
    # Home/Host flags
    home_host = df_fixture_feats.get('home_host_nation', 0).fillna(0).astype(int)
    away_host = df_fixture_feats.get('away_host_nation', 0).fillna(0).astype(int)
    
    df_mapped['is_home'] = home_host
    df_mapped['is_host'] = home_host
    df_mapped['opp_is_host'] = away_host
    df_mapped['neutral_venue'] = ((home_host == 0) & (away_host == 0)).astype(int)
    df_mapped['same_confederation'] = 0  # fallback
    
    # World Cup history
    df_mapped['wc_appearances'] = df_fixture_feats.get('home_wc_appearances', 0.0).fillna(0.0)
    df_mapped['opp_wc_appearances'] = df_fixture_feats.get('away_wc_appearances', 0.0).fillna(0.0)
    df_mapped['wc_wins'] = df_fixture_feats.get('home_wc_wins', 0.0).fillna(0.0)
    df_mapped['opp_wc_wins'] = df_fixture_feats.get('away_wc_wins', 0.0).fillna(0.0)
    df_mapped['wc_finals'] = df_fixture_feats.get('home_wc_finals', 0.0).fillna(0.0)
    df_mapped['opp_wc_finals'] = df_fixture_feats.get('away_wc_finals', 0.0).fillna(0.0)
    df_mapped['wc_semis'] = df_fixture_feats.get('home_wc_semis', 0.0).fillna(0.0)
    df_mapped['opp_wc_semis'] = df_fixture_feats.get('away_wc_semis', 0.0).fillna(0.0)
    df_mapped['wc_avg_goals'] = 0.0  # updated at run-time
    
    # Form details
    df_mapped['form_5'] = df_fixture_feats.get('home_form_10', 0.5).fillna(0.5)
    df_mapped['opp_form_5'] = df_fixture_feats.get('away_form_10', 0.5).fillna(0.5)
    df_mapped['goals_scored_form5'] = df_fixture_feats.get('home_goals_scored_form10', 1.5).fillna(1.5) / 2.0
    df_mapped['goals_conceded_form5'] = df_fixture_feats.get('home_goals_conceded_form10', 1.0).fillna(1.0) / 2.0
    df_mapped['opp_goals_scored_form5'] = df_fixture_feats.get('away_goals_scored_form10', 1.5).fillna(1.5) / 2.0
    
    # Head-to-head defaults
    df_mapped['h2h_winrate'] = 0.5
    df_mapped['h2h_matches'] = 0
    
    # Rest days (Group stage match 1 defaults)
    df_mapped['rest_days'] = 4.0
    df_mapped['opp_rest_days'] = 4.0
    df_mapped['rest_days_adv'] = 0.0
    df_mapped['tournament_match_num'] = df_fixture_feats.get('fixture_id', 1).fillna(1)
    
    # Tournament progress variables
    tourn_progress_cols = [
        'tourn_matches_played', 'tourn_goals_for', 'tourn_goals_against',
        'tourn_goal_diff', 'tourn_wins', 'tourn_winrate', 'tourn_goals_per_match'
    ]
    for col in tourn_progress_cols:
        df_mapped[col] = 0.0
        
    # Squad features
    df_mapped['squad_xg_per_match'] = df_fixture_feats.get('home_squad_xg_p90', 0.0).fillna(0.0)
    df_mapped['squad_goals_per_match'] = df_fixture_feats.get('home_squad_goals_p90', 0.0).fillna(0.0)
    df_mapped['squad_shots_per_match'] = 0.0
    df_mapped['squad_key_passes_per_match'] = df_fixture_feats.get('home_squad_key_passes_p90', 0.0).fillna(0.0)
    df_mapped['squad_interceptions_per_match'] = df_fixture_feats.get('home_squad_interceptions_p90', 0.0).fillna(0.0)
    df_mapped['squad_dribbles_per_match'] = 0.0
    df_mapped['squad_squad_pass_accuracy'] = df_fixture_feats.get('home_squad_pass_accuracy', 0.8).fillna(0.8)
    
    df_mapped['opp_squad_xg_per_match'] = df_fixture_feats.get('away_squad_xg_p90', 0.0).fillna(0.0)
    df_mapped['opp_squad_goals_per_match'] = df_fixture_feats.get('away_squad_goals_p90', 0.0).fillna(0.0)
    df_mapped['opp_squad_shots_per_match'] = 0.0
    df_mapped['opp_squad_key_passes_per_match'] = df_fixture_feats.get('away_squad_key_passes_p90', 0.0).fillna(0.0)
    df_mapped['opp_squad_interceptions_per_match'] = df_fixture_feats.get('away_squad_interceptions_p90', 0.0).fillna(0.0)
    df_mapped['opp_squad_dribbles_per_match'] = 0.0
    df_mapped['opp_squad_squad_pass_accuracy'] = df_fixture_feats.get('away_squad_pass_accuracy', 0.8).fillna(0.8)
    
    # Demographics
    df_mapped['squad_avg_age'] = df_fixture_feats.get('home_squad_avg_age_2026', 28.0).fillna(28.0)
    df_mapped['opp_squad_avg_age'] = df_fixture_feats.get('away_squad_avg_age_2026', 28.0).fillna(28.0)
    df_mapped['age_diff'] = df_mapped['squad_avg_age'] - df_mapped['opp_squad_avg_age']
    
    df_mapped['avg_club_prestige'] = df_fixture_feats.get('home_avg_club_prestige', 5.0).fillna(5.0)
    df_mapped['max_club_prestige'] = df_fixture_feats.get('home_max_club_prestige', 5.0).fillna(5.0)
    df_mapped['opp_avg_club_prestige'] = df_fixture_feats.get('away_avg_club_prestige', 5.0).fillna(5.0)
    df_mapped['opp_max_club_prestige'] = df_fixture_feats.get('away_max_club_prestige', 5.0).fillna(5.0)
    df_mapped['club_prestige_diff'] = df_mapped['avg_club_prestige'] - df_mapped['opp_avg_club_prestige']
    
    # Confederation flags
    df_mapped['team_conf_code'] = 1
    df_mapped['opp_conf_code'] = 1
    
    # Fill remaining columns from FINAL_FEATURES to ensure exact match
    for col in FINAL_FEATURES:
        if col not in df_mapped.columns:
            df_mapped[col] = 0.0
            
    return df_mapped

def generate_wc2026_predictions(predictor: ATLASPredictor, df_fixture_feats: pd.DataFrame, 
                                 all_models_dict=None, scaler=None) -> pd.DataFrame:
    """Generate probabilistic outcome predictions for all 72 group stage fixtures."""
    df_mapped = build_wc2026_features_df(df_fixture_feats)
    
    # Generate probabilities using primary predictor [loss, draw, win]
    probs = predictor.predict_probs(df_mapped)
    
    predictions = []
    for idx, row in df_fixture_feats.iterrows():
        prob_loss = probs[idx, 0]
        prob_draw = probs[idx, 1]
        prob_win  = probs[idx, 2]
        
        confidence = max(prob_loss, prob_draw, prob_win)
        
        if confidence == prob_win:
            pred = 'Home Win'
        elif confidence == prob_draw:
            pred = 'Draw'
        else:
            pred = 'Away Win'
            
        predictions.append({
            'fixture_id': int(row['fixture_id']),
            'date': row['date'],
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'home_win_prob': round(prob_win, 4),
            'draw_prob': round(prob_draw, 4),
            'away_win_prob': round(prob_loss, 4),
            'predicted_result': pred,
            'confidence': round(confidence, 4),
            'elo_diff': float(row.get('elo_diff', 0.0)),
        })
        
    df_predictions = pd.DataFrame(predictions)
    
    # Add ensemble predictions if multiple models are passed
    if all_models_dict is not None and scaler is not None:
        model_predictions = {}
        for mname, model in all_models_dict.items():
            try:
                # Use scaled features if required by model type
                if mname in ['Logistic Regression', 'MLP Neural Net']:
                    # Feature engineering on df_mapped to add interactions
                    from ..models.feature_engineering import engineer_features
                    df_eng = engineer_features(df_mapped)
                    X_scaled = scaler.transform(df_eng[FINAL_FEATURES].values)
                    m_probs = model.predict_proba(X_scaled)
                else:
                    from ..models.feature_engineering import engineer_features
                    df_eng = engineer_features(df_mapped)
                    X = df_eng[FINAL_FEATURES].values
                    X = np.nan_to_num(X, nan=0.0)
                    m_probs = model.predict_proba(X)
                model_predictions[mname] = m_probs
            except Exception as e:
                print(f"      Warning: could not run prediction with {mname}: {e}")
                
        if model_predictions:
            avg_probs = np.mean(list(model_predictions.values()), axis=0)
            for i in range(len(df_predictions)):
                df_predictions.loc[i, 'ensemble_home_win'] = round(float(avg_probs[i, 2]), 4)
                df_predictions.loc[i, 'ensemble_draw'] = round(float(avg_probs[i, 1]), 4)
                df_predictions.loc[i, 'ensemble_away_win'] = round(float(avg_probs[i, 0]), 4)
                
    return df_predictions
