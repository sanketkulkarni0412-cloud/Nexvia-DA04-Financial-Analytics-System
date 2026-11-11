"""
Automated Test Suite for Phase 3 Architecture, Integrity & Rules
Financial Analytics and Risk Reporting System (DA-04)

Tests:
1. Schema DDL syntax and table creation (8 dimensional entities)
2. Primary-key uniqueness enforcement
3. Foreign-key referential integrity enforcement
4. Credit risk default classification logic (preserving unresolved late loans)
5. Footer and section header filtering rule (protecting legitimate loans)
6. Traceability of rejected applications via source_row_num
"""

import os
import sqlite3
import pandas as pd
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQLITE_SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema_sqlite.sql")
ANSI_SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema.sql")

EXPECTED_TABLES = [
    "dim_calendar_date",
    "dim_loan_grade",
    "dim_geography",
    "dim_borrower_credit_profile",
    "dim_financial_budget",
    "fact_accepted_loans",
    "fact_rejected_applications",
    "fact_underwriting_funnel_monthly",
    "etl_ingestion_checkpoints"
]


def classify_loan_status(status_str: str):
    """
    Standardized classification rule for loan statuses.
    Ensures severe late loans are NOT conflated with confirmed charge-offs/defaults.
    """
    if not isinstance(status_str, str):
        return None, "Unknown", 0
    
    s = status_str.strip()
    if s in ["Fully Paid", "Does not meet the credit policy. Status:Fully Paid"]:
        return 0, "Closed Good", 1
    elif s in ["Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"]:
        return 1, "Closed Default", 1
    elif s == "Current":
        return None, "Current", 0
    elif s == "In Grace Period":
        return None, "Grace Period", 0
    elif s == "Late (16-30 days)":
        return None, "Late (16-30)", 0
    elif s == "Late (31-120 days)":
        return None, "Severe Late (31-120)", 0
    else:
        return None, "Other", 0


def filter_accepted_footers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strict filtering rule:
    Removes partition summaries ('Total amount funded...') and section headers ('Loans that do not meet...').
    Guarantees legitimate loan records (numeric id, non-null loan_amnt) are preserved.
    """
    is_footer = df["loan_amnt"].isnull() | df["id"].astype(str).str.contains("Total amount funded|Loans that do not meet", regex=True, na=False)
    return df[~is_footer].copy()


def test_schema_files_exist():
    assert os.path.exists(SQLITE_SCHEMA_PATH), f"Missing {SQLITE_SCHEMA_PATH}"
    assert os.path.exists(ANSI_SCHEMA_PATH), f"Missing {ANSI_SCHEMA_PATH}"


def test_sqlite_schema_executes_in_memory():
    """Validates that schema_sqlite.sql executes and creates all 8 dimensional tables."""
    conn = sqlite3.connect(":memory:")
    with open(SQLITE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        ddl = f.read()
    
    conn.executescript(ddl)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    
    for expected in EXPECTED_TABLES:
        assert expected in tables, f"Expected table {expected} was not created in SQLite DDL."


def test_primary_key_uniqueness():
    """Validates that duplicate primary keys are rejected by SQLite."""
    conn = sqlite3.connect(":memory:")
    with open(SQLITE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    cursor = conn.cursor()
    
    # Insert initial geography
    cursor.execute("INSERT INTO dim_geography (state_code, state_name, census_region, economic_division) VALUES ('CA', 'California', 'West', 'Pacific');")
    conn.commit()
    
    # Attempt duplicate insert
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO dim_geography (state_code, state_name, census_region, economic_division) VALUES ('CA', 'Duplicate CA', 'West', 'Pacific');")


def test_foreign_key_integrity():
    """Validates that inserting fact records referencing invalid dimension keys fails under PRAGMA foreign_keys = ON."""
    conn = sqlite3.connect(":memory:")
    with open(SQLITE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Attempt to insert loan with non-existent foreign keys
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO fact_accepted_loans (
                loan_id, issue_date_key, grade_key, state_code,
                loan_amnt, funded_amnt, funded_amnt_inv, term_months,
                int_rate, installment, loan_status, delinquency_tier, is_seasoned_closed
            ) VALUES (
                'NON_EXISTENT_LOAN', 20151201, 999, 'ZZ',
                10000.0, 10000.0, 10000.0, 36,
                10.0, 322.0, 'Fully Paid', 'Closed Good', 1
            );
        """)


