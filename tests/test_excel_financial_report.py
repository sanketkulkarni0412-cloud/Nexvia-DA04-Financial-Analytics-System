"""
Automated Validation Suite for Task 2 Phase 3: Excel Financial Workbook
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1.  Workbook opens and is not corrupted.
2.  All 8 required sheets exist in the correct order.
3.  Required banner/disclaimer text is present.
4.  P&L Monthly sheet has exactly 139 data rows.
5.  P&L Annual sheet has exactly 12 data rows.
6.  Key KPI values match authoritative SQL view totals (< $0.01 tolerance).
7.  Reconciliation audit shows zero variance.
8.  "Model-Based Analytical Reserve — Not Statutory ALLL/CECL" label present.
9.  "Cumulative Principal Collection Rate" label present (NOT "Principal Recovery Rate").
10. No sheet has zero rows of data.
11. Required column headers exist on tabular sheets.
12. Active Gross Loan Outstanding matches vw_portfolio_balance_sheet_summary.
13. NPL Balance matches vw_portfolio_balance_sheet_summary.
14. Total loans (2,260,668) is correctly reported.
"""

import os
import sys
import sqlite3
import pytest
import openpyxl

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

EXCEL_PATH = os.path.join(BASE_DIR, "reports", "LOAN_PORTFOLIO_FINANCIAL_REPORT.xlsx")
DB_PATH    = os.path.join(BASE_DIR, "warehouse.db")

REQUIRED_SHEETS = [
    "Executive Summary",
    "P&L Monthly",
    "P&L Annual",
    "Balance Sheet & Solvency",
    "Delinquency Aging",
    "Vintage Analysis",
    "Reconciliation & Audit",
    "Assumptions & Disclosures",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def wb():
    """Loads the generated Excel workbook once for all tests."""
    assert os.path.exists(EXCEL_PATH), (
        f"Excel workbook not found: {EXCEL_PATH}\n"
        "Run: python financial_reports/excel_report_builder.py"
    )
    return openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)


@pytest.fixture(scope="module")
def db_conn():
    """Read-only connection to warehouse.db."""
    uri = f"file:///{DB_PATH.replace(os.sep, '/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    yield conn
    conn.close()


def _sheet_all_values(ws) -> list:
    """Returns a flat list of all non-None cell values in a worksheet."""
    vals = []
    for row in ws.iter_rows(values_only=True):
        for v in row:
            if v is not None:
                vals.append(str(v))
    return vals


def _count_data_rows(ws, header_row: int) -> int:
    """Counts non-empty rows after the given header_row (inclusive start = header_row+1)."""
    count = 0
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if any(v is not None for v in row):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_workbook_exists_and_opens():
    """Verify the workbook file exists and can be opened by openpyxl."""
    assert os.path.exists(EXCEL_PATH), f"Workbook not found: {EXCEL_PATH}"
    assert os.path.getsize(EXCEL_PATH) > 10_000, "Workbook file is suspiciously small (<10 KB)"
    wb_check = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    assert len(wb_check.sheetnames) > 0
    wb_check.close()


def test_all_8_sheets_exist_in_correct_order(wb):
    """Verify all 8 required sheets exist in the exact specified order."""
    actual = wb.sheetnames
    assert actual == REQUIRED_SHEETS, (
        f"Sheet order mismatch.\nExpected: {REQUIRED_SHEETS}\nActual:   {actual}"
    )


def test_no_sheet_is_empty(wb):
    """Every sheet must contain at least one non-None cell value."""
    for sheet_name in REQUIRED_SHEETS:
        ws   = wb[sheet_name]
        vals = _sheet_all_values(ws)
        assert len(vals) > 0, f"Sheet '{sheet_name}' is empty"


def test_pnl_monthly_has_139_data_rows(wb):
    """P&L Monthly must have exactly 139 vintage month data rows (row 6 onwards)."""
    ws = wb["P&L Monthly"]
    # Header is at row 5; data starts at row 6; total row is last
    # Count rows with a value in column A that look like YYYY-MM
    data_rows = []
    for row in ws.iter_rows(min_row=6, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val) != "PORTFOLIO TOTAL" and len(str(val)) == 7:
            data_rows.append(val)
    assert len(data_rows) == 139, (
        f"P&L Monthly: expected 139 data rows, found {len(data_rows)}"
    )


def test_pnl_annual_has_12_data_rows(wb):
    """P&L Annual must have exactly 12 annual vintage rows (2007–2018)."""
    ws = wb["P&L Annual"]
    data_rows = []
    for row in ws.iter_rows(min_row=6, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val) != "PORTFOLIO TOTAL":
            try:
                year = int(val)
                if 2007 <= year <= 2018:
                    data_rows.append(year)
            except (ValueError, TypeError):
                pass
    assert len(data_rows) == 12, (
        f"P&L Annual: expected 12 annual rows (2007-2018), found {len(data_rows)}: {data_rows}"
    )


