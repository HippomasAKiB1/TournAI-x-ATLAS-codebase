import numpy as np
import pandas as pd
from ..data.preprocessor import ATLASPreprocessor
from .feature_engineering import engineer_features, FINAL_FEATURES

class ATLASPredictor:
    """Predictor class that loads models and preprocessors to forecast outcomes of new fixtures."""
    def __init__(self, model, preprocessor: ATLASPreprocessor):
        self.model = model
        self.preprocessor = preprocessor
        
    def predict_probs(self, df_fixture: pd.DataFrame) -> np.ndarray:
        """Predict win/draw/loss probabilities for a DataFrame of fixtures."""
        df_engineered = engineer_features(df_fixture)
        
        # Check if the model is Logistic Regression or MLP to determine if scaling is required
        model_name = type(self.model).__name__
        if model_name in ['LogisticRegression', 'MLPClassifier']:
            X = self.preprocessor.transform(df_engineered)
        else:
            # Trees (XGBoost, LightGBM, CatBoost) don't require feature scaling
            # But they still need correct column order and missing value imputation
            df_imputed = self.preprocessor.impute(df_engineered)
            X = df_imputed[FINAL_FEATURES].values
            X = np.nan_to_num(X, nan=0.0)
            
        return self.model.predict_proba(X)

    def predict_match(self, match_row_dict: dict) -> dict:
        """Predict probabilities for a single match represented as a dictionary of features."""
        df = pd.DataFrame([match_row_dict])
        probs = self.predict_probs(df)[0]
        
        prob_away_win = float(probs[0])
        prob_draw = float(probs[1])
        prob_home_win = float(probs[2])
        
        confidence = max(prob_away_win, prob_draw, prob_home_win)
        
        if confidence == prob_home_win:
            pred = 'Home Win'
        elif confidence == prob_draw:
            pred = 'Draw'
        else:
            pred = 'Away Win'
            
        return {
            'home_win_prob': round(prob_home_win, 4),
            'draw_prob': round(prob_draw, 4),
            'away_win_prob': round(prob_away_win, 4),
            'predicted_result': pred,
            'confidence': round(confidence, 4)
        }
