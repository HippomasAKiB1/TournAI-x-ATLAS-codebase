import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    log_loss, cohen_kappa_score, matthews_corrcoef,
    classification_report, confusion_matrix, roc_auc_score
)

class ATLASModelEvaluator:
    """Evaluator class for calculating classification metrics and running pairwise statistical significance tests."""
    def __init__(self, models, cv_results=None):
        self.models = models
        self.cv_results = cv_results or {}
        self.results = {}
        
    def evaluate(self, X_test, y_test, X_test_scaled) -> pd.DataFrame:
        """Run full evaluation suite for all trained models on test set."""
        comparison_data = []
        
        for name, model in self.models.items():
            # Use scaled data for LR and MLP, raw features for trees/ensembles
            X_te = X_test_scaled if name in ['Logistic Regression', 'MLP Neural Net'] else X_test
            
            y_pred = model.predict(X_te)
            y_prob = model.predict_proba(X_te)
            
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
            
            # ROC AUC (weighted one-vs-rest)
            try:
                roc_auc = roc_auc_score(y_test, y_prob, multi_class='ovr', average='weighted')
            except Exception:
                roc_auc = np.nan
                
            cv_mean = self.cv_results.get(name, {}).get('mean', np.nan)
            cv_std = self.cv_results.get(name, {}).get('std', np.nan)
            
            self.results[name] = {
                'y_pred': y_pred,
                'y_prob': y_prob,
                'accuracy': acc,
                'balanced_accuracy': bal_acc,
                'f1_macro': f1_macro,
                'brier_score': brier,
                'log_loss': logloss,
                'roc_auc': roc_auc,
            }
            
            comparison_data.append({
                'Model': name,
                'Accuracy': acc,
                'Balanced Acc': bal_acc,
                'F1 Macro': f1_macro,
                'F1 Weighted': f1_weighted,
                'Cohen Kappa': kappa,
                'MCC': mcc,
                'Log Loss': logloss,
                'Brier Score': brier,
                'ROC AUC': roc_auc,
                'CV Mean': cv_mean,
                'CV Std': cv_std,
            })
            
        df_comparison = pd.DataFrame(comparison_data).sort_values('Accuracy', ascending=False)
        return df_comparison

    def get_best_model(self, df_comparison: pd.DataFrame):
        """Retrieve the best-performing model based on accuracy."""
        best_name = df_comparison.iloc[0]['Model']
        return best_name, self.models[best_name]

    def generate_classification_report(self, best_model_name, X_test, y_test, X_test_scaled) -> dict:
        """Generate classification report dictionary for the best model."""
        model = self.models[best_model_name]
        X_te = X_test_scaled if best_model_name in ['Logistic Regression', 'MLP Neural Net'] else X_test
        y_pred = model.predict(X_te)
        return classification_report(y_test, y_pred, target_names=['Loss', 'Draw', 'Win'], output_dict=True)

    def run_significance_tests(self, best_model_name, y_test) -> pd.DataFrame:
        """Run pairwise McNemar's tests comparing the best model against all others."""
        significance_results = []
        best_preds = self.results[best_model_name]['y_pred']
        
        for name in self.models.keys():
            if name == best_model_name:
                continue
            other_preds = self.results[name]['y_pred']
            
            # contingency table elements
            correct_best = (best_preds == y_test)
            correct_other = (other_preds == y_test)
            b = np.sum(correct_best & ~correct_other)  # best right, other wrong
            c = np.sum(~correct_best & correct_other)  # best wrong, other right
            
            if (b + c) > 0:
                chi2 = (abs(b - c) - 1)**2 / (b + c)
                p_val = 1 - stats.chi2.cdf(chi2, df=1)
            else:
                chi2, p_val = 0.0, 1.0
                
            sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
            significance_results.append({
                'Comparison': f'{best_model_name} vs {name}',
                'b (best_only)': b, 'c (other_only)': c,
                'McNemar_chi2': chi2, 'p_value': p_val, 'Significance': sig
            })
            
        return pd.DataFrame(significance_results)