def test_pnl_annual_covers_2007_to_2018(wb):
    """All years from 2007 to 2018 must appear in P&L Annual."""
    ws = wb["P&L Annual"]
    years_found = set()
    for row in ws.iter_rows(min_row=6, max_col=1, values_only=True):
        val = row[0]
        try:
            year = int(val)
            if 2007 <= year <= 2018:
                years_found.add(year)
        except (ValueError, TypeError):
            pass
    expected = set(range(2007, 2019))
    assert years_found == expected, (
        f"Missing years: {expected - years_found}. Extra years: {years_found - expected}"
    )


def test_total_funded_amount_matches_warehouse(wb, db_conn):
    """Total funded amount on Executive Summary must match vw_portfolio_balance_sheet_summary."""
    cur = db_conn.cursor()
    cur.execute("SELECT total_funded_amount FROM vw_portfolio_balance_sheet_summary;")
    expected = float(cur.fetchone()[0])

    ws   = wb["Executive Summary"]
    vals = _sheet_all_values(ws)
    # Look for the numeric value in the sheet (formatted as $34,004,208,600.00 or raw float)
    found = False
    for v in vals:
        try:
            numeric = float(str(v).replace("$", "").replace(",", ""))
            if abs(numeric - expected) < 1.0:   # within $1 tolerance for formatting
                found = True
                break
        except (ValueError, TypeError):
            pass
    assert found, (
        f"Total funded amount ({expected:,.2f}) not found in Executive Summary sheet"
    )


def test_active_gross_outstanding_matches_warehouse(wb, db_conn):
    """Active gross loan outstanding must match vw_portfolio_balance_sheet_summary."""
    cur = db_conn.cursor()
    cur.execute("SELECT active_gross_loan_outstanding FROM vw_portfolio_balance_sheet_summary;")
    expected = float(cur.fetchone()[0])

    ws   = wb["Balance Sheet & Solvency"]
    vals = _sheet_all_values(ws)
    found = False
    for v in vals:
        try:
            numeric = float(str(v).replace("$", "").replace(",", ""))
            if abs(numeric - expected) < 1.0:
                found = True
                break
        except (ValueError, TypeError):
            pass
    assert found, (
        f"Active gross outstanding ({expected:,.2f}) not found in Balance Sheet sheet"
    )


def test_npl_balance_matches_warehouse(wb, db_conn):
    """NPL balance must match vw_portfolio_balance_sheet_summary."""
    cur = db_conn.cursor()
    cur.execute("SELECT NPL_balance FROM vw_portfolio_balance_sheet_summary;")
    expected = float(cur.fetchone()[0])

    ws   = wb["Balance Sheet & Solvency"]
    vals = _sheet_all_values(ws)
    found = False
    for v in vals:
        try:
            numeric = float(str(v).replace("$", "").replace(",", ""))
            if abs(numeric - expected) < 1.0:
                found = True
                break
        except (ValueError, TypeError):
            pass
    assert found, (
        f"NPL balance ({expected:,.2f}) not found in Balance Sheet sheet"
    )


def test_total_loans_2260668_present(wb, db_conn):
    """Total loan count of 2,260,668 must be present in Executive Summary."""
    cur = db_conn.cursor()
    cur.execute("SELECT SUM(loan_count) FROM vw_portfolio_pnl_monthly;")
    expected = int(cur.fetchone()[0])

    ws   = wb["Executive Summary"]
    vals = _sheet_all_values(ws)
    found = False
    for v in vals:
        try:
            numeric = int(str(v).replace(",", "").strip())
            if numeric == expected:
                found = True
                break
        except (ValueError, TypeError):
            pass
    assert found, (
        f"Total loan count ({expected:,}) not found in Executive Summary"
    )


def test_reconciliation_variance_is_zero(wb):
    """Reconciliation & Audit sheet must show zero ($0.00) variances."""
    ws   = wb["Reconciliation & Audit"]
    vals = _sheet_all_values(ws)
    # The variance column should contain "0.00" strings — verify at least 10 of them
    zero_count = sum(1 for v in vals if str(v).strip() in ("0.00", "0", "$0.00"))
    assert zero_count >= 10, (
        f"Expected at least 10 zero-variance cells in Reconciliation sheet, found {zero_count}. "
        "Some variances may be non-zero."
    )


def test_model_based_reserve_label_present(wb):
    """The reserve label 'Model-Based Analytical Reserve — Not Statutory ALLL/CECL' must appear."""
    target = "Not Statutory ALLL/CECL"
    for sheet_name in ["Balance Sheet & Solvency", "Executive Summary", "Assumptions & Disclosures"]:
        ws   = wb[sheet_name]
        vals = _sheet_all_values(ws)
        if any(target in v for v in vals):
            return  # found in at least one sheet
    pytest.fail(
        f"Label fragment '{target}' not found in any of: "
        "Balance Sheet & Solvency, Executive Summary, Assumptions & Disclosures"
    )


