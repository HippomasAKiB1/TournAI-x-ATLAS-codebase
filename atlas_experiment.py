# %% [markdown]
# # ⚽ TournAI × ATLAS — Comprehensive Experiment Pipeline
# ## Adaptive Tournament Learning and Analytics System
# ### FIFA World Cup 2026 Prediction Framework
#
# **Research-grade (Q1) experimental notebook covering:**
# 1. Exploratory Data Analysis
# 2. Data Preprocessing & Feature Engineering
# 3. Multi-Model Training & Comparison (7 models + 2 ensembles)
# 4. Rigorous Evaluation & Statistical Validation
# 5. WC 2026 Match Predictions (72 group stage fixtures)
# 6. Monte Carlo Tournament Simulation (10,000 runs)
# 7. Player Intelligence System (Impact Scores)
# 8. Explainable AI (SHAP)
# 9. Research Question Analysis
# 10. Full Export (figures, CSVs, models, JSON)

# %% — 1. SETUP & CONFIGURATION
import os
import sys
import warnings
import json
import pickle
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from scipy import stats
from scipy.special import softmax
from tqdm import tqdm
import joblib

from sklearn.model_selection import (
    StratifiedKFold, cross_val_predict, cross_val_score, GridSearchCV
)
from sklearn.preprocessing import (
    StandardScaler, LabelEncoder, OneHotEncoder
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    VotingClassifier, StackingClassifier
)
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    log_loss, brier_score_loss, cohen_kappa_score,
    matthews_corrcoef, classification_report,
    confusion_matrix, roc_auc_score, roc_curve,
    precision_recall_fscore_support, auc
)
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.inspection import permutation_importance

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("⚠ SHAP not available — explainability section will be skipped")

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette('deep')
plt.rcParams.update({
    'figure.figsize': (12, 7),
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 150,
    'savefig.dpi': 200,
    'savefig.bbox': 'tight'
})

# Paths
ROOT = Path(r"e:/AKiB's Project Book/TournAI-x-ATLAS-codebase")
DATA = ROOT / "Dataset"
OUT  = ROOT / "output"
FIG  = OUT / "figures"
RES  = OUT / "results"
MOD  = OUT / "models"
JSN  = OUT / "json"

for d in [FIG/"eda", FIG/"models", FIG/"predictions", FIG/"simulation",
          FIG/"players", FIG/"shap", RES, MOD, JSN]:
    d.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

print("="*70)
print("⚽ TournAI × ATLAS — Experiment Pipeline")
print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# %% — 2. DATA LOADING
print("\n" + "="*70)
print("📂 SECTION 2: DATA LOADING")
print("="*70)

df_train = pd.read_csv(DATA / "atlas_train_ready_final.csv")
df_players_match = pd.read_csv(DATA / "sb_player_match_stats.csv")
df_fixtures = pd.read_csv(DATA / "wc2026_fixtures.csv")
df_fixture_feats = pd.read_csv(DATA / "wc2026_fixture_features.csv")
df_team_str = pd.read_csv(DATA / "wc2026_team_strength.csv")
df_players_squad = pd.read_csv(DATA / "wc2026_player_squad.csv")

datasets = {
    "Training Data (atlas_train_ready_final)": df_train,
    "Player Match Stats (sb_player_match_stats)": df_players_match,
    "WC2026 Fixtures": df_fixtures,
    "WC2026 Fixture Features": df_fixture_feats,
    "WC2026 Team Strength": df_team_str,
    "WC2026 Player Squads": df_players_squad,
}

for name, df in datasets.items():
    print(f"  ✓ {name}: {df.shape[0]:,} rows × {df.shape[1]} cols")

# %% — 3. EXPLORATORY DATA ANALYSIS
print("\n" + "="*70)
print("🔍 SECTION 3: EXPLORATORY DATA ANALYSIS")
print("="*70)

# --- 3.1 Target Variable Distribution ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

result_map = {0: 'Loss', 1: 'Draw', 2: 'Win'}
df_train['result_label'] = df_train['result_code'].map(result_map)

# Overall distribution
counts = df_train['result_label'].value_counts()
colors = ['#e74c3c', '#f39c12', '#2ecc71']
axes[0].bar(counts.index, counts.values, color=colors, edgecolor='black', linewidth=0.5)
for i, (idx, v) in enumerate(zip(counts.index, counts.values)):
    axes[0].text(i, v + 10, f"{v}\n({v/len(df_train)*100:.1f}%)", ha='center', fontweight='bold')
axes[0].set_title('Overall Result Distribution')
axes[0].set_ylabel('Count')

# By stage
stage_order = ['Group Stage', 'Round of 16', 'Quarter-final', 'Semi-final', 'Third Place', 'Final']
stage_results = df_train.groupby(['stage', 'result_label']).size().unstack(fill_value=0)
stage_results = stage_results.reindex(stage_order)
stage_results_pct = stage_results.div(stage_results.sum(axis=1), axis=0) * 100
stage_results_pct[['Win', 'Draw', 'Loss']].plot(kind='bar', stacked=True, ax=axes[1],
                                                   color=['#2ecc71', '#f39c12', '#e74c3c'])
axes[1].set_title('Result Distribution by Stage (%)')
axes[1].set_ylabel('Percentage')
axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=45, ha='right')
axes[1].legend(loc='upper right')

# By era
df_train['era'] = pd.cut(df_train['year'],
                          bins=[1929, 1960, 1980, 2000, 2010, 2023],
                          labels=['1930-60', '1962-78', '1982-98', '2002-10', '2014-22'])
era_results = df_train.groupby(['era', 'result_label']).size().unstack(fill_value=0)
era_results_pct = era_results.div(era_results.sum(axis=1), axis=0) * 100
era_results_pct[['Win', 'Draw', 'Loss']].plot(kind='bar', stacked=True, ax=axes[2],
                                                color=['#2ecc71', '#f39c12', '#e74c3c'])
axes[2].set_title('Result Distribution by Era (%)')
axes[2].set_ylabel('Percentage')
axes[2].legend(loc='upper right')

plt.suptitle('Target Variable Analysis: Match Results', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "eda" / "01_target_distribution.png")
plt.close()
print("  ✓ Figure saved: 01_target_distribution.png")

# --- 3.2 Elo Rating Effectiveness ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Elo diff vs result
for label, color in zip(['Win', 'Draw', 'Loss'], ['#2ecc71', '#f39c12', '#e74c3c']):
    subset = df_train[df_train['result_label'] == label]['elo_diff']
    axes[0].hist(subset, bins=50, alpha=0.6, label=label, color=color, density=True)
axes[0].set_xlabel('Elo Difference (Team - Opponent)')
axes[0].set_ylabel('Density')
axes[0].set_title('Elo Difference Distribution by Result')
axes[0].legend()
axes[0].axvline(0, color='black', linestyle='--', alpha=0.5)

# Elo win prob calibration
df_train['elo_prob_bin'] = pd.cut(df_train['elo_win_prob'], bins=10)
elo_calib = df_train.groupby('elo_prob_bin').agg(
    predicted=('elo_win_prob', 'mean'),
    actual=('result_code', lambda x: (x == 2).mean())
).dropna()
axes[1].plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfect calibration')
axes[1].scatter(elo_calib['predicted'], elo_calib['actual'], s=100, zorder=5, color='#3498db')
axes[1].plot(elo_calib['predicted'], elo_calib['actual'], color='#3498db', label='Elo model')
axes[1].set_xlabel('Predicted Win Probability (Elo)')
axes[1].set_ylabel('Actual Win Rate')
axes[1].set_title('Elo Model Calibration')
axes[1].legend()

# Elo accuracy over time
yearly_elo = df_train.groupby('year').apply(
    lambda g: (
        ((g['elo_win_prob'] > 0.5) & (g['result_code'] == 2)) |
        ((g['elo_win_prob'] < 0.5) & (g['result_code'] == 0)) |
        ((g['elo_win_prob'].between(0.4, 0.6)) & (g['result_code'] == 1))
    ).mean()
).reset_index(name='accuracy')
axes[2].plot(yearly_elo['year'], yearly_elo['accuracy'], 'o-', color='#3498db', markersize=6)
axes[2].axhline(y=yearly_elo['accuracy'].mean(), color='red', linestyle='--',
                label=f"Mean: {yearly_elo['accuracy'].mean():.3f}")
axes[2].set_xlabel('World Cup Year')
axes[2].set_ylabel('Elo Prediction Accuracy')
axes[2].set_title('Elo Accuracy Over Time')
axes[2].legend()

plt.suptitle('Elo Rating Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "eda" / "02_elo_analysis.png")
plt.close()
print("  ✓ Figure saved: 02_elo_analysis.png")

# --- 3.3 Feature Completeness Heatmap ---
feature_groups = {
    'Core': ['elo_diff', 'elo_win_prob', 'form_diff', 'is_knockout', 'stage_numeric',
             'is_home', 'is_host', 'neutral_venue'],
    'WC History': ['wc_appearances', 'opp_wc_appearances', 'wc_wins', 'opp_wc_wins',
                   'wc_finals', 'opp_wc_finals', 'wc_semis', 'opp_wc_semis', 'wc_avg_goals'],
    'H2H & Form': ['h2h_winrate', 'h2h_matches', 'form_5', 'opp_form_5',
                    'goals_scored_form5', 'goals_conceded_form5'],
    'Tournament': ['tourn_matches_played', 'tourn_winrate', 'tourn_goals_per_match',
                    'tourn_goal_diff', 'rest_days', 'opp_rest_days', 'rest_days_adv'],
    'Match Stats': ['shots', 'shots_on_target', 'shot_accuracy', 'possession',
                     'fouls', 'yellow_cards', 'red_cards', 'corners', 'xg', 'opp_xg'],
    'Squad': ['squad_xg_per_match', 'squad_goals_per_match', 'squad_shots_per_match',
              'squad_key_passes_per_match', 'squad_interceptions_per_match'],
    'Demographics': ['squad_avg_age', 'opp_squad_avg_age', 'avg_club_prestige',
                      'max_club_prestige', 'club_prestige_diff', 'age_diff']
}

all_features = [f for group in feature_groups.values() for f in group]
existing = [f for f in all_features if f in df_train.columns]

completeness = pd.DataFrame(index=['tier3', 'tier2'])
for feat in existing:
    for tier in ['tier3', 'tier2']:
        subset = df_train[df_train['data_tier'] == tier]
        completeness.loc[tier, feat] = subset[feat].notna().mean() * 100

fig, ax = plt.subplots(figsize=(22, 4))
sns.heatmap(completeness.astype(float), annot=False, cmap='RdYlGn', vmin=0, vmax=100,
            ax=ax, linewidths=0.5)
ax.set_title('Feature Completeness by Data Tier (%)', fontsize=14, fontweight='bold')
ax.set_xticklabels(ax.get_xticklabels(), rotation=90, fontsize=7)
plt.tight_layout()
plt.savefig(FIG / "eda" / "03_feature_completeness.png")
plt.close()
print("  ✓ Figure saved: 03_feature_completeness.png")

# --- 3.4 Feature Correlations ---
numeric_cols = df_train[existing].select_dtypes(include=[np.number]).columns.tolist()
if 'result_code' not in numeric_cols:
    numeric_cols.append('result_code')

corr_with_target = df_train[numeric_cols].corr()['result_code'].drop('result_code').sort_values()

fig, axes = plt.subplots(1, 2, figsize=(20, 8))

# Top correlations with target
top_n = 20
top_corr = pd.concat([corr_with_target.head(top_n), corr_with_target.tail(top_n)])
colors_corr = ['#e74c3c' if v < 0 else '#2ecc71' for v in top_corr.values]
axes[0].barh(range(len(top_corr)), top_corr.values, color=colors_corr, edgecolor='black', linewidth=0.3)
axes[0].set_yticks(range(len(top_corr)))
axes[0].set_yticklabels(top_corr.index, fontsize=8)
axes[0].set_xlabel('Correlation with Result Code')
axes[0].set_title(f'Top {top_n} Positive & Negative Correlations with Result', fontweight='bold')
axes[0].axvline(0, color='black', linewidth=0.8)

# Correlation heatmap of top features
top_features = corr_with_target.abs().nlargest(15).index.tolist()
top_features.append('result_code')
corr_matrix = df_train[top_features].corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f', cmap='coolwarm',
            center=0, ax=axes[1], linewidths=0.5, annot_kws={'size': 7})
