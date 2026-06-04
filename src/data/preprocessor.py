import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

class ATLASPreprocessor:
    """ATLAS preprocessor to handle feature imputation, demographic fallback, and scaling."""
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names = None
        self.is_fitted = False
        
    def fit(self, df: pd.DataFrame, feature_names):
        """Fit preprocessor parameters on a DataFrame for a given list of features."""
        self.feature_names = list(feature_names)
        df_imputed = self.impute(df)
        X = df_imputed[self.feature_names].values
        self.scaler.fit(X)
        self.is_fitted = True
        return self
        
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Apply scaling and imputation to a new DataFrame using the fitted preprocessor."""
        if not self.is_fitted:
            raise ValueError("Preprocessor has not been fitted yet.")
        df_imputed = self.impute(df)
        
        # Ensure all columns exist in the DataFrame
        for col in self.feature_names:
            if col not in df_imputed.columns:
                df_imputed[col] = 0.0
                
        X = df_imputed[self.feature_names].values
        # Double check for NaN values that might have slipped through and replace with 0
        X = np.nan_to_num(X, nan=0.0)
        return self.scaler.transform(X)
        
    def fit_transform(self, df: pd.DataFrame, feature_names) -> np.ndarray:
        """Fit and transform the DataFrame in one step."""
        self.fit(df, feature_names)
        return self.transform(df)
        
    def impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform custom missing-value imputation based on data types and fallbacks."""
        df_model = df.copy()
        
        # Fill tournament-progress features with 0 (e.g. for first match)
        tourn_fill_zero = [
            'tourn_matches_played', 'tourn_goals_for', 'tourn_goals_against',
            'tourn_goal_diff', 'tourn_wins', 'tourn_winrate', 'tourn_goals_per_match'
        ]
        for col in tourn_fill_zero:
            if col in df_model.columns:
                df_model[col] = df_model[col].fillna(0.0)
                
        # Fill squad features with 0 (not available for older tournaments)
        squad_features = [
            'squad_xg_per_match', 'squad_goals_per_match', 'squad_shots_per_match',
            'squad_key_passes_per_match', 'squad_interceptions_per_match',
            'squad_dribbles_per_match', 'squad_squad_pass_accuracy',
            'opp_squad_xg_per_match', 'opp_squad_goals_per_match', 'opp_squad_shots_per_match',
            'opp_squad_key_passes_per_match', 'opp_squad_interceptions_per_match',
            'opp_squad_dribbles_per_match', 'opp_squad_squad_pass_accuracy',
        ]
        for col in squad_features:
            if col in df_model.columns:
                df_model[col] = df_model[col].fillna(0.0)
                
        # Fill demographics with median or defaults
        demo_features = [
            'squad_avg_age', 'opp_squad_avg_age', 'age_diff',
            'avg_club_prestige', 'max_club_prestige',
            'opp_avg_club_prestige', 'opp_max_club_prestige',
            'club_prestige_diff',
        ]
        for col in demo_features:
            if col in df_model.columns:
                median_val = df_model[col].median()
                if pd.isna(median_val):
                    median_val = 0.0
                df_model[col] = df_model[col].fillna(median_val)
                
        # Fill confederation codes with mode or 1 (fallback)
        conf_features = ['team_conf_code', 'opp_conf_code']
        for col in conf_features:
            if col in df_model.columns:
                if not df_model[col].isnull().all():
                    mode_val = df_model[col].mode()[0]
                else:
                    mode_val = 1
                df_model[col] = df_model[col].fillna(mode_val)
                
        # Fill rest_days features with default median
        for col in ['rest_days', 'opp_rest_days', 'rest_days_adv']:
            if col in df_model.columns:
                median_val = df_model[col].median()
                if pd.isna(median_val):
                    median_val = 4.0
                df_model[col] = df_model[col].fillna(median_val)
                
        # Impute remaining features with 0.0
        if self.feature_names:
            available_feats = [f for f in self.feature_names if f in df_model.columns]
            df_model[available_feats] = df_model[available_feats].fillna(0.0)
        else:
            # Impute all numeric cols with 0
            num_cols = df_model.select_dtypes(include=[np.number]).columns
            df_model[num_cols] = df_model[num_cols].fillna(0.0)
            
        return df_model
        
    def save(self, path):
        """Save the preprocessor parameters to a file."""
        joblib.dump({
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted
        }, path)
        
    def load(self, path):
        """Load preprocessor parameters from a file."""
        data = joblib.load(path)
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']
        self.is_fitted = data['is_fitted']
        return self
