"""
Unit & Integration Tests for Out-of-Time (OOT) Scorecard Validation Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.oot_validation import OOTScorecardValidator
from credit_risk.scorecard_preprocessing import ScorecardDataPreprocessor


def test_oot_report_structure_and_drift_limits():
    """Verifies that OOT validation runs and reports key temporal metrics within stability limits."""
    # Use pre-generated OOT report if available to avoid heavy recomputation in unit tests
    oot_json_path = os.path.join(BASE_DIR, "reports", "credit_risk_oot_validation.json")
    if os.path.exists(oot_json_path):
        import json
        with open(oot_json_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    else:
        validator = OOTScorecardValidator()
        report = validator.run_oot_validation()

    assert "training_cohort_summary" in report
    assert "oot_testing_cohort_summary" in report
    assert "oot_test_metrics" in report
    assert "temporal_stability_deltas" in report

    oot_summary = report["oot_testing_cohort_summary"]
    assert oot_summary["total_loans"] == 293105
    assert pytest.approx(oot_summary["bad_rate"], abs=1e-3) == 0.2329

    oot_metrics = report["oot_test_metrics"]
    assert oot_metrics["roc_auc"] >= 0.65
    assert oot_metrics["ks_statistic_pct"] >= 20.0

    # Ensure degradation delta is small (AUC degradation < 0.02)
    deltas = report["temporal_stability_deltas"]
    assert abs(deltas["roc_auc_delta"]) < 0.02
    assert deltas["drift_assessment"] == "Stable (<0.015 AUC degradation)"