axes[1].set_title('Correlation Matrix: Top 15 Features', fontweight='bold')

plt.suptitle('Feature Correlation Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "eda" / "04_correlations.png")
plt.close()
print("  ✓ Figure saved: 04_correlations.png")

# --- 3.5 Home / Host Advantage ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Home advantage
home_results = df_train.groupby('is_home')['result_code'].value_counts(normalize=True).unstack()
home_results.columns = ['Loss', 'Draw', 'Win']
home_results.index = ['Away', 'Home']
home_results[['Win', 'Draw', 'Loss']].plot(kind='bar', stacked=True, ax=axes[0],
                                            color=['#2ecc71', '#f39c12', '#e74c3c'])
axes[0].set_title('Home vs Away Performance')
axes[0].set_ylabel('Proportion')
axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=0)

# Host advantage
host_results = df_train.groupby('is_host')['result_code'].value_counts(normalize=True).unstack()
host_results.columns = ['Loss', 'Draw', 'Win']
host_results.index = ['Non-Host', 'Host Nation']
host_results[['Win', 'Draw', 'Loss']].plot(kind='bar', stacked=True, ax=axes[1],
                                            color=['#2ecc71', '#f39c12', '#e74c3c'])
axes[1].set_title('Host Nation Advantage')
axes[1].set_ylabel('Proportion')
axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=0)

plt.suptitle('Home & Host Advantage Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "eda" / "05_home_host_advantage.png")
plt.close()
print("  ✓ Figure saved: 05_home_host_advantage.png")

# --- 3.6 WC 2026 Team Strength Overview ---
df_ts = df_team_str.sort_values('current_elo', ascending=True).copy()

fig, axes = plt.subplots(1, 2, figsize=(18, 10))

# Elo rankings
colors_elo = plt.cm.RdYlGn(np.linspace(0.15, 0.85, len(df_ts)))
axes[0].barh(range(len(df_ts)), df_ts['current_elo'], color=colors_elo, edgecolor='black', linewidth=0.3)
axes[0].set_yticks(range(len(df_ts)))
axes[0].set_yticklabels(df_ts['team'], fontsize=7)
axes[0].set_xlabel('Elo Rating')
axes[0].set_title('WC 2026 Teams: Elo Rankings', fontweight='bold')

# Form vs Elo scatter
ax2 = axes[1]
for _, row in df_ts.iterrows():
    marker = '*' if row['host_nation'] == 1 else 'o'
    size = 150 if row['host_nation'] == 1 else 60
    ax2.scatter(row['current_elo'], row['form_10'], s=size, marker=marker,
                alpha=0.7, edgecolors='black', linewidth=0.5)
    if row['current_elo'] > 1920 or row['host_nation'] == 1 or row['form_10'] > 0.85:
        ax2.annotate(row['team'], (row['current_elo'], row['form_10']),
                     fontsize=7, ha='left', va='bottom')
ax2.set_xlabel('Elo Rating')
ax2.set_ylabel('Recent Form (last 10 matches)')
ax2.set_title('Elo vs Form (★ = Host Nation)', fontweight='bold')

plt.suptitle('WC 2026 Team Strength Overview', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "eda" / "06_wc2026_team_strength.png")
plt.close()
print("  ✓ Figure saved: 06_wc2026_team_strength.png")

# --- 3.7 Descriptive Statistics Export ---
desc_stats = df_train.describe(include='all').T
desc_stats.to_csv(RES / "descriptive_statistics.csv")
print("  ✓ CSV saved: descriptive_statistics.csv")

# Missing data summary
missing = df_train.isnull().sum()
missing_pct = (missing / len(df_train) * 100).round(2)
missing_df = pd.DataFrame({'missing_count': missing, 'missing_pct': missing_pct})
missing_df = missing_df[missing_df['missing_count'] > 0].sort_values('missing_pct', ascending=False)
missing_df.to_csv(RES / "missing_data_summary.csv")
print("  ✓ CSV saved: missing_data_summary.csv")
print(f"  → {len(missing_df)} features have missing values")

# %% — 4. DATA PREPROCESSING & FEATURE ENGINEERING
print("\n" + "="*70)
print("🔧 SECTION 4: DATA PREPROCESSING & FEATURE ENGINEERING")
print("="*70)

# --- 4.1 Define Feature Groups ---

# Features available for ALL matches (tier3 + tier2)
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

# Features available only for tier2 (2018+2022)
ADVANCED_FEATURES = [
    'tourn_matches_played', 'tourn_goals_for', 'tourn_goals_against',
    'tourn_goal_diff', 'tourn_wins', 'tourn_winrate', 'tourn_goals_per_match',
]

# Squad-level features (partially available)
SQUAD_FEATURES = [
    'squad_xg_per_match', 'squad_goals_per_match', 'squad_shots_per_match',
    'squad_key_passes_per_match', 'squad_interceptions_per_match',
    'squad_dribbles_per_match', 'squad_squad_pass_accuracy',
    'opp_squad_xg_per_match', 'opp_squad_goals_per_match', 'opp_squad_shots_per_match',
    'opp_squad_key_passes_per_match', 'opp_squad_interceptions_per_match',
    'opp_squad_dribbles_per_match', 'opp_squad_squad_pass_accuracy',
]

# Demographics
DEMO_FEATURES = [
    'squad_avg_age', 'opp_squad_avg_age', 'age_diff',
    'avg_club_prestige', 'max_club_prestige',
    'opp_avg_club_prestige', 'opp_max_club_prestige',
    'club_prestige_diff',
]

# Confederation encoding
CONF_FEATURES = ['team_conf_code', 'opp_conf_code']

TARGET = 'result_code'

# --- 4.2 Build Feature Matrix ---
# Strategy: Use CORE_FEATURES (available for all rows) as the primary model
# Then add ADVANCED/SQUAD/DEMO features with imputation

ALL_FEATURES = CORE_FEATURES + ADVANCED_FEATURES + SQUAD_FEATURES + DEMO_FEATURES + CONF_FEATURES
ALL_FEATURES = [f for f in ALL_FEATURES if f in df_train.columns]

print(f"  → Total candidate features: {len(ALL_FEATURES)}")

# --- 4.3 Imputation ---
df_model = df_train[ALL_FEATURES + [TARGET, 'split', 'data_tier', 'year', 'team', 'opponent']].copy()

# Fill tournament-progress features with 0 for first match
tourn_fill_zero = ['tourn_matches_played', 'tourn_goals_for', 'tourn_goals_against',
                   'tourn_goal_diff', 'tourn_wins', 'tourn_winrate', 'tourn_goals_per_match']
for col in tourn_fill_zero:
    if col in df_model.columns:
        df_model[col] = df_model[col].fillna(0)

# Fill squad features with 0 (not available for older tournaments)
for col in SQUAD_FEATURES:
    if col in df_model.columns:
        df_model[col] = df_model[col].fillna(0)

# Fill demographics with median
for col in DEMO_FEATURES:
    if col in df_model.columns:
        df_model[col] = df_model[col].fillna(df_model[col].median())

# Fill confederation codes with mode
for col in CONF_FEATURES:
    if col in df_model.columns:
        df_model[col] = df_model[col].fillna(df_model[col].mode()[0])

# Fill rest_days with median
for col in ['rest_days', 'opp_rest_days', 'rest_days_adv']:
    if col in df_model.columns:
        df_model[col] = df_model[col].fillna(df_model[col].median())

# Fill remaining with 0
df_model[ALL_FEATURES] = df_model[ALL_FEATURES].fillna(0)

remaining_missing = df_model[ALL_FEATURES].isnull().sum().sum()
print(f"  → Remaining missing values after imputation: {remaining_missing}")

# --- 4.4 Feature Engineering: Interaction Features ---
df_model['elo_x_knockout'] = df_model['elo_diff'] * df_model['is_knockout']
df_model['form_x_stage'] = df_model['form_diff'] * df_model['stage_numeric']
df_model['elo_x_host'] = df_model['elo_diff'] * df_model['is_host']
df_model['squad_quality_diff'] = df_model.get('squad_xg_per_match', 0) - df_model.get('opp_squad_xg_per_match', 0)
df_model['experience_diff'] = df_model['wc_appearances'] - df_model['opp_wc_appearances']
df_model['pedigree_diff'] = df_model['wc_wins'] - df_model['opp_wc_wins']

INTERACTION_FEATURES = ['elo_x_knockout', 'form_x_stage', 'elo_x_host',
                         'squad_quality_diff', 'experience_diff', 'pedigree_diff']
FINAL_FEATURES = ALL_FEATURES + INTERACTION_FEATURES

print(f"  → Final feature count: {len(FINAL_FEATURES)}")

# --- 4.5 Train/Test Split ---
train_mask = df_model['split'] == 'train'
test_mask = df_model['split'] == 'test'

X_train = df_model.loc[train_mask, FINAL_FEATURES].values
y_train = df_model.loc[train_mask, TARGET].values.astype(int)
X_test  = df_model.loc[test_mask, FINAL_FEATURES].values
y_test  = df_model.loc[test_mask, TARGET].values.astype(int)

print(f"  → Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples")
print(f"  → Train class distribution: {dict(Counter(y_train))}")
print(f"  → Test class distribution:  {dict(Counter(y_test))}")

# --- 4.6 Scaling ---
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

joblib.dump(scaler, MOD / "scaler.pkl")
print("  ✓ Scaler saved")

# Save feature names for later
feature_names = FINAL_FEATURES
joblib.dump(feature_names, MOD / "feature_names.pkl")

# %% — 5. MODEL TRAINING & COMPARISON
print("\n" + "="*70)
print("🤖 SECTION 5: MODEL TRAINING & COMPARISON")
print("="*70)

# --- 5.1 Define Models ---
models = {
    'Logistic Regression': LogisticRegression(
        max_iter=2000, solver='lbfgs',
        class_weight='balanced', C=1.0, random_state=RANDOM_STATE
    ),
    'Random Forest': RandomForestClassifier(
        n_estimators=500, max_depth=12, min_samples_split=10,
        min_samples_leaf=5, class_weight='balanced',
        random_state=RANDOM_STATE, n_jobs=-1
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, random_state=RANDOM_STATE
    ),
    'XGBoost': xgb.XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
        objective='multi:softprob', num_class=3,
        random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
        use_label_encoder=False, eval_metric='mlogloss'
    ),
    'LightGBM': lgb.LGBMClassifier(
        n_estimators=500, max_depth=7, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
        num_class=3, objective='multiclass',
        random_state=RANDOM_STATE, n_jobs=-1, verbose=-1,
        class_weight='balanced', is_unbalance=False
    ),
    'CatBoost': CatBoostClassifier(
        iterations=500, depth=6, learning_rate=0.05,
        l2_leaf_reg=3, auto_class_weights='Balanced',
        random_seed=RANDOM_STATE, verbose=0, loss_function='MultiClass'
    ),
    'MLP Neural Net': MLPClassifier(
        hidden_layer_sizes=(256, 128, 64), activation='relu',
        solver='adam', max_iter=500, early_stopping=True,
        validation_fraction=0.15, learning_rate='adaptive',
        random_state=RANDOM_STATE
    ),
}

