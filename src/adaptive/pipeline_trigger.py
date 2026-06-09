import os
import json
import warnings
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import joblib

# Import ELO and Retraining modules
from .elo_updater import update_elo_ratings
from .retrain import append_match_to_training_set, execute_model_retraining

# Import core loaders and logic
from ..data.loader import (
    load_train_ready_data,
    load_player_match_stats,
    load_wc2026_fixtures,
    load_wc2026_fixture_features,
    load_wc2026_team_strength,
    load_wc2026_player_squad,
    DEFAULT_DATA_DIR
)
from ..data.preprocessor import ATLASPreprocessor
from ..models.feature_engineering import engineer_features, FINAL_FEATURES
from ..models.trainer import ATLASModelTrainer
from ..models.evaluator import ATLASModelEvaluator
from ..models.predictor import ATLASPredictor
from ..predictions.wc2026_predictor import generate_wc2026_predictions, build_wc2026_features_df
from ..predictions.group_standings import compute_group_standings, extract_groups_from_fixtures
from ..simulation.monte_carlo import ATLASMonteCarloSimulator
from ..players.impact_score import calculate_player_impact_scores
from ..players.team_aggregator import aggregate_team_strength
from ..players.what_if import simulate_injury_scenarios
from ..explainability.shap_explainer import ATLASShapExplainer
from ..explainability.narrative_generator import generate_prediction_narratives

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
RES = OUT / "results"
MOD = OUT / "models"
JSN = OUT / "json"
FRONTEND_DATA_DIR = ROOT / "frontend" / "public" / "data"

RANDOM_STATE = 42

def sanitize_nans(obj):
    """Recursively replace float NaN and Inf values with None (JSON null)."""
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nans(x) for x in obj]
    return obj