def test_default_classification_logic():
    """
    Validates that:
    1. Fully Paid -> is_confirmed_default = 0
    2. Charged Off and Default -> is_confirmed_default = 1
    3. Severe Late (31-120 days) -> is_confirmed_default = None (NOT classified as confirmed default)
    4. Current -> is_confirmed_default = None
    """
    # Fully Paid
    d_flag, tier, closed = classify_loan_status("Fully Paid")
    assert d_flag == 0
    assert tier == "Closed Good"
    assert closed == 1

    # Charged Off
    d_flag, tier, closed = classify_loan_status("Charged Off")
    assert d_flag == 1
    assert tier == "Closed Default"
    assert closed == 1

    # Default
    d_flag, tier, closed = classify_loan_status("Default")
    assert d_flag == 1
    assert tier == "Closed Default"
    assert closed == 1

    # Current
    d_flag, tier, closed = classify_loan_status("Current")
    assert d_flag is None
    assert tier == "Current"
    assert closed == 0

    # Severe Late (31-120 days) - Must NOT be default
    d_flag, tier, closed = classify_loan_status("Late (31-120 days)")
    assert d_flag is None, "Severe late loan must not be automatically classified as confirmed default"
    assert tier == "Severe Late (31-120)"
    assert closed == 0


def test_footer_filtering_rule():
    """
    Tests the footer filtering logic on a controlled test dataset containing:
    - Legitimate loans
    - Partition footers ('Total amount funded in policy code 1: ...')
    - Partition footers ('Total amount funded in policy code 2: ...')
    - Section header ('Loans that do not meet the credit policy')
    """
    test_data = pd.DataFrame([
        {"id": "10001", "loan_amnt": 15000.0, "term": " 36 months", "emp_title": "Engineer"},
        {"id": "10002", "loan_amnt": 25000.0, "term": " 60 months", "emp_title": None}, # Missing optional field
        {"id": "Total amount funded in policy code 1: 1465324575", "loan_amnt": None, "term": None, "emp_title": None},
        {"id": "Total amount funded in policy code 2: 521953170", "loan_amnt": None, "term": None, "emp_title": None},
        {"id": "Loans that do not meet the credit policy", "loan_amnt": None, "term": None, "emp_title": None},
        {"id": "10003", "loan_amnt": 8000.0, "term": " 36 months", "emp_title": "Analyst"},
    ])
    
    clean_df = filter_accepted_footers(test_data)
    
    # Assertions
    assert len(clean_df) == 3, f"Expected 3 clean loans, got {len(clean_df)}"
    assert list(clean_df["id"]) == ["10001", "10002", "10003"]
    assert clean_df["loan_amnt"].sum() == 48000.0


def test_rejected_source_row_num_uniqueness():
    """Validates that source_row_num in fact_rejected_applications is strictly unique (UNIQUE constraint)."""
    conn = sqlite3.connect(":memory:")
    with open(SQLITE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Insert required calendar date dimension
    cursor.execute("""
        INSERT INTO dim_calendar_date (
            date_key, full_date, year, quarter, month, month_name, year_month, year_quarter, fiscal_year, fiscal_quarter
        ) VALUES (20161231, '2016-12-31', 2016, 4, 12, 'December', '2016-12', '2016-Q4', 2016, 'FY16-Q4');
    """)
    conn.commit()
    
    # Insert initial rejected application with source_row_num = 2
    cursor.execute("""
        INSERT INTO fact_rejected_applications (
            source_row_num, app_date_key, application_date, amount_requested, risk_score
        ) VALUES (2, 20161231, '2016-12-31', 10000.0, 650.0);
    """)
    conn.commit()
    
    # Attempt to insert another application with identical source_row_num = 2 -> Must fail!
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO fact_rejected_applications (
                source_row_num, app_date_key, application_date, amount_requested, risk_score
            ) VALUES (2, 20161231, '2016-12-31', 15000.0, 590.0);
        """)

