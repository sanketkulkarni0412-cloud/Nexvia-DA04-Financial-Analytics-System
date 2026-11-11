"""
Automated Test for SQL Schema DDL Syntax & Integrity
Financial Analytics and Risk Reporting System (DA-04)
Validates that the SQLite DDL scripts execute cleanly without syntax errors.
"""

import os
import sqlite3
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
        
    print(f"\n[PASS] All {len(EXPECTED_TABLES)} dimensional tables successfully verified in SQLite in-memory engine!")
