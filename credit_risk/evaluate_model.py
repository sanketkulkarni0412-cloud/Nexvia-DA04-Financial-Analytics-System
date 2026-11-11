"""
Scorecard Model Evaluation & Diagnostic Module
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2A (Model Evaluation & Calibration)
Framing: Retail Credit Risk Scorecard Diagnostics

Metrics Evaluated:
1. Discrimination:
   - ROC-AUC
   - Gini Index (2 * AUC - 1)
   - Kolmogorov-Smirnov (KS) Statistic
   - Precision-Recall AUC (PR-AUC)
2. Calibration & Error:
   - Brier Score
   - Decile Calibration Table (Observed vs. Predicted Default Rate)
3. Classification Performance:
   - Confusion Matrix (at 0.5 threshold and optimal KS threshold)
   - Precision, Recall, Specificity, F1-Score
"""

import os
import sys
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_curve
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class ScorecardEvaluator:
    """
    Computes discrimination, calibration, confusion matrix, and decile tables
    for scorecard probability models.
    """

    @staticmethod
    def calculate_ks(y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, float]:
        """
        Calculates the two-sample Kolmogorov-Smirnov (KS) statistic and optimal threshold.
        KS = max(Cumulative Bads - Cumulative Goods).
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        # Difference between true positive rate (cumulative bads) and false positive rate (cumulative goods)
        ks_distances = tpr - fpr
        max_idx = np.argmax(ks_distances)
        ks_stat = float(ks_distances[max_idx])
        optimal_threshold = float(thresholds[max_idx])
        return round(ks_stat * 100.0, 2), round(optimal_threshold, 4)

    @classmethod
    def evaluate_dataset(
        cls,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        dataset_name: str = "Test"
    ) -> Dict[str, Any]:
        """
        Computes all standard discrimination and calibration metrics for a dataset.
        """
        auc = float(roc_auc_score(y_true, y_prob))
        gini = float(2.0 * auc - 1.0)
        pr_auc = float(average_precision_score(y_true, y_prob))
        brier = float(brier_score_loss(y_true, y_prob))
        ks_stat, opt_thresh = cls.calculate_ks(y_true, y_prob)

        # Standard 0.5 threshold metrics
        y_pred_50 = (y_prob >= 0.50).astype(int)
        cm_50 = confusion_matrix(y_true, y_pred_50)
        p_50, r_50, f1_50, _ = precision_recall_fscore_support(
            y_true, y_pred_50, average="binary", zero_division=0
        )

        # Optimal KS threshold metrics
        y_pred_opt = (y_prob >= opt_thresh).astype(int)
        cm_opt = confusion_matrix(y_true, y_pred_opt)
        p_opt, r_opt, f1_opt, _ = precision_recall_fscore_support(
            y_true, y_pred_opt, average="binary", zero_division=0
        )

        return {
            "dataset": dataset_name,
            "sample_size": len(y_true),
            "actual_bad_count": int(y_true.sum()),
            "actual_bad_rate": round(float(y_true.mean()), 4),
            "roc_auc": round(auc, 4),
            "gini": round(gini, 4),
            "ks_statistic_pct": ks_stat,
            "ks_optimal_threshold": opt_thresh,
            "pr_auc": round(pr_auc, 4),
            "brier_score": round(brier, 4),
            "metrics_at_0_50": {
                "threshold": 0.50,
                "precision": round(float(p_50), 4),
                "recall": round(float(r_50), 4),
                "f1_score": round(float(f1_50), 4),
                "confusion_matrix": {
                    "tn": int(cm_50[0, 0]),
                    "fp": int(cm_50[0, 1]),
                    "fn": int(cm_50[1, 0]),
                    "tp": int(cm_50[1, 1])
                }
            },
            "metrics_at_optimal_ks": {
                "threshold": opt_thresh,
                "precision": round(float(p_opt), 4),
                "recall": round(float(r_opt), 4),
                "f1_score": round(float(f1_opt), 4),
                "confusion_matrix": {
                    "tn": int(cm_opt[0, 0]),
                    "fp": int(cm_opt[0, 1]),
                    "fn": int(cm_opt[1, 0]),
                    "tp": int(cm_opt[1, 1])
                }
            }
        }

    @staticmethod
    def generate_decile_calibration_table(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        n_bins: int = 10
    ) -> pd.DataFrame:
        """
        Creates an institutional risk decile calibration table:
        Ranks borrowers into 10 risk buckets from lowest risk (Decile 1) to highest risk (Decile 10).
        """
        df = pd.DataFrame({
            "actual": y_true,
            "pred_prob": y_prob
        })

        # Divide into risk deciles based on predicted probability
        df["decile"] = pd.qcut(df["pred_prob"], q=n_bins, labels=False, duplicates="drop") + 1

        summary = df.groupby("decile").agg(
            loan_count=("actual", "count"),
            bad_count=("actual", "sum"),
            min_predicted_prob=("pred_prob", "min"),
            max_predicted_prob=("pred_prob", "max"),
            mean_predicted_prob=("pred_prob", "mean")
        ).reset_index()

        summary["good_count"] = summary["loan_count"] - summary["bad_count"]
        summary["observed_bad_rate"] = summary["bad_count"] / summary["loan_count"]
        summary["calibration_ratio"] = summary["mean_predicted_prob"] / summary["observed_bad_rate"]

        # Cumulative metrics for KS calculation
        total_bads = summary["bad_count"].sum()
        total_goods = summary["good_count"].sum()

        summary["pct_of_all_bads"] = summary["bad_count"] / total_bads
        summary["pct_of_all_goods"] = summary["good_count"] / total_goods
        summary["cum_pct_bads"] = summary["pct_of_all_bads"].cumsum()
        summary["cum_pct_goods"] = summary["pct_of_all_goods"].cumsum()
        summary["decile_ks"] = (summary["cum_pct_bads"] - summary["cum_pct_goods"]).abs() * 100.0

        # Formatting
        summary["min_predicted_prob"] = summary["min_predicted_prob"].round(4)
        summary["max_predicted_prob"] = summary["max_predicted_prob"].round(4)
        summary["mean_predicted_prob"] = summary["mean_predicted_prob"].round(4)
        summary["observed_bad_rate"] = summary["observed_bad_rate"].round(4)
        summary["calibration_ratio"] = summary["calibration_ratio"].round(4)
        summary["decile_ks"] = summary["decile_ks"].round(2)

        return summary

