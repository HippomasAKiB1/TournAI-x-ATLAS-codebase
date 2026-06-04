import numpy as np
import pandas as pd
import shap
from pathlib import Path
from ..models.feature_engineering import FINAL_FEATURES

class ATLASShapExplainer:
    """Explainer class for wrapping SHAP value computations using fast TreeExplainer fallback logic."""
    def __init__(self, best_model, best_model_name: str, models_dict: dict, feature_names: list):
        self.feature_names = list(feature_names)
        self.shap_model_name = best_model_name
        self.shap_model = best_model
        
        # Fall back to best tree-based model if primary model is an ensemble/neural net
        tree_based_classes = ['XGBoost', 'LightGBM', 'CatBoost', 'Random Forest', 'Gradient Boosting']
        if self.shap_model_name not in tree_based_classes:
            best_tree_acc = -1.0
            for name in tree_based_classes:
                if name in models_dict:
                    # We can't access accuracy directly unless we pass it, so let's check if we have results
                    # Or we can just use the first available tree model as a fallback (usually XGBoost/LightGBM)
                    self.shap_model_name = name
                    self.shap_model = models_dict[name]
                    break
                    
        self.explainer = shap.TreeExplainer(self.shap_model)
        
    def compute_shap_values(self, X_test) -> np.ndarray:
        """Compute SHAP values for a given test set."""
        return self.explainer.shap_values(X_test)
        
    def get_global_importance(self, shap_values) -> pd.DataFrame:
        """Calculate global feature importances by averaging absolute SHAP values across classes."""
        if isinstance(shap_values, list):
            # List of arrays (multiclass output)
            shap_abs_mean = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
        elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
            # 3D array: (n_samples, n_features, n_classes)
            shap_abs_mean = np.abs(shap_values).mean(axis=(0, 2))
        else:
            # 2D array: (n_samples, n_features)
            shap_abs_mean = np.abs(shap_values).mean(axis=0)
            
        df_importance = pd.DataFrame({
            'feature': self.feature_names,
            'shap_importance': shap_abs_mean
        }).sort_values('shap_importance', ascending=False)
        
        return df_importance

    def explain_prediction(self, X_sample) -> np.ndarray:
        """Compute SHAP values for a single prediction row."""
        # Ensure correct shape (1, n_features)
        if len(X_sample.shape) == 1:
            X_sample = X_sample.reshape(1, -1)
            
        fix_shap = self.explainer.shap_values(X_sample)
        
        # Handle shape differences for multiclass
        if isinstance(fix_shap, list):
            shap_vals = fix_shap[2][0]  # Win class (index 2)
        elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 3:
            # Shape is (1, n_features, n_classes) -> extract Win class
            shap_vals = fix_shap[0, :, 2]
        elif isinstance(fix_shap, np.ndarray) and len(fix_shap.shape) == 2:
            # Shape is (1, n_features)
            shap_vals = fix_shap[0]
        else:
            shap_vals = fix_shap
            
        return shap_vals
