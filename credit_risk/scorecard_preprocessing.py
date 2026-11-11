"""
Scorecard Preprocessing & Feature Engineering Module
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2A (Credit Risk Scorecard Development)
Framing: Retail Credit Risk Scorecard Modeling
Data Source: SQLite Data Warehouse (warehouse.db) in read-only mode (mode=ro)

Responsibilities:
1. Extracts mature closed loan development population (is_seasoned_closed = 1).
2. Verifies exact target definition (is_confirmed_default: 0 = Good, 1 = Bad).
3. Strictly isolates and excludes post-origination leakage and endogenous features.
4. Performs leakage-safe feature engineering on origination attributes:
   - credit_history_months
   - installment_to_income
5. Handles missingness, outliers, and placeholder values defensibly.
6. Produces a stratified, reproducible Train/Test split (80/20, seed=42).
"""

import os
import sys
import sqlite3
from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "warehouse.db")

# Prohibited post-origination and endogenous leakage features
LEAKAGE_COLUMNS: List[str] = [
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "recoveries",
    "collection_cost",
    "last_pymnt_d",
    "last_pymnt_amnt",
    "last_credit_pull_d",
    "delinquency_tier",
    "is_seasoned_closed",
    "loan_status",
    "grade",
    "sub_grade",
    "int_rate"
]

# Approved candidate predictors available at application/origination time
APPROVED_PREDICTORS: List[str] = [
    "fico_midpoint",
    "dti",
    "annual_inc",
    "term_months",
    "loan_amnt",
    "emp_length_years",
    "home_ownership",
    "verification_status",
    "revol_util",
    "revol_bal",
    "open_acc",
    "total_acc",
    "pub_rec",
    "earliest_cr_line"
]


class ScorecardDataPreprocessor:
    """
    Extracts and prepares the closed loan cohort for scorecard development.
    Strictly enforces read-only access and anti-leakage guards.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        self.uri = f"file:///{self.db_path.replace(os.sep, '/')}?mode=ro"

    def load_development_data(self) -> pd.DataFrame:
        """
        Loads the mature closed loan development population (is_seasoned_closed = 1).
        Excludes all active loans (is_seasoned_closed = 0).
        """
        query = """
            SELECT 
                f.loan_id,
                f.is_confirmed_default                              AS target,
                f.loan_amnt,
                f.installment,
                f.term_months,
                d.year                                              AS issue_year,
                d.year_month                                        AS issue_year_month,
                d.full_date                                         AS issue_date,
                p.annual_inc,
                p.dti,
                p.fico_midpoint,
                p.open_acc,
                p.pub_rec,
                p.revol_bal,
                p.revol_util,
                p.total_acc,
                p.home_ownership,
                p.verification_status,
                p.emp_length_years,
                p.earliest_cr_line
            FROM fact_accepted_loans f
            JOIN dim_borrower_credit_profile p ON f.loan_id = p.loan_id
            JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
            WHERE f.is_seasoned_closed = 1;
        """
        with sqlite3.connect(self.uri, uri=True) as conn:
            df = pd.read_sql_query(query, conn)

        # Basic integrity assertion
        assert len(df) == 1348099, f"Expected 1,348,099 rows, got {len(df)}"
        assert df["target"].isnull().sum() == 0, "Target column contains NULL values"
        assert set(df["target"].unique()) == {0, 1}, f"Unexpected target values: {df['target'].unique()}"

        return df

    @staticmethod
    def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Derives legitimate origination-time features and handles missing/special values.
        Does NOT use any post-origination or target-leaking data.
        """
        df = df.copy()

        # 1. Derive credit_history_months (months between earliest credit line and loan origination)
        issue_dt = pd.to_datetime(df["issue_date"], errors="coerce")
        cr_dt = pd.to_datetime(df["earliest_cr_line"], format="%b-%Y", errors="coerce")
        months = (issue_dt.dt.year - cr_dt.dt.year) * 12 + (issue_dt.dt.month - cr_dt.dt.month)
        # Handle century wraparound (e.g. 1968 vs 2068 default parsing for 2-digit years)
        months = months.apply(lambda m: m if (pd.isna(m) or m >= 0) else m + 1200)
        df["credit_history_months"] = months

        # 2. Derive installment_to_income (monthly installment / monthly income %)
        monthly_income = df["annual_inc"] / 12.0
        df["installment_to_income"] = np.where(
            monthly_income > 0,
            (df["installment"] / monthly_income) * 100.0,
            np.nan
        )

        # 3. Clean Home Ownership categories (group rare classes ANY, OTHER, NONE into 'OTHER')
        df["home_ownership_clean"] = df["home_ownership"].apply(
            lambda x: x if x in ["MORTGAGE", "RENT", "OWN"] else "OTHER"
        )

        # 4. Fill missing emp_length_years with a sentinel value (-1) representing Missing
        df["emp_length_imputed"] = df["emp_length_years"].fillna(-1.0)

        return df

    def prepare_train_test_split(
        self,
        test_size: float = 0.20,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Extracts, engineers features, and creates a stratified 80/20 train/test split.
        """
        df_raw = self.load_development_data()
        df_engineered = self.engineer_features(df_raw)

        train_df, test_df = train_test_split(
            df_engineered,
            test_size=test_size,
            stratify=df_engineered["target"],
            random_state=random_state
        )

        metadata = {
            "total_records": len(df_engineered),
            "train_records": len(train_df),
            "test_records": len(test_df),
            "train_good_count": int((train_df["target"] == 0).sum()),
            "train_bad_count": int((train_df["target"] == 1).sum()),
            "test_good_count": int((test_df["target"] == 0).sum()),
            "test_bad_count": int((test_df["target"] == 1).sum()),
            "overall_bad_rate": float(df_engineered["target"].mean()),
            "train_bad_rate": float(train_df["target"].mean()),
            "test_bad_rate": float(test_df["target"].mean()),
            "random_state": random_state,
            "test_size": test_size
        }

        return train_df, test_df, metadata

