"""
Data Cleaning & Transformation Pipeline
Financial Analytics and Risk Reporting System (DA-04)

Functions for:
1. CSV chunk streaming & cleaning
2. Date parsing to YYYYMMDD dimensional date keys
3. Strict non-loan partition row filtering (33 verified rows)
4. Standardized default & delinquency tier classification
5. Numeric type casting, validation, and NULL preservation
6. Schema transformations for fact_accepted_loans and dim_borrower_credit_profile
"""

import re
from datetime import datetime
import pandas as pd
import numpy as np


MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}


def parse_date_to_key(date_val) -> int:
    """
    Parses date strings (e.g., 'Dec-2015', '2015-12-01', 'Dec-15') to integer date key YYYYMMDD.
    Returns 19000101 if date_val is missing or unparseable.
    """
    if pd.isnull(date_val):
        return 19000101
    
    val_str = str(date_val).strip()
    if not val_str:
        return 19000101
        
    # Match Mon-YYYY (e.g., 'Dec-2015')
    m_mon_yyyy = re.match(r"^([A-Za-z]{3})-(\d{4})$", val_str)
    if m_mon_yyyy:
        mon_str, yyyy_str = m_mon_yyyy.groups()
        month = MONTH_MAP.get(mon_str.capitalize(), 1)
        year = int(yyyy_str)
        return year * 10000 + month * 100 + 1

    # Match YYYY-MM-DD (e.g., '2016-12-31')
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", val_str)
    if m_iso:
        yyyy_str, mm_str, dd_str = m_iso.groups()
        return int(yyyy_str) * 10000 + int(mm_str) * 100 + int(dd_str)

    # Match Mon-YY (e.g., 'Dec-15')
    m_mon_yy = re.match(r"^([A-Za-z]{3})-(\d{2})$", val_str)
    if m_mon_yy:
        mon_str, yy_str = m_mon_yy.groups()
        month = MONTH_MAP.get(mon_str.capitalize(), 1)
        yy = int(yy_str)
        year = 2000 + yy if yy < 50 else 1900 + yy
        return year * 10000 + month * 100 + 1

    try:
        dt = pd.to_datetime(val_str)
        return dt.year * 10000 + dt.month * 100 + dt.day
    except Exception:
        return 19000101


def parse_employment_years(emp_str):
    """
    Converts employment tenure string to clean integer years (0 to 10).
    '< 1 year' -> 0
    '1 year' -> 1, ..., '9 years' -> 9
    '10+ years' -> 10
    Returns None for missing or unparseable values.
    """
    if pd.isnull(emp_str):
        return None
    s = str(emp_str).strip()
    if not s or s.lower() in ["n/a", "unknown", "nan", "none"]:
        return None
    if "<" in s:
        return 0
    if "10" in s:
        return 10
    digits = re.findall(r"\d+", s)
    if digits:
        return int(digits[0])
    return None


def classify_loan_status(status_str: str) -> tuple:
    """
    Standardized classification rule for loan statuses.
    Returns: (is_confirmed_default, delinquency_tier, is_seasoned_closed)
    
    Guarantees:
    - 'Fully Paid' -> is_confirmed_default = 0, delinquency_tier = 'Closed Good', closed = 1
    - 'Charged Off', 'Default' -> is_confirmed_default = 1, delinquency_tier = 'Closed Default', closed = 1
    - 'Current' -> is_confirmed_default = None, delinquency_tier = 'Current', closed = 0
    - 'Late (31-120 days)' -> is_confirmed_default = None, delinquency_tier = 'Severe Late (31-120)', closed = 0
    - 'In Grace Period' -> is_confirmed_default = None, delinquency_tier = 'Grace Period', closed = 0
    - 'Late (16-30 days)' -> is_confirmed_default = None, delinquency_tier = 'Late (16-30)', closed = 0
    """
    if pd.isnull(status_str):
        return None, "Unknown", 0
    
    s = str(status_str).strip()
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


