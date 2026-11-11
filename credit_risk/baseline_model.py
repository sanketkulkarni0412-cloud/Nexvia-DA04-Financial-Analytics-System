"""
Baseline Logistic Regression Scorecard Model
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2A (Baseline Scorecard Model)
Framing: Retail Credit Risk Scorecard Modeling

Model Specification:
    Standard Multivariate Logistic Regression on WOE-transformed features.
    No synthetic class balancing (SMOTE); preserves natural ~20% empirical prior.
    Objective: Predict probability of confirmed default P(Y=1) where 1 = Bad, 0 = Good.
"""

import os
import sys
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class BaselineScorecardModel:
    """
    Fits and manages the baseline logistic regression credit risk scorecard.
    """

    DEFAULT_FEATURE_NAMES: List[str] = [
        "term_months_woe",
        "fico_midpoint_woe",
        "installment_to_income_woe",
        "dti_woe",
        "verification_status_woe",
        "annual_inc_woe",
        "home_ownership_clean_woe",
        "revol_util_woe",
        "loan_amnt_woe"
    ]

    def __init__(
        self,
        c_param: float = 1.0,
        solver: str = "lbfgs",
        max_iter: int = 1000,
        random_state: int = 42,
        feature_names: Optional[List[str]] = None
    ):
        self.c_param = c_param
        self.solver = solver
        self.max_iter = max_iter
        self.random_state = random_state
        self.feature_names = feature_names or self.DEFAULT_FEATURE_NAMES

        # Initialize scikit-learn LogisticRegression without deprecated penalty parameter
        self.model = LogisticRegression(
            C=self.c_param,
            solver=self.solver,
            max_iter=self.max_iter,
            random_state=self.random_state
        )
        self.is_fitted = False
        self.coefficients_: Dict[str, float] = {}
        self.intercept_: float = 0.0

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray) -> "BaselineScorecardModel":
        """
        Fits logistic regression model on training WOE features.
        """
        assert all(col in X_train.columns for col in self.feature_names), (
            f"Missing required features in X_train. Expected: {self.feature_names}"
        )

        X_sub = X_train[self.feature_names].values
        self.model.fit(X_sub, y_train)

        self.intercept_ = float(self.model.intercept_[0])
        self.coefficients_ = {
            feat: float(coef) for feat, coef in zip(self.feature_names, self.model.coef_[0])
        }
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Returns predicted probability of default P(Y=1).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_proba().")
        X_sub = X[self.feature_names].values
        return self.model.predict_proba(X_sub)[:, 1]

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """
        Returns binary class predictions at given cutoff threshold.
        """
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def get_coefficient_table(self) -> pd.DataFrame:
        """
        Returns a clean tabular summary of model weights, odds ratios, and WOE orientation.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before requesting coefficient table.")

        rows = []
        for feat, coef in self.coefficients_.items():
            rows.append({
                "feature": feat,
                "coefficient": round(coef, 4),
                "odds_ratio": round(np.exp(coef), 4),
                "woe_direction": "Protective / Risk-Reducing" if coef < 0 else "Risk-Increasing"
            })

        df_coef = pd.DataFrame(rows)
        # Append Intercept
        intercept_row = pd.DataFrame([{
            "feature": "Intercept",
            "coefficient": round(self.intercept_, 4),
            "odds_ratio": round(np.exp(self.intercept_), 4),
            "woe_direction": "Base Log-Odds"
        }])
        return pd.concat([df_coef, intercept_row], ignore_index=True)

    def get_model_metadata(self) -> Dict[str, Any]:
        """
        Returns comprehensive metadata regarding model hyperparameters and structure.
        """
        return {
            "model_type": "LogisticRegression (Baseline Scorecard)",
            "solver": self.solver,
            "C": self.c_param,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "features_used": self.feature_names,
            "num_features": len(self.feature_names),
            "intercept": self.intercept_,
            "coefficients": self.coefficients_,
            "is_fitted": self.is_fitted
        }

