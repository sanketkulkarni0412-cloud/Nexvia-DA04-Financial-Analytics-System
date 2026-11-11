"""
Scorecard Scaling, Point Allocation & Risk Banding Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B (Scorecard Scaling & Calibration)
Framing: Retail Credit Risk Scorecard Engineering

Methodological Formulation:
    Target Score: 600 points at 50:1 Good:Bad odds
    Points to Double the Odds (PDO): 20 points
    
    Factor = PDO / ln(2) = 20 / ln(2) ≈ 28.85390
    Offset = Base_Score - Factor * ln(Base_Odds) = 600 - 28.85390 * ln(50) ≈ 487.12288

    Individual Feature Points Calculation:
    For k approved features and logistic regression intercept beta_0:
        Base_Points_Per_Feature = (Offset - Factor * beta_0) / k
        Points(j, i) = round(Base_Points_Per_Feature - Factor * beta_j * WOE(j, i))
    
    Total Score = sum(Points(j, i)) across all k features.
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class ScorecardScaler:
    """
    Transforms calibrated logistic regression parameters into a transparent integer scorecard,
    computes score-to-PD calibrations, and assigns neutral risk bands.
    """

    BASE_SCORE: float = 600.0
    BASE_ODDS: float = 50.0  # 50:1 Good:Bad odds
    PDO: float = 20.0

    # Approved 6 Neutral Risk Bands
    RISK_BANDS = [
        {"band": "Very Low Risk", "min_score": 555, "max_score": 999, "tier": 1},
        {"band": "Low Risk", "min_score": 540, "max_score": 554, "tier": 2},
        {"band": "Moderate Risk", "min_score": 530, "max_score": 539, "tier": 3},
        {"band": "Elevated Risk", "min_score": 520, "max_score": 529, "tier": 4},
        {"band": "High Risk", "min_score": 505, "max_score": 519, "tier": 5},
        {"band": "Very High Risk", "min_score": 0, "max_score": 504, "tier": 6}
    ]

    def __init__(
        self,
        base_score: float = BASE_SCORE,
        base_odds: float = BASE_ODDS,
        pdo: float = PDO
    ):
        self.base_score = float(base_score)
        self.base_odds = float(base_odds)
        self.pdo = float(pdo)

        # Mathematical derivation
        self.factor = self.pdo / np.log(2.0)
        self.offset = self.base_score - self.factor * np.log(self.base_odds)

        self.points_table_: Optional[pd.DataFrame] = None
        self.points_lookup_: Dict[str, Dict[str, int]] = {}
        self.base_points_per_feature_: float = 0.0
        self.is_fitted: bool = False

    def build_points_table(
        self,
        coefficients: Dict[str, float],
        intercept: float,
        woe_tables: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Derives integer points lookup table per bin across all features.
        """
        k = len(coefficients)
        assert k > 0, "At least one coefficient required"

        self.base_points_per_feature_ = (self.offset - self.factor * intercept) / k
        points_records = []
        self.points_lookup_ = {}

        for feat_woe, beta in coefficients.items():
            feat_name = feat_woe.replace("_woe", "")
            if feat_name not in woe_tables:
                continue

            woe_tbl = woe_tables[feat_name]
            feat_dict = {}

            for _, row in woe_tbl.iterrows():
                bin_label = str(row["bin"])
                woe_val = float(row["woe"])

                # Exact points formula:
                # Points = Base_Points_Per_Feature - Factor * beta * WOE
                # With beta < 0 and WOE > 0 for lower-risk tiers, -Factor*beta*WOE is positive.
                raw_pts = self.base_points_per_feature_ - self.factor * beta * woe_val
                int_pts = int(round(raw_pts))

                feat_dict[bin_label] = int_pts

                points_records.append({
                    "feature": feat_name,
                    "bin": bin_label,
                    "total_count": int(row.get("total_count", 0)),
                    "good_count": int(row.get("good_count", 0)),
                    "bad_count": int(row.get("bad_count", 0)),
                    "bad_rate": round(float(row.get("bad_rate", 0.0)), 6),
                    "woe": round(woe_val, 4),
                    "iv_contribution": round(float(row.get("iv_contribution", 0.0)), 6),
                    "coefficient": round(beta, 4),
                    "raw_points": round(raw_pts, 2),
                    "points": int_pts
                })

            self.points_lookup_[feat_name] = feat_dict

        self.points_table_ = pd.DataFrame(points_records)
        self.is_fitted = True
        return self.points_table_

    def score_single(self, bin_assignments: Dict[str, str]) -> Tuple[int, Dict[str, int]]:
        """
        Scores a single loan profile by summing integer points across attributes.
        """
        if not self.is_fitted:
            raise RuntimeError("Points table must be built before scoring.")

        breakdown = {}
        total_score = 0

        for feat, lookup in self.points_lookup_.items():
            bin_val = str(bin_assignments.get(feat, "Missing"))
            pts = lookup.get(bin_val, int(round(np.mean(list(lookup.values())))))
            breakdown[feat] = pts
            total_score += pts

        return total_score, breakdown

    def score_from_log_odds(self, log_odds: np.ndarray) -> np.ndarray:
        """
        Computes continuous scores directly from model log-odds.
        Score = Offset - Factor * log_odds
        """
        return self.offset - self.factor * log_odds

    def score_to_pd(self, score: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Converts credit scorecard points back to theoretical Probability of Default (PD).
        Formula:
            log_odds = (Offset - Score) / Factor
            Odds(Bad) = exp(log_odds)
            PD = Odds / (1 + Odds) = 1 / (1 + exp((Score - Offset) / Factor))
        """
        z = (score - self.offset) / self.factor
        return 1.0 / (1.0 + np.exp(z))

    def pd_to_score(self, pd_val: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Converts PD to credit scorecard points.
        """
        eps = 1e-12
        pd_clipped = np.clip(pd_val, eps, 1.0 - eps)
        log_odds = np.log(pd_clipped / (1.0 - pd_clipped))
        return self.offset - self.factor * log_odds

    def assign_risk_band(self, score: Union[int, float]) -> Dict[str, Any]:
        """
        Assigns an institutional risk band based on score.
        """
        s = int(round(score))
        for b in self.RISK_BANDS:
            if b["min_score"] <= s <= b["max_score"]:
                return {
                    "band": b["band"],
                    "tier": b["tier"],
                    "score": s,
                    "theoretical_pd": round(float(self.score_to_pd(s)), 4)
                }
        return {
            "band": "Very High Risk",
            "tier": 6,
            "score": s,
            "theoretical_pd": round(float(self.score_to_pd(s)), 4)
        }

    def generate_risk_band_summary(self, df_scored: pd.DataFrame, target_col: str = "target") -> pd.DataFrame:
        """
        Computes the portfolio distribution and calibration across the 6 risk bands.
        """
        assert "score" in df_scored.columns, "score column required"
        assert target_col in df_scored.columns, f"{target_col} column required"

        records = []
        total_pop = len(df_scored)
        total_bads = int(df_scored[target_col].sum())

        for b in self.RISK_BANDS:
            sub = df_scored[(df_scored["score"] >= b["min_score"]) & (df_scored["score"] <= b["max_score"])]
            count = len(sub)
            if count == 0:
                continue

            bads = int(sub[target_col].sum())
            actual_bad_rate = bads / count
            mean_score = float(sub["score"].mean())
            mean_prob = float(sub["prob"].mean()) if "prob" in sub.columns else float(self.score_to_pd(mean_score))

            records.append({
                "tier": b["tier"],
                "risk_band": b["band"],
                "score_range": f"{b['min_score']} - {b['max_score'] if b['max_score'] < 900 else '+'}",
                "total_count": count,
                "pct_portfolio": round(count / total_pop * 100.0, 2),
                "bad_count": bads,
                "actual_bad_rate": round(actual_bad_rate * 100.0, 2),
                "pred_bad_rate": round(mean_prob * 100.0, 2),
                "bad_capture_pct": round(bads / total_bads * 100.0, 2) if total_bads > 0 else 0.0,
                "mean_score": round(mean_score, 1)
            })

        summary_df = pd.DataFrame(records).sort_values("tier").reset_index(drop=True)
        summary_df["cumulative_bad_capture_pct"] = summary_df["bad_capture_pct"].cumsum().round(2)
        return summary_df

    def export_points_csv(self, output_path: str) -> None:
        """Exports points table to CSV."""
        if self.points_table_ is None:
            raise RuntimeError("Points table must be built before export.")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.points_table_.to_csv(output_path, index=False)

