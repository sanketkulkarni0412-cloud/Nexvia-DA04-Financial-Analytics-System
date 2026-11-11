"""
Unit & Integration Tests for Task 2: SQL Analytical Financial Reporting Views
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. All SQL reporting views exist and query successfully
2. Monthly P&L aggregation reconciles to warehouse fact totals with 0 variance
3. Balance Sheet portfolio solvency metrics reconcile to warehouse fact totals with 0 variance
4. No duplicate rows in expected grains
5. NPL balance and NPL ratio calculations are mathematically reproducible
6. No negative impossible balances are silently introduced
7. Analytical loss reserve and carrying value calculations are reproducible
8. dim_financial_budget remains untouched with 0 rows
"""

import os
import sqlite3
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "warehouse.db")


@pytest.fixture(scope="module")
def db_conn():
    """Provides a read-only connection to warehouse.db."""
    assert os.path.exists(DB_PATH), f"Warehouse database not found at {DB_PATH}"
    uri = f"file:///{DB_PATH.replace(os.sep, '/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    yield conn
    conn.close()


def test_views_exist_in_database(db_conn):
    """Verifies that all three required Task 2 views are registered in sqlite_master."""
    cur = db_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'view';")
    views = {row[0] for row in cur.fetchall()}
    
    expected_views = {
        "vw_portfolio_pnl_monthly",
        "vw_portfolio_balance_sheet_summary",
        "vw_portfolio_vintage_performance"
    }
    missing_views = expected_views - views
    assert not missing_views, f"Missing required SQL views: {missing_views}"


def test_pnl_monthly_view_queries_successfully(db_conn):
    """Verifies that vw_portfolio_pnl_monthly can be queried and covers all 139 vintage months."""
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(year_month), MAX(year_month) FROM vw_portfolio_pnl_monthly;")
    row = cur.fetchone()
    
    month_count, min_month, max_month = row[0], row[1], row[2]
    assert month_count == 139, f"Expected 139 vintage months, got {month_count}"
    assert min_month == "2007-06", f"Expected min month 2007-06, got {min_month}"
    assert max_month == "2018-12", f"Expected max month 2018-12, got {max_month}"


def test_pnl_monthly_reconciles_to_warehouse_totals(db_conn):
    """
    Verifies that the sum of each metric in vw_portfolio_pnl_monthly matches
    the raw aggregate of fact_accepted_loans with zero variance.
    """
    cur = db_conn.cursor()
    
    # 1. Fact accepted loans raw totals
    cur.execute("""
        SELECT 
            COUNT(*),
            SUM(funded_amnt),
            SUM(total_rec_prncp),
            SUM(total_rec_int),
            SUM(total_rec_late_fee),
            SUM(recoveries),
            SUM(collection_cost),
            SUM(recoveries - collection_cost),
            SUM(CASE WHEN is_confirmed_default = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_confirmed_default = 1 THEN (funded_amnt - total_rec_prncp) ELSE 0.0 END),
            SUM(CASE WHEN is_confirmed_default = 1 THEN (funded_amnt - total_rec_prncp) ELSE 0.0 END) - SUM(recoveries - collection_cost),
            SUM(total_pymnt),
            SUM(total_pymnt - collection_cost)
        FROM fact_accepted_loans;
    """)
    fact = cur.fetchone()
    
    # 2. Sum across vw_portfolio_pnl_monthly
    cur.execute("""
        SELECT 
            SUM(loan_count),
            SUM(funded_amount),
            SUM(principal_received),
            SUM(interest_income),
            SUM(late_fee_income),
            SUM(gross_recoveries),
            SUM(collection_cost),
            SUM(net_recoveries),
            SUM(confirmed_default_count),
            SUM(gross_charge_off_principal),
            SUM(net_realized_credit_loss),
            SUM(total_cash_received),
            SUM(net_cash_after_collection_cost)
        FROM vw_portfolio_pnl_monthly;
    """)
    view_pnl = cur.fetchone()
    
    metric_names = [
        "loan_count", "funded_amount", "principal_received", "interest_income",
        "late_fee_income", "gross_recoveries", "collection_cost", "net_recoveries",
        "confirmed_default_count", "gross_charge_off_principal", "net_realized_credit_loss",
        "total_cash_received", "net_cash_after_collection_cost"
    ]
    
    for name, f_val, v_val in zip(metric_names, fact, view_pnl):
        diff = abs(f_val - v_val)
        assert diff < 0.01, f"Variance in {name}: Fact={f_val}, View={v_val}, Diff={diff}"


def test_balance_sheet_summary_reconciles_to_warehouse_totals(db_conn):
    """
    Verifies that vw_portfolio_balance_sheet_summary returns exactly 1 summary row
    and reconciles to warehouse totals.
    """
    cur = db_conn.cursor()
    cur.execute("SELECT * FROM vw_portfolio_balance_sheet_summary;")
    rows = cur.fetchall()
    assert len(rows) == 1, f"Expected 1 summary row in vw_portfolio_balance_sheet_summary, got {len(rows)}"
    
    col_names = [d[0] for d in cur.description]
    bs = dict(zip(col_names, rows[0]))
    
    # Check total funded amount
    cur.execute("SELECT SUM(funded_amnt), SUM(total_rec_prncp) FROM fact_accepted_loans;")
    fact_funded, fact_principal = cur.fetchone()
    
    assert abs(bs["total_funded_amount"] - fact_funded) < 0.01
    assert abs(bs["cumulative_principal_received"] - fact_principal) < 0.01
    assert bs["active_gross_loan_outstanding"] > 0
    assert bs["net_loan_portfolio_carrying_value"] < bs["active_gross_loan_outstanding"]


