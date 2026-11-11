"""
Final Credit Risk Scorecard & Probability of Default Model
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B (Production Credit Risk Scorecard)
Framing: Retail Credit Risk Scorecard Modeling
Data Source: SQLite Data Warehouse (warehouse.db) in read-only mode (mode=ro)

Approved Predictors (7 Features):
1. term_months_woe
2. fico_midpoint_woe
3. installment_to_income_woe
4. dti_woe
5. verification_status_woe
6. home_ownership_clean_woe
7. annual_inc_woe
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.woe_iv import WOEBinningTransformer
from credit_risk.scorecard_scaling import ScorecardScaler
from credit_risk.reason_codes import AdverseReasonCodeGenerator


class FinalScorecardModel:
    """
    Manages training, inference, scoring, and calibration for the final 7-predictor scorecard.
    """

    APPROVED_FEATURES: List[str] = [
        "term_months_woe",
        "fico_midpoint_woe",
        "installment_to_income_woe",
        "dti_woe",
        "verification_status_woe",
        "home_ownership_clean_woe",
        "annual_inc_woe"
    ]

    def __init__(
        self,
        c_param: float = 1.0,
        solver: str = "lbfgs",
        max_iter: int = 1000,
        random_state: int = 42,
        C: Optional[float] = None
    ):
        self.c_param = C if C is not None else c_param
        self.solver = solver
        self.max_iter = max_iter
        self.random_state = random_state

        self.model = LogisticRegression(
            C=self.c_param,
            solver=self.solver,
            max_iter=self.max_iter,
            random_state=self.random_state
        )

        self.transformer: Optional[WOEBinningTransformer] = None
        self.scaler = ScorecardScaler()
        self.reason_generator: Optional[AdverseReasonCodeGenerator] = None

        self.is_fitted = False
        self.intercept_: float = 0.0
        self.coefficients_: Dict[str, float] = {}

    def fit(self, train_df: pd.DataFrame, target_col: str = "target") -> "FinalScorecardModel":
        """
        Fits WOE binning, logistic regression, scaling points, and reason code generator on train only.
        """
        assert target_col in train_df.columns, f"Target column '{target_col}' missing in train_df"

        # 1. Fit WOE binning transformer
        self.transformer = WOEBinningTransformer()
        self.transformer.fit(train_df, target_col=target_col)

        # 2. Transform train data to WOE features
        X_train_woe = self.transformer.transform(train_df)[self.APPROVED_FEATURES]
        y_train = train_df[target_col].values

        # 3. Fit Logistic Regression
        self.model.fit(X_train_woe.values, y_train)
        self.intercept_ = float(self.model.intercept_[0])
        self.coefficients_ = {
            feat: float(coef) for feat, coef in zip(self.APPROVED_FEATURES, self.model.coef_[0])
        }

        # 4. Build Scorecard Scaling points table
        self.scaler.build_points_table(
            coefficients=self.coefficients_,
            intercept=self.intercept_,
            woe_tables=self.transformer.woe_tables
        )

        # 5. Initialize Reason Code Generator
        self.reason_generator = AdverseReasonCodeGenerator(self.scaler.points_table_)

        self.is_fitted = True
        return self

    def predict_proba(self, df_raw: pd.DataFrame) -> np.ndarray:
        """
        Computes predicted default probabilities P(Y=1).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba().")
        X_woe = self.transformer.transform(df_raw)[self.APPROVED_FEATURES]
        return self.model.predict_proba(X_woe.values)[:, 1]

    def predict(self, df_raw: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """
        Computes binary default predictions.
        """
        probs = self.predict_proba(df_raw)
        return (probs >= threshold).astype(int)

    def score(self, df_raw: pd.DataFrame) -> np.ndarray:
        """
        Computes continuous credit scores.
        Score = Offset - Factor * log_odds
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before scoring.")
        X_woe = self.transformer.transform(df_raw)[self.APPROVED_FEATURES]
        log_odds = self.intercept_ + np.dot(
            X_woe.values,
            [self.coefficients_[f] for f in self.APPROVED_FEATURES]
        )
        return self.scaler.score_from_log_odds(log_odds)

    def evaluate(self, df_raw: pd.DataFrame, target_col: str = "target") -> Dict[str, Any]:
        """
        Evaluates discrimination (AUC, Gini, KS, PR-AUC) and calibration (Brier, Deciles).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before evaluate().")
        assert target_col in df_raw.columns, f"Target column '{target_col}' missing"

        y_true = df_raw[target_col].values
        probs = self.predict_proba(df_raw)
        scores = self.score(df_raw)

        auc = float(roc_auc_score(y_true, probs))
        gini = float(2.0 * auc - 1.0)
        prauc = float(average_precision_score(y_true, probs))
        brier = float(brier_score_loss(y_true, probs))

        # KS Statistic
        eval_df = pd.DataFrame({"target": y_true, "prob": probs, "score": scores})
        eval_df = eval_df.sort_values("prob", ascending=False).reset_index(drop=True)
        total_bads = int((y_true == 1).sum())
        total_goods = int((y_true == 0).sum())

        eval_df["cum_bads"] = (eval_df["target"] == 1).cumsum() / total_bads
        eval_df["cum_goods"] = (eval_df["target"] == 0).cumsum() / total_goods
        ks_stat = float(np.max(np.abs(eval_df["cum_bads"] - eval_df["cum_goods"])) * 100.0)

        # 10 Decile Calibration
        # Decile 1 = lowest risk (highest score) to Decile 10 = highest risk (lowest score)
        eval_df["decile_rank"] = pd.qcut(eval_df["prob"], q=10, labels=False, duplicates="drop")
        decile_rows = []
        for d in range(10):
            sub = eval_df[eval_df["decile_rank"] == d]
            count = len(sub)
            if count == 0:
                continue
            act_b = int(sub["target"].sum())
            pred_b = float(sub["prob"].sum())
            act_rate = act_b / count
            pred_rate = pred_b / count
            decile_rows.append({
                "decile": d + 1,
                "total_count": count,
                "actual_bads": act_b,
                "predicted_bads": round(pred_b, 1),
                "actual_bad_rate": round(act_rate, 4),
                "predicted_bad_rate": round(pred_rate, 4),
                "calibration_ratio": round(pred_rate / act_rate, 4) if act_rate > 0 else 1.0,
                "min_score": int(round(sub["score"].min())),
                "max_score": int(round(sub["score"].max()))
            })

        # Risk Bands Summary
        risk_band_df = self.scaler.generate_risk_band_summary(eval_df, target_col="target")

        return {
            "sample_size": len(df_raw),
            "good_count": total_goods,
            "bad_count": total_bads,
            "empirical_bad_rate": round(float(y_true.mean()), 6),
            "discrimination_metrics": {
                "roc_auc": round(auc, 4),
                "gini": round(gini, 4),
                "ks_statistic_pct": round(ks_stat, 2),
                "pr_auc": round(prauc, 4)
            },
            "calibration_metrics": {
                "brier_score": round(brier, 4)
            },
            "decile_calibration_table": decile_rows,
            "risk_band_distribution": risk_band_df.to_dict(orient="records")
        }

    def explain_adverse_action(self, applicant_profile: Dict[str, Any], top_n: int = 4) -> Dict[str, Any]:
        """
        Takes raw applicant features, determines bin and points, and returns top adverse reason codes.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before explaining adverse action.")

        df_single = pd.DataFrame([applicant_profile])
        X_woe = self.transformer.transform(df_single)
        prob = float(self.predict_proba(df_single)[0])
        score = int(round(float(self.score(df_single)[0])))
        risk_band = self.scaler.assign_risk_band(score)

        # Get bin assignments for each feature
        bin_assignments = {}
        for feat in self.scaler.points_lookup_.keys():
            if feat in self.transformer.continuous_bins:
                edges = self.transformer.continuous_bins[feat]
                val = float(applicant_profile.get(feat, np.nan))
                binned = pd.cut([val], bins=edges, right=True, include_lowest=True).astype(str)[0]
                bin_assignments[feat] = binned
            else:
                bin_assignments[feat] = str(applicant_profile.get(feat, "Missing"))

        _, breakdown = self.scaler.score_single(bin_assignments)
        reasons = self.reason_generator.generate_adverse_reasons(breakdown, top_n=top_n)

        return {
            "credit_score": score,
            "probability_of_default": round(prob, 4),
            "risk_band": risk_band["band"],
            "tier": risk_band["tier"],
            "points_breakdown": breakdown,
            "adverse_action_reasons": reasons
        }

