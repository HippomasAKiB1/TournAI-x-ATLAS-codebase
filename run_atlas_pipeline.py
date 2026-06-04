import os
import sys
import json
import warnings
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import joblib

# Add current workspace directory to Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Import modular components
from src.data.loader import (
    load_train_ready_data,
    load_player_match_stats,
    load_wc2026_fixtures,
    load_wc2026_fixture_features,
    load_wc2026_team_strength,
    load_wc2026_player_squad
)
from src.data.preprocessor import ATLASPreprocessor
from src.models.feature_engineering import (
    engineer_features,
    FINAL_FEATURES,
    ALL_CANDIDATE_FEATURES
)
from src.models.trainer import ATLASModelTrainer
from src.models.evaluator import ATLASModelEvaluator
from src.models.predictor import ATLASPredictor
from src.predictions.wc2026_predictor import generate_wc2026_predictions
from src.predictions.group_standings import compute_group_standings
from src.simulation.monte_carlo import ATLASMonteCarloSimulator
from src.players.impact_score import calculate_player_impact_scores
from src.players.team_aggregator import aggregate_team_strength
from src.players.what_if import simulate_injury_scenarios
from src.explainability.shap_explainer import ATLASShapExplainer
from src.explainability.narrative_generator import generate_prediction_narratives

warnings.filterwarnings('ignore')

# Paths configuration
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
RES = OUT / "results"
MOD = OUT / "models"
JSN = OUT / "json"

for d in [RES, MOD, JSN]:
    d.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

