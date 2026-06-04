import numpy as np
import pandas as pd
from .shap_explainer import ATLASShapExplainer

def generate_prediction_narratives(explainer: ATLASShapExplainer, df_predictions: pd.DataFrame, 
                                   X_wc2026: np.ndarray, feature_names: list) -> pd.DataFrame:
    """Generate human-readable explanations based on top 3 contributing SHAP values for each match."""
    explanations = []
    
    for idx, fixture in df_predictions.iterrows():
        fix_id = int(fixture['fixture_id']) - 1
        
        # Ensure we don't index out of bounds
        if fix_id >= len(X_wc2026) or fix_id < 0:
            # Fallback if indices mismatch
            explanations.append({
                'fixture_id': fixture['fixture_id'],
                'match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'prediction': fixture['predicted_result'],
                'reason_1': 'Elo-based baseline prediction',
                'reason_2': '', 'reason_3': '',
            })
            continue
            
        fix_features = X_wc2026[fix_id:fix_id+1]
        
        try:
            # Get SHAP contributions for the "Win" class
            shap_vals = explainer.explain_prediction(fix_features)
            
            # Sort features by absolute contribution
            top3_idx = np.argsort(np.abs(shap_vals))[-3:][::-1]
            reasons = []
            
            # Map column names to user-friendly titles
            feature_name_mapping = {
                'elo_diff': 'Elo rating difference',
                'elo_win_prob': 'Elo win probability',
                'form_diff': 'Recent form trend',
                'is_host': 'Host nation advantage',
                'squad_xg_per_match': 'Squad expected goals',
                'opp_squad_xg_per_match': 'Opponent expected goals',
                'squad_quality_diff': 'Squad quality difference',
                'experience_diff': 'World Cup experience differential',
                'pedigree_diff': 'World Cup pedigree differential',
                'rest_days_adv': 'Rest days advantage',
                'club_prestige_diff': 'Club prestige difference',
            }
            
            for i in top3_idx:
                val = shap_vals[i]
                direction = 'increases win chance by' if val > 0 else 'decreases win chance by'
                raw_feat_name = feature_names[i]
                friendly_name = feature_name_mapping.get(raw_feat_name, raw_feat_name.replace('_', ' '))
                
                # Format explanation string
                reasons.append(f"{friendly_name} {direction} {abs(val)*100:.1f}%")
                
            explanations.append({
                'fixture_id': fixture['fixture_id'],
                'match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'prediction': fixture['predicted_result'],
                'reason_1': reasons[0] if len(reasons) > 0 else 'Core Elo ratings',
                'reason_2': reasons[1] if len(reasons) > 1 else '',
                'reason_3': reasons[2] if len(reasons) > 2 else '',
            })
            
        except Exception as e:
            # Safe fallback if SHAP calculation encounters issues
            explanations.append({
                'fixture_id': fixture['fixture_id'],
                'match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'prediction': fixture['predicted_result'],
                'reason_1': f'Elo-based (fallback due to error: {str(e)[:30]})',
                'reason_2': '', 'reason_3': '',
            })
            
    return pd.DataFrame(explanations)