def trigger_adaptive_update(
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    stage: str = "Group Stage"
):
    """
    Orchestrate the complete live update cycle:
    1. Update team strength ratings in wc2026_team_strength.csv (ELOs).
    2. Add new match to training data csv.
    3. Retrain preprocessor and Voting Ensemble.
    4. Regenerate forecasting predictions.
    5. Re-run 10,000 Monte Carlo simulations.
    6. Update player grades, injury scores, and SHAP explanations.
    7. Sanitize and write JSON files directly to frontend public path.
    """
    print("=" * 70)
    print(f"ATLAS Adaptive Update Triggered: {home_team} vs {away_team} ({home_score}-{away_score})")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Query completed match scores and knockout winners from DB
    completed_group_scores = {}
    completed_knockouts = {}
    db_knockout_scores = {}
    
    try:
        from backend.app.db.session import SessionLocal
        from backend.app.db.models import Match
        if SessionLocal is not None and Match is not None:
            db = SessionLocal()
            try:
                completed_matches = db.query(Match).filter(Match.status == "completed").all()
                for m in completed_matches:
                    h = m.home_team
                    a = m.away_team
                    stg = m.stage or "Group Stage"
                    if stg == "Group Stage":
                        if m.home_score is not None and m.away_score is not None:
                            completed_group_scores[(h.lower(), a.lower())] = (int(m.home_score), int(m.away_score))
                    else:
                        if m.home_score is not None and m.away_score is not None:
                            winner = h if m.home_score > m.away_score else a
                            completed_knockouts[(h.lower(), a.lower(), stg.lower())] = winner
                            completed_knockouts[(a.lower(), h.lower(), stg.lower())] = winner
                            db_knockout_scores[(h.lower(), a.lower(), stg.lower())] = (m.home_score, m.away_score)
                            db_knockout_scores[(a.lower(), h.lower(), stg.lower())] = (m.away_score, m.home_score)
                print(f"  Loaded {len(completed_group_scores)} completed group scores and {len(completed_knockouts)//2} knockout winners from DB.")
            except Exception as e:
                print(f"  [WARN] Failed to query database for completed matches: {e}")
            finally:
                db.close()
    except Exception as e:
        print(f"  [WARN] Database models not available, using offline defaults: {e}")

    # 1. UPDATE TEAM ELO RATINGS
    print("\n[1/7] Updating Team Elo Ratings...")
    team_strength_path = DEFAULT_DATA_DIR / "wc2026_team_strength.csv"
    df_team_str = pd.read_csv(team_strength_path)
    
    home_mask = df_team_str['team'].str.lower() == home_team.lower()
    away_mask = df_team_str['team'].str.lower() == away_team.lower()
    
    if not home_mask.any() or not away_mask.any():
        print(f"  [WARN] Teams not found in ELO profiles: {home_team} or {away_team}")
        elo_home = 1600.0
        elo_away = 1600.0
    else:
        elo_home = float(df_team_str.loc[home_mask, 'current_elo'].iloc[0])
        elo_away = float(df_team_str.loc[away_mask, 'current_elo'].iloc[0])
        
    new_elo_home, new_elo_away = update_elo_ratings(
        elo_home, elo_away, home_score, away_score, is_knockout=(stage != "Group Stage")
    )
    # Store old Elo ratings for shift narrative calculation
    old_elo_home = elo_home
    old_elo_away = elo_away
    new_elo_home_val = new_elo_home
    new_elo_away_val = new_elo_away
    
    if home_mask.any():
        df_team_str.loc[home_mask, 'current_elo'] = new_elo_home
        # Update Form metric
        current_form = float(df_team_str.loc[home_mask, 'form_10'].fillna(0.5).iloc[0])
        outcome = 1.0 if home_score > away_score else 0.5 if home_score == away_score else 0.0
        df_team_str.loc[home_mask, 'form_10'] = round(current_form * 0.9 + outcome * 0.1, 4)
        
    if away_mask.any():
        df_team_str.loc[away_mask, 'current_elo'] = new_elo_away
        current_form = float(df_team_str.loc[away_mask, 'form_10'].fillna(0.5).iloc[0])
        outcome = 1.0 if away_score > home_score else 0.5 if home_score == away_score else 0.0
        df_team_str.loc[away_mask, 'form_10'] = round(current_form * 0.9 + outcome * 0.1, 4)
        
    df_team_str.to_csv(team_strength_path, index=False)
    print(f"  [OK] Updated Elo: {home_team} ({elo_home} -> {new_elo_home}) | {away_team} ({elo_away} -> {new_elo_away})")

    # 2. APPEND MATCH TO TRAINING SET
    print("\n[2/7] Appending match to historical database...")
    try:
        append_match_to_training_set(home_team, away_team, home_score, away_score, stage)
    except Exception as e:
        print(f"  [ERROR] Failed to append match: {e}. Proceeding with retraining anyway...")

    # 3. RETRAIN MODELS
    print("\n[3/7] Re-fitting preprocessor & retraining models...")
    execute_model_retraining(random_state=RANDOM_STATE)

    # 4. REGENERATE FORECAST PREDICTIONS & STANDINGS
    print("\n[4/7] Re-predicting upcoming fixtures...")
    # Reload newly trained preprocessor and best model
    preprocessor = ATLASPreprocessor().load(MOD / "preprocessor.pkl")
    
    trainer = ATLASModelTrainer(random_state=RANDOM_STATE)
    trainer.load_models(MOD)
    
    # Evaluate and get best model
    df_train = load_train_ready_data()
    df_train_engineered = engineer_features(df_train)
    test_mask = df_train_engineered['split'] == 'test'
    X_test = df_train_engineered.loc[test_mask, FINAL_FEATURES].values
    X_test_scaled = preprocessor.transform(df_train_engineered[test_mask])
    y_test = df_train_engineered.loc[test_mask, 'result_code'].values.astype(int)
    
    evaluator = ATLASModelEvaluator(trainer.models, trainer.cv_results)
    df_comparison = evaluator.evaluate(X_test, y_test, X_test_scaled)
    df_comparison.to_csv(RES / "model_comparison.csv", index=False)
    
    best_name, best_model = evaluator.get_best_model(df_comparison)
    predictor_engine = ATLASPredictor(best_model, preprocessor)
    
    # Reload fixture features
    df_fixture_feats = load_wc2026_fixture_features()
    
    # Update ELOs in fixture features if they match
    # This ensures that future match predictions use updated ELOs!
    for idx, row in df_fixture_feats.iterrows():
        h = row['home_team']
        a = row['away_team']
        h_str = df_team_str[df_team_str['team'].str.lower() == h.lower()]
        a_str = df_team_str[df_team_str['team'].str.lower() == a.lower()]
        if len(h_str) > 0:
            h_elo = float(h_str['current_elo'].iloc[0])
            df_fixture_feats.loc[idx, 'home_current_elo'] = h_elo
        if len(a_str) > 0:
            a_elo = float(a_str['current_elo'].iloc[0])
            df_fixture_feats.loc[idx, 'away_current_elo'] = a_elo
        # Re-calc elo diff
        df_fixture_feats.loc[idx, 'elo_diff'] = df_fixture_feats.loc[idx, 'home_current_elo'] - df_fixture_feats.loc[idx, 'away_current_elo']
    df_fixture_feats.to_csv(DEFAULT_DATA_DIR / "wc2026_fixture_features.csv", index=False)
    
    df_predictions = generate_wc2026_predictions(
        predictor_engine, df_fixture_feats, trainer.models, preprocessor.scaler
    )
    df_predictions.to_csv(RES / "wc2026_predictions.csv", index=False)
    
    # Re-calc standings
    df_fixtures = load_wc2026_fixtures()
    
    # Sync all completed group stage matches from DB to the CSV
    try:
        from backend.app.db.session import SessionLocal
        from backend.app.db.models import Match
        if SessionLocal is not None and Match is not None:
            db = SessionLocal()
            try:
                db_completed = db.query(Match).filter(Match.status == "completed", Match.stage == "Group Stage").all()
                for m in db_completed:
                    mask = (
                        ((df_fixtures['home_team'].str.lower() == m.home_team.lower()) & (df_fixtures['away_team'].str.lower() == m.away_team.lower())) |
                        ((df_fixtures['home_team'].str.lower() == m.away_team.lower()) & (df_fixtures['away_team'].str.lower() == m.home_team.lower()))
                    )
                    if mask.any():
                        idx = df_fixtures[mask].index[0]
                        h_csv = df_fixtures.loc[idx, 'home_team']
                        if h_csv.lower() == m.home_team.lower():
                            df_fixtures.loc[idx, 'home_score'] = m.home_score
                            df_fixtures.loc[idx, 'away_score'] = m.away_score
                        else:
                            df_fixtures.loc[idx, 'home_score'] = m.away_score
                            df_fixtures.loc[idx, 'away_score'] = m.home_score
                        df_fixtures.loc[idx, 'result_available'] = 1
            except Exception as e:
                print(f"  [WARN] Failed to sync completed group matches from DB: {e}")
            finally:
                db.close()
    except Exception as e:
        print(f"  [WARN] Database models not available for sync: {e}")

    # Update standings with the actual score of the triggered match if it was group stage
    if stage == "Group Stage":
        for idx, row in df_fixtures.iterrows():
            if (row['home_team'].lower() == home_team.lower() and row['away_team'].lower() == away_team.lower()) or \
               (row['home_team'].lower() == away_team.lower() and row['away_team'].lower() == home_team.lower()):
                df_fixtures.loc[idx, 'home_score'] = home_score
                df_fixtures.loc[idx, 'away_score'] = away_score
                df_fixtures.loc[idx, 'result_available'] = 1
                
    df_fixtures.to_csv(DEFAULT_DATA_DIR / "wc2026_fixtures.csv", index=False)
    
    df_standings = compute_group_standings(df_predictions, df_fixtures)
    df_standings.to_csv(RES / "wc2026_group_standings.csv", index=False)
    print("  [OK] Predicted standings updated.")

    # 5. MONTE CARLO SIMULATION
    print("\n[5/7] Running Monte Carlo Tournament Re-Simulations...")
    
    # Read old simulations.json to compute deltas for latest shift narrative
    old_sim_path = FRONTEND_DATA_DIR / "simulations.json"
    old_probs = {}
    if old_sim_path.exists():
        try:
            with open(old_sim_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for item in old_data.get("results", []):
                    old_probs[item["Team"]] = {
                        "r32": item.get("Round of 32 %", 0.0),
                        "r16": item.get("Round of 16 %", 0.0),
                        "champion": item.get("Champion %", 0.0)
                    }
        except Exception as e:
            print(f"  [WARN] Failed to load old simulations: {e}")

    groups = extract_groups_from_fixtures(df_fixtures)
    fixture_probs_lookup = {}
    for _, row in df_predictions.iterrows():
        key = (row['home_team'], row['away_team'])
        fixture_probs_lookup[key] = [row['away_win_prob'], row['draw_prob'], row['home_win_prob']]
        
    team_elos = dict(zip(df_team_str['team'], df_team_str['current_elo']))
    all_teams = sorted(set(df_fixtures['home_team']) | set(df_fixtures['away_team']))
    
    n_simulations = 10000
    # Fallback to load completed group scores from fixtures list CSV as well
    for idx, row in df_fixtures.iterrows():
        if row.get('result_available', 0) == 1 and pd.notna(row.get('home_score')) and pd.notna(row.get('away_score')):
            h = row['home_team']
            a = row['away_team']
            completed_group_scores[(h.lower(), a.lower())] = (int(row['home_score']), int(row['away_score']))
            
    simulator = ATLASMonteCarloSimulator(
        groups, fixture_probs_lookup, team_elos, all_teams,
        completed_group_scores=completed_group_scores,
        completed_knockouts=completed_knockouts
    )

    df_sim = simulator.run_simulations(n_simulations=n_simulations, show_progress=False)
    df_sim.to_csv(RES / "wc2026_simulation_results.csv", index=False)
    print("  [OK] Re-simulations completed.")

    # Generate narrative shift statement
    shift_narrative = ""
    try:
        home_old = old_probs.get(home_team, {"r32": 50.0, "champion": 2.0})
        away_old = old_probs.get(away_team, {"r32": 50.0, "champion": 2.0})
        
        home_new_row = df_sim[df_sim['Team'] == home_team]
        away_new_row = df_sim[df_sim['Team'] == away_team]
        
        if len(home_new_row) > 0 and len(away_new_row) > 0:
            home_new_r32 = float(home_new_row['Round of 32 %'].iloc[0])
            home_new_champ = float(home_new_row['Champion %'].iloc[0])
            away_new_r32 = float(away_new_row['Round of 32 %'].iloc[0])
            away_new_champ = float(away_new_row['Champion %'].iloc[0])
            
            home_delta_r32 = home_new_r32 - home_old["r32"]
            home_delta_champ = home_new_champ - home_old["champion"]
            away_delta_r32 = away_new_r32 - away_old["r32"]
            away_delta_champ = away_new_champ - away_old["champion"]
            
            elo_change_h = new_elo_home_val - old_elo_home
            elo_change_a = new_elo_away_val - old_elo_away
            
            winner = home_team if home_score > away_score else away_team if away_score > home_score else None
            
            if winner == home_team:
                shift_narrative = (
                    f"Following {home_team}'s {home_score}-{away_score} victory over {away_team}, "
                    f"{home_team}'s Elo rose by {elo_change_h:+.1f} pts, increasing their Round of 32 advancement probability by {home_delta_r32:+.1f}% "
                    f"(now {home_new_r32:.1f}%) and title chances by {home_delta_champ:+.1f}%. "
                    f"Conversely, {away_team}'s Elo fell by {abs(elo_change_a):.1f} pts, dropping their advancement odds by {abs(away_delta_r32):.1f}%."
                )
            elif winner == away_team:
                shift_narrative = (
                    f"Following {away_team}'s {away_score}-{home_score} victory over {home_team}, "
                    f"{away_team}'s Elo rose by {elo_change_a:+.1f} pts, increasing their Round of 32 advancement probability by {away_delta_r32:+.1f}% "
                    f"(now {away_new_r32:.1f}%) and title chances by {away_delta_champ:+.1f}%. "
                    f"Conversely, {home_team}'s Elo fell by {abs(elo_change_h):.1f} pts, dropping their advancement odds by {abs(home_delta_r32):.1f}%."
                )
            else:
                shift_narrative = (
                    f"The {home_team} vs {away_team} match ended in a {home_score}-{away_score} draw. "
                    f"{home_team}'s Elo changed by {elo_change_h:+.1f} pts, adjusting their Round of 32 probability by {home_delta_r32:+.1f}%. "
                    f"{away_team}'s Elo changed by {elo_change_a:+.1f} pts, adjusting their Round of 32 probability by {away_delta_r32:+.1f}%."
                )
    except Exception as e:
        shift_narrative = f"Completed match: {home_team} {home_score}-{away_score} {away_team}."
        print(f"  [WARN] Failed to compute shift narrative: {e}")

    # 6. PLAYER INTELLIGENCE & SHAP EXPLANATIONS
    print("\n[6/7] Regenerating Player Scores & SHAP Explanations...")
    df_players_squad = load_wc2026_player_squad()
    df_ps_graded = calculate_player_impact_scores(df_players_squad)
    df_top50 = df_ps_graded.nlargest(50, 'impact_score')[
        ['player_name', 'team', 'impact_score', 'xg_p90', 'goals_p90',
         'key_passes_p90', 'interceptions_p90', 'prog_carries_p90', 'pass_accuracy']
    ].reset_index(drop=True)
    
    df_team_breakdown = aggregate_team_strength(df_ps_graded, df_team_str)
    df_injuries = simulate_injury_scenarios(df_ps_graded, top_n_players=10)
    
    # SHAP
    feature_names = FINAL_FEATURES
    shap_explainer = ATLASShapExplainer(best_model, best_name, trainer.models, feature_names)
    shap_values = shap_explainer.compute_shap_values(X_test)
    df_shap_fi = shap_explainer.get_global_importance(shap_values)
    
    df_wc_mapped = build_wc2026_features_df(df_fixture_feats)
    df_wc_engineered = engineer_features(df_wc_mapped)
    X_wc2026 = df_wc_engineered[FINAL_FEATURES].values
    X_wc2026 = np.nan_to_num(X_wc2026, nan=0.0)
    
    df_narratives = generate_prediction_narratives(shap_explainer, df_predictions, X_wc2026, feature_names)
    print("  [OK] Player and SHAP outputs computed.")

    # 7. EXPORT SANITIZED JSON TO FRONTEND
    print("\n[7/7] Exporting sanitized JSON files to Frontend...")
    
    # Helper to save sanitized JSON
    def save_clean_json(data_dict, file_name):
        sanitized = sanitize_nans(data_dict)
        # Write to output folder
        with open(JSN / file_name, 'w', encoding='utf-8') as f:
            json.dump(sanitized, f, indent=2, ensure_ascii=False)
        # Write to frontend public folder
        with open(FRONTEND_DATA_DIR / file_name, 'w', encoding='utf-8') as f:
            json.dump(sanitized, f, indent=2, ensure_ascii=False)
            
    # Predictions JSON
    predictions_json = {
        'model': best_name,
        'accuracy_on_test': float(df_comparison.loc[df_comparison['Model'] == best_name, 'Accuracy'].iloc[0]),
        'generated_at': datetime.now().isoformat(),
        'predictions': df_predictions.to_dict('records'),
    }
    save_clean_json(predictions_json, "predictions.json")
    
    # Simulations JSON
    simulations_json = {
        'n_simulations': n_simulations,
        'results': df_sim.to_dict('records'),
    }
    save_clean_json(simulations_json, "simulations.json")
    
    # Players JSON
    players_json = {
        'top50': df_top50.to_dict('records'),
        'team_strength': df_team_breakdown.to_dict('records'),
    }
    save_clean_json(players_json, "players.json")
    
    # Explanations JSON
    explanations_json = {
        'feature_importance': df_shap_fi.head(20).to_dict('records'),
        'match_explanations': df_narratives.to_dict('records'),
    }
    save_clean_json(explanations_json, "explanations.json")
    
    # Model Comparison JSON
    model_comp_json = {
        'models': df_comparison.to_dict('records'),
        'best_model': best_name,
    }
    save_clean_json(model_comp_json, "model_comparison.json")
    
    # Group Standings JSON
    standings_json = {}
    for label, group_df in df_standings.groupby('Group'):
        standings_json[f"Group {label}"] = group_df.drop(columns=['Group']).to_dict('records')
    save_clean_json(standings_json, "group_standings.json")
    
    # Injuries JSON
    save_clean_json(df_injuries.to_dict('records'), "injuries.json")
    
    # Qualification JSON
    qualification_json = simulator.team_positions_pct
    save_clean_json(qualification_json, "qualification.json")
    
    # Latest Shift JSON (computes pre/post delta shifts)
    shifts = []
    try:
        team_changes = []
        for _, row in df_sim.iterrows():
            t_name = row['Team']
            new_champ = float(row['Champion %'])
            old_val = old_probs.get(t_name, {"champion": 0.0})
            old_champ = old_val["champion"]
            delta = new_champ - old_champ
            team_changes.append((t_name, new_champ, old_champ, delta))
            
        team_changes.sort(key=lambda x: abs(x[3]), reverse=True)
        for t_name, new_c, old_c, d in team_changes[:8]:
            if abs(d) > 0.01:
                sign = "+" if d >= 0 else ""
                shifts.append({
                    "team": t_name,
                    "champion_change": f"{sign}{d:.2f}%",
                    "reason": f"Title chances adjusted from {old_c:.2f}% to {new_c:.2f}% following match results and updated ELO rankings."
                })
    except Exception as e:
        print(f"  [WARN] Failed to compute shift deltas: {e}")

    shift_json = {
        "generated_at": datetime.now().isoformat(),
        "trigger_match": {
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "stage": stage
        },
        "shift_narrative": shift_narrative,
        "shifts": shifts
    }
    save_clean_json(shift_json, "latest_shift.json")
    
    # Bracket JSON Compilation
    group_winners = {}
    group_runners_up = {}
    third_place_teams = []
    
    for group_label, grp_df in df_standings.groupby('Group'):
        grp_sorted = grp_df.sort_values('Position')
        if len(grp_sorted) >= 3:
            winner = grp_sorted.iloc[0]['Team']
            runner = grp_sorted.iloc[1]['Team']
            third = grp_sorted.iloc[2]['Team']
            
            group_winners[group_label] = winner
            group_runners_up[group_label] = runner
            
            pts = int(grp_sorted.iloc[2]['Pts'])
            gd = int(grp_sorted.iloc[2]['GD'])
            gf = int(grp_sorted.iloc[2]['GF'])
            third_place_teams.append({'team': third, 'pts': pts, 'gd': gd, 'gf': gf})
            
    third_place_teams.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)
    best_thirds = [x['team'] for x in third_place_teams[:8]]
    
    r32_pairings = [
        (group_winners.get('A', 'TBD'), group_runners_up.get('B', 'TBD')),
        (group_winners.get('C', 'TBD'), group_runners_up.get('D', 'TBD')),
        (group_winners.get('E', 'TBD'), group_runners_up.get('F', 'TBD')),
        (group_winners.get('G', 'TBD'), group_runners_up.get('H', 'TBD')),
        (group_winners.get('I', 'TBD'), group_runners_up.get('J', 'TBD')),
        (group_winners.get('K', 'TBD'), group_runners_up.get('L', 'TBD')),
        (group_winners.get('B', 'TBD'), group_runners_up.get('A', 'TBD')),
        (group_winners.get('D', 'TBD'), group_runners_up.get('C', 'TBD')),
        (group_winners.get('F', 'TBD'), group_runners_up.get('E', 'TBD')),
        (group_winners.get('H', 'TBD'), group_runners_up.get('G', 'TBD')),
        (group_winners.get('J', 'TBD'), group_runners_up.get('I', 'TBD')),
        (group_winners.get('L', 'TBD'), group_runners_up.get('K', 'TBD')),
        (best_thirds[0] if len(best_thirds) > 0 else "TBD", best_thirds[1] if len(best_thirds) > 1 else "TBD"),
        (best_thirds[2] if len(best_thirds) > 2 else "TBD", best_thirds[3] if len(best_thirds) > 3 else "TBD"),
        (best_thirds[4] if len(best_thirds) > 4 else "TBD", best_thirds[5] if len(best_thirds) > 5 else "TBD"),
        (best_thirds[6] if len(best_thirds) > 6 else "TBD", best_thirds[7] if len(best_thirds) > 7 else "TBD"),
    ]
    
    def get_stage_prob(team_name, stage_key):
        row = df_sim[df_sim['Team'] == team_name]
        if len(row) > 0:
            return float(row[stage_key].iloc[0])
        return 0.0
        
    def get_likely_winner(team_a, team_b, stage_prob_key):
        prob_a = get_stage_prob(team_a, stage_prob_key)
        prob_b = get_stage_prob(team_b, stage_prob_key)
        return team_a if prob_a >= prob_b else team_b

    def get_match_score(home, away, stage):
        key = (home.lower(), away.lower(), stage.lower())
        if key in db_knockout_scores:
            return db_knockout_scores[key]
        return (None, None)

    r32_matches = []
    for idx, (h, a) in enumerate(r32_pairings):
        score_h, score_a = get_match_score(h, a, "Round of 32")
        r32_matches.append({
            'match_id': idx + 1,
            'home_team': h,
            'away_team': a,
            'home_prob': get_stage_prob(h, 'Round of 32 %'),
            'away_prob': get_stage_prob(a, 'Round of 32 %'),
            'home_adv_prob': get_stage_prob(h, 'Round of 16 %'),
            'away_adv_prob': get_stage_prob(a, 'Round of 16 %'),
            'home_score': score_h,
            'away_score': score_a
        })
        
    r16_pairings = []
    for i in range(0, 16, 2):
        h = get_likely_winner(r32_pairings[i][0], r32_pairings[i][1], 'Round of 16 %')
        a = get_likely_winner(r32_pairings[i+1][0], r32_pairings[i+1][1], 'Round of 16 %')
        r16_pairings.append((h, a))
        
    r16_matches = []
    for idx, (h, a) in enumerate(r16_pairings):
        score_h, score_a = get_match_score(h, a, "Round of 16")
        r16_matches.append({
            'match_id': 17 + idx,
            'home_team': h,
            'away_team': a,
            'home_prob': get_stage_prob(h, 'Round of 16 %'),
            'away_prob': get_stage_prob(a, 'Round of 16 %'),
            'home_adv_prob': get_stage_prob(h, 'Quarter-Final %'),
            'away_adv_prob': get_stage_prob(a, 'Quarter-Final %'),
            'home_score': score_h,
            'away_score': score_a
        })
        
    qf_pairings = []
    for i in range(0, 8, 2):
        h = get_likely_winner(r16_pairings[i][0], r16_pairings[i][1], 'Quarter-Final %')
        a = get_likely_winner(r16_pairings[i+1][0], r16_pairings[i+1][1], 'Quarter-Final %')
        qf_pairings.append((h, a))
        
    qf_matches = []
    for idx, (h, a) in enumerate(qf_pairings):
        score_h, score_a = get_match_score(h, a, "Quarter-Final")
        qf_matches.append({
            'match_id': 25 + idx,
            'home_team': h,
            'away_team': a,
            'home_prob': get_stage_prob(h, 'Quarter-Final %'),
            'away_prob': get_stage_prob(a, 'Quarter-Final %'),
            'home_adv_prob': get_stage_prob(h, 'Semi-Final %'),
            'away_adv_prob': get_stage_prob(a, 'Semi-Final %'),
            'home_score': score_h,
            'away_score': score_a
        })
        
    sf_pairings = []
    for i in range(0, 4, 2):
        h = get_likely_winner(qf_pairings[i][0], qf_pairings[i][1], 'Semi-Final %')
        a = get_likely_winner(qf_pairings[i+1][0], qf_pairings[i+1][1], 'Semi-Final %')
        sf_pairings.append((h, a))
        
    sf_matches = []
    for idx, (h, a) in enumerate(sf_pairings):
        score_h, score_a = get_match_score(h, a, "Semi-Final")
        sf_matches.append({
            'match_id': 29 + idx,
            'home_team': h,
            'away_team': a,
            'home_prob': get_stage_prob(h, 'Semi-Final %'),
            'away_prob': get_stage_prob(a, 'Semi-Final %'),
            'home_adv_prob': get_stage_prob(h, 'Finalist %'),
            'away_adv_prob': get_stage_prob(a, 'Finalist %'),
            'home_score': score_h,
            'away_score': score_a
        })
        
    f_home = get_likely_winner(sf_pairings[0][0], sf_pairings[0][1], 'Finalist %')
    f_away = get_likely_winner(sf_pairings[1][0], sf_pairings[1][1], 'Finalist %')
    
    score_h, score_a = get_match_score(f_home, f_away, "Final")
    final_match = [{
        'match_id': 31,
        'home_team': f_home,
        'away_team': f_away,
        'home_prob': get_stage_prob(f_home, 'Finalist %'),
        'away_prob': get_stage_prob(f_away, 'Finalist %'),
        'home_adv_prob': get_stage_prob(f_home, 'Champion %'),
        'away_adv_prob': get_stage_prob(f_away, 'Champion %'),
        'home_score': score_h,
        'away_score': score_a
    }]
    
    bracket_json = {
        'r32': r32_matches,
        'r16': r16_matches,
        'qf': qf_matches,
        'sf': sf_matches,
        'final': final_match
    }
    save_clean_json(bracket_json, "bracket.json")
    
    print("\n" + "=" * 70)
    print("ATLAS Adaptive Update & Sanitization Complete!")
    print("=" * 70)