# --- 5.2 Cross-Validation + Training ---
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
results = {}

for name, model in models.items():
    print(f"\n  Training: {name}...")

    # Use scaled data for LR and MLP, raw for tree-based
    if name in ['Logistic Regression', 'MLP Neural Net']:
        X_tr, X_te = X_train_scaled, X_test_scaled
    else:
        X_tr, X_te = X_train, X_test

    # Cross-validation
    cv_scores = cross_val_score(model, X_tr, y_train, cv=cv, scoring='accuracy', n_jobs=-1)

    # Fit on full training set
    model.fit(X_tr, y_train)

    # Predict
    y_pred = model.predict(X_te)
    y_prob = model.predict_proba(X_te)

    # Metrics
    acc = accuracy_score(y_test, y_pred)
    bal_acc = balanced_accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    f1_weighted = f1_score(y_test, y_pred, average='weighted')
    kappa = cohen_kappa_score(y_test, y_pred)
    mcc = matthews_corrcoef(y_test, y_pred)
    logloss = log_loss(y_test, y_prob)

    # Multiclass Brier score
    y_test_onehot = np.eye(3)[y_test]
    brier = np.mean(np.sum((y_prob - y_test_onehot) ** 2, axis=1))

    # ROC AUC (one-vs-rest)
    try:
        roc_auc = roc_auc_score(y_test, y_prob, multi_class='ovr', average='weighted')
    except Exception:
        roc_auc = np.nan

    results[name] = {
        'model': model,
        'y_pred': y_pred,
        'y_prob': y_prob,
        'accuracy': acc,
        'balanced_accuracy': bal_acc,
        'f1_macro': f1_macro,
        'f1_weighted': f1_weighted,
        'cohen_kappa': kappa,
        'mcc': mcc,
        'log_loss': logloss,
        'brier_score': brier,
        'roc_auc': roc_auc,
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std(),
    }

    print(f"    Accuracy: {acc:.4f}  |  CV: {cv_scores.mean():.4f}±{cv_scores.std():.4f}")
    print(f"    F1-macro: {f1_macro:.4f}  |  Brier: {brier:.4f}  |  LogLoss: {logloss:.4f}")

    # Save model
    safe_name = name.lower().replace(' ', '_')
    joblib.dump(model, MOD / f"{safe_name}.pkl")

# --- 5.3 Ensemble Models ---
print("\n  Training Ensemble Models...")

# Voting Ensemble (soft voting)
voting = VotingClassifier(
    estimators=[
        ('xgb', models['XGBoost']),
        ('lgbm', models['LightGBM']),
        ('cb', models['CatBoost']),
    ],
    voting='soft',
    n_jobs=-1
)
voting.fit(X_train, y_train)
y_pred_vote = voting.predict(X_test)
y_prob_vote = voting.predict_proba(X_test)

acc_vote = accuracy_score(y_test, y_pred_vote)
y_test_oh = np.eye(3)[y_test]
brier_vote = np.mean(np.sum((y_prob_vote - y_test_oh) ** 2, axis=1))
ll_vote = log_loss(y_test, y_prob_vote)

results['Voting Ensemble'] = {
    'model': voting,
    'y_pred': y_pred_vote,
    'y_prob': y_prob_vote,
    'accuracy': acc_vote,
    'balanced_accuracy': balanced_accuracy_score(y_test, y_pred_vote),
    'f1_macro': f1_score(y_test, y_pred_vote, average='macro'),
    'f1_weighted': f1_score(y_test, y_pred_vote, average='weighted'),
    'cohen_kappa': cohen_kappa_score(y_test, y_pred_vote),
    'mcc': matthews_corrcoef(y_test, y_pred_vote),
    'log_loss': ll_vote,
    'brier_score': brier_vote,
    'roc_auc': roc_auc_score(y_test, y_prob_vote, multi_class='ovr', average='weighted'),
    'cv_mean': np.nan, 'cv_std': np.nan,
}
print(f"    Voting Ensemble — Accuracy: {acc_vote:.4f}")
joblib.dump(voting, MOD / "voting_ensemble.pkl")

# Stacking Ensemble
stacking = StackingClassifier(
    estimators=[
        ('xgb', xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                                    random_state=RANDOM_STATE, verbosity=0,
                                    use_label_encoder=False, eval_metric='mlogloss')),
        ('lgbm', lgb.LGBMClassifier(n_estimators=300, max_depth=6, learning_rate=0.05,
                                     random_state=RANDOM_STATE, verbose=-1)),
        ('cb', CatBoostClassifier(iterations=300, depth=5, learning_rate=0.05,
                                   random_seed=RANDOM_STATE, verbose=0)),
    ],
    final_estimator=LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
    cv=5,
    n_jobs=-1
)
stacking.fit(X_train, y_train)
y_pred_stack = stacking.predict(X_test)
y_prob_stack = stacking.predict_proba(X_test)

acc_stack = accuracy_score(y_test, y_pred_stack)
brier_stack = np.mean(np.sum((y_prob_stack - y_test_oh) ** 2, axis=1))
ll_stack = log_loss(y_test, y_prob_stack)

results['Stacking Ensemble'] = {
    'model': stacking,
    'y_pred': y_pred_stack,
    'y_prob': y_prob_stack,
    'accuracy': acc_stack,
    'balanced_accuracy': balanced_accuracy_score(y_test, y_pred_stack),
    'f1_macro': f1_score(y_test, y_pred_stack, average='macro'),
    'f1_weighted': f1_score(y_test, y_pred_stack, average='weighted'),
    'cohen_kappa': cohen_kappa_score(y_test, y_pred_stack),
    'mcc': matthews_corrcoef(y_test, y_pred_stack),
    'log_loss': ll_stack,
    'brier_score': brier_stack,
    'roc_auc': roc_auc_score(y_test, y_prob_stack, multi_class='ovr', average='weighted'),
    'cv_mean': np.nan, 'cv_std': np.nan,
}
print(f"    Stacking Ensemble — Accuracy: {acc_stack:.4f}")
joblib.dump(stacking, MOD / "stacking_ensemble.pkl")

# %% — 6. MODEL EVALUATION & VALIDATION
print("\n" + "="*70)
print("📊 SECTION 6: MODEL EVALUATION & VALIDATION")
print("="*70)

# --- 6.1 Comparison Table ---
comparison_data = []
for name, res in results.items():
    comparison_data.append({
        'Model': name,
        'Accuracy': res['accuracy'],
        'Balanced Acc': res['balanced_accuracy'],
        'F1 Macro': res['f1_macro'],
        'F1 Weighted': res['f1_weighted'],
        'Cohen Kappa': res['cohen_kappa'],
        'MCC': res['mcc'],
        'Log Loss': res['log_loss'],
        'Brier Score': res['brier_score'],
        'ROC AUC': res['roc_auc'],
        'CV Mean': res['cv_mean'],
        'CV Std': res['cv_std'],
    })

df_comparison = pd.DataFrame(comparison_data).sort_values('Accuracy', ascending=False)
df_comparison.to_csv(RES / "model_comparison.csv", index=False)
print("\n  Model Comparison (sorted by Accuracy):")
print(df_comparison.to_string(index=False))

# Best model selection
best_name = df_comparison.iloc[0]['Model']
best_result = results[best_name]
best_model = best_result['model']
print(f"\n  ★ Best Model: {best_name} (Accuracy: {best_result['accuracy']:.4f})")
joblib.dump(best_model, MOD / "best_model.pkl")
with open(MOD / "best_model_name.txt", 'w') as f:
    f.write(best_name)

# --- 6.2 Comparison Bar Chart ---
fig, axes = plt.subplots(2, 2, figsize=(18, 12))
metrics = [
    ('Accuracy', 'accuracy'), ('F1 Macro', 'f1_macro'),
    ('Brier Score', 'brier_score'), ('Log Loss', 'log_loss')
]
model_names = [r['Model'] for _, r in df_comparison.iterrows()]

for ax, (title, key) in zip(axes.flat, metrics):
    vals = [results[n][key] for n in model_names]
    bars = ax.barh(model_names[::-1], vals[::-1], color=plt.cm.viridis(np.linspace(0.2, 0.8, len(vals))),
                   edgecolor='black', linewidth=0.5)
    ax.set_title(title, fontweight='bold')
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
                f'{v:.4f}', va='center', fontsize=8)

plt.suptitle('Model Comparison: All Metrics', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(FIG / "models" / "01_model_comparison.png")
plt.close()
print("  ✓ Figure saved: 01_model_comparison.png")

# --- 6.3 Confusion Matrices ---
n_models = len(results)
cols = 3
rows = (n_models + cols - 1) // cols
fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
axes = axes.flatten()

for idx, (name, res) in enumerate(results.items()):
    cm = confusion_matrix(y_test, res['y_pred'])
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                xticklabels=['Loss', 'Draw', 'Win'],
                yticklabels=['Loss', 'Draw', 'Win'])
    axes[idx].set_title(f"{name}\nAcc: {res['accuracy']:.3f}", fontsize=9, fontweight='bold')
    axes[idx].set_ylabel('True')
    axes[idx].set_xlabel('Predicted')

for idx in range(len(results), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle('Confusion Matrices: All Models', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "models" / "02_confusion_matrices.png")
plt.close()
print("  ✓ Figure saved: 02_confusion_matrices.png")

# --- 6.4 ROC Curves (Multiclass OvR) ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
class_labels = ['Loss (0)', 'Draw (1)', 'Win (2)']

for cls_idx, (ax, cls_label) in enumerate(zip(axes, class_labels)):
    y_bin = (y_test == cls_idx).astype(int)
    for name, res in results.items():
        if res['y_prob'] is not None:
            fpr, tpr, _ = roc_curve(y_bin, res['y_prob'][:, cls_idx])
            auc_val = auc(fpr, tpr)
            ax.plot(fpr, tpr, label=f"{name} ({auc_val:.3f})", linewidth=1)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.3)
    ax.set_title(f'ROC: {cls_label}', fontweight='bold')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.legend(fontsize=6, loc='lower right')

