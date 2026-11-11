"""
Automated Test Suite for Phase 2: Data Acquisition, Profiling & EDA
Financial Analytics and Risk Reporting System (DA-04)
Executed via pytest to ensure 100% data integrity and pipeline compliance.
"""

import os
import pytest
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_PATH = os.path.join(BASE_DIR, "dataset", "raw", "lending_club_loans.csv")
CHARTS_DIR = os.path.join(BASE_DIR, "reports", "eda_charts")
SUMMARY_REPORT_PATH = os.path.join(BASE_DIR, "reports", "EDA_SUMMARY.md")
DICTIONARY_PATH = os.path.join(BASE_DIR, "documentation", "DATA_DICTIONARY.md")

REQUIRED_COLUMNS = [
    "loan_amnt", "int_rate", "grade", "emp_length", "annual_inc",
    "dti", "fico_range_low", "loan_status", "issue_d", "term",
    "installment", "total_pymnt"
]

EXPECTED_CHARTS = [
    "loan_grade_distribution.png",
    "default_rate_by_grade.png",
    "loan_amount_distribution.png",
    "interest_rate_distribution.png",
    "loan_status_distribution.png",
    "correlation_heatmap.png",
    "default_rate_by_emp_length.png"
]


@pytest.fixture(scope="module")
def raw_dataframe():
    """Loads raw dataframe once for testing."""
    assert os.path.exists(RAW_DATA_PATH), f"Raw dataset not found at {RAW_DATA_PATH}"
    df = pd.read_csv(RAW_DATA_PATH, low_memory=False)
    return df


def test_dataset_loads_and_row_count(raw_dataframe):
    """Verify dataset loads successfully and row count > 0."""
    assert raw_dataframe is not None, "DataFrame failed to load."
    assert len(raw_dataframe) > 0, f"Expected rows > 0, got {len(raw_dataframe)}"
    assert len(raw_dataframe) >= 50000, f"Expected institutional dataset >= 50,000 rows, got {len(raw_dataframe):,}"
    assert len(raw_dataframe.columns) >= 100, f"Expected 100+ raw columns, got {len(raw_dataframe.columns)}"


def test_required_columns_exist(raw_dataframe):
    """Verify all 12 mandatory financial assessment columns exist."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in raw_dataframe.columns]
    assert len(missing_cols) == 0, f"Missing required assessment columns: {missing_cols}"


def test_data_types_and_range_validity(raw_dataframe):
    """Verify numeric and categorical data types and business ranges."""
    # Loan amount should be positive numeric
    assert pd.api.types.is_numeric_dtype(raw_dataframe["loan_amnt"]), "loan_amnt must be numeric"
    assert (raw_dataframe["loan_amnt"] > 0).all(), "loan_amnt must be strictly positive"
    
    # Interest rate should be positive percentage
    assert pd.api.types.is_numeric_dtype(raw_dataframe["int_rate"]), "int_rate must be numeric"
    assert (raw_dataframe["int_rate"] > 0).all(), "int_rate must be strictly positive"
    
    # Loan grades must only contain A through G
    valid_grades = {"A", "B", "C", "D", "E", "F", "G"}
    found_grades = set(raw_dataframe["grade"].dropna().unique())
    assert found_grades.issubset(valid_grades), f"Unexpected grades found: {found_grades - valid_grades}"
    assert len(found_grades) == 7, "All 7 grades (A to G) must be present in portfolio"
    
    # FICO scores should be in valid credit bureau range (300 to 850)
    assert pd.api.types.is_numeric_dtype(raw_dataframe["fico_range_low"]), "fico_range_low must be numeric"
    valid_fico = raw_dataframe["fico_range_low"].dropna()
    assert (valid_fico >= 300).all() and (valid_fico <= 850).all(), "FICO scores out of regulatory bounds"


def test_all_eda_charts_generated():
    """Verify all 7 Matplotlib/Seaborn charts were created with valid binary size."""
    assert os.path.exists(CHARTS_DIR), f"Charts directory missing: {CHARTS_DIR}"
    for chart_name in EXPECTED_CHARTS:
        chart_path = os.path.join(CHARTS_DIR, chart_name)
        assert os.path.exists(chart_path), f"Chart file missing: {chart_name}"
        assert os.path.getsize(chart_path) > 10000, f"Chart file appears corrupt/empty: {chart_name}"


def test_documentation_and_reports_created():
    """Verify EDA_SUMMARY.md and DATA_DICTIONARY.md are created and non-empty."""
    assert os.path.exists(SUMMARY_REPORT_PATH), f"Report missing at {SUMMARY_REPORT_PATH}"
    assert os.path.getsize(SUMMARY_REPORT_PATH) > 1000, "EDA_SUMMARY.md is unexpectedly small"
    
    assert os.path.exists(DICTIONARY_PATH), f"Data dictionary missing at {DICTIONARY_PATH}"
    assert os.path.getsize(DICTIONARY_PATH) > 1000, "DATA_DICTIONARY.md is unexpectedly small"
    
    # Verify core sections exist in summary report
    with open(SUMMARY_REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Loan Volume by Credit Grade" in content
        assert "Default Distribution by Credit Grade" in content
        assert "Monotonic Risk Pricing Law Verified" in content
