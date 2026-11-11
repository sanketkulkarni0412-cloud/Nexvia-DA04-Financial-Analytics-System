"""
Weight of Evidence (WOE) & Information Value (IV) Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2A (Scorecard Coarse Classing & Variable Selection)
Methodology: Credit Risk Scorecard Engineering

Mathematical Formulation:
    For bin i:
        Goods_i = count of Y = 0 in bin i
        Bads_i  = count of Y = 1 in bin i
        Dist_Goods_i = Goods_i / Total_Goods
        Dist_Bads_i  = Bads_i / Total_Bads

        WOE_i = ln( Dist_Goods_i / Dist_Bads_i )
        IV_i  = ( Dist_Goods_i - Dist_Bads_i ) * WOE_i
        Total_IV = sum( IV_i )

Orientation Note:
    With WOE = ln(Dist_Goods / Dist_Bads), higher WOE indicates a higher concentration
    of Good borrowers (lower default risk). When predicting log-odds of Bad in standard
    logistic regression, the feature coefficient is expected to be negative.
"""

import os
import sys
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class WOEBinningTransformer:
    """
    Fits coarse classing and WOE mappings exclusively on training data,
    then transforms train and test datasets without data leakage.
    """

    # Domain-informed candidate bin cuts for continuous predictors (Phase 2B Refined)
    DEFAULT_CONTINUOUS_BINS: Dict[str, List[float]] = {
        "fico_midpoint": [-np.inf, 670, 690, 715, 745, 780, np.inf],
        "dti": [-np.inf, 0.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, np.inf],
        "annual_inc": [-np.inf, 0.0, 35000, 50000, 75000, 100000, 150000, np.inf],
        "loan_amnt": [-np.inf, 7500, 12000, 18000, 25000, 35000, np.inf],
        "revol_util": [-np.inf, 0.0, 25.0, 50.0, 75.0, 100.0, np.inf],
        "emp_length_imputed": [-np.inf, 0.0, 2.0, 5.0, 8.0, 10.0, np.inf],
        "credit_history_months": [-np.inf, 120, 180, 240, 360, np.inf],
        "installment_to_income": [-np.inf, 0.0, 6.0, 10.0, 14.0, 20.0, np.inf],
        "open_acc": [-np.inf, 6, 10, 15, 20, np.inf],
        "total_acc": [-np.inf, 15, 25, 35, 50, np.inf],
        "pub_rec": [-np.inf, 0, 1, np.inf],
        "revol_bal": [-np.inf, 5000, 10000, 20000, 40000, np.inf]
    }

    # Approved categorical predictors
    CATEGORICAL_PREDICTORS: List[str] = [
        "term_months",
        "home_ownership_clean",
        "verification_status"
    ]

    def __init__(self, continuous_bins: Optional[Dict[str, List[float]]] = None):
        self.continuous_bins = continuous_bins or self.DEFAULT_CONTINUOUS_BINS
        self.is_fitted = False
        self.woe_tables: Dict[str, pd.DataFrame] = {}
        self.bin_mappings: Dict[str, Dict[str, float]] = {}
        self.iv_summary: Optional[pd.DataFrame] = None
        self.total_goods = 0
        self.total_bads = 0

    def fit(self, df: pd.DataFrame, target_col: str = "target") -> "WOEBinningTransformer":
        """
        Learns coarse classing and computes WOE and IV strictly on training data.
        """
        assert target_col in df.columns, f"Target column '{target_col}' not in dataframe"
        y = df[target_col].values
        self.total_goods = int((y == 0).sum())
        self.total_bads = int((y == 1).sum())

        assert self.total_goods > 0 and self.total_bads > 0, "Both Goods and Bads required for WOE calculation"

        all_ivs = []

        # 1. Process continuous predictors
        for var, edges in self.continuous_bins.items():
            if var not in df.columns:
                continue

            # Binning
            series = df[var].copy()
            binned = pd.cut(series, bins=edges, right=True, include_lowest=True).astype(str)
            # Tag nulls as a distinct bin if any
            binned = binned.fillna("Missing")

            woe_table, var_iv = self._compute_woe_table(var, binned, df[target_col])
            self.woe_tables[var] = woe_table
            self.bin_mappings[var] = dict(zip(woe_table["bin"], woe_table["woe"]))
            all_ivs.append({"variable": var, "iv": var_iv, "feature_type": "continuous"})

        # 2. Process categorical predictors
        for var in self.CATEGORICAL_PREDICTORS:
            if var not in df.columns:
                continue

            series = df[var].fillna("Missing").astype(str)
            woe_table, var_iv = self._compute_woe_table(var, series, df[target_col])
            self.woe_tables[var] = woe_table
            self.bin_mappings[var] = dict(zip(woe_table["bin"], woe_table["woe"]))
            all_ivs.append({"variable": var, "iv": var_iv, "feature_type": "categorical"})

        # Create IV summary table
        iv_df = pd.DataFrame(all_ivs).sort_values("iv", ascending=False).reset_index(drop=True)
        iv_df["predictive_power"] = iv_df["iv"].apply(self._classify_iv)
        self.iv_summary = iv_df
        self.is_fitted = True

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies learned WOE mappings to any dataset (Train, Test, or OOT)
        without refitting or data leakage.
        """
        if not self.is_fitted:
            raise RuntimeError("Transformer must be fitted on training data before transform().")

        df_out = pd.DataFrame(index=df.index)

        # Transform continuous features
        for var, edges in self.continuous_bins.items():
            if var not in df.columns or var not in self.bin_mappings:
                continue

            series = df[var].copy()
            binned = pd.cut(series, bins=edges, right=True, include_lowest=True).astype(str)
            binned = binned.fillna("Missing")

            mapping = self.bin_mappings[var]
            # Use mean WOE of the variable as a fallback for any completely unseen bin
            fallback = np.mean(list(mapping.values()))
            df_out[f"{var}_woe"] = binned.map(mapping).fillna(fallback).astype(float)

        # Transform categorical features
        for var in self.CATEGORICAL_PREDICTORS:
            if var not in df.columns or var not in self.bin_mappings:
                continue

            series = df[var].fillna("Missing").astype(str)
            mapping = self.bin_mappings[var]
            fallback = np.mean(list(mapping.values()))
            df_out[f"{var}_woe"] = series.map(mapping).fillna(fallback).astype(float)

        return df_out

    def _compute_woe_table(
        self,
        var_name: str,
        binned_series: pd.Series,
        target_series: pd.Series
    ) -> Tuple[pd.DataFrame, float]:
        """
        Computes the detailed bin-level WOE and IV table for a single feature.
        """
        grouped = pd.crosstab(binned_series, target_series, margins=False)
        # Ensure both classes exist
        if 0 not in grouped.columns:
            grouped[0] = 0
        if 1 not in grouped.columns:
            grouped[1] = 0

        grouped = grouped.rename(columns={0: "good_count", 1: "bad_count"})
        grouped["total_count"] = grouped["good_count"] + grouped["bad_count"]

        # Calculate rates
        grouped["good_rate"] = grouped["good_count"] / grouped["total_count"]
        grouped["bad_rate"] = grouped["bad_count"] / grouped["total_count"]

        # Distributions with Laplace smoothing (offset 0.5) to avoid div-by-zero
        goods_smoothed = grouped["good_count"] + 0.5
        bads_smoothed = grouped["bad_count"] + 0.5
        dist_goods = goods_smoothed / (self.total_goods + 0.5 * len(grouped))
        dist_bads = bads_smoothed / (self.total_bads + 0.5 * len(grouped))

        grouped["dist_goods"] = dist_goods
        grouped["dist_bads"] = dist_bads

        # WOE & IV
        grouped["woe"] = np.log(dist_goods / dist_bads)
        grouped["iv_contribution"] = (dist_goods - dist_bads) * grouped["woe"]
        grouped["cumulative_iv"] = grouped["iv_contribution"].cumsum()

        table = grouped.reset_index().rename(columns={binned_series.name or "index": "bin"})
        table.insert(0, "variable", var_name)

        var_total_iv = float(grouped["iv_contribution"].sum())
        return table, var_total_iv

    @staticmethod
    def _classify_iv(iv: float) -> str:
        """Classifies predictive power per retail banking scorecard standards."""
        if iv < 0.02:
            return "Unpredictive (<0.02)"
        elif iv < 0.10:
            return "Weak (0.02 - 0.10)"
        elif iv < 0.30:
            return "Medium (0.10 - 0.30)"
        elif iv <= 0.50:
            return "Strong (0.30 - 0.50)"
        else:
            return "Suspiciously High (>0.50) - Check Leakage"

    def export_woe_summary(self, output_csv_path: str) -> None:
        """Exports all bin tables into a consolidated CSV report."""
        if not self.is_fitted:
            raise RuntimeError("Transformer must be fitted before exporting summary.")
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        all_tables = [table for table in self.woe_tables.values()]
        consolidated = pd.concat(all_tables, ignore_index=True)
        consolidated.to_csv(output_csv_path, index=False)
