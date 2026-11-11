"""
Unit Tests for Scorecard Scaling, Point Allocation & Risk Banding Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.scorecard_scaling import ScorecardScaler


def test_scorecard_scaling_mathematics():
    """Verify Factor and Offset derivation from Base Score 600 at 50:1 odds and PDO 20."""
    scaler = ScorecardScaler(base_score=600.0, base_odds=50.0, pdo=20.0)

    # Theoretical factor: 20 / ln(2) ≈ 28.85390
    expected_factor = 20.0 / np.log(2.0)
    assert pytest.approx(scaler.factor, rel=1e-5) == expected_factor

    # Theoretical offset: 600 - factor * ln(50) ≈ 487.12288
    expected_offset = 600.0 - expected_factor * np.log(50.0)
    assert pytest.approx(scaler.offset, rel=1e-5) == expected_offset

    # Verify score at exact 50:1 odds
    # p = 1/51 ≈ 0.0196078
    p_base = 1.0 / (1.0 + 50.0)
    score_base = scaler.pd_to_score(p_base)
    assert pytest.approx(score_base, abs=0.01) == 600.0

    # Verify score at 100:1 odds (double the odds of Good:Bad, score should increase by PDO = 20)
    p_100 = 1.0 / (1.0 + 100.0)
    score_100 = scaler.pd_to_score(p_100)
    assert pytest.approx(score_100, abs=0.01) == 620.0

    # Verify score at 25:1 odds (half the odds of Good:Bad, score should decrease by PDO = 20)
    p_25 = 1.0 / (1.0 + 25.0)
    score_25 = scaler.pd_to_score(p_25)
    assert pytest.approx(score_25, abs=0.01) == 580.0


def test_score_to_pd_inverse_consistency():
    """Verify that score_to_pd and pd_to_score are exact inverses."""
    scaler = ScorecardScaler()

    test_scores = [470.0, 500.0, 530.0, 550.0, 580.0, 610.0]
    for s in test_scores:
        pd_val = scaler.score_to_pd(s)
        recovered_score = scaler.pd_to_score(pd_val)
        assert pytest.approx(recovered_score, abs=1e-4) == s


def test_points_table_monotonicity():
    """Verify that lower-risk bins receive higher points than higher-risk bins."""
    scaler = ScorecardScaler()
    coefficients = {
        "term_months_woe": -1.0,
        "fico_midpoint_woe": -0.9
    }
    intercept = -1.4
    woe_tables = {
        "term_months": pd.DataFrame({
            "bin": ["36", "60"],
            "woe": [0.26, -0.65],
            "total_count": [8000, 2000],
            "bad_count": [1200, 600],
            "bad_rate": [0.15, 0.30]
        }),
        "fico_midpoint": pd.DataFrame({
            "bin": ["Low", "High"],
            "woe": [-0.35, 1.15],
            "total_count": [5000, 5000],
            "bad_count": [1300, 350],
            "bad_rate": [0.26, 0.07]
        })
    }

    tbl = scaler.build_points_table(coefficients, intercept, woe_tables)
    assert scaler.is_fitted
    assert len(tbl) == 4

    term_pts = scaler.points_lookup_["term_months"]
    assert term_pts["36"] > term_pts["60"], "36 month loan should receive more points than 60 month loan"

    fico_pts = scaler.points_lookup_["fico_midpoint"]
    assert fico_pts["High"] > fico_pts["Low"], "Higher FICO should receive more points than Lower FICO"


def test_risk_bands_coverage():
    """Verify that all 6 risk bands are contiguous and cover from 0 to 999."""
    scaler = ScorecardScaler()
    bands = scaler.RISK_BANDS
    assert len(bands) == 6

    # Verify tiers 1 to 6
    tiers = [b["tier"] for b in bands]
    assert tiers == [1, 2, 3, 4, 5, 6]

    # Verify score assignments
    assert scaler.assign_risk_band(570)["band"] == "Very Low Risk"
    assert scaler.assign_risk_band(545)["band"] == "Low Risk"
    assert scaler.assign_risk_band(535)["band"] == "Moderate Risk"
    assert scaler.assign_risk_band(525)["band"] == "Elevated Risk"
    assert scaler.assign_risk_band(510)["band"] == "High Risk"
    assert scaler.assign_risk_band(480)["band"] == "Very High Risk"

