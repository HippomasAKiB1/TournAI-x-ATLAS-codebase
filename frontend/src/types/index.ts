export interface Prediction {
  fixture_id: number;
  date: string;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  predicted_result: 'Home Win' | 'Draw' | 'Away Win';
  confidence: number;
  elo_diff: number;
  ensemble_home_win: number;
  ensemble_draw: number;
  ensemble_away_win: number;
}

export interface PredictionsResponse {
  model: string;
  accuracy_on_test: number;
  generated_at: string;
  predictions: Prediction[];
}

export interface SimulationResult {
  Team: string;
  "Champion %": number;
  "Finalist %": number;
  "Semi-Final %": number;
  "Quarter-Final %": number;
  "Round of 16 %": number;
  "Round of 32 %": number;
  "Group Exit %": number;
}

export interface SimulationsResponse {
  n_simulations: number;
  results: SimulationResult[];
}

export interface Player {
  player_name: string;
  team: string;
  impact_score: number;
  xg_p90: number;
  goals_p90: number;
  key_passes_p90: number;
  interceptions_p90: number;
  prog_carries_p90: number;
  pass_accuracy: number;
}

export interface TeamStrength {
  team: string;
  avg_impact: number;
  max_impact: number;
  squad_size: number;
  top5_avg: number;
  depth: number;
  current_elo: number | null;
  form_10: number | null;
}

export interface PlayersResponse {
  top50: Player[];
  team_strength: TeamStrength[];
}

export interface FeatureImportance {
  feature: string;
  shap_importance: number;
}

export interface MatchExplanation {
  fixture_id: number;
  match: string;
  prediction: string;
  reason_1: string;
  reason_2: string;
  reason_3: string;
}

export interface ExplanationsResponse {
  feature_importance: FeatureImportance[];
  match_explanations: MatchExplanation[];
}

export interface ModelMetric {
  Model: string;
  Accuracy: number;
  "Balanced Acc": number;
  "F1 Macro": number;
  "F1 Weighted": number;
  "Cohen Kappa": number;
  MCC: number;
  "Log Loss": number;
  "Brier Score": number;
  "ROC AUC": number;
  "CV Mean": number | null;
  "CV Std": number | null;
}

export interface ModelComparisonResponse {
  models: ModelMetric[];
  best_model: string;
}

export interface GroupStandingRow {
  Position: number;
  Team: string;
  MP: number;
  W: number;
  D: number;
  L: number;
  GF: number;
  GA: number;
  GD: number;
  Pts: number;
  Qualifies: string;
}

export interface GroupStandingsResponse {
  [groupName: string]: GroupStandingRow[];
}

export interface InjuryScenario {
  Player: string;
  Team: string;
  "Impact Score": number;
  "Team Avg (with)": number;
  "Team Avg (without)": number;
  "Strength Drop %": number;
}