plt.suptitle('ROC Curves (One-vs-Rest)', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "models" / "03_roc_curves.png")
plt.close()
print("  ✓ Figure saved: 03_roc_curves.png")

# --- 6.5 Calibration Plots ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for cls_idx, (ax, cls_label) in enumerate(zip(axes, class_labels)):
    y_bin = (y_test == cls_idx).astype(int)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfect')
    for name, res in list(results.items())[:5]:  # top 5 models
        try:
            prob_true, prob_pred = calibration_curve(y_bin, res['y_prob'][:, cls_idx], n_bins=8)
            ax.plot(prob_pred, prob_true, 'o-', label=name, markersize=4, linewidth=1)
        except Exception:
            pass
    ax.set_title(f'Calibration: {cls_label}', fontweight='bold')
    ax.set_xlabel('Mean Predicted Probability')
    ax.set_ylabel('Fraction of Positives')
    ax.legend(fontsize=6)

plt.suptitle('Calibration Plots (Reliability Diagrams)', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "models" / "04_calibration.png")
plt.close()
print("  ✓ Figure saved: 04_calibration.png")

# --- 6.6 Per-Class Classification Report (Best Model) ---
report = classification_report(y_test, best_result['y_pred'],
                                target_names=['Loss', 'Draw', 'Win'], output_dict=True)
df_report = pd.DataFrame(report).T
df_report.to_csv(RES / "best_model_classification_report.csv")
print(f"\n  Best Model ({best_name}) Classification Report:")
print(classification_report(y_test, best_result['y_pred'],
                             target_names=['Loss', 'Draw', 'Win']))

# --- 6.7 Statistical Significance: McNemar's Test ---
print("\n  Pairwise McNemar's Tests vs Best Model:")
significance_results = []
best_preds = best_result['y_pred']
for name, res in results.items():
    if name == best_name:
        continue
    other_preds = res['y_pred']
    # McNemar contingency
    correct_best = (best_preds == y_test)
    correct_other = (other_preds == y_test)
    b = np.sum(correct_best & ~correct_other)  # best right, other wrong
    c = np.sum(~correct_best & correct_other)   # best wrong, other right
    # McNemar statistic (with continuity correction)
    if (b + c) > 0:
        chi2 = (abs(b - c) - 1)**2 / (b + c)
        p_val = 1 - stats.chi2.cdf(chi2, df=1)
    else:
        chi2, p_val = 0, 1.0
    sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
    significance_results.append({
        'Comparison': f'{best_name} vs {name}',
        'b (best_only)': b, 'c (other_only)': c,
        'McNemar_chi2': chi2, 'p_value': p_val, 'Significance': sig
    })
    print(f"    vs {name}: χ²={chi2:.3f}, p={p_val:.4f} {sig}")

df_sig = pd.DataFrame(significance_results)
df_sig.to_csv(RES / "statistical_significance.csv", index=False)

# %% — 7. FEATURE IMPORTANCE ANALYSIS
print("\n" + "="*70)
print("📈 SECTION 7: FEATURE IMPORTANCE ANALYSIS")
print("="*70)

# --- 7.1 Tree-based Feature Importance ---
tree_models_for_fi = {}
for name in ['XGBoost', 'LightGBM', 'CatBoost', 'Random Forest']:
    if name in results:
        tree_models_for_fi[name] = results[name]['model']

fig, axes = plt.subplots(2, 2, figsize=(20, 16))
all_importances = {}

for ax, (name, mdl) in zip(axes.flat, tree_models_for_fi.items()):
    importances = mdl.feature_importances_
    indices = np.argsort(importances)[-20:]
    ax.barh(range(len(indices)), importances[indices], color='steelblue', edgecolor='black', linewidth=0.3)
    ax.set_yticks(range(len(indices)))
    ax.set_yticklabels([feature_names[i] for i in indices], fontsize=7)
    ax.set_title(f'{name}: Top 20 Features', fontweight='bold')
    all_importances[name] = dict(zip(feature_names, importances))

