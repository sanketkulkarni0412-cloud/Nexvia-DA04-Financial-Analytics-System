"""
Automated Validation Suite for Task 2 Phase 2: Python Financial Reporting Engines
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. P&L engine totals reconcile exactly to vw_portfolio_pnl_monthly.
2. Balance Sheet engine reconciles exactly to vw_portfolio_balance_sheet_summary.
3. Executive summary KPIs reconcile to the SQL views.
4. No hard-coded financial totals are used in production engine code.
5. Database is opened strictly in read-only mode (mode=ro).
6. Analytical reserve is explicitly labeled as Model-Based (not statutory ALLL/CECL).
7. No unavailable corporate accounting items (cash, debt, equity, OpEx, taxes) are fabricated.
"""

import os
import sys
import ast
import sqlite3
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from financial_reports.p_and_l_engine import PortfolioPnLEngine
from financial_reports.balance_sheet_engine import PortfolioBalanceSheetEngine
from financial_reports.executive_summary import PortfolioExecutiveSummaryEngine

DB_PATH = os.path.join(BASE_DIR, "warehouse.db")


@pytest.fixture(scope="module")
def db_conn():
    """Provides a read-only SQLite connection directly to warehouse.db."""
    uri = f"file:///{DB_PATH.replace(os.sep, '/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    yield conn
    conn.close()


def test_pnl_engine_totals_reconcile_to_view(db_conn):
    """Verifies that PortfolioPnLEngine dynamically computes totals matching vw_portfolio_pnl_monthly."""
    engine = PortfolioPnLEngine(db_path=DB_PATH)
    summary = engine.get_portfolio_summary_totals()
    
    cur = db_conn.cursor()
    cur.execute("""
        SELECT 
            SUM(loan_count),
            SUM(funded_amount),
            SUM(principal_received),
            SUM(interest_income),
            SUM(late_fee_income),
            SUM(total_cash_received),
            SUM(gross_recoveries),
            SUM(collection_cost),
            SUM(net_recoveries),
            SUM(confirmed_default_count),
            SUM(gross_charge_off_principal),
            SUM(net_realized_credit_loss)
        FROM vw_portfolio_pnl_monthly;
    """)
    row = cur.fetchone()
    
    assert summary["total_loans_originated"] == row[0]
    assert abs(summary["total_funded_amount"] - row[1]) < 0.01
    assert abs(summary["total_principal_received"] - row[2]) < 0.01
    assert abs(summary["gross_interest_income"] - row[3]) < 0.01
    assert abs(summary["late_fee_income"] - row[4]) < 0.01
    assert abs(summary["total_cash_received"] - row[5]) < 0.01
    assert abs(summary["gross_recoveries"] - row[6]) < 0.01
    assert abs(summary["collection_cost"] - row[7]) < 0.01
    assert abs(summary["net_recoveries"] - row[8]) < 0.01
    assert summary["confirmed_default_count"] == row[9]
    assert abs(summary["gross_charge_off_principal"] - row[10]) < 0.01
    assert abs(summary["net_realized_credit_loss"] - row[11]) < 0.01


def test_balance_sheet_engine_reconciles_to_view(db_conn):
    """Verifies that PortfolioBalanceSheetEngine metrics reconcile to vw_portfolio_balance_sheet_summary."""
    engine = PortfolioBalanceSheetEngine(db_path=DB_PATH)
    solvency = engine.get_solvency_summary()
    
    cur = db_conn.cursor()
    cur.execute("SELECT * FROM vw_portfolio_balance_sheet_summary;")
    cols = [d[0] for d in cur.description]
    row = dict(zip(cols, cur.fetchone()))
    
    assert abs(solvency["total_funded_amount"] - row["total_funded_amount"]) < 0.01
    assert abs(solvency["cumulative_principal_received"] - row["cumulative_principal_received"]) < 0.01
    assert abs(solvency["active_gross_loan_outstanding"] - row["active_gross_loan_outstanding"]) < 0.01
    assert abs(solvency["NPL_balance"] - row["NPL_balance"]) < 0.01
    assert abs(solvency["NPL_ratio"] - row["NPL_ratio"]) < 0.0001
    assert abs(solvency["analytical_loss_reserve"] - row["analytical_loss_reserve"]) < 0.01
    assert abs(solvency["net_loan_portfolio_carrying_value"] - row["net_loan_portfolio_carrying_value"]) < 0.01


