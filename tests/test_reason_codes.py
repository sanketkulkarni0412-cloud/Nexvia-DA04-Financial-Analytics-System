"""
Unit Tests for Adverse Action Reason Codes Generator
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B
"""

import os
import sys
import pytest
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.reason_codes import AdverseReasonCodeGenerator


def test_reason_code_generation():
    # Synthetic points table
    points_df = pd.DataFrame([
        {"feature": "fico_midpoint", "bin": "Low", "points": 66},
        {"feature": "fico_midpoint", "bin": "High", "points": 107},
        {"feature": "term_months", "bin": "60", "points": 56},
        {"feature": "term_months", "bin": "36", "points": 83},
        {"feature": "dti", "bin": "High", "points": 65},
        {"feature": "dti", "bin": "Low", "points": 82},
        {"feature": "annual_inc", "bin": "Low", "points": 72},
        {"feature": "annual_inc", "bin": "High", "points": 80}
    ])

    generator = AdverseReasonCodeGenerator(points_df)

    # Applicant with lowest points across FICO and Term
    assigned = {
        "fico_midpoint": 66,  # lost 41 pts
        "term_months": 56,    # lost 27 pts
        "dti": 82,            # lost 0 pts
        "annual_inc": 72      # lost 8 pts
    }

    reasons = generator.generate_adverse_reasons(assigned, top_n=3)

    assert len(reasons) == 3
    # Top reason must be FICO (lost 41 pts)
    assert reasons[0]["feature"] == "fico_midpoint"
    assert reasons[0]["code"] == "RC01"
    assert reasons[0]["points_lost"] == 41

    # Second reason must be Term (lost 27 pts)
    assert reasons[1]["feature"] == "term_months"
    assert reasons[1]["code"] == "RC02"
    assert reasons[1]["points_lost"] == 27

    # Third reason must be Annual Income (lost 8 pts)
    assert reasons[2]["feature"] == "annual_inc"
    assert reasons[2]["code"] == "RC07"
    assert reasons[2]["points_lost"] == 8