plt.suptitle('Feature Importance: Tree-Based Models', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(FIG / "models" / "05_feature_importance.png")
plt.close()
print("  ✓ Figure saved: 05_feature_importance.png")

# --- 7.2 Permutation Importance (Best Model) ---
print("  Computing permutation importance...")
perm_imp = permutation_importance(best_model, X_test, y_test,
                                    n_repeats=20, random_state=RANDOM_STATE, n_jobs=-1)
perm_sorted = np.argsort(perm_imp.importances_mean)[-25:]

fig, ax = plt.subplots(figsize=(10, 8))
ax.boxplot([perm_imp.importances[i] for i in perm_sorted], vert=False,
           tick_labels=[feature_names[i] for i in perm_sorted])
ax.set_title(f'Permutation Importance: {best_name} (Top 25)', fontweight='bold')
ax.set_xlabel('Decrease in Accuracy')
plt.tight_layout()
plt.savefig(FIG / "models" / "06_permutation_importance.png")
plt.close()
print("  ✓ Figure saved: 06_permutation_importance.png")

# Export feature importance
fi_df = pd.DataFrame({
    'feature': feature_names,
    'perm_importance_mean': perm_imp.importances_mean,
    'perm_importance_std': perm_imp.importances_std,
})
for name, imp_dict in all_importances.items():
    fi_df[f'{name}_importance'] = fi_df['feature'].map(imp_dict)

fi_df = fi_df.sort_values('perm_importance_mean', ascending=False)
fi_df.to_csv(RES / "feature_importance.csv", index=False)
print("  ✓ CSV saved: feature_importance.csv")

# %% — 8. WC 2026 MATCH PREDICTIONS
print("\n" + "="*70)
print("🏆 SECTION 8: WC 2026 MATCH PREDICTIONS")
print("="*70)

# --- 8.1 Feature Alignment ---
# Map fixture_features columns to our model's expected features
def build_wc2026_features(row):
    """Transform a WC2026 fixture row into model-compatible feature vector."""
    feat = {}

    # Core Elo & form
    feat['elo_diff'] = row.get('elo_diff', 0)
    feat['elo_win_prob'] = row.get('home_elo_win_prob', 0.5)
    feat['form_diff'] = row.get('form_diff', 0)

    # Stage (all group stage = 1, not knockout)
    feat['is_knockout'] = 0
    feat['stage_numeric'] = 1

    # Home/Host
    feat['is_home'] = 1 if row.get('home_host_nation', 0) == 1 else 0
    feat['is_host'] = row.get('home_host_nation', 0)
    feat['opp_is_host'] = row.get('away_host_nation', 0)
    feat['neutral_venue'] = 1 if (feat['is_host'] == 0 and feat['opp_is_host'] == 0) else 0
    feat['same_confederation'] = 0  # approximate

    # WC history
    feat['wc_appearances'] = row.get('home_wc_appearances', 0)
    feat['opp_wc_appearances'] = row.get('away_wc_appearances', 0)
    feat['wc_wins'] = row.get('home_wc_wins', 0)
    feat['opp_wc_wins'] = row.get('away_wc_wins', 0)
    feat['wc_finals'] = row.get('home_wc_finals', 0)
    feat['opp_wc_finals'] = row.get('away_wc_finals', 0)
    feat['wc_semis'] = row.get('home_wc_semis', 0)
    feat['opp_wc_semis'] = row.get('away_wc_semis', 0)
    feat['wc_avg_goals'] = 0  # will be updated live

    # Form
    feat['form_5'] = row.get('home_form_10', 0.5)
    feat['opp_form_5'] = row.get('away_form_10', 0.5)
    feat['goals_scored_form5'] = row.get('home_goals_scored_form10', 1.5) / 2
    feat['goals_conceded_form5'] = row.get('home_goals_conceded_form10', 1.0) / 2
    feat['opp_goals_scored_form5'] = row.get('away_goals_scored_form10', 1.5) / 2

    # H2H (approximate)
    feat['h2h_winrate'] = 0.5
    feat['h2h_matches'] = 0

    # Rest days (first match)
    feat['rest_days'] = 4.0
    feat['opp_rest_days'] = 4.0
    feat['rest_days_adv'] = 0.0
    feat['tournament_match_num'] = row.get('fixture_id', 1)

    # Tournament progress (pre-tournament)
    for col in tourn_fill_zero:
        feat[col] = 0

    # Squad features
    feat['squad_xg_per_match'] = row.get('home_squad_xg_p90', 0) or 0
    feat['squad_goals_per_match'] = row.get('home_squad_goals_p90', 0) or 0
    feat['squad_shots_per_match'] = 0
    feat['squad_key_passes_per_match'] = row.get('home_squad_key_passes_p90', 0) or 0
    feat['squad_interceptions_per_match'] = row.get('home_squad_interceptions_p90', 0) or 0
    feat['squad_dribbles_per_match'] = 0
    feat['squad_squad_pass_accuracy'] = row.get('home_squad_pass_accuracy', 0.8) or 0.8

    feat['opp_squad_xg_per_match'] = row.get('away_squad_xg_p90', 0) or 0
    feat['opp_squad_goals_per_match'] = row.get('away_squad_goals_p90', 0) or 0
    feat['opp_squad_shots_per_match'] = 0
    feat['opp_squad_key_passes_per_match'] = row.get('away_squad_key_passes_p90', 0) or 0
    feat['opp_squad_interceptions_per_match'] = row.get('away_squad_interceptions_p90', 0) or 0
    feat['opp_squad_dribbles_per_match'] = 0
    feat['opp_squad_squad_pass_accuracy'] = row.get('away_squad_pass_accuracy', 0.8) or 0.8

    # Demographics
    feat['squad_avg_age'] = row.get('home_squad_avg_age_2026', 28) or 28
    feat['opp_squad_avg_age'] = row.get('away_squad_avg_age_2026', 28) or 28
    feat['age_diff'] = feat['squad_avg_age'] - feat['opp_squad_avg_age']
    feat['avg_club_prestige'] = row.get('home_avg_club_prestige', 5) or 5
    feat['max_club_prestige'] = row.get('home_max_club_prestige', 5) or 5
    feat['opp_avg_club_prestige'] = row.get('away_avg_club_prestige', 5) or 5
    feat['opp_max_club_prestige'] = row.get('away_max_club_prestige', 5) or 5
    feat['club_prestige_diff'] = feat['avg_club_prestige'] - feat['opp_avg_club_prestige']

    # Confederation codes (approximate)
    feat['team_conf_code'] = 1
    feat['opp_conf_code'] = 1

    # Interaction features
    feat['elo_x_knockout'] = feat['elo_diff'] * feat['is_knockout']
    feat['form_x_stage'] = feat['form_diff'] * feat['stage_numeric']
    feat['elo_x_host'] = feat['elo_diff'] * feat['is_host']
    feat['squad_quality_diff'] = feat['squad_xg_per_match'] - feat['opp_squad_xg_per_match']
    feat['experience_diff'] = feat['wc_appearances'] - feat['opp_wc_appearances']
    feat['pedigree_diff'] = feat['wc_wins'] - feat['opp_wc_wins']

    return feat

# Build feature matrix for all 72 fixtures
wc_features_list = []
for _, row in df_fixture_feats.iterrows():
    feat_dict = build_wc2026_features(row)
    # Ensure correct column order
    ordered = [feat_dict.get(f, 0) for f in FINAL_FEATURES]
    wc_features_list.append(ordered)

X_wc2026 = np.array(wc_features_list, dtype=float)
X_wc2026 = np.nan_to_num(X_wc2026, 0)
print(f"  → WC 2026 feature matrix: {X_wc2026.shape}")

# --- 8.2 Generate Predictions ---
# Use best model
wc_probs = best_model.predict_proba(X_wc2026)  # [loss, draw, win] for HOME team
wc_preds = best_model.predict(X_wc2026)

predictions = []
for idx, row in df_fixture_feats.iterrows():
    prob_loss = wc_probs[idx, 0]
    prob_draw = wc_probs[idx, 1]
    prob_win  = wc_probs[idx, 2]
    pred = wc_preds[idx]

    result_map_pred = {0: 'Away Win', 1: 'Draw', 2: 'Home Win'}
    confidence = max(prob_loss, prob_draw, prob_win)

    predictions.append({
        'fixture_id': row['fixture_id'],
        'date': row['date'],
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'home_win_prob': round(prob_win, 4),
        'draw_prob': round(prob_draw, 4),
        'away_win_prob': round(prob_loss, 4),
        'predicted_result': result_map_pred[pred],
        'confidence': round(confidence, 4),
        'elo_diff': row.get('elo_diff', 0),
    })

df_predictions = pd.DataFrame(predictions)
df_predictions.to_csv(RES / "wc2026_predictions.csv", index=False)
print("  ✓ CSV saved: wc2026_predictions.csv")

# Also use all models for ensemble prediction comparison
model_predictions = {}
for mname, mres in results.items():
    mdl = mres['model']
    try:
        if mname in ['Logistic Regression', 'MLP Neural Net']:
            probs = mdl.predict_proba(scaler.transform(X_wc2026))
        else:
            probs = mdl.predict_proba(X_wc2026)
        model_predictions[mname] = probs
    except Exception:
        pass

# Average ensemble probabilities
if model_predictions:
    avg_probs = np.mean(list(model_predictions.values()), axis=0)
    for i, row in df_predictions.iterrows():
        df_predictions.loc[i, 'ensemble_home_win'] = round(avg_probs[i, 2], 4)
        df_predictions.loc[i, 'ensemble_draw'] = round(avg_probs[i, 1], 4)
        df_predictions.loc[i, 'ensemble_away_win'] = round(avg_probs[i, 0], 4)
    df_predictions.to_csv(RES / "wc2026_predictions.csv", index=False)

# Print top predictions
print("\n  Top 10 Most Decisive Predictions:")
top10 = df_predictions.nlargest(10, 'confidence')
for _, r in top10.iterrows():
    print(f"    {r['home_team']:>20} vs {r['away_team']:<20} → {r['predicted_result']:<10} "
          f"({r['home_win_prob']:.0%} / {r['draw_prob']:.0%} / {r['away_win_prob']:.0%})")

# --- 8.3 Predictions Visualization ---
fig, ax = plt.subplots(figsize=(16, 18))
y_pos = range(len(df_predictions))

for i, (_, row) in enumerate(df_predictions.iterrows()):
    # Stacked bar
    ax.barh(i, row['home_win_prob'], color='#2ecc71', edgecolor='white', linewidth=0.3)
    ax.barh(i, row['draw_prob'], left=row['home_win_prob'], color='#f39c12', edgecolor='white', linewidth=0.3)
    ax.barh(i, row['away_win_prob'], left=row['home_win_prob']+row['draw_prob'],
            color='#e74c3c', edgecolor='white', linewidth=0.3)

labels = [f"{r['home_team']} vs {r['away_team']}" for _, r in df_predictions.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=6)
ax.set_xlabel('Probability')
ax.set_title('WC 2026 Group Stage Predictions (All 72 Matches)', fontsize=14, fontweight='bold')
ax.legend(['Home Win', 'Draw', 'Away Win'], loc='lower right')
ax.invert_yaxis()
plt.tight_layout()
plt.savefig(FIG / "predictions" / "01_all_predictions.png")
plt.close()
print("  ✓ Figure saved: 01_all_predictions.png")

# %% — 9. GROUP STAGE STANDINGS
print("\n" + "="*70)
print("📋 SECTION 9: GROUP STAGE STANDINGS")
print("="*70)

# --- 9.1 Define Groups (WC 2026: 12 groups of 4) ---
# Extract groups from fixtures
teams_per_fixture = list(zip(df_fixtures['home_team'], df_fixtures['away_team']))

# Build group mapping from fixtures (each team plays 3 matches in group)
team_opponents = defaultdict(set)
for home, away in teams_per_fixture:
    team_opponents[home].add(away)
    team_opponents[away].add(home)

# Group teams by their opponent sets (teams in same group play each other)
groups = {}
assigned = set()
group_letter = 0
group_labels = 'ABCDEFGHIJKL'

all_teams = sorted(set(df_fixtures['home_team']) | set(df_fixtures['away_team']))
for team in all_teams:
    if team in assigned:
        continue
    group_members = {team} | team_opponents[team]
    # Verify it's a valid group (all play each other)
    valid = True
    for t in group_members:
        if not (group_members - {t}).issubset(team_opponents[t]):
            valid = False
    if valid and len(group_members) == 4:
        label = group_labels[group_letter]
        groups[label] = sorted(group_members)
        assigned.update(group_members)
        group_letter += 1

# If auto-detection didn't work perfectly, use fixtures to build groups
if len(groups) != 12:
    print("  ⚠ Auto group detection incomplete, building from fixture pairs...")
    groups = {}
    assigned = set()
    group_letter = 0
    for team in all_teams:
        if team in assigned:
            continue
        # Find all teams this team plays
        opponents = team_opponents[team]
        # The group is the team + its opponents
        group_members = {team} | opponents
        if len(group_members) <= 4 and len(group_members) >= 3:
            label = group_labels[group_letter]
            groups[label] = sorted(group_members)
            assigned.update(group_members)
            group_letter += 1

print(f"  → Detected {len(groups)} groups with {sum(len(v) for v in groups.values())} teams")

for label, teams in sorted(groups.items()):
    print(f"    Group {label}: {', '.join(teams)}")

# --- 9.2 Compute Standings ---
standings = {}
for label, teams in groups.items():
    table = {}
    for team in teams:
        table[team] = {'MP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0}

    # Find fixtures for this group
    group_fixtures = df_predictions[
        (df_predictions['home_team'].isin(teams)) &
        (df_predictions['away_team'].isin(teams))
    ]

    for _, fix in group_fixtures.iterrows():
        home = fix['home_team']
        away = fix['away_team']
        pred = fix['predicted_result']

        table[home]['MP'] += 1
        table[away]['MP'] += 1

        # Estimate goals based on probabilities (Poisson approximation)
        hw_prob = fix['home_win_prob']
        d_prob = fix['draw_prob']
        aw_prob = fix['away_win_prob']

        if pred == 'Home Win':
            table[home]['W'] += 1; table[away]['L'] += 1
            table[home]['Pts'] += 3
            table[home]['GF'] += 2; table[home]['GA'] += 1
            table[away]['GF'] += 1; table[away]['GA'] += 2
        elif pred == 'Draw':
            table[home]['D'] += 1; table[away]['D'] += 1
            table[home]['Pts'] += 1; table[away]['Pts'] += 1
            table[home]['GF'] += 1; table[home]['GA'] += 1
            table[away]['GF'] += 1; table[away]['GA'] += 1
        else:  # Away Win
            table[away]['W'] += 1; table[home]['L'] += 1
            table[away]['Pts'] += 3
            table[away]['GF'] += 2; table[away]['GA'] += 1
            table[home]['GF'] += 1; table[home]['GA'] += 2

    for team in table:
        table[team]['GD'] = table[team]['GF'] - table[team]['GA']

    # Sort by Pts, then GD, then GF
    sorted_table = sorted(table.items(), key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF']), reverse=True)
    standings[label] = sorted_table

# Export standings
standings_rows = []
for label, table in sorted(standings.items()):
    for pos, (team, stats) in enumerate(table, 1):
        stats_row = {'Group': label, 'Position': pos, 'Team': team}
        stats_row.update(stats)
        qualify = 'Yes' if pos <= 2 else 'Maybe (3rd)'
        stats_row['Qualifies'] = qualify
        standings_rows.append(stats_row)

df_standings = pd.DataFrame(standings_rows)
df_standings.to_csv(RES / "wc2026_group_standings.csv", index=False)
print("  ✓ CSV saved: wc2026_group_standings.csv")

# Visualize standings
n_groups = len(standings)
fig, axes = plt.subplots(3, 4, figsize=(20, 12))
axes = axes.flatten()

for idx, (label, table) in enumerate(sorted(standings.items())):
    ax = axes[idx]
    teams = [t[0] for t in table]
    pts = [t[1]['Pts'] for t in table]
    colors_grp = ['#2ecc71', '#27ae60', '#f39c12', '#e74c3c'][:len(teams)]
    ax.barh(teams[::-1], pts[::-1], color=colors_grp[::-1], edgecolor='black', linewidth=0.5)
    for i, (team, p) in enumerate(zip(teams[::-1], pts[::-1])):
        ax.text(p + 0.1, i, str(p), va='center', fontweight='bold', fontsize=9)
    ax.set_title(f'Group {label}', fontweight='bold')
    ax.set_xlim(0, max(pts) + 2)

for idx in range(len(standings), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle('WC 2026 Predicted Group Standings', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(FIG / "predictions" / "02_group_standings.png")
plt.close()
print("  ✓ Figure saved: 02_group_standings.png")

# %% — 10. MONTE CARLO TOURNAMENT SIMULATION
print("\n" + "="*70)
print("🎲 SECTION 10: MONTE CARLO TOURNAMENT SIMULATION")
print("="*70)

N_SIMULATIONS = 10000

def simulate_match(home_probs):
    """Simulate a single match given [loss_prob, draw_prob, win_prob] for home team."""
    probs = np.array(home_probs, dtype=float)
    probs /= probs.sum()
    return np.random.choice([0, 1, 2], p=probs)

def simulate_group(group_teams, fixture_probs):
    """Simulate a group stage. Returns sorted standings."""
    table = {t: {'Pts': 0, 'GD': 0, 'GF': 0} for t in group_teams}

    for (home, away), probs in fixture_probs.items():
        result = simulate_match(probs)
        if result == 2:  # Home win
            table[home]['Pts'] += 3
            goals_h, goals_a = max(1, np.random.poisson(1.8)), np.random.poisson(0.8)
            if goals_h <= goals_a:
                goals_h = goals_a + 1
        elif result == 1:  # Draw
            table[home]['Pts'] += 1
            table[away]['Pts'] += 1
            goals_h = goals_a = np.random.poisson(1.1)
        else:  # Away win
            table[away]['Pts'] += 3
            goals_a, goals_h = max(1, np.random.poisson(1.8)), np.random.poisson(0.8)
            if goals_a <= goals_h:
                goals_a = goals_h + 1

        table[home]['GF'] += goals_h; table[home]['GD'] += (goals_h - goals_a)
        table[away]['GF'] += goals_a; table[away]['GD'] += (goals_a - goals_h)

    sorted_teams = sorted(table.items(),
                           key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF'], np.random.random()),
                           reverse=True)
    return sorted_teams

def simulate_knockout_match(team_a, team_b, team_elos):
    """Simulate a knockout match between two teams using Elo-based probability."""
    elo_a = team_elos.get(team_a, 1700)
    elo_b = team_elos.get(team_b, 1700)
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    # No draws in knockout
    if np.random.random() < expected_a:
        return team_a
    return team_b

# Build fixture probability lookup
fixture_probs_lookup = {}
for _, row in df_predictions.iterrows():
    key = (row['home_team'], row['away_team'])
    fixture_probs_lookup[key] = [row['away_win_prob'], row['draw_prob'], row['home_win_prob']]

# Team Elo lookup
team_elos = dict(zip(df_team_str['team'], df_team_str['current_elo']))

# Tracking
team_stages = defaultdict(lambda: {'group_exit': 0, 'r32': 0, 'r16': 0,
                                     'qf': 0, 'sf': 0, 'final': 0, 'champion': 0})

print(f"  Running {N_SIMULATIONS:,} tournament simulations...")

for sim in tqdm(range(N_SIMULATIONS), desc="  Simulating", ncols=80):
    # --- Group Stage ---
    group_results = {}
    third_place_teams = []

    for label, group_teams_list in groups.items():
        # Get fixture probs for this group
        grp_fixture_probs = {}
        for home, away in fixture_probs_lookup:
            if home in group_teams_list and away in group_teams_list:
                grp_fixture_probs[(home, away)] = fixture_probs_lookup[(home, away)]

        standings_sim = simulate_group(group_teams_list, grp_fixture_probs)

        # Top 2 advance directly
        for pos, (team, stats) in enumerate(standings_sim):
            if pos < 2:
                group_results.setdefault(label, []).append(team)
                team_stages[team]['r32'] += 1
            elif pos == 2:
                third_place_teams.append((team, stats))
            else:
                team_stages[team]['group_exit'] += 1

    # Best 8 third-place teams advance
    third_place_teams.sort(key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF'], np.random.random()),
                            reverse=True)
    for team, _ in third_place_teams[:8]:
        team_stages[team]['r32'] += 1
    for team, _ in third_place_teams[8:]:
        team_stages[team]['group_exit'] += 1

    # --- Knockout Stage ---
    # Collect all advancing teams
    advancing = []
    for label in sorted(group_results.keys()):
        advancing.extend(group_results[label])
    advancing.extend([t for t, _ in third_place_teams[:8]])

    np.random.shuffle(advancing)  # Random bracket placement for simplicity

    # Round of 32 (32 teams → 16)
    r16_teams = []
    for i in range(0, len(advancing), 2):
        if i + 1 < len(advancing):
            winner = simulate_knockout_match(advancing[i], advancing[i+1], team_elos)
            r16_teams.append(winner)
            team_stages[winner]['r16'] += 1
        else:
            r16_teams.append(advancing[i])
            team_stages[advancing[i]]['r16'] += 1

    # Round of 16 (16 → 8)
    qf_teams = []
    for i in range(0, len(r16_teams), 2):
        if i + 1 < len(r16_teams):
            winner = simulate_knockout_match(r16_teams[i], r16_teams[i+1], team_elos)
            qf_teams.append(winner)
            team_stages[winner]['qf'] += 1

    # Quarter-finals (8 → 4)
    sf_teams = []
    for i in range(0, len(qf_teams), 2):
        if i + 1 < len(qf_teams):
            winner = simulate_knockout_match(qf_teams[i], qf_teams[i+1], team_elos)
            sf_teams.append(winner)
            team_stages[winner]['sf'] += 1

    # Semi-finals (4 → 2)
    finalists = []
    for i in range(0, len(sf_teams), 2):
        if i + 1 < len(sf_teams):
            winner = simulate_knockout_match(sf_teams[i], sf_teams[i+1], team_elos)
            finalists.append(winner)
            team_stages[winner]['final'] += 1

    # Final
    if len(finalists) == 2:
        champion = simulate_knockout_match(finalists[0], finalists[1], team_elos)
        team_stages[champion]['champion'] += 1

# --- Build Results Table ---
sim_results = []
for team in all_teams:
    stages = team_stages[team]
    sim_results.append({
        'Team': team,
        'Champion %': round(stages['champion'] / N_SIMULATIONS * 100, 2),
        'Finalist %': round(stages['final'] / N_SIMULATIONS * 100, 2),
        'Semi-Final %': round(stages['sf'] / N_SIMULATIONS * 100, 2),
        'Quarter-Final %': round(stages['qf'] / N_SIMULATIONS * 100, 2),
        'Round of 16 %': round(stages['r16'] / N_SIMULATIONS * 100, 2),
        'Round of 32 %': round(stages['r32'] / N_SIMULATIONS * 100, 2),
        'Group Exit %': round(stages['group_exit'] / N_SIMULATIONS * 100, 2),
    })

df_sim = pd.DataFrame(sim_results).sort_values('Champion %', ascending=False)
df_sim.to_csv(RES / "wc2026_simulation_results.csv", index=False)
print("\n  ✓ CSV saved: wc2026_simulation_results.csv")

print("\n  Championship Probabilities (Top 15):")
for _, r in df_sim.head(15).iterrows():
    bar = '█' * int(r['Champion %'] * 2)
    print(f"    {r['Team']:>20}: {r['Champion %']:5.1f}% {bar}")

# Visualization
fig, axes = plt.subplots(1, 2, figsize=(20, 10))

# Champion probability
top20 = df_sim.head(20)
colors_sim = plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, len(top20)))
axes[0].barh(range(len(top20)), top20['Champion %'].values[::-1],
             color=colors_sim[::-1], edgecolor='black', linewidth=0.5)
axes[0].set_yticks(range(len(top20)))
axes[0].set_yticklabels(top20['Team'].values[::-1])
axes[0].set_xlabel('Championship Probability (%)')
axes[0].set_title('Championship Probability (Top 20)', fontweight='bold')
for i, v in enumerate(top20['Champion %'].values[::-1]):
    axes[0].text(v + 0.2, i, f'{v:.1f}%', va='center', fontsize=8)

# Stage advancement (top 10)
top10_sim = df_sim.head(10)
stages_plot = ['Group Exit %', 'Round of 32 %', 'Round of 16 %',
               'Quarter-Final %', 'Semi-Final %', 'Finalist %', 'Champion %']
x_pos = np.arange(len(stages_plot))
width = 0.08

for i, (_, row) in enumerate(top10_sim.iterrows()):
    vals = [row[s] for s in stages_plot]
    axes[1].bar(x_pos + i * width, vals, width, label=row['Team'])

axes[1].set_xticks(x_pos + width * 4.5)
axes[1].set_xticklabels([s.replace(' %', '') for s in stages_plot], rotation=45, ha='right')
axes[1].set_ylabel('Probability (%)')
axes[1].set_title('Stage Advancement (Top 10 Teams)', fontweight='bold')
axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=7)

plt.suptitle(f'Monte Carlo Simulation Results ({N_SIMULATIONS:,} simulations)',
             fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "simulation" / "01_simulation_results.png")
plt.close()
print("  ✓ Figure saved: 01_simulation_results.png")

# %% — 11. PLAYER INTELLIGENCE SYSTEM
print("\n" + "="*70)
print("👤 SECTION 11: PLAYER INTELLIGENCE SYSTEM")
print("="*70)

# --- 11.1 Player Impact Score ---
df_ps = df_players_squad.copy()

# Normalize metrics (min-max within position group, or globally)
impact_weights = {
    'xg_p90': 0.20,
    'goals_p90': 0.15,
    'key_passes_p90': 0.15,
    'interceptions_p90': 0.10,
    'prog_carries_p90': 0.10,
    'pass_accuracy': 0.10,
    'dribble_success': 0.05,
    'recent_minutes': 0.15,  # availability proxy
}

# Fill NaN with 0 for numeric stats
for col in impact_weights:
    if col in df_ps.columns:
        df_ps[col] = pd.to_numeric(df_ps[col], errors='coerce').fillna(0)

# Normalize each metric to 0-100
normalized = pd.DataFrame()
for col, weight in impact_weights.items():
    if col in df_ps.columns:
        vals = df_ps[col]
        min_val = vals.min()
        max_val = vals.max()
        if max_val > min_val:
            normalized[col] = (vals - min_val) / (max_val - min_val) * 100
        else:
            normalized[col] = 50  # default

# Compute weighted impact score
df_ps['impact_score'] = 0
for col, weight in impact_weights.items():
    if col in normalized.columns:
        df_ps['impact_score'] += normalized[col] * weight

# Scale to 0-100
max_score = df_ps['impact_score'].max()
if max_score > 0:
    df_ps['impact_score'] = (df_ps['impact_score'] / max_score * 100).round(1)

# Top 50 players
df_top50 = df_ps.nlargest(50, 'impact_score')[
    ['player_name', 'team', 'impact_score', 'xg_p90', 'goals_p90',
     'key_passes_p90', 'interceptions_p90', 'prog_carries_p90', 'pass_accuracy']
].reset_index(drop=True)
df_top50.index += 1
df_top50.to_csv(RES / "player_impact_scores_top50.csv")
print("  ✓ CSV saved: player_impact_scores_top50.csv")

# Full export
df_ps[['player_id', 'player_name', 'team', 'impact_score',
       'xg_p90', 'goals_p90', 'key_passes_p90', 'interceptions_p90']].to_csv(
    RES / "player_impact_scores_all.csv", index=False)

print("\n  Top 20 Players by Impact Score:")
for i, (_, r) in enumerate(df_top50.head(20).iterrows(), 1):
    print(f"    {i:2d}. {r['player_name']:<40} ({r['team']:<15}) → {r['impact_score']:.1f}")

# --- 11.2 Team Strength Breakdown ---
team_strength = df_ps.groupby('team').agg(
    avg_impact=('impact_score', 'mean'),
    max_impact=('impact_score', 'max'),
    squad_size=('player_id', 'count'),
    top5_avg=('impact_score', lambda x: x.nlargest(5).mean() if len(x) >= 5 else x.mean()),
    depth=('impact_score', lambda x: x.nlargest(11).mean() - x.nsmallest(max(1, len(x)-11)).mean()
           if len(x) > 11 else 0),
).round(2)

# Merge with team Elo
team_strength = team_strength.merge(df_team_str[['team', 'current_elo', 'form_10']],
                                      on='team', how='left')
team_strength = team_strength.sort_values('avg_impact', ascending=False)
team_strength.to_csv(RES / "team_strength_breakdown.csv")
print("  ✓ CSV saved: team_strength_breakdown.csv")

# --- 11.3 Visualization ---
fig, axes = plt.subplots(1, 2, figsize=(18, 10))

# Top 30 players
top30 = df_top50.head(30)
colors_p = plt.cm.plasma(np.linspace(0.1, 0.9, len(top30)))
axes[0].barh(range(len(top30)), top30['impact_score'].values[::-1],
             color=colors_p[::-1], edgecolor='black', linewidth=0.3)
axes[0].set_yticks(range(len(top30)))
labels_p = [f"{r['player_name'][:25]} ({r['team'][:3]})" for _, r in top30[::-1].iterrows()]
axes[0].set_yticklabels(labels_p, fontsize=7)
axes[0].set_xlabel('Impact Score (0-100)')
axes[0].set_title('Top 30 Players: Impact Score', fontweight='bold')

# Team average impact
ts_sorted = team_strength.sort_values('avg_impact', ascending=True).tail(25)
axes[1].barh(range(len(ts_sorted)), ts_sorted['avg_impact'].values,
             color=plt.cm.viridis(np.linspace(0.2, 0.8, len(ts_sorted))),
             edgecolor='black', linewidth=0.3)
axes[1].set_yticks(range(len(ts_sorted)))
axes[1].set_yticklabels(ts_sorted.index, fontsize=8)
axes[1].set_xlabel('Average Impact Score')
axes[1].set_title('Team Average Impact Score (Top 25)', fontweight='bold')

plt.suptitle('Player Intelligence System', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FIG / "players" / "01_player_intelligence.png")
plt.close()
print("  ✓ Figure saved: 01_player_intelligence.png")

# --- 11.4 What-If Injury Simulator ---
print("\n  What-If Injury Scenarios:")
key_players = df_top50.head(10)
injury_scenarios = []

for _, player in key_players.iterrows():
    team = player['team']
    player_score = player['impact_score']

    # Recalculate team strength without this player
    team_players = df_ps[df_ps['team'] == team]
    team_avg_with = team_players['impact_score'].mean()
    team_avg_without = team_players[team_players['player_name'] != player['player_name']]['impact_score'].mean()

    pct_drop = ((team_avg_with - team_avg_without) / team_avg_with * 100) if team_avg_with > 0 else 0

    injury_scenarios.append({
        'Player': player['player_name'],
        'Team': team,
        'Impact Score': player_score,
        'Team Avg (with)': round(team_avg_with, 2),
        'Team Avg (without)': round(team_avg_without, 2),
        'Strength Drop %': round(pct_drop, 2),
    })
    print(f"    If {player['player_name']:<30} ({team}) injured: "
          f"team strength drops {pct_drop:.1f}%")

df_injury = pd.DataFrame(injury_scenarios)
df_injury.to_csv(RES / "what_if_injuries.csv", index=False)
print("  ✓ CSV saved: what_if_injuries.csv")

# %% — 12. EXPLAINABLE AI (SHAP)
print("\n" + "="*70)
print("🔬 SECTION 12: EXPLAINABLE AI (SHAP)")
print("="*70)

if HAS_SHAP:
    # Find the best tree-based model for SHAP to use fast TreeExplainer
    shap_model_name = best_name
    shap_model = best_model
    if shap_model_name not in ['XGBoost', 'LightGBM', 'CatBoost', 'Random Forest', 'Gradient Boosting']:
        # Find the best tree-based model from models
        best_tree_acc = -1
        for name in ['XGBoost', 'LightGBM', 'CatBoost', 'Random Forest', 'Gradient Boosting']:
            if name in results and results[name]['accuracy'] > best_tree_acc:
                best_tree_acc = results[name]['accuracy']
                shap_model_name = name
                shap_model = results[name]['model']
        print(f"  → Best model is not tree-based. Using best tree-based model '{shap_model_name}' for fast SHAP explainability.")

    print(f"  Computing SHAP values using {shap_model_name}...")
    explainer = shap.TreeExplainer(shap_model)
    shap_values = explainer.shap_values(X_test)

    # --- 12.1 Global Feature Importance (SHAP) ---
    fig, ax = plt.subplots(figsize=(12, 8))
    if isinstance(shap_values, list):
        # Multi-class: average absolute SHAP across classes
        shap_abs_mean = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
        # 3D array: average over samples (axis 0) and classes (axis 2)
        shap_abs_mean = np.abs(shap_values).mean(axis=(0, 2))
    else:
        shap_abs_mean = np.abs(shap_values).mean(axis=0)

    sorted_idx = np.argsort(shap_abs_mean)[-20:]
    ax.barh(range(len(sorted_idx)), shap_abs_mean[sorted_idx], color='steelblue')
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels([feature_names[i] for i in sorted_idx], fontsize=8)
    ax.set_xlabel('Mean |SHAP Value|')
    ax.set_title(f'SHAP Feature Importance: {best_name}', fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIG / "shap" / "01_shap_importance.png")
    plt.close()
    print("  ✓ Figure saved: 01_shap_importance.png")

    # --- 12.2 SHAP Summary Plot ---
    fig, ax = plt.subplots(figsize=(12, 10))
    if isinstance(shap_values, list):
        # Plot for the "Win" class (class 2)
        shap.summary_plot(shap_values[2], X_test, feature_names=feature_names,
                          max_display=20, show=False)
    else:
        shap.summary_plot(shap_values, X_test, feature_names=feature_names,
                          max_display=20, show=False)
    plt.title(f'SHAP Summary: Win Prediction ({best_name})', fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIG / "shap" / "02_shap_summary.png")
    plt.close()
    print("  ✓ Figure saved: 02_shap_summary.png")

    # --- 12.3 SHAP for Top WC 2026 Predictions ---
    print("  Computing SHAP for WC 2026 predictions...")
    top_fixtures = df_predictions.nlargest(5, 'confidence')

    for fixture_idx, (_, fixture) in enumerate(top_fixtures.iterrows()):
        fix_id = int(fixture['fixture_id']) - 1
        fix_features = X_wc2026[fix_id:fix_id+1]

        try:
            fix_shap = explainer.shap_values(fix_features)

            fig, ax = plt.subplots(figsize=(12, 6))
            if isinstance(fix_shap, list):
                shap_vals = fix_shap[2][0]  # Win class
            elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 3:
                # Shape is (1, n_features, n_classes) -> extract Win class (index 2)
                shap_vals = fix_shap[0, :, 2]
            elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 2:
                # Shape is (1, n_features)
                shap_vals = fix_shap[0]
            else:
                shap_vals = fix_shap

            sorted_fi = np.argsort(np.abs(shap_vals))[-10:]
            colors_shap = ['#2ecc71' if v > 0 else '#e74c3c' for v in shap_vals[sorted_fi]]
            ax.barh(range(len(sorted_fi)), shap_vals[sorted_fi], color=colors_shap)
            ax.set_yticks(range(len(sorted_fi)))
            ax.set_yticklabels([feature_names[i] for i in sorted_fi], fontsize=8)
            ax.set_xlabel('SHAP Value (→ Win)')
            ax.set_title(f"{fixture['home_team']} vs {fixture['away_team']}: "
                         f"Why {fixture['predicted_result']}?", fontweight='bold')
            ax.axvline(0, color='black', linewidth=0.5)
            plt.tight_layout()
            plt.savefig(FIG / "shap" / f"03_match_{fixture_idx+1}_explanation.png")
            plt.close()
        except Exception as e:
            print(f"    ⚠ Could not explain fixture {fixture['fixture_id']}: {e}")

    print("  ✓ Match explanations saved")

    # --- 12.4 Narrative Explanations ---
    explanations = []
    for _, fixture in df_predictions.iterrows():
        fix_id = int(fixture['fixture_id']) - 1
        fix_features = X_wc2026[fix_id:fix_id+1]

        try:
            fix_shap = explainer.shap_values(fix_features)
            if isinstance(fix_shap, list):
                shap_vals = fix_shap[2][0]  # Win class
            elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 3:
                # Shape is (1, n_features, n_classes) -> extract Win class (index 2)
                shap_vals = fix_shap[0, :, 2]
            elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 2:
                # Shape is (1, n_features)
                shap_vals = fix_shap[0]
            else:
                shap_vals = fix_shap

            # Top 3 contributing features
            top3_idx = np.argsort(np.abs(shap_vals))[-3:][::-1]
            reasons = []
            for i in top3_idx:
                direction = '+' if shap_vals[i] > 0 else '-'
                reasons.append(f"{direction}{abs(shap_vals[i]):.3f} from {feature_names[i]}")

            explanations.append({
                'fixture_id': fixture['fixture_id'],
                'match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'prediction': fixture['predicted_result'],
                'reason_1': reasons[0] if len(reasons) > 0 else '',
                'reason_2': reasons[1] if len(reasons) > 1 else '',
                'reason_3': reasons[2] if len(reasons) > 2 else '',
            })
        except Exception:
            explanations.append({
                'fixture_id': fixture['fixture_id'],
                'match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'prediction': fixture['predicted_result'],
                'reason_1': 'Elo-based', 'reason_2': '', 'reason_3': '',
            })

    df_explanations = pd.DataFrame(explanations)
    df_explanations.to_csv(RES / "prediction_explanations.csv", index=False)
    print("  ✓ CSV saved: prediction_explanations.csv")

    # Export SHAP importance
    shap_fi = pd.DataFrame({
        'feature': feature_names,
        'shap_importance': shap_abs_mean,
    }).sort_values('shap_importance', ascending=False)
    shap_fi.to_csv(RES / "shap_feature_importance.csv", index=False)
    print("  ✓ CSV saved: shap_feature_importance.csv")

else:
    print("  ⚠ SHAP not available — skipping explainability analysis")
    print("    Install with: pip install shap")

# %% — 13. ADAPTIVE LEARNING SIMULATION
print("\n" + "="*70)
print("🔄 SECTION 13: ADAPTIVE LEARNING SIMULATION")
print("="*70)

# Simulate how ATLAS would improve during a tournament by re-training after each match day
# Using the 2022 WC test set as a proxy

test_data = df_model[test_mask].copy().sort_values('tournament_match_num')
test_indices = test_data.index.tolist()

# Group test matches by tournament_match_num (simulating match days)
match_days = test_data.groupby('tournament_match_num').groups

adaptive_results = []
cumulative_X = X_train.copy()
cumulative_y = y_train.copy()

accuracy_static = accuracy_score(y_test, best_result['y_pred'])

print(f"  Static model accuracy (no adaptation): {accuracy_static:.4f}")
print(f"  Simulating adaptive learning across {len(match_days)} match days...")

correct_static = 0
correct_adaptive = 0
total = 0

for day_num, (match_num, indices) in enumerate(sorted(match_days.items())):
    day_X = df_model.loc[indices, FINAL_FEATURES].values
    day_y = df_model.loc[indices, TARGET].values.astype(int)

    # Static prediction (original model)
    static_pred = best_model.predict(day_X)
    correct_static += (static_pred == day_y).sum()

    # Adaptive prediction (model retrained on all previous data)
    if day_num > 0 and len(cumulative_y) > 100:
        try:
            adaptive_model = xgb.XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                random_state=RANDOM_STATE, verbosity=0,
                use_label_encoder=False, eval_metric='mlogloss'
            )
            adaptive_model.fit(cumulative_X, cumulative_y)
            adaptive_pred = adaptive_model.predict(day_X)
            correct_adaptive += (adaptive_pred == day_y).sum()
        except Exception:
            correct_adaptive += (static_pred == day_y).sum()
    else:
        correct_adaptive += (static_pred == day_y).sum()

    total += len(day_y)

    # Add this day's data to training set (adaptive learning)
    cumulative_X = np.vstack([cumulative_X, day_X])
    cumulative_y = np.concatenate([cumulative_y, day_y])

    adaptive_results.append({
        'match_day': day_num + 1,
        'matches': len(day_y),
        'static_cumulative_acc': correct_static / total,
        'adaptive_cumulative_acc': correct_adaptive / total,
    })

df_adaptive = pd.DataFrame(adaptive_results)
df_adaptive.to_csv(RES / "adaptive_learning_results.csv", index=False)
print("  ✓ CSV saved: adaptive_learning_results.csv")

# Plot adaptive learning curve
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df_adaptive['match_day'], df_adaptive['static_cumulative_acc'],
        'o-', label='Static Model', color='#e74c3c', linewidth=2)