def test_executive_summary_reconciles_to_views(db_conn):
    """Verifies that PortfolioExecutiveSummaryEngine dynamically computes KPIs matching SQL views."""
    engine = PortfolioExecutiveSummaryEngine(db_path=DB_PATH)
    kpis = engine.get_executive_kpis()
    
    cur = db_conn.cursor()
    cur.execute("""
        SELECT 
            SUM(loan_count),
            SUM(interest_income),
            SUM(net_realized_credit_loss)
        FROM vw_portfolio_pnl_monthly;
    """)
    pnl = cur.fetchone()
    
    cur.execute("""
        SELECT 
            total_funded_amount,
            active_gross_loan_outstanding,
            NPL_balance,
            NPL_ratio,
            analytical_loss_reserve,
            net_loan_portfolio_carrying_value
        FROM vw_portfolio_balance_sheet_summary;
    """)
    bs = cur.fetchone()
    
    assert kpis["total_loans"] == pnl[0]
    assert abs(kpis["interest_income"] - pnl[1]) < 0.01
    assert abs(kpis["net_realized_credit_loss"] - pnl[2]) < 0.01
    assert abs(kpis["total_funded_amount"] - bs[0]) < 0.01
    assert abs(kpis["active_portfolio_outstanding"] - bs[1]) < 0.01
    assert abs(kpis["NPL_balance"] - bs[2]) < 0.01
    assert abs(kpis["NPL_ratio"] - bs[3]) < 0.0001
    assert abs(kpis["analytical_reserve"] - bs[4]) < 0.01
    assert abs(kpis["net_carrying_value"] - bs[5]) < 0.01


def test_no_hardcoded_financial_totals_in_engine_code():
    """
    Parses Python engine source files via AST to ensure that no hard-coded
    financial totals (e.g., 34004208600, 21489393643, 9510001923, 244246366)
    are embedded as literals in production code.
    """
    forbidden_numbers = {
        34004208600,
        21489393643,
        5496560266,
        27314649582,
        9510001923,
        244246366,
        772880427,
        8737121495,
        2733766666,
        3004813004
    }
    
    engine_files = [
        os.path.join(BASE_DIR, "financial_reports", "p_and_l_engine.py"),
        os.path.join(BASE_DIR, "financial_reports", "balance_sheet_engine.py"),
        os.path.join(BASE_DIR, "financial_reports", "executive_summary.py")
    ]
    
    for file_path in engine_files:
        assert os.path.exists(file_path), f"File {file_path} does not exist"
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                val = node.value
                if isinstance(val, (int, float)):
                    int_val = int(abs(val))
                    assert int_val not in forbidden_numbers, (
                        f"Hard-coded financial literal {val} detected in {file_path} at line {getattr(node, 'lineno', '?')}"
                    )


def test_database_opened_readonly():
    """Verifies that all three engines open SQLite exclusively in read-only mode (mode=ro)."""
    pnl = PortfolioPnLEngine(db_path=DB_PATH)
    bs = PortfolioBalanceSheetEngine(db_path=DB_PATH)
    exec_eng = PortfolioExecutiveSummaryEngine(db_path=DB_PATH)
    
    for eng in [pnl, bs, exec_eng]:
        assert "mode=ro" in eng.uri, f"Engine {eng.__class__.__name__} URI missing mode=ro"
        with eng._get_connection() as conn:
            cur = conn.cursor()
            # Attempting write operation must raise OperationalError
            with pytest.raises(sqlite3.OperationalError):
                cur.execute("CREATE TABLE test_should_fail (id INT);")


def test_analytical_reserve_labeled_as_model_based():
    """Verifies that analytical reserve is explicitly labeled as Model-Based."""
    bs_engine = PortfolioBalanceSheetEngine(db_path=DB_PATH)
    summary = bs_engine.get_solvency_summary()
    
    expected_label = "Model-Based Analytical Reserve — Not Statutory ALLL/CECL"
    assert summary.get("analytical_loss_reserve_label") == expected_label, (
        f"Label mismatch in BalanceSheetEngine: {summary.get('analytical_loss_reserve_label')}"
    )
    
    exec_engine = PortfolioExecutiveSummaryEngine(db_path=DB_PATH)
    kpis = exec_engine.get_executive_kpis()
    assert kpis.get("analytical_reserve_label") == expected_label, (
        f"Label mismatch in ExecutiveSummaryEngine: {kpis.get('analytical_reserve_label')}"
    )


def test_no_unavailable_corporate_items_fabricated():
    """
    Verifies that unavailable corporate balance sheet items are not fabricated
    as numeric balances in the reporting engines.
    """
    bs_engine = PortfolioBalanceSheetEngine(db_path=DB_PATH)
    summary = bs_engine.get_solvency_summary()
    
    unavailable = [
        "corporate_cash",
        "corporate_debt",
        "shareholder_equity",
        "retained_earnings",
        "corporate_operating_expenses",
        "income_tax"
    ]
    
    for item in unavailable:
        assert item not in summary, f"Prohibited corporate item '{item}' was fabricated in balance sheet summary"
        
    assert "unavailable_corporate_items" in summary
    assert set(unavailable).issubset(set(summary["unavailable_corporate_items"]))

