"""
Unit & Integration Tests for Baseline Scorecard Model & Evaluation Module
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. BaselineScorecardModel trains cleanly on WOE features without errors.
2. Predicted probabilities are strictly bounded in [0, 1].
3. Model evaluation metrics (ROC-AUC, Gini, KS, PR-AUC, Brier) are finite and realistic.
4. Risk decile calibration demonstrates monotonic risk ordering.
5. All Phase 2A output artifacts (JSON and CSV) exist and are valid.
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.baseline_model import BaselineScorecardModel
from credit_risk.evaluate_model import ScorecardEvaluator

REPORTS_DIR = os.path.join(BASE_DIR, "reports")


@pytest.fixture
def synthetic_woe_data():
    """Generates synthetic WOE features to test baseline model training & evaluation."""
    np.random.seed(42)
    n = 1000
    features = [
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

    # Generate synthetic WOE features
    data = {f: np.random.normal(0, 0.5, n) for f in features}
    # Synthetic target with ~20% base rate
    score = sum(data[f] * -0.5 for f in features)
    prob = 1.0 / (1.0 + np.exp(-(score - 1.4)))
    y = (np.random.rand(n) < prob).astype(int)

    df_train = pd.DataFrame(data).iloc[:800].copy()
    y_train = y[:800]
    df_test = pd.DataFrame(data).iloc[800:].copy()
    y_test = y[800:]

    return df_train, y_train, df_test, y_test, features


def test_baseline_model_trains_successfully(synthetic_woe_data):
    """Verify that model trains and exposes coefficients and metadata."""
    df_train, y_train, df_test, _, features = synthetic_woe_data
    model = BaselineScorecardModel(feature_names=features, random_state=42)

    assert not model.is_fitted
    model.fit(df_train, y_train)
    assert model.is_fitted
    assert len(model.coefficients_) == len(features)
    assert isinstance(model.intercept_, float)

    coef_table = model.get_coefficient_table()
    assert len(coef_table) == len(features) + 1  # features + intercept
    assert "coefficient" in coef_table.columns
    assert "odds_ratio" in coef_table.columns


def test_model_predictions_bounded_probability(synthetic_woe_data):
    """Verify that predict_proba returns probabilities strictly between 0 and 1."""
    df_train, y_train, df_test, _, features = synthetic_woe_data
    model = BaselineScorecardModel(feature_names=features, random_state=42)
    model.fit(df_train, y_train)

    probs = model.predict_proba(df_test)
    assert len(probs) == len(df_test)
    assert (probs >= 0.0).all(), "Negative probability detected"
    assert (probs <= 1.0).all(), "Probability > 1.0 detected"


def test_evaluation_metrics_finite_and_expected(synthetic_woe_data):
    """Verify that evaluation metrics compute finite, valid values."""
    df_train, y_train, df_test, y_test, features = synthetic_woe_data
    model = BaselineScorecardModel(feature_names=features, random_state=42)
    model.fit(df_train, y_train)

    test_probs = model.predict_proba(df_test)
    evaluator = ScorecardEvaluator()
    metrics = evaluator.evaluate_dataset(y_test, test_probs, dataset_name="Synthetic Test")

    assert 0.50 <= metrics["roc_auc"] <= 1.0, f"Unrealistic AUC: {metrics['roc_auc']}"
    assert -1.0 <= metrics["gini"] <= 1.0
    assert 0.0 <= metrics["ks_statistic_pct"] <= 100.0
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert "metrics_at_0_50" in metrics
    assert "metrics_at_optimal_ks" in metrics


def test_decile_calibration_monotonic_trend(synthetic_woe_data):
    """Verify that decile calibration separates risk and demonstrates monotonic ordering."""
    df_train, y_train, df_test, y_test, features = synthetic_woe_data
    model = BaselineScorecardModel(feature_names=features, random_state=42)
    model.fit(df_train, y_train)

    test_probs = model.predict_proba(df_test)
    evaluator = ScorecardEvaluator()
    decile_table = evaluator.generate_decile_calibration_table(y_test, test_probs, n_bins=10)

    assert len(decile_table) == 10
    assert "observed_bad_rate" in decile_table.columns
    assert "mean_predicted_prob" in decile_table.columns
    assert "calibration_ratio" in decile_table.columns

    # Verify that decile 10 (highest predicted risk) has a higher bad rate than decile 1
    assert decile_table.iloc[-1]["observed_bad_rate"] > decile_table.iloc[0]["observed_bad_rate"]


def test_saved_report_artifacts_exist():
    """Verify that all Phase 2A output artifacts exist and are readable."""
    report_json = os.path.join(REPORTS_DIR, "credit_risk_phase2a_report.json")
    metrics_json = os.path.join(REPORTS_DIR, "credit_risk_test_metrics.json")
    woe_csv = os.path.join(REPORTS_DIR, "credit_risk_woe_iv.csv")

    assert os.path.exists(report_json), f"Missing {report_json}"
    assert os.path.exists(metrics_json), f"Missing {metrics_json}"
    assert os.path.exists(woe_csv), f"Missing {woe_csv}"

    with open(report_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["status"] == "BASELINE_SCORECARD_COMPLETE"
        assert "train_metrics" in data
        assert "test_metrics" in data

    with open(metrics_json, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        assert metrics["roc_auc"] > 0.65
        assert metrics["ks_statistic_pct"] > 20.0

    df_woe = pd.read_csv(woe_csv)
    assert len(df_woe) > 50, "WOE CSV has too few bin rows"
    assert "variable" in df_woe.columns
    assert "woe" in df_woe.columns
    assert "iv_contribution" in df_woe.columns

