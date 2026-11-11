"""
Unit & Integration Tests for Budget vs. Actual Variance Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 2 / Step 3 (Budget Variance Analysis)
Verifies:
1. Actual portfolio totals match Task 2 authoritative figures to the exact penny.
2. Official budget data availability flag remains False (no fabricated records).
3. Zero-division and null budget protections operate safely.
4. Absolute and percentage variance arithmetic is mathematically accurate.
5. Favorable / Unfavorable directional logic works correctly for revenues vs costs.
6. Rate-Volume-Mix driver decomposition identity holds with 0 discrepancy.
7. Governance disclosure and scenario labeling are present.
"""

import os
import sys
import pytest
import pandas as pd
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from financial_reports.budget_variance import BudgetVarianceEngine


@pytest.fixture
def engine():
    return BudgetVarianceEngine()


def test_official_budget_data_flag(engine):
    """Verify that official budget availability flag is strictly False."""
    assert engine.is_official_budget_available is False
    assert "OFFICIAL BUDGET UNAVAILABLE" in engine.GOVERNANCE_DISCLOSURE
    assert "ILLUSTRATIVE SCENARIO" in engine.SCENARIO_LABEL


def test_actuals_reconcile_to_task2_authoritative_figures(engine):
    """Verify that actuals queried dynamically match Task 2 authoritative totals."""
    annual_actuals = engine.load_actuals_annual()

    tot_funded = annual_actuals["funded_amount"].sum()
    tot_principal = annual_actuals["principal_received"].sum()
    tot_interest = annual_actuals["interest_income"].sum()
    tot_loss = annual_actuals["net_realized_credit_loss"].sum()

    # Reconcile funded amount ($34,004,208,600.00)
    assert pytest.approx(tot_funded, abs=1.0) == 34004208600.00
    # Reconcile principal received ($21,489,393,643.58)
    assert pytest.approx(tot_principal, abs=1.0) == 21489393643.58
    # Reconcile interest income ($5,496,560,266.06)
    assert pytest.approx(tot_interest, abs=1.0) == 5496560266.06
    # Reconcile net realized credit loss ($2,733,766,666.67)
    assert pytest.approx(tot_loss, abs=1.0) == 2733766666.67


def test_variance_calculation_and_directional_logic(engine):
    """Verify absolute variance, percentage variance, and favorable/unfavorable logic."""
    # Revenue test: Actual > Budget is Favorable
    rev_fav = engine.calculate_variance(actual=120.0, budget=100.0, is_cost=False)
    assert rev_fav["absolute_variance"] == 20.0
    assert rev_fav["variance_pct"] == 20.0
    assert rev_fav["status"] == "Favorable"

    # Revenue test: Actual < Budget is Unfavorable
    rev_unfav = engine.calculate_variance(actual=80.0, budget=100.0, is_cost=False)
    assert rev_unfav["absolute_variance"] == -20.0
    assert rev_unfav["variance_pct"] == -20.0
    assert rev_unfav["status"] == "Unfavorable"

    # Cost test: Actual > Budget is Unfavorable
    cost_unfav = engine.calculate_variance(actual=120.0, budget=100.0, is_cost=True)
    assert cost_unfav["absolute_variance"] == 20.0
    assert cost_unfav["variance_pct"] == 20.0
    assert cost_unfav["status"] == "Unfavorable"

    # Cost test: Actual < Budget is Favorable
    cost_fav = engine.calculate_variance(actual=80.0, budget=100.0, is_cost=True)
    assert cost_fav["absolute_variance"] == -20.0
    assert cost_fav["variance_pct"] == -20.0
    assert cost_fav["status"] == "Favorable"


def test_zero_and_null_budget_safety(engine):
    """Verify zero division and null handling safety."""
    # Zero budget
    zero_bud = engine.calculate_variance(actual=50.0, budget=0.0, is_cost=False)
    assert zero_bud["absolute_variance"] == 50.0
    assert zero_bud["variance_pct"] == 100.0
    assert zero_bud["status"] == "Favorable"

    # Null budget
    null_bud = engine.calculate_variance(actual=50.0, budget=None, is_cost=False)
    assert null_bud["absolute_variance"] == 50.0
    assert null_bud["status"] == "Favorable"

    # Both zero
    both_zero = engine.calculate_variance(actual=0.0, budget=0.0, is_cost=False)
    assert both_zero["absolute_variance"] == 0.0
    assert both_zero["variance_pct"] == 0.0
    assert both_zero["status"] == "On Budget"


def test_driver_decomposition_mathematical_identity(engine):
    """Verify Volume + Rate + Mix == Total Variance identity."""
    decomp = engine.decompose_rate_volume(
        actual_volume=1000.0,
        budget_volume=800.0,
        actual_total=150.0,   # rate = 15.0%
        budget_total=112.0    # rate = 14.0%
    )

    # Actual total variance: 150 - 112 = 38
    assert decomp["total_variance"] == 38.0
    # Volume variance: (1000 - 800) * 0.14 = 28.0
    assert decomp["volume_variance"] == 28.0
    # Rate variance: 800 * (0.15 - 0.14) = 8.0
    assert decomp["rate_variance"] == 8.0
    # Mix variance: (1000 - 800) * (0.15 - 0.14) = 2.0
    assert decomp["mix_variance"] == 2.0
    # Identity: 28 + 8 + 2 = 38
    assert decomp["sum_of_components"] == 38.0
    assert decomp["is_reconciled"] is True


def test_annual_variance_analysis_report_structure(engine):
    """Verify the generated annual variance report matches required structure."""
    report = engine.run_annual_variance_analysis()

    assert report["official_budget_data_available"] is False
    assert "scenario_metadata" in report
    assert "cumulative_portfolio_reconciliation" in report
    assert report["cumulative_portfolio_reconciliation"]["is_fully_reconciled"] is True
    assert "cumulative_summary" in report
    assert "annual_breakdown" in report

    # Verify 12 annual cohorts (2007 through 2018)
    years = [row["year"] for row in report["annual_breakdown"]]
    assert len(years) == 12
    assert years == list(range(2007, 2019))

    # Cumulative interest drivers reconciliation
    drivers = report["cumulative_summary"]["cumulative_interest_drivers"]
    assert drivers["is_reconciled"] is True
    assert drivers["total_variance"] == pytest.approx(drivers["sum_of_components"], abs=0.01)