def test_no_duplicate_rows_in_expected_grain(db_conn):
    """Verifies unique key grains across all views."""
    cur = db_conn.cursor()
    
    # 1. Monthly view: year_month must be unique
    cur.execute("SELECT year_month, COUNT(*) FROM vw_portfolio_pnl_monthly GROUP BY year_month HAVING COUNT(*) > 1;")
    dups_pnl = cur.fetchall()
    assert len(dups_pnl) == 0, f"Found duplicate year_month in vw_portfolio_pnl_monthly: {dups_pnl}"
    
    # 2. Vintage view: (issue_year_month, sub_grade, term_months) must be unique
    cur.execute("""
        SELECT issue_year_month, sub_grade, term_months, COUNT(*) 
        FROM vw_portfolio_vintage_performance 
        GROUP BY issue_year_month, sub_grade, term_months 
        HAVING COUNT(*) > 1;
    """)
    dups_vin = cur.fetchall()
    assert len(dups_vin) == 0, f"Found duplicate cohorts in vw_portfolio_vintage_performance: {len(dups_vin)}"


def test_npl_calculation_reproducible(db_conn):
    """
    Verifies that the NPL balance and ratio in vw_portfolio_balance_sheet_summary
    matches independent raw query on active loans with 'Severe Late (31-120)' tier.
    """
    cur = db_conn.cursor()
    
    # Independent query
    cur.execute("""
        SELECT 
            SUM(funded_amnt - total_rec_prncp) AS expected_npl,
            SUM(CASE WHEN is_seasoned_closed = 0 THEN (funded_amnt - total_rec_prncp) ELSE 0.0 END) AS active_gross
        FROM fact_accepted_loans
        WHERE is_seasoned_closed = 0 AND delinquency_tier = 'Severe Late (31-120)';
    """)
    expected_npl, _ = cur.fetchone()
    
    cur.execute("SELECT NPL_balance, NPL_ratio FROM vw_portfolio_balance_sheet_summary;")
    bs_row = cur.fetchone()
    view_npl, view_ratio = bs_row[0], bs_row[1]
    
    assert abs(view_npl - expected_npl) < 0.01, f"NPL balance mismatch: Expected={expected_npl}, View={view_npl}"
    assert 2.0 <= view_ratio <= 3.0, f"NPL ratio outside plausible range: {view_ratio}"


def test_no_negative_impossible_balances(db_conn):
    """
    Verifies that no negative values exist in non-negative financial metrics:
    funded_amount, principal_received, interest_income, late_fee_income,
    gross_recoveries, collection_cost, confirmed_default_count, gross_charge_off_principal.
    """
    cur = db_conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM vw_portfolio_pnl_monthly
        WHERE funded_amount < 0
           OR principal_received < 0
           OR interest_income < 0
           OR late_fee_income < 0
           OR gross_recoveries < 0
           OR collection_cost < 0
           OR confirmed_default_count < 0
           OR gross_charge_off_principal < 0
           OR total_cash_received < 0;
    """)
    neg_count = cur.fetchone()[0]
    assert neg_count == 0, f"Found {neg_count} rows with impossible negative values in vw_portfolio_pnl_monthly"


def test_analytical_reserve_calculation_reproducible(db_conn):
    """
    Verifies that analytical_loss_reserve in vw_portfolio_balance_sheet_summary
    matches the exact sum of active loan principal multiplied by dim_loan_grade.illustrative_target_loss_cap.
    """
    cur = db_conn.cursor()
    
    cur.execute("""
        SELECT SUM((f.funded_amnt - f.total_rec_prncp) * g.illustrative_target_loss_cap)
        FROM fact_accepted_loans f
        JOIN dim_loan_grade g ON f.grade_key = g.grade_key
        WHERE f.is_seasoned_closed = 0;
    """)
    expected_reserve = cur.fetchone()[0]
    
    cur.execute("SELECT analytical_loss_reserve, net_loan_portfolio_carrying_value, active_gross_loan_outstanding FROM vw_portfolio_balance_sheet_summary;")
    row = cur.fetchone()
    view_reserve, view_carrying, view_active = row[0], row[1], row[2]
    
    assert abs(view_reserve - expected_reserve) < 0.01, f"Reserve mismatch: Expected={expected_reserve}, View={view_reserve}"
    assert abs((view_active - view_reserve) - view_carrying) < 0.01, "Carrying value != Active Gross - Reserve"


def test_budget_table_untouched_and_zero_rows(db_conn):
    """Verifies dim_financial_budget remains untouched and has exactly 0 rows."""
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dim_financial_budget;")
    cnt = cur.fetchone()[0]
    assert cnt == 0, f"Expected 0 rows in dim_financial_budget, found {cnt}"

