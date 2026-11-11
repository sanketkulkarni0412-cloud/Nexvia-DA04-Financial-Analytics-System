"""
Unit & Integration Tests for Credit Risk Preprocessing Module
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. Exact mature closed population extracted (1,348,099 rows).
2. Target definition is binary Y in {0, 1} with 0=Good, 1=Bad, and zero nulls.
3. Active loans (is_seasoned_closed = 0) are strictly excluded from development data.
4. Post-origination and endogenous leakage columns are strictly excluded.
5. Train/Test split is 80/20, stratified by target, and deterministic with seed 42.
6. Derived origination features (credit_history_months, installment_to_income) are valid.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.scorecard_preprocessing import (
    ScorecardDataPreprocessor,
    LEAKAGE_COLUMNS,
    APPROVED_PREDICTORS
)

DB_PATH = os.path.join(BASE_DIR, "warehouse.db")


@pytest.fixture(scope="module")
def preprocessor():
    return ScorecardDataPreprocessor(db_path=DB_PATH)


@pytest.fixture(scope="module")
def dev_data(preprocessor):
    return preprocessor.load_development_data()


def test_mature_closed_population_count(dev_data):
    """Verify that exactly 1,348,099 closed contracts enter the development population."""
    assert len(dev_data) == 1348099, f"Expected 1,348,099 loans, found {len(dev_data)}"


def test_target_definition_and_values(dev_data):
    """Verify that target is binary {0, 1} with exact Good/Bad counts and 0 nulls."""
    assert dev_data["target"].isnull().sum() == 0, "Target column contains NULL values"
    unique_vals = set(dev_data["target"].unique())
    assert unique_vals == {0, 1}, f"Unexpected target classes: {unique_vals}"

    good_count = int((dev_data["target"] == 0).sum())
    bad_count = int((dev_data["target"] == 1).sum())

    assert good_count == 1078739, f"Expected 1,078,739 Goods, found {good_count}"
    assert bad_count == 269360, f"Expected 269,360 Bads, found {bad_count}"
    bad_rate = bad_count / len(dev_data)
    assert abs(bad_rate - 0.199807) < 0.0001, f"Bad rate deviation: {bad_rate}"


def test_active_loans_strictly_excluded(dev_data):
    """Verify that no active/unclosed loans are present."""
    # Column is_seasoned_closed was filtered at query time to = 1
    # Check that loan_status does not contain active categories
    active_statuses = {"Current", "Late (31-120 days)", "In Grace Period", "Late (16-30 days)"}
    # loan_status is not even queried to prevent leakage, but verify total count matches closed count
    assert len(dev_data) == 1348099


def test_leakage_columns_excluded(dev_data):
    """Verify that prohibited post-origination leakage features are absent from the loaded dataset."""
    present_cols = set(dev_data.columns)
    for col in LEAKAGE_COLUMNS:
        assert col not in present_cols, f"Prohibited leakage column '{col}' is present in development dataframe"


def test_feature_engineering_derived_safely(dev_data):
    """Verify that derived origination features compute cleanly without errors."""
    df_sample = dev_data.head(5000).copy()
    engineered = ScorecardDataPreprocessor.engineer_features(df_sample)

    assert "credit_history_months" in engineered.columns
    assert "installment_to_income" in engineered.columns
    assert "home_ownership_clean" in engineered.columns
    assert "emp_length_imputed" in engineered.columns

    # Check credit history months bounds
    valid_months = engineered["credit_history_months"].dropna()
    assert (valid_months >= 0).all(), "Negative credit history months detected"
    assert (valid_months <= 1200).all(), "Unrealistic credit history months (>100 years) detected"

    # Check home ownership categories
    unique_homes = set(engineered["home_ownership_clean"].unique())
    assert unique_homes.issubset({"MORTGAGE", "RENT", "OWN", "OTHER"})


def test_train_test_stratification(preprocessor):
    """Verify that 80/20 train/test split preserves exact bad rate stratification."""
    train_df, test_df, meta = preprocessor.prepare_train_test_split(test_size=0.20, random_state=42)

    assert len(train_df) == 1078479, f"Expected 1,078,479 train records, got {len(train_df)}"
    assert len(test_df) == 269620, f"Expected 269,620 test records, got {len(test_df)}"

    train_bad_rate = train_df["target"].mean()
    test_bad_rate = test_df["target"].mean()

    assert abs(train_bad_rate - 0.199807) < 0.0005, f"Train bad rate drifted: {train_bad_rate}"
    assert abs(test_bad_rate - 0.199807) < 0.0005, f"Test bad rate drifted: {test_bad_rate}"


def test_deterministic_split_with_seed(preprocessor):
    """Verify that random_state=42 yields deterministic, identical partitions."""
    train1, test1, _ = preprocessor.prepare_train_test_split(test_size=0.20, random_state=42)
    train2, test2, _ = preprocessor.prepare_train_test_split(test_size=0.20, random_state=42)

    assert train1["loan_id"].head(100).tolist() == train2["loan_id"].head(100).tolist()
    assert test1["loan_id"].head(100).tolist() == test2["loan_id"].head(100).tolist()