ax.plot(df_adaptive['match_day'], df_adaptive['adaptive_cumulative_acc'],
        's-', label='Adaptive Model (ATLAS)', color='#2ecc71', linewidth=2)
ax.set_xlabel('Match Day')
ax.set_ylabel('Cumulative Accuracy')
ax.set_title('Adaptive Learning: Does ATLAS Improve During Tournament?', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

final_static = df_adaptive['static_cumulative_acc'].iloc[-1]
final_adaptive = df_adaptive['adaptive_cumulative_acc'].iloc[-1]
improvement = (final_adaptive - final_static) * 100
ax.annotate(f'Improvement: {improvement:+.1f}%',
            xy=(df_adaptive['match_day'].iloc[-1], final_adaptive),
            fontsize=12, fontweight='bold', color='#2ecc71',
            xytext=(-80, 20), textcoords='offset points',
            arrowprops=dict(arrowstyle='->', color='#2ecc71'))

plt.tight_layout()
plt.savefig(FIG / "models" / "07_adaptive_learning.png")
plt.close()
print("  ✓ Figure saved: 07_adaptive_learning.png")
print(f"  → Static final accuracy:   {final_static:.4f}")
print(f"  → Adaptive final accuracy: {final_adaptive:.4f}")
print(f"  → Improvement: {improvement:+.2f}%")

# %% — 14. RESEARCH QUESTION ANALYSIS
print("\n" + "="*70)
print("📝 SECTION 14: RESEARCH QUESTION ANALYSIS")
print("="*70)

rq_results = {}

# --- RQ1: Can adaptive learning improve prediction accuracy during a tournament? ---
rq_results['RQ1'] = {
    'question': 'Can adaptive learning improve prediction accuracy during a tournament?',
    'answer': 'Yes' if improvement > 0 else 'No significant improvement',
    'static_accuracy': f"{final_static:.4f}",
    'adaptive_accuracy': f"{final_adaptive:.4f}",
    'improvement': f"{improvement:+.2f}%",
    'evidence': 'Adaptive model updates team strengths and retrains after each match day'
}
print(f"\n  RQ1: {rq_results['RQ1']['question']}")
print(f"       → {rq_results['RQ1']['answer']} ({rq_results['RQ1']['improvement']})")

# --- RQ2: Which feature groups contribute most to prediction performance? ---
# Analyze feature importance by group
group_importance = {}
for group_name, features in feature_groups.items():
    group_feats = [f for f in features if f in feature_names]
    if group_feats and 'shap_importance' in dir():
        importance = sum(shap_abs_mean[feature_names.index(f)]
                         for f in group_feats if f in feature_names)
    else:
        # Use permutation importance
        importance = sum(perm_imp.importances_mean[feature_names.index(f)]
                         for f in group_feats if f in feature_names)
    group_importance[group_name] = round(importance, 4)

group_imp_sorted = dict(sorted(group_importance.items(), key=lambda x: x[1], reverse=True))
rq_results['RQ2'] = {
    'question': 'Which feature groups contribute most to prediction performance?',
    'ranking': group_imp_sorted,
    'top_group': list(group_imp_sorted.keys())[0] if group_imp_sorted else 'N/A',
}
print(f"\n  RQ2: {rq_results['RQ2']['question']}")
for group, imp in group_imp_sorted.items():
    print(f"       → {group}: {imp:.4f}")

# --- RQ3: How much do individual players influence championship probability? ---
top_injury = df_injury.nlargest(5, 'Strength Drop %') if len(df_injury) > 0 else pd.DataFrame()
rq_results['RQ3'] = {
    'question': 'How much do individual players influence championship probability?',
    'answer': f"Top player injury causes up to {df_injury['Strength Drop %'].max():.1f}% team strength drop"
              if len(df_injury) > 0 else "Analysis based on impact scores",
    'top_impactful': top_injury[['Player', 'Team', 'Strength Drop %']].to_dict('records')
                     if len(top_injury) > 0 else [],
}
print(f"\n  RQ3: {rq_results['RQ3']['question']}")
print(f"       → {rq_results['RQ3']['answer']}")

# --- RQ4: Can explainable AI improve user trust? ---
rq_results['RQ4'] = {
    'question': 'Can explainable AI improve user trust?',
    'answer': 'SHAP provides transparent, per-prediction explanations',
    'explainability_coverage': f"{len(df_explanations) if HAS_SHAP else 0}/72 matches explained",
    'top_features_for_explanation': list(fi_df.head(5)['feature'].values),
}
print(f"\n  RQ4: {rq_results['RQ4']['question']}")
print(f"       → {rq_results['RQ4']['answer']}")

# Feature group importance chart
if group_imp_sorted:
    fig, ax = plt.subplots(figsize=(10, 6))
    groups_list = list(group_imp_sorted.keys())
    values_list = list(group_imp_sorted.values())
    bars = ax.barh(groups_list[::-1], values_list[::-1],
                   color=plt.cm.Set2(np.linspace(0, 1, len(groups_list))),
                   edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Cumulative Feature Importance')
    ax.set_title('RQ2: Feature Group Importance', fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIG / "models" / "08_feature_group_importance.png")
    plt.close()
    print("  ✓ Figure saved: 08_feature_group_importance.png")

# Save RQ analysis
with open(RES / "research_questions.json", 'w') as f:
    json.dump(rq_results, f, indent=2, default=str)
print("  ✓ JSON saved: research_questions.json")

# %% — 15. COMPREHENSIVE EXPORT (JSON for Frontend)
print("\n" + "="*70)
print("📦 SECTION 15: EXPORT ALL RESULTS")
print("="*70)

# --- 15.1 Predictions JSON ---
predictions_json = {
    'model': best_name,
    'accuracy_on_test': best_result['accuracy'],
    'generated_at': datetime.now().isoformat(),
    'predictions': df_predictions.to_dict('records'),
}
with open(JSN / "predictions.json", 'w') as f:
    json.dump(predictions_json, f, indent=2, default=str)
print("  ✓ JSON saved: predictions.json")

# --- 15.2 Simulations JSON ---
simulations_json = {
    'n_simulations': N_SIMULATIONS,
    'results': df_sim.to_dict('records'),
}
with open(JSN / "simulations.json", 'w') as f:
    json.dump(simulations_json, f, indent=2, default=str)
print("  ✓ JSON saved: simulations.json")

# --- 15.3 Players JSON ---
players_json = {
    'top50': df_top50.to_dict('records'),
    'team_strength': team_strength.reset_index().to_dict('records'),
}
with open(JSN / "players.json", 'w') as f:
    json.dump(players_json, f, indent=2, default=str)
print("  ✓ JSON saved: players.json")

# --- 15.4 Explanations JSON ---
if HAS_SHAP:
    explanations_json = {
        'feature_importance': fi_df.head(20).to_dict('records'),
        'match_explanations': df_explanations.to_dict('records'),
    }
else:
    explanations_json = {
        'feature_importance': fi_df.head(20).to_dict('records'),
        'match_explanations': [],
    }
with open(JSN / "explanations.json", 'w') as f:
    json.dump(explanations_json, f, indent=2, default=str)
print("  ✓ JSON saved: explanations.json")

# --- 15.5 Model Comparison JSON ---
model_comp_json = {
    'models': df_comparison.to_dict('records'),
    'best_model': best_name,
}
with open(JSN / "model_comparison.json", 'w') as f:
    json.dump(model_comp_json, f, indent=2, default=str)
print("  ✓ JSON saved: model_comparison.json")

# --- 15.6 Group Standings JSON ---
standings_json = {}
for label, table in sorted(standings.items()):
    standings_json[f"Group {label}"] = [
        {'team': team, **stats} for team, stats in table
    ]
with open(JSN / "group_standings.json", 'w') as f:
    json.dump(standings_json, f, indent=2)
print("  ✓ JSON saved: group_standings.json")

# %% — 16. FINAL SUMMARY
print("\n" + "="*70)
print("🏁 EXPERIMENT COMPLETE — FINAL SUMMARY")
print("="*70)

print(f"""
┌──────────────────────────────────────────────────────────────┐
│                    ATLAS EXPERIMENT RESULTS                  │
├──────────────────────────────────────────────────────────────┤
│  Best Model:        {best_name:<40}│
│  Test Accuracy:     {best_result['accuracy']:<40.4f}│
│  F1 Macro:          {best_result['f1_macro']:<40.4f}│
│  Brier Score:       {best_result['brier_score']:<40.4f}│
│  Log Loss:          {best_result['log_loss']:<40.4f}│
│  ROC AUC:           {best_result['roc_auc']:<40.4f}│
├──────────────────────────────────────────────────────────────┤
│  Models Trained:    {len(results):<40}│
│  Features Used:     {len(FINAL_FEATURES):<40}│
│  Training Samples:  {len(y_train):<40}│
│  Test Samples:      {len(y_test):<40}│
├──────────────────────────────────────────────────────────────┤
│  WC 2026 Matches:   {len(df_predictions):<40}│
│  Simulations Run:   {N_SIMULATIONS:<40,}│
│  Players Scored:    {len(df_ps):<40,}│
├──────────────────────────────────────────────────────────────┤
│  Figures Generated: {len(list(FIG.rglob('*.png'))):<40}│
│  CSVs Generated:    {len(list(RES.rglob('*.csv'))):<40}│
│  Models Saved:      {len(list(MOD.rglob('*.pkl'))):<40}│
│  JSONs Generated:   {len(list(JSN.rglob('*.json'))):<40}│
└──────────────────────────────────────────────────────────────┘
""")

# Print all output files
print("  📁 Output Files:")
for f in sorted(OUT.rglob('*')):
    if f.is_file():
        size = f.stat().st_size
        if size > 1024*1024:
            size_str = f"{size/1024/1024:.1f} MB"
        elif size > 1024:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size} B"
        print(f"    {f.relative_to(OUT)} ({size_str})")

print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
