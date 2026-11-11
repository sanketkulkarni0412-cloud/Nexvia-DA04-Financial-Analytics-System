"""
Unit & Integration Tests for Final Credit Risk Scorecard Model
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

from credit_risk.final_scorecard import FinalScorecardModel


@pytest.fixture
def synthetic_credit_data():
    np.random.seed(42)
    n = 1500
    fico = np.random.normal(700, 35, n)
    dti = np.random.uniform(5, 40, n)
    term = np.random.choice([36, 60], size=n, p=[0.7, 0.3])
    home = np.random.choice(["MORTGAGE", "RENT", "OWN", "OTHER"], size=n)
    verif = np.random.choice(["Not Verified", "Source Verified", "Verified"], size=n)
    inc = np.random.lognormal(11.0, 0.5, n)
    installment = (inc / 12.0) * np.random.uniform(0.04, 0.20, n)
    inst_to_inc = (installment / (inc / 12.0)) * 100.0

    z = -1.2 - 0.015 * (fico - 680) + 0.04 * (dti - 15) + 0.6 * (term == 60) + 0.03 * (inst_to_inc - 10)
    p = 1.0 / (1.0 + np.exp(-z))
    y = (np.random.rand(n) < p).astype(int)

    df = pd.DataFrame({
        "fico_midpoint": fico,
        "dti": dti,
        "term_months": term,
        "home_ownership_clean": home,
        "verification_status": verif,
        "annual_inc": inc,
        "installment_to_income": inst_to_inc,
        "target": y
    })
    return df.iloc[:1200].copy(), df.iloc[1200:].copy()


def test_final_scorecard_fit_and_coefficients(synthetic_credit_data):
    train_df, test_df = synthetic_credit_data
    model = FinalScorecardModel(random_state=42)
    model.fit(train_df, target_col="target")

    assert model.is_fitted
    assert len(model.coefficients_) == 7
    # Verify all approved features are present
    for feat in model.APPROVED_FEATURES:
        assert feat in model.coefficients_
        # All coefficients should be negative (higher WOE = safer = lower log-odds of Bad)
        assert model.coefficients_[feat] < 0.0, f"Expected negative coefficient for {feat}, got {model.coefficients_[feat]}"


def test_final_scorecard_predictions_and_scores(synthetic_credit_data):
    train_df, test_df = synthetic_credit_data
    model = FinalScorecardModel(random_state=42)
    model.fit(train_df, target_col="target")

    probs = model.predict_proba(test_df)
    scores = model.score(test_df)

    assert len(probs) == len(test_df)
    assert len(scores) == len(test_df)
    assert np.all((probs >= 0.0) & (probs <= 1.0))

    # Verify score and probability relationship is strictly inverse
    # Higher score = lower probability of default
    corr = np.corrcoef(scores, probs)[0, 1]
    assert corr < -0.95, f"Expected strong negative correlation between score and PD, got {corr}"


def test_final_scorecard_evaluation_metrics(synthetic_credit_data):
    train_df, test_df = synthetic_credit_data
    model = FinalScorecardModel(random_state=42)
    model.fit(train_df, target_col="target")

    eval_result = model.evaluate(test_df, target_col="target")

    assert "discrimination_metrics" in eval_result
    assert "calibration_metrics" in eval_result
    assert "decile_calibration_table" in eval_result
    assert "risk_band_distribution" in eval_result

    discrim = eval_result["discrimination_metrics"]
    assert 0.5 <= discrim["roc_auc"] <= 1.0
    assert 0.0 <= discrim["gini"] <= 1.0
    assert 0.0 <= discrim["ks_statistic_pct"] <= 100.0
    assert len(eval_result["decile_calibration_table"]) == 10

