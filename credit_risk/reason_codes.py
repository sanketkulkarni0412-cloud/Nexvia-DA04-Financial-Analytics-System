"""
Adverse Action Reason Codes Generator
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B (Adverse Reason Code Engine)
Framing: Retail Credit Risk Compliance & ECOA / FCRA Adverse Action Explainability

Methodology:
    Computes point deficit per attribute relative to maximum achievable points:
        Deficit(j) = Max_Points(j) - Assigned_Points(j)
    Ranks attributes descending by Deficit to identify primary drivers of risk.
"""

import os
import sys
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class AdverseReasonCodeGenerator:
    """
    Generates FCRA/ECOA-compliant adverse action reason codes from scorecard points.
    """

    REASON_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
        "fico_midpoint": {
            "code": "RC01",
            "name": "Credit Bureau Score",
            "narrative": "Credit bureau score is below prime benchmark threshold."
        },
        "term_months": {
            "code": "RC02",
            "name": "Loan Term Length",
            "narrative": "Extended loan maturity (60 months) elevates duration risk exposure."
        },
        "installment_to_income": {
            "code": "RC03",
            "name": "Installment Burden",
            "narrative": "Monthly installment represents an elevated proportion of monthly gross income."
        },
        "dti": {
            "code": "RC04",
            "name": "Debt-to-Income Ratio",
            "narrative": "Total monthly debt obligations are high relative to declared income."
        },
        "home_ownership_clean": {
            "code": "RC05",
            "name": "Residential Tenure",
            "narrative": "Residential rental or non-ownership status lacks property equity stability."
        },
        "verification_status": {
            "code": "RC06",
            "name": "Income Verification Level",
            "narrative": "Application required formal verification indicating marginal underwriting tier."
        },
        "annual_inc": {
            "code": "RC07",
            "name": "Annual Income",
            "narrative": "Reported annual gross income is below preferred threshold for requested facility."
        }
    }

    def __init__(self, points_table: pd.DataFrame):
        self.points_table = points_table.copy()
        # Find maximum achievable points per feature
        self.max_points_per_feature = (
            self.points_table.groupby("feature")["points"].max().to_dict()
        )

    def generate_adverse_reasons(
        self,
        breakdown_points: Dict[str, int],
        top_n: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Ranks attributes by point deficit and returns the top N adverse reason codes.
        """
        deficits = []

        for feat, pts in breakdown_points.items():
            max_pts = self.max_points_per_feature.get(feat, pts)
            deficit = max(0, max_pts - pts)
            desc_info = self.REASON_DESCRIPTIONS.get(feat, {
                "code": "RC99",
                "name": feat,
                "narrative": f"Sub-optimal score contribution on {feat}."
            })

            deficits.append({
                "feature": feat,
                "code": desc_info["code"],
                "reason_name": desc_info["name"],
                "narrative": desc_info["narrative"],
                "assigned_points": pts,
                "maximum_points": max_pts,
                "points_lost": deficit
            })

        # Sort descending by points lost (highest adverse impact first)
        deficits.sort(key=lambda x: x["points_lost"], reverse=True)
        return deficits[:top_n]