def main():
    print("=" * 70)
    # Proactively using a safe string to avoid console encoding crashes
    print("ATLAS Modular Production Pipeline")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ----------------------------------------------------
    # 1. DATA LOADING
    # ----------------------------------------------------
    print("\n[Step 1/7] Loading Datasets...")
    df_train = load_train_ready_data()
    df_players_match = load_player_match_stats()
    df_fixtures = load_wc2026_fixtures()
    df_fixture_feats = load_wc2026_fixture_features()
    df_team_str = load_wc2026_team_strength()
    df_players_squad = load_wc2026_player_squad()
    
    print(f"  ✓ Training matches: {len(df_train)}")
    print(f"  ✓ WC2026 fixtures:  {len(df_fixtures)}")
    print(f"  ✓ WC2026 squad players: {len(df_players_squad)}")

    # ----------------------------------------------------
    # 2. PREPROCESSING & FEATURE ENGINEERING
    # ----------------------------------------------------
    print("\n[Step 2/7] Preprocessing and Feature Engineering...")
    df_train_engineered = engineer_features(df_train)
    
    # Train / Test splitting (historical vs 2022 World Cup test)
    train_mask = df_train_engineered['split'] == 'train'
    test_mask = df_train_engineered['split'] == 'test'
    
    # Preprocessor initialization and fitting
    preprocessor = ATLASPreprocessor()
    preprocessor.fit(df_train_engineered[train_mask], FINAL_FEATURES)
    preprocessor.save(MOD / "preprocessor.pkl")
    
    # Transform matrices
    X_train = df_train_engineered.loc[train_mask, FINAL_FEATURES].values
    X_train_scaled = preprocessor.transform(df_train_engineered[train_mask])
    y_train = df_train_engineered.loc[train_mask, 'result_code'].values.astype(int)
    
    X_test = df_train_engineered.loc[test_mask, FINAL_FEATURES].values
    X_test_scaled = preprocessor.transform(df_train_engineered[test_mask])
    y_test = df_train_engineered.loc[test_mask, 'result_code'].values.astype(int)
    
    print(f"  ✓ Training sample matrix shape: {X_train.shape}")
    print(f"  ✓ Test sample matrix shape:     {X_test.shape}")
    print("  ✓ Saved preprocessor.pkl to output/models/")

    # ----------------------------------------------------
    # 3. TRAINING & EVALUATION
    # ----------------------------------------------------
    print("\n[Step 3/7] Training Core Predictors...")
    trainer = ATLASModelTrainer(random_state=RANDOM_STATE)
    trainer.train_and_cross_validate(X_train, y_train, X_train_scaled)
    trainer.save_models(MOD)
    
    print("\n[Step 4/7] Evaluating Classifiers & Stacking Ensembles...")
    evaluator = ATLASModelEvaluator(trainer.models, trainer.cv_results)
    df_comparison = evaluator.evaluate(X_test, y_test, X_test_scaled)
    df_comparison.to_csv(RES / "model_comparison.csv", index=False)
    
    best_name, best_model = evaluator.get_best_model(df_comparison)
    print(f"  ★ Best Performing Model: {best_name}")
    print(df_comparison[['Model', 'Accuracy', 'Brier Score', 'Log Loss']].to_string(index=False))
    
    # Classification report & McNemar significance tests
    report = evaluator.generate_classification_report(best_name, X_test, y_test, X_test_scaled)
    pd.DataFrame(report).T.to_csv(RES / "best_model_classification_report.csv")
    
    df_sig = evaluator.run_significance_tests(best_name, y_test)
    df_sig.to_csv(RES / "statistical_significance.csv", index=False)
    print("  ✓ Saved evaluation reports to output/results/")

    # ----------------------------------------------------
    # 4. WC 2026 MATCH PREDICTIONS
    # ----------------------------------------------------
    print("\n[Step 5/7] Forecasting World Cup 2026 Matches...")
    # Initialize Predictor Engine
    predictor_engine = ATLASPredictor(best_model, preprocessor)
    
    # Generate fixture predictions
    df_predictions = generate_wc2026_predictions(
        predictor_engine, df_fixture_feats, trainer.models, preprocessor.scaler
    )
    df_predictions.to_csv(RES / "wc2026_predictions.csv", index=False)
    
    # Compute group standings
    df_standings = compute_group_standings(df_predictions, df_fixtures)
    df_standings.to_csv(RES / "wc2026_group_standings.csv", index=False)
    
    print("  ✓ Generated predictions for all 72 group stage matches.")
    print("  ✓ Saved wc2026_predictions.csv and wc2026_group_standings.csv to output/results/")

    # ----------------------------------------------------
    # 5. MONTE CARLO SIMULATION
    # ----------------------------------------------------
    print("\n[Step 6/7] Running Monte Carlo Tournament Simulations...")
    # Set up simulator inputs
    from src.predictions.group_standings import extract_groups_from_fixtures
    groups = extract_groups_from_fixtures(df_fixtures)
    
    # Build lookup
    fixture_probs_lookup = {}
    for _, row in df_predictions.iterrows():
        key = (row['home_team'], row['away_team'])
        fixture_probs_lookup[key] = [row['away_win_prob'], row['draw_prob'], row['home_win_prob']]
        
    team_elos = dict(zip(df_team_str['team'], df_team_str['current_elo']))
    all_teams = sorted(set(df_fixtures['home_team']) | set(df_fixtures['away_team']))
    
    n_simulations = 10000
    simulator = ATLASMonteCarloSimulator(groups, fixture_probs_lookup, team_elos, all_teams)
    df_sim = simulator.run_simulations(n_simulations=n_simulations, show_progress=False)
    df_sim.to_csv(RES / "wc2026_simulation_results.csv", index=False)
    
    print("  ✓ Ran 10,000 Monte Carlo runs.")
    print("  ✓ Saved wc2026_simulation_results.csv to output/results/")
    print("\n  Top 5 Champions Probability:")
    for _, row in df_sim.head(5).iterrows():
        print(f"    - {row['Team']}: {row['Champion %']}%")

    # ----------------------------------------------------
    # 6. PLAYER INTELLIGENCE
    # ----------------------------------------------------
    print("\n[Step 7/7] Grading Players & Injury Scenarios...")
    df_ps_graded = calculate_player_impact_scores(df_players_squad)
    
    df_top50 = df_ps_graded.nlargest(50, 'impact_score')[
        ['player_name', 'team', 'impact_score', 'xg_p90', 'goals_p90',
         'key_passes_p90', 'interceptions_p90', 'prog_carries_p90', 'pass_accuracy']
    ].reset_index(drop=True)
    df_top50.to_csv(RES / "player_impact_scores_top50.csv", index=False)
    
    df_ps_graded[['player_id', 'player_name', 'team', 'impact_score',
                  'xg_p90', 'goals_p90', 'key_passes_p90', 'interceptions_p90']].to_csv(
        RES / "player_impact_scores_all.csv", index=False
    )
    
    df_team_breakdown = aggregate_team_strength(df_ps_graded, df_team_str)
    df_team_breakdown.to_csv(RES / "team_strength_breakdown.csv", index=False)
    
    df_injuries = simulate_injury_scenarios(df_ps_graded, top_n_players=10)
    df_injuries.to_csv(RES / "what_if_injuries.csv", index=False)
    
    print("  ✓ Scored player stats and squad profiles.")
    print("  ✓ Saved player grades and what-if injury scenarios to output/results/")

    # ----------------------------------------------------
    # 7. EXPLAINABLE AI (SHAP)
    # ----------------------------------------------------
    print("\nGenerating SHAP Explanations...")
    # Initialize explainability wrapper
    # Map feature names
    feature_names = FINAL_FEATURES
    joblib.dump(feature_names, MOD / "feature_names.pkl")
    
    # We can run TreeExplainer on the best tree-based model
    shap_explainer = ATLASShapExplainer(best_model, best_name, trainer.models, feature_names)
    
    # Compute global shap values on test set
    shap_values = shap_explainer.compute_shap_values(X_test)
    df_shap_fi = shap_explainer.get_global_importance(shap_values)
    df_shap_fi.to_csv(RES / "shap_feature_importance.csv", index=False)
    
    # Compute local match-prediction narratives for all 72 fixtures
    from src.predictions.wc2026_predictor import build_wc2026_features_df
    df_wc_mapped = build_wc2026_features_df(df_fixture_feats)
    df_wc_engineered = engineer_features(df_wc_mapped)
    X_wc2026 = df_wc_engineered[FINAL_FEATURES].values
    X_wc2026 = np.nan_to_num(X_wc2026, nan=0.0)
    
    df_narratives = generate_prediction_narratives(shap_explainer, df_predictions, X_wc2026, feature_names)
    df_narratives.to_csv(RES / "prediction_explanations.csv", index=False)
    
    print("  ✓ Completed SHAP explainability analyses.")
    print("  ✓ Saved shap_feature_importance.csv and prediction_explanations.csv to output/results/")

    # ----------------------------------------------------
    # 8. JSON EXPORT FOR FRONTEND
    # ----------------------------------------------------
    print("\nExporting static JSON API for Frontend...")
    
    # 1. Predictions API
    predictions_json = {
        'model': best_name,
        'accuracy_on_test': float(df_comparison.loc[df_comparison['Model'] == best_name, 'Accuracy'].iloc[0]),
        'generated_at': datetime.now().isoformat(),
        'predictions': df_predictions.to_dict('records'),
    }
    with open(JSN / "predictions.json", 'w') as f:
        json.dump(predictions_json, f, indent=2, default=str)
        
    # 2. Simulations API
    simulations_json = {
        'n_simulations': n_simulations,
        'results': df_sim.to_dict('records'),
    }
    with open(JSN / "simulations.json", 'w') as f:
        json.dump(simulations_json, f, indent=2, default=str)
        
    # 3. Players API
    players_json = {
        'top50': df_top50.to_dict('records'),
        'team_strength': df_team_breakdown.to_dict('records'),
    }
    with open(JSN / "players.json", 'w') as f:
        json.dump(players_json, f, indent=2, default=str)
        
    # 4. Explanations API
    explanations_json = {
        'feature_importance': df_shap_fi.head(20).to_dict('records'),
        'match_explanations': df_narratives.to_dict('records'),
    }
    with open(JSN / "explanations.json", 'w') as f:
        json.dump(explanations_json, f, indent=2, default=str)
        
    # 5. Model Comparison API
    model_comp_json = {
        'models': df_comparison.to_dict('records'),
        'best_model': best_name,
    }
    with open(JSN / "model_comparison.json", 'w') as f:
        json.dump(model_comp_json, f, indent=2, default=str)
        
    # 6. Group Standings API
    standings_json = {}
    for label, group_df in df_standings.groupby('Group'):
        standings_json[f"Group {label}"] = group_df.drop(columns=['Group']).to_dict('records')
    with open(JSN / "group_standings.json", 'w') as f:
        json.dump(standings_json, f, indent=2, default=str)
        
    print("  ✓ Exported all JSON endpoints to output/json/")
    print("\n" + "=" * 70)
    print("ATLAS Modular Production Pipeline Run Successful!")
    print("=" * 70)

if __name__ == '__main__':
    main()
