import os
import joblib
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    VotingClassifier, StackingClassifier
)
from sklearn.neural_network import MLPClassifier
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

class ATLASModelTrainer:
    """Trainer class for defining, cross-validating, and exporting ATLAS machine learning models."""
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {}
        self.cv_results = {}
        self._initialize_base_models()
        
    def _initialize_base_models(self):
        """Initialize the 7 core classifiers with predefined hyperparameters."""
        self.models['Logistic Regression'] = LogisticRegression(
            max_iter=2000, solver='lbfgs', class_weight='balanced',
            C=1.0, random_state=self.random_state
        )
        self.models['Random Forest'] = RandomForestClassifier(
            n_estimators=500, max_depth=12, min_samples_split=10,
            min_samples_leaf=5, class_weight='balanced',
            random_state=self.random_state, n_jobs=-1
        )
        self.models['Gradient Boosting'] = GradientBoostingClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, random_state=self.random_state
        )
        self.models['XGBoost'] = xgb.XGBClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
            objective='multi:softprob', num_class=3,
            random_state=self.random_state, n_jobs=-1, verbosity=0,
            use_label_encoder=False, eval_metric='mlogloss'
        )
        self.models['LightGBM'] = lgb.LGBMClassifier(
            n_estimators=500, max_depth=7, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
            num_class=3, objective='multiclass',
            random_state=self.random_state, n_jobs=-1, verbose=-1,
            class_weight='balanced', is_unbalance=False
        )
        self.models['CatBoost'] = CatBoostClassifier(
            iterations=500, depth=6, learning_rate=0.05,
            l2_leaf_reg=3, auto_class_weights='Balanced',
            random_seed=self.random_state, verbose=0, loss_function='MultiClass'
        )
        self.models['MLP Neural Net'] = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64), activation='relu',
            solver='adam', max_iter=500, early_stopping=True,
            validation_fraction=0.15, learning_rate='adaptive',
            random_state=self.random_state
        )

    def train_and_cross_validate(self, X_train, y_train, X_train_scaled, n_splits=5):
        """Run Stratified K-Fold cross-validation and fit base models on full training data."""
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)
        
        for name, model in self.models.items():
            print(f"  Training & CV: {name}...")
            # Use scaled data for LR and MLP, raw features for tree-based classifiers
            X_tr = X_train_scaled if name in ['Logistic Regression', 'MLP Neural Net'] else X_train
            
            # Cross-validation score
            scores = cross_val_score(model, X_tr, y_train, cv=cv, scoring='accuracy', n_jobs=-1)
            self.cv_results[name] = {
                'mean': float(np.mean(scores)),
                'std': float(np.std(scores))
            }
            
            # Fit on full training set
            model.fit(X_tr, y_train)
            
        # Train ensembles
        self._train_ensembles(X_train, y_train, X_train_scaled)
        
    def _train_ensembles(self, X_train, y_train, X_train_scaled):
        """Train Voting and Stacking meta-ensembles on top of the base classifiers."""
        print("  Training Voting Ensemble...")
        voting = VotingClassifier(
            estimators=[
                ('xgb', self.models['XGBoost']),
                ('lgbm', self.models['LightGBM']),
                ('cb', self.models['CatBoost']),
            ],
            voting='soft',
            n_jobs=-1
        )
        voting.fit(X_train, y_train)
        self.models['Voting Ensemble'] = voting
        self.cv_results['Voting Ensemble'] = {'mean': np.nan, 'std': np.nan}
        
        print("  Training Stacking Ensemble...")
        stacking = StackingClassifier(
            estimators=[
                ('xgb', xgb.XGBClassifier(
                    n_estimators=300, max_depth=5, learning_rate=0.05,
                    random_state=self.random_state, verbosity=0,
                    use_label_encoder=False, eval_metric='mlogloss'
                )),
                ('lgbm', lgb.LGBMClassifier(
                    n_estimators=300, max_depth=6, learning_rate=0.05,
                    random_state=self.random_state, verbose=-1
                )),
                ('cb', CatBoostClassifier(
                    iterations=300, depth=5, learning_rate=0.05,
                    random_seed=self.random_state, verbose=0
                )),
            ],
            final_estimator=LogisticRegression(max_iter=1000, random_state=self.random_state),
            cv=5,
            n_jobs=-1
        )
        stacking.fit(X_train, y_train)
        self.models['Stacking Ensemble'] = stacking
        self.cv_results['Stacking Ensemble'] = {'mean': np.nan, 'std': np.nan}
        
    def save_models(self, out_dir: Path):
        """Serialize and save all trained models to the specified directory."""
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, model in self.models.items():
            safe_name = name.lower().replace(' ', '_')
            joblib.dump(model, out_dir / f"{safe_name}.pkl")
        print(f"  ✓ Saved {len(self.models)} models to {out_dir}")
        
    def load_models(self, in_dir: Path):
        """Deserialize and load saved models from the specified directory."""
        for name in list(self.models.keys()) + ['Voting Ensemble', 'Stacking Ensemble']:
            safe_name = name.lower().replace(' ', '_')
            path = Path(in_dir) / f"{safe_name}.pkl"
            if path.exists():
                self.models[name] = joblib.load(path)
        print(f"  ✓ Loaded available models from {in_dir}")
        return self
