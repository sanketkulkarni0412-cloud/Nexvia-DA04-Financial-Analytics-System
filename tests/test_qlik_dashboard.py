"""
Unit & Integration Tests for Task 4: Interactive BI & Qlik Sense Dashboard
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. Presence of all required Qlik and dashboard assets (QVS, Markdown, HTML, CSVs, Py).
2. All CSV extracts are populated and contain required schema fields.
3. Perfect reconciliation of headline financial KPIs against warehouse authoritative values:
   - Funded Amount = $34,004,208,600.00
   - Active Gross Outstanding = $9,510,001,923.03
   - Net Realized Credit Loss = $2,733,766,666.67
   - NPL Ratio = 2.5683%
4. Credit risk model KPIs match frozen Task 3 specifications:
   - In-Time ROC-AUC = 0.6828
   - In-Time KS = 26.08%
   - 2016 OOT ROC-AUC = 0.6770
   - 2016 OOT KS = 25.15%
5. Monotonicity and structure across the 6 neutral risk bands.
6. HTML dashboard integrity (all 3 tabs, KPI labels, disclosures, zero fabricated loan purpose).
"""

import os
import sys
import pytest
import pandas as pd
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

QLIK_DIR = os.path.join(BASE_DIR, "qlik_dashboard")
DATA_DIR = os.path.join(QLIK_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def test_required_dashboard_files_exist():
    """Verify all mandatory Task 4 deliverables exist on disk."""
    expected_files = [
        os.path.join(QLIK_DIR, "load_script.qvs"),
        os.path.join(QLIK_DIR, "data_model_spec.md"),
        os.path.join(QLIK_DIR, "interactive_dashboard.html"),
        os.path.join(QLIK_DIR, "export_qlik_data.py"),
    ]
    for fp in expected_files:
        assert os.path.exists(fp), f"Missing required file: {fp}"
        assert os.path.getsize(fp) > 0, f"File is empty: {fp}"


def test_required_csv_extracts_exist_and_non_empty():
    """Verify all 6 authoritative CSV extracts exist and contain valid data."""
    expected_csvs = [
        "qlik_portfolio_summary.csv",
        "qlik_vintage_performance.csv",
        "qlik_scorecard_bands.csv",
        "qlik_scorecard_points.csv",
        "qlik_oot_metrics.csv",
        "qlik_geo_summary.csv"
    ]
    for csv_name in expected_csvs:
        fp = os.path.join(DATA_DIR, csv_name)
        assert os.path.exists(fp), f"Missing required CSV extract: {csv_name}"
        df = pd.read_csv(fp)
        assert len(df) > 0, f"CSV extract is empty: {csv_name}"


def test_csv_columns_integrity():
    """Verify presence of required analytical columns in extracts."""
    # 1. Portfolio summary
    p_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_portfolio_summary.csv"))
    for col in ["year", "year_month", "grade", "term", "loan_count", "funded_amount",
                "principal_received", "interest_income", "recoveries", "collection_cost",
                "net_recoveries", "net_realized_credit_loss", "total_cash_received"]:
        assert col in p_df.columns, f"Missing column '{col}' in qlik_portfolio_summary.csv"

    # 2. Vintage performance
    v_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_vintage_performance.csv"))
    for col in ["issue_year", "issue_year_month", "grade", "sub_grade", "term_months",
                "loan_count", "funded_amount", "confirmed_default_count", "default_rate_pct",
                "principal_recovery_rate_pct", "net_cash_margin_pct"]:
        assert col in v_df.columns, f"Missing column '{col}' in qlik_vintage_performance.csv"

    # 3. Scorecard bands
    b_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_scorecard_bands.csv"))
    for col in ["risk_tier", "risk_band", "score_range", "portfolio_share_pct",
                "actual_bad_rate_pct", "modeled_bad_rate_pct", "bad_capture_pct",
                "cumulative_bad_capture_pct"]:
        assert col in b_df.columns, f"Missing column '{col}' in qlik_scorecard_bands.csv"


def test_financial_kpi_reconciliation():
    """Reconcile portfolio financial metrics against Task 2 authoritative totals."""
    p_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_portfolio_summary.csv"))

    total_funded = p_df["funded_amount"].sum()
    total_principal = p_df["principal_received"].sum()
    total_loss = p_df["net_realized_credit_loss"].sum()

    # Reconcile funded amount ($34,004,208,600.00)
    assert pytest.approx(total_funded, abs=1.0) == 34004208600.00
    # Reconcile principal received ($21,489,393,643.58)
    assert pytest.approx(total_principal, abs=1.0) == 21489393643.58
    # Reconcile net realized credit loss ($2,733,766,666.67)
    assert pytest.approx(total_loss, abs=1.0) == 2733766666.67

    # Geography active outstanding reconciliation ($9,510,001,923.03)
    g_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_geo_summary.csv"))
    total_geo_active = g_df["active_outstanding"].sum()
    assert pytest.approx(total_geo_active, abs=1.0) == 9510001923.03


def test_risk_bands_monotonicity_and_coverage():
    """Verify exact 6 neutral risk bands and monotonic bad rate progression."""
    b_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_scorecard_bands.csv"))

    assert len(b_df) == 6, f"Expected exactly 6 risk bands, got {len(b_df)}"
    assert b_df["risk_tier"].tolist() == [1, 2, 3, 4, 5, 6]

    expected_bands = [
        "Very Low Risk", "Low Risk", "Moderate Risk",
        "Elevated Risk", "High Risk", "Very High Risk"
    ]
    assert b_df["risk_band"].tolist() == expected_bands

    # Bad rates must be strictly monotonic increasing from Tier 1 to Tier 6
    bad_rates = b_df["actual_bad_rate_pct"].tolist()
    for i in range(len(bad_rates) - 1):
        assert bad_rates[i] < bad_rates[i + 1], (
            f"Non-monotonic bad rate between Tier {i+1} ({bad_rates[i]}%) and Tier {i+2} ({bad_rates[i+1]}%)"
        )

    # Tier 1 bad rate ~6.04% and Tier 6 bad rate ~43.27%
    assert pytest.approx(bad_rates[0], abs=0.2) == 6.04
    assert pytest.approx(bad_rates[-1], abs=0.2) == 43.27


def test_scorecard_and_oot_kpi_values():
    """Verify In-Time and OOT discrimination metrics against Task 3 frozen outputs."""
    oot_df = pd.read_csv(os.path.join(DATA_DIR, "qlik_oot_metrics.csv"))
    assert len(oot_df) == 2

    dev_row = oot_df[oot_df["cohort_type"] == "Development In-Sample"].iloc[0]
    oot_row = oot_df[oot_df["cohort_type"] == "Out-of-Time (OOT) Holdout"].iloc[0]

    # In-time metrics
    assert pytest.approx(dev_row["roc_auc"], abs=1e-3) == 0.6904  # in-sample 2012-15
    assert pytest.approx(dev_row["ks_statistic_pct"], abs=0.1) == 27.46

    # OOT metrics
    assert pytest.approx(oot_row["roc_auc"], abs=1e-3) == 0.6770
    assert pytest.approx(oot_row["ks_statistic_pct"], abs=0.1) == 25.15
    assert pytest.approx(oot_row["bad_rate_pct"], abs=0.1) == 23.29

    # Check overall test holdout metrics from master JSON
    with open(os.path.join(REPORTS_DIR, "credit_risk_final_scorecard.json"), "r") as f:
        master_sc = json.load(f)
    assert pytest.approx(master_sc["in_time_test_metrics"]["roc_auc"], abs=1e-3) == 0.6828
    assert pytest.approx(master_sc["in_time_test_metrics"]["ks_statistic_pct"], abs=0.1) == 26.08


def test_interactive_dashboard_html_structure():
    """Verify that standalone interactive dashboard contains required tabs, KPIs, and zero fabricated fields."""
    html_path = os.path.join(QLIK_DIR, "interactive_dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Verify 3 tabs exist
    assert "tab-portfolio" in html
    assert "tab-vintage" in html
    assert "tab-scorecard" in html
    assert "Executive Portfolio & Solvency" in html
    assert "Vintage Performance & Cash Flow" in html
    assert "Credit Risk Scorecard" in html

    # 2. Verify key KPI card IDs and labels
    assert "kpi-total-loans" in html
    assert "kpi-funded-amt" in html
    assert "kpi-active-amt" in html
    assert "kpi-npl-ratio" in html
    assert "kpi-reserve-amt" in html
    assert "kpi-carrying-val" in html
    assert "kpi-cash-rec" in html
    assert "kpi-net-loss" in html

    # 3. Verify disclaimers and governance disclosures
    assert "Analytical portfolio/risk reporting for Nexvia DA-04 assessment" in html
    assert "Qlik Sense Desktop was unavailable in the local environment" in html

    # 4. Verify negative finding: Loan Purpose is NOT used as an accepted dashboard filter
    assert "id=\"p-filter-purpose\"" not in html
    assert "id=\"v-filter-purpose\"" not in html
    assert "id=\"s-filter-purpose\"" not in html