def filter_non_loan_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Identifies and removes partition footers and section headers.
    Returns clean DataFrame and list of dropped row details.
    """
    mask_non_loan = df["loan_amnt"].isnull() | df["id"].astype(str).str.contains(
        "Total amount funded|Loans that do not meet", regex=True, na=False
    )
    
    excluded_rows = []
    if mask_non_loan.any():
        for idx, row in df[mask_non_loan].iterrows():
            excluded_rows.append({
                "index": idx,
                "id": str(row.get("id")),
                "loan_amnt": str(row.get("loan_amnt"))
            })
            
    clean_df = df[~mask_non_loan].copy()
    return clean_df, excluded_rows


def clean_accepted_chunk(
    chunk_df: pd.DataFrame, 
    subgrade_map: dict
) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """
    Transforms a raw chunk of accepted loan records into two validated DataFrames:
    1. fact_accepted_loans
    2. dim_borrower_credit_profile
    
    Also returns list of excluded non-loan rows.
    """
    clean_df, excluded_rows = filter_non_loan_rows(chunk_df)
    if clean_df.empty:
        return pd.DataFrame(), pd.DataFrame(), excluded_rows
        
    # Standardize string ID
    clean_df["clean_id"] = clean_df["id"].astype(str).str.strip()
    
    # Extract Term Months (e.g., ' 36 months' -> 36)
    def parse_term(term_val):
        if pd.isnull(term_val):
            return 36
        digits = re.findall(r"\d+", str(term_val))
        return int(digits[0]) if digits else 36
        
    clean_df["clean_term"] = clean_df["term"].apply(parse_term)
    
    # Map Grade Key via sub_grade (fallback 1 for A1 if missing)
    clean_df["clean_sub_grade"] = clean_df["sub_grade"].astype(str).str.strip().str.upper()
    clean_df["grade_key"] = clean_df["clean_sub_grade"].map(subgrade_map).fillna(1).astype(int)
    
    # Issue Date Key
    clean_df["issue_date_key"] = clean_df["issue_d"].apply(parse_date_to_key)
    
    # State Code
    clean_df["state_code"] = clean_df["addr_state"].astype(str).str.strip().str.upper()
    clean_df["state_code"] = clean_df["state_code"].replace({"NAN": "XX", "NONE": "XX", "": "XX"})
    
    # Credit Status Classification
    status_tuples = clean_df["loan_status"].apply(classify_loan_status)
    clean_df["is_confirmed_default"] = [t[0] for t in status_tuples]
    clean_df["delinquency_tier"] = [t[1] for t in status_tuples]
    clean_df["is_seasoned_closed"] = [t[2] for t in status_tuples]
    
    # Numerics for Fact Accepted Loans
    clean_df["loan_amnt"] = pd.to_numeric(clean_df["loan_amnt"], errors="coerce").fillna(0.0)
    clean_df["funded_amnt"] = pd.to_numeric(clean_df["funded_amnt"], errors="coerce").fillna(0.0)
    clean_df["funded_amnt_inv"] = pd.to_numeric(clean_df["funded_amnt_inv"], errors="coerce").fillna(0.0)
    clean_df["int_rate"] = pd.to_numeric(clean_df["int_rate"], errors="coerce").fillna(0.0)
    clean_df["installment"] = pd.to_numeric(clean_df["installment"], errors="coerce").fillna(0.0)
    clean_df["total_pymnt"] = pd.to_numeric(clean_df["total_pymnt"], errors="coerce").fillna(0.0)
    clean_df["total_rec_prncp"] = pd.to_numeric(clean_df["total_rec_prncp"], errors="coerce").fillna(0.0)
    clean_df["total_rec_int"] = pd.to_numeric(clean_df["total_rec_int"], errors="coerce").fillna(0.0)
    clean_df["total_rec_late_fee"] = pd.to_numeric(clean_df["total_rec_late_fee"], errors="coerce").fillna(0.0)
    clean_df["recoveries"] = pd.to_numeric(clean_df["recoveries"], errors="coerce").fillna(0.0)
    
    col_rec_fee = "collection_recovery_fee" if "collection_recovery_fee" in clean_df.columns else "collection_cost"
    clean_df["collection_cost"] = pd.to_numeric(clean_df.get(col_rec_fee, 0.0), errors="coerce").fillna(0.0)
    clean_df["last_pymnt_amnt"] = pd.to_numeric(clean_df["last_pymnt_amnt"], errors="coerce").fillna(0.0)
    
    policy_code = pd.to_numeric(clean_df.get("policy_code", 1), errors="coerce").fillna(1).astype(int)
    clean_df["policy_code"] = policy_code
    
    last_pymnt_d = clean_df["last_pymnt_d"].astype(str).where(clean_df["last_pymnt_d"].notnull(), None) if "last_pymnt_d" in clean_df.columns else None
    last_credit_pull_d = clean_df["last_credit_pull_d"].astype(str).where(clean_df["last_credit_pull_d"].notnull(), None) if "last_credit_pull_d" in clean_df.columns else None

    # Build fact_accepted_loans DataFrame
    fact_df = pd.DataFrame({
        "loan_id": clean_df["clean_id"],
        "issue_date_key": clean_df["issue_date_key"].astype(int),
        "grade_key": clean_df["grade_key"].astype(int),
        "state_code": clean_df["state_code"],
        "loan_amnt": clean_df["loan_amnt"].astype(float),
        "funded_amnt": clean_df["funded_amnt"].astype(float),
        "funded_amnt_inv": clean_df["funded_amnt_inv"].astype(float),
        "term_months": clean_df["clean_term"].astype(int),
        "int_rate": clean_df["int_rate"].astype(float),
        "installment": clean_df["installment"].astype(float),
        "total_pymnt": clean_df["total_pymnt"].astype(float),
        "total_rec_prncp": clean_df["total_rec_prncp"].astype(float),
        "total_rec_int": clean_df["total_rec_int"].astype(float),
        "total_rec_late_fee": clean_df["total_rec_late_fee"].astype(float),
        "recoveries": clean_df["recoveries"].astype(float),
        "collection_cost": clean_df["collection_cost"].astype(float),
        "last_pymnt_amnt": clean_df["last_pymnt_amnt"].astype(float),
        "loan_status": clean_df["loan_status"].astype(str),
        "is_confirmed_default": clean_df["is_confirmed_default"],
        "delinquency_tier": clean_df["delinquency_tier"],
        "is_seasoned_closed": clean_df["is_seasoned_closed"].astype(int),
        "last_pymnt_d": last_pymnt_d,
        "last_credit_pull_d": last_credit_pull_d,
        "policy_code": clean_df["policy_code"]
    })
    
    # Numerics & Nulls for dim_borrower_credit_profile
    annual_inc = pd.to_numeric(clean_df.get("annual_inc", np.nan), errors="coerce")
    dti = pd.to_numeric(clean_df.get("dti", np.nan), errors="coerce")
    fico_low = pd.to_numeric(clean_df.get("fico_range_low", np.nan), errors="coerce")
    fico_high = pd.to_numeric(clean_df.get("fico_range_high", np.nan), errors="coerce")
    open_acc = pd.to_numeric(clean_df.get("open_acc", np.nan), errors="coerce")
    pub_rec = pd.to_numeric(clean_df.get("pub_rec", np.nan), errors="coerce")
    revol_bal = pd.to_numeric(clean_df.get("revol_bal", np.nan), errors="coerce")
    
    if "revol_util" in clean_df.columns:
        revol_util_series = clean_df["revol_util"].astype(str).str.rstrip("%")
        revol_util = pd.to_numeric(revol_util_series, errors="coerce")
    else:
        revol_util = pd.Series([np.nan] * len(clean_df), index=clean_df.index)
        
    total_acc = pd.to_numeric(clean_df.get("total_acc", np.nan), errors="coerce")
    
    if "emp_length" in clean_df.columns:
        emp_length_years = clean_df["emp_length"].apply(parse_employment_years)
        emp_length_val = clean_df["emp_length"].where(clean_df["emp_length"].notnull(), None)
    else:
        emp_length_years = pd.Series([None] * len(clean_df), index=clean_df.index)
        emp_length_val = pd.Series([None] * len(clean_df), index=clean_df.index)
        
    fico_midpoint = (fico_low + fico_high) / 2.0
    home_ownership = clean_df["home_ownership"].where(clean_df["home_ownership"].notnull(), None) if "home_ownership" in clean_df.columns else None
    verification_status = clean_df["verification_status"].where(clean_df["verification_status"].notnull(), None) if "verification_status" in clean_df.columns else None
    earliest_cr_line = clean_df["earliest_cr_line"].where(clean_df["earliest_cr_line"].notnull(), None) if "earliest_cr_line" in clean_df.columns else None
    
    profile_df = pd.DataFrame({
        "loan_id": clean_df["clean_id"],
        "annual_inc": annual_inc,
        "emp_length": emp_length_val,
        "emp_length_years": emp_length_years,
        "home_ownership": home_ownership,
        "verification_status": verification_status,
        "dti": dti,
        "fico_range_low": fico_low,
        "fico_range_high": fico_high,
        "fico_midpoint": fico_midpoint,
        "open_acc": open_acc,
        "pub_rec": pub_rec,
        "revol_bal": revol_bal,
        "revol_util": revol_util,
        "total_acc": total_acc,
        "earliest_cr_line": earliest_cr_line
    })
    
    return fact_df, profile_df, excluded_rows


def clean_rejected_chunk(
    chunk_df: pd.DataFrame, 
    start_row_num: int
) -> tuple[pd.DataFrame, list]:
    """
    Cleans a chunk of rejected applications (from rejected_2007_to_2018Q4.csv).
    Parameters:
        chunk_df: DataFrame slice from rejected CSV
        start_row_num: 1-indexed physical starting row number in the CSV
    Returns:
        tuple[pd.DataFrame, list]:
            - Cleaned DataFrame ready for fact_rejected_applications
            - List of invalid or flagged record dictionaries for audit trail
    """
    if chunk_df.empty:
        return pd.DataFrame(), []

    invalid_records = []
    num_rows = len(chunk_df)
    source_row_nums = list(range(start_row_num, start_row_num + num_rows))
    
    # Amount Requested
    amt_col = "Amount Requested" if "Amount Requested" in chunk_df.columns else "amount_requested"
    amount_requested = pd.to_numeric(chunk_df[amt_col], errors="coerce").fillna(0.0)
    
    # Application Date
    date_col = "Application Date" if "Application Date" in chunk_df.columns else "application_date"
    app_dates = chunk_df[date_col].astype(str)
    app_date_keys = app_dates.apply(parse_date_to_key)
    
    # Risk Score (Preserve NULL when unretrieved)
    risk_col = "Risk_Score" if "Risk_Score" in chunk_df.columns else "risk_score"
    risk_scores = pd.to_numeric(chunk_df.get(risk_col, np.nan), errors="coerce")
    
    # Debt-To-Income Ratio (strip '%' character)
    dti_col = "Debt-To-Income Ratio" if "Debt-To-Income Ratio" in chunk_df.columns else "dti_ratio"
    if dti_col in chunk_df.columns:
        dti_raw = chunk_df[dti_col].astype(str).str.rstrip("%")
        dti_ratios = pd.to_numeric(dti_raw, errors="coerce")
    else:
        dti_ratios = pd.Series([np.nan] * num_rows, index=chunk_df.index)
    
    # State Code
    state_col = "State" if "State" in chunk_df.columns else "state_code"
    if state_col in chunk_df.columns:
        states = chunk_df[state_col].astype(str).str.strip().str.upper()
        states = states.replace({"NAN": None, "NONE": None, "": None})
    else:
        states = pd.Series([None] * num_rows, index=chunk_df.index)
    
    # Zip Code
    zip_col = "Zip Code" if "Zip Code" in chunk_df.columns else "zip_code"
    if zip_col in chunk_df.columns:
        zip_codes = chunk_df[zip_col].astype(str).replace({"nan": None, "None": None, "": None})
    else:
        zip_codes = pd.Series([None] * num_rows, index=chunk_df.index)
    
    # Employment Length
    emp_col = "Employment Length" if "Employment Length" in chunk_df.columns else "emp_length_raw"
    if emp_col in chunk_df.columns:
        emp_lengths = chunk_df[emp_col].astype(str).replace({"nan": None, "None": None, "": None})
    else:
        emp_lengths = pd.Series([None] * num_rows, index=chunk_df.index)
    
    # Loan Title
    title_col = "Loan Title" if "Loan Title" in chunk_df.columns else "loan_title"
    if title_col in chunk_df.columns:
        loan_titles = chunk_df[title_col].astype(str).replace({"nan": None, "None": None, "": None})
    else:
        loan_titles = pd.Series([None] * num_rows, index=chunk_df.index)
    
    # Policy Code
    pol_col = "Policy Code" if "Policy Code" in chunk_df.columns else "policy_code"
    policy_codes = pd.to_numeric(chunk_df.get(pol_col, 0), errors="coerce").fillna(0).astype(int)
    
    clean_rejected_df = pd.DataFrame({
        "source_row_num": source_row_nums,
        "app_date_key": app_date_keys.astype(int),
        "application_date": app_dates,
        "amount_requested": amount_requested.astype(float),
        "risk_score": risk_scores,
        "dti_ratio": dti_ratios,
        "state_code": states,
        "zip_code": zip_codes,
        "emp_length_raw": emp_lengths,
        "loan_title": loan_titles,
        "policy_code": policy_codes
    })
    
    # Audit for flagged/invalid amounts
    invalid_mask = clean_rejected_df["amount_requested"] <= 0
    if invalid_mask.any():
        for _, inv_row in clean_rejected_df[invalid_mask].iterrows():
            invalid_records.append({
                "source_row_num": int(inv_row["source_row_num"]),
                "reason": "Non-positive amount requested",
                "amount_requested": float(inv_row["amount_requested"])
            })
            
    return clean_rejected_df, invalid_records