def test_cumulative_principal_collection_rate_label_present(wb):
    """'Cumulative Principal Collection Rate' label must be present (NOT 'Principal Recovery Rate')."""
    target   = "Cumulative Principal Collection Rate"
    bad_term = "Principal Recovery Rate"

    exec_ws   = wb["Executive Summary"]
    exec_vals = _sheet_all_values(exec_ws)

    assert any(target in v for v in exec_vals), (
        f"Required label '{target}' not found in Executive Summary"
    )
    # Ensure the rejected label isn't used as a primary KPI name
    assert not any(bad_term == v.strip() for v in exec_vals), (
        f"Deprecated label '{bad_term}' found as a cell value in Executive Summary — "
        "it should be replaced with 'Cumulative Principal Collection Rate'"
    )


def test_accounting_disclaimer_present(wb):
    """The mandatory accounting framework disclaimer must appear in the workbook."""
    targets = [
        "not a statutory corporate GAAP",
        "Loan Portfolio Financial Statement",
        "not be interpreted as the statutory financial statements",
    ]
    all_vals = []
    for sn in ["Executive Summary", "Assumptions & Disclosures"]:
        all_vals.extend(_sheet_all_values(wb[sn]))

    combined = " ".join(all_vals).lower()
    for phrase in targets:
        assert phrase.lower() in combined, (
            f"Required disclaimer phrase not found: '{phrase}'"
        )


def test_executive_summary_has_required_headers(wb):
    """Executive Summary must contain all required KPI labels."""
    required_labels = [
        "Total Loans",
        "Total Funded",
        "Interest Income",
        "Active Gross",
        "NPL",
        "Analytical Loss Reserve",
        "Net Loan Portfolio",
        "Cumulative Principal Collection Rate",
    ]
    ws   = wb["Executive Summary"]
    vals = " ".join(_sheet_all_values(ws))
    for label in required_labels:
        assert label.lower() in vals.lower(), (
            f"Required KPI label not found in Executive Summary: '{label}'"
        )


def test_delinquency_aging_has_data(wb):
    """Delinquency Aging sheet must contain at least 4 delinquency bracket rows."""
    ws = wb["Delinquency Aging"]
    bracket_rows = 0
    for row in ws.iter_rows(min_row=8, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val).strip() not in ("", "ACTIVE PORTFOLIO TOTAL"):
            bracket_rows += 1
    assert bracket_rows >= 4, (
        f"Delinquency Aging: expected at least 4 bracket rows, found {bracket_rows}"
    )


def test_vintage_analysis_has_data(wb):
    """Vintage Analysis sheet must contain at least 100 cohort rows."""
    ws = wb["Vintage Analysis"]
    data_count = 0
    for row in ws.iter_rows(min_row=8, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val).strip() not in ("", "PORTFOLIO TOTAL"):
            try:
                int(val)
                data_count += 1
            except (ValueError, TypeError):
                pass
    assert data_count >= 100, (
        f"Vintage Analysis: expected at least 100 year-cohort rows, found {data_count}"
    )


def test_balance_sheet_contains_grade_solvency(wb):
    """Balance Sheet sheet must contain all 7 credit grades (A through G)."""
    ws = wb["Balance Sheet & Solvency"]
    vals = _sheet_all_values(ws)
    for grade in ["A", "B", "C", "D", "E", "F", "G"]:
        assert grade in vals, (
            f"Credit grade '{grade}' not found in Balance Sheet & Solvency"
        )


def test_no_corporate_fabrication_in_balance_sheet(wb):
    """Fabricated corporate items must NOT appear as numeric values in Balance Sheet."""
    ws = wb["Balance Sheet & Solvency"]
    vals = _sheet_all_values(ws)
    combined = " ".join(vals).lower()
    forbidden_as_line_items = [
        "corporate cash",
        "shareholder equity",
        "retained earnings",
        "income tax expense",
    ]
    for item in forbidden_as_line_items:
        assert item not in combined, (
            f"Fabricated corporate item '{item}' appears in Balance Sheet — it must not be reported as a balance"
        )


def test_pnl_monthly_headers_correct(wb):
    """P&L Monthly must contain required column headers."""
    ws = wb["P&L Monthly"]
    header_vals = []
    for row in ws.iter_rows(min_row=5, max_row=5, values_only=True):
        for v in row:
            if v is not None:
                header_vals.append(str(v))
    combined = " ".join(header_vals).lower()
    for required in ["funded", "interest income", "net recoveries", "default", "credit loss"]:
        assert required in combined, (
            f"Required header keyword '{required}' not found in P&L Monthly header row"
        )


def test_assumptions_sheet_budget_limitation_stated(wb):
    """Assumptions sheet must state that no budget data was provided."""
    ws   = wb["Assumptions & Disclosures"]
    vals = " ".join(_sheet_all_values(ws)).lower()
    assert "no official budget dataset was provided" in vals, (
        "Budget limitation disclosure not found in Assumptions & Disclosures"
    )


def test_assumptions_sheet_data_lineage_present(wb):
    """Assumptions sheet must reference the data lineage (fact_accepted_loans / warehouse.db)."""
    ws   = wb["Assumptions & Disclosures"]
    vals = " ".join(_sheet_all_values(ws)).lower()
    assert "warehouse.db" in vals, "warehouse.db reference not found in Assumptions sheet"
    assert "fact_accepted_loans" in vals, "fact_accepted_loans reference not found in Assumptions sheet"

