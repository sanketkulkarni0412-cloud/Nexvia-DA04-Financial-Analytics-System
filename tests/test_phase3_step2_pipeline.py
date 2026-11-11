"""
Automated Test Suite for Phase 3 Step 2: Pipeline, Ingestion & Resilience
Financial Analytics and Risk Reporting System (DA-04)

Tests:
1. Cleaning transformations (dates, employment, term, grade mapping)
2. Credit default & delinquency tier classification
3. Footer filtering logic
4. Batch insertion & referential integrity
5. Checkpoint & resume persistence
6. Transaction rollback on failure
7. Idempotent re-execution (deduplication)
8. Financial reconciliation assertion engine
"""

import os
import sys
import sqlite3
import pandas as pd
import pytest
from sqlalchemy import create_engine, text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data_cleaning.clean_pipeline import (
    parse_date_to_key,
    parse_employment_years,
    classify_loan_status,
    filter_non_loan_rows,
    clean_accepted_chunk,
    clean_rejected_chunk
)
from sql.load_warehouse import (
    init_database,
    seed_reference_dimensions,
    insert_accepted_batch,
    insert_rejected_batch,
    get_checkpoint,
    record_checkpoint,
    reconcile_warehouse,
    reconcile_rejected_warehouse,
    audit_and_log_ignored,
    IGNORED_LOG_PATH,
    SUBGRADE_TO_KEY
)

SQLITE_SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema_sqlite.sql")


@pytest.fixture
def memory_db():
    """Provides an isolated, seeded SQLite in-memory database."""
    conn = sqlite3.connect(":memory:")
    with open(SQLITE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    
    # Wrap in SQLAlchemy engine for loader compatibility
    engine = create_engine("sqlite://", creator=lambda: conn)
    seed_reference_dimensions(engine)
    return engine, conn


def test_cleaning_transformations():
    """Tests date, employment, and term transformations."""
    # Date parsing
    assert parse_date_to_key("Dec-2015") == 20151201
    assert parse_date_to_key("2016-12-31") == 20161231
    assert parse_date_to_key("Nov-15") == 20151101
    assert parse_date_to_key(None) == 19000101
    assert parse_date_to_key("") == 19000101

    # Employment years parsing
    assert parse_employment_years("< 1 year") == 0
    assert parse_employment_years("1 year") == 1
    assert parse_employment_years("5 years") == 5
    assert parse_employment_years("10+ years") == 10
    assert parse_employment_years("n/a") is None
    assert parse_employment_years(None) is None


def test_default_classification():
    """Tests exact loan status to default and delinquency tier mapping."""
    # Closed Good
    d_flag, tier, closed = classify_loan_status("Fully Paid")
    assert (d_flag, tier, closed) == (0, "Closed Good", 1)

    # Closed Default
    d_flag, tier, closed = classify_loan_status("Charged Off")
    assert (d_flag, tier, closed) == (1, "Closed Default", 1)

    d_flag, tier, closed = classify_loan_status("Default")
    assert (d_flag, tier, closed) == (1, "Closed Default", 1)

    # Current
    d_flag, tier, closed = classify_loan_status("Current")
    assert (d_flag, tier, closed) == (None, "Current", 0)

    # Severe Late (31-120 days) - Must be distinct from default
    d_flag, tier, closed = classify_loan_status("Late (31-120 days)")
    assert (d_flag, tier, closed) == (None, "Severe Late (31-120)", 0)

    # Grace Period & Early Late
    d_flag, tier, closed = classify_loan_status("In Grace Period")
    assert (d_flag, tier, closed) == (None, "Grace Period", 0)

    d_flag, tier, closed = classify_loan_status("Late (16-30 days)")
    assert (d_flag, tier, closed) == (None, "Late (16-30)", 0)


def test_footer_filtering():
    """Tests filtering of partition footers and section headers."""
    sample_df = pd.DataFrame([
        {"id": "50001", "loan_amnt": 10000.0, "term": " 36 months"},
        {"id": "Total amount funded in policy code 1: 1465324575", "loan_amnt": None, "term": None},
        {"id": "Loans that do not meet the credit policy", "loan_amnt": None, "term": None},
        {"id": "50002", "loan_amnt": 20000.0, "term": " 60 months"}
    ])
    clean_df, excluded = filter_non_loan_rows(sample_df)
    assert len(clean_df) == 2
    assert len(excluded) == 2
    assert list(clean_df["id"]) == ["50001", "50002"]


def test_batch_insertion_and_referential_integrity(memory_db):
    """Tests insertion of valid loan and borrower profile with foreign keys."""
    engine, _ = memory_db
    
    mock_chunk = pd.DataFrame([{
        "id": "99001",
        "loan_amnt": 12000.0,
        "funded_amnt": 12000.0,
        "funded_amnt_inv": 12000.0,
        "term": " 36 months",
        "int_rate": 10.5,
        "installment": 390.0,
        "grade": "B",
        "sub_grade": "B2",
        "emp_length": "5 years",
        "home_ownership": "MORTGAGE",
        "annual_inc": 75000.0,
        "verification_status": "Verified",
        "issue_d": "Dec-2015",
        "loan_status": "Fully Paid",
        "addr_state": "CA",
        "dti": 15.2,
        "fico_range_low": 700,
        "fico_range_high": 704,
        "open_acc": 10,
        "pub_rec": 0,
        "revol_bal": 12000.0,
        "revol_util": 45.0,
        "total_acc": 20,
        "total_pymnt": 13500.0,
        "total_rec_prncp": 12000.0,
        "total_rec_int": 1500.0,
        "total_rec_late_fee": 0.0,
        "recoveries": 0.0,
        "collection_recovery_fee": 0.0,
        "last_pymnt_amnt": 390.0,
        "policy_code": 1
    }])
    
    fact_df, profile_df, _ = clean_accepted_chunk(mock_chunk, SUBGRADE_TO_KEY)
    
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        insert_accepted_batch(conn, fact_df, profile_df)
        
    with engine.connect() as conn:
        fact_rows = conn.execute(text("SELECT COUNT(*) FROM fact_accepted_loans;")).scalar()
        profile_rows = conn.execute(text("SELECT COUNT(*) FROM dim_borrower_credit_profile;")).scalar()
        
    assert fact_rows == 1
    assert profile_rows == 1


def test_checkpoint_handling(memory_db):
    """Tests saving and retrieving ETL ingestion checkpoints."""
    engine, _ = memory_db
    
    # Initial state
    last_idx, rows = get_checkpoint(engine, "test_pipeline")
    assert last_idx == -1
    assert rows == 0
    
    # Record checkpoint
    record_checkpoint(engine, "test_pipeline", chunk_idx=3, rows_total=300000, status="IN_PROGRESS")
    last_idx, rows = get_checkpoint(engine, "test_pipeline")
    assert last_idx == 3
    assert rows == 300000
    
    # Update checkpoint to complete
    record_checkpoint(engine, "test_pipeline", chunk_idx=5, rows_total=500000, status="COMPLETED")
    last_idx, rows = get_checkpoint(engine, "test_pipeline")
    assert last_idx == 5
    assert rows == 500000


def test_transaction_rollback_on_failure(memory_db):
    """Tests that an exception during batch processing rolls back the entire transaction."""
    engine, _ = memory_db
    
    # Clean initial state
    with engine.connect() as conn:
        initial_count = conn.execute(text("SELECT COUNT(*) FROM fact_accepted_loans;")).scalar()
    assert initial_count == 0
    
    # Attempt an insert wrapped in an engine.begin() block that deliberately fails midway
    try:
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON;"))
            
            # Step 1: Insert valid profile
            conn.execute(text("""
                INSERT INTO dim_borrower_credit_profile (loan_id, annual_inc)
                VALUES ('FAIL_TEST_LOAN', 50000.0);
            """))
            
            # Step 2: Deliberate failure (invalid foreign key to dim_geography)
            conn.execute(text("""
                INSERT INTO fact_accepted_loans (
                    loan_id, issue_date_key, grade_key, state_code,
                    loan_amnt, funded_amnt, funded_amnt_inv, term_months,
                    int_rate, installment, loan_status, delinquency_tier, is_seasoned_closed
                ) VALUES (
                    'FAIL_TEST_LOAN', 20151201, 1, 'NON_EXISTENT_STATE_XYZ',
                    10000.0, 10000.0, 10000.0, 36,
                    10.0, 300.0, 'Current', 'Current', 0
                );
            """))
    except Exception:
        pass  # Expected rollback
        
    # Verify that the borrower profile was ALSO rolled back and not left orphaned!
    with engine.connect() as conn:
        profile_count = conn.execute(text("SELECT COUNT(*) FROM dim_borrower_credit_profile;")).scalar()
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_accepted_loans;")).scalar()
        
    assert profile_count == 0, "Transaction rollback failed: orphaned profile remained in database!"
    assert fact_count == 0, "Transaction rollback failed: partial fact row remained in database!"


def test_idempotent_reexecution(memory_db):
    """Tests that re-inserting the exact same records does not duplicate rows."""
    engine, _ = memory_db
    
    mock_chunk = pd.DataFrame([{
        "id": "88001",
        "loan_amnt": 15000.0,
        "funded_amnt": 15000.0,
        "funded_amnt_inv": 15000.0,
        "term": " 36 months",
        "int_rate": 8.5,
        "installment": 450.0,
        "grade": "A",
        "sub_grade": "A3",
        "emp_length": "10+ years",
        "home_ownership": "OWN",
        "annual_inc": 110000.0,
        "verification_status": "Not Verified",
        "issue_d": "Nov-2015",
        "loan_status": "Fully Paid",
        "addr_state": "NY",
        "dti": 12.0,
        "fico_range_low": 750,
        "fico_range_high": 754,
        "open_acc": 12,
        "pub_rec": 0,
        "revol_bal": 8000.0,
        "revol_util": 20.0,
        "total_acc": 25,
        "total_pymnt": 16000.0,
        "total_rec_prncp": 15000.0,
        "total_rec_int": 1000.0,
        "total_rec_late_fee": 0.0,
        "recoveries": 0.0,
        "collection_recovery_fee": 0.0,
        "last_pymnt_amnt": 450.0,
        "policy_code": 1
    }])
    
    fact_df, profile_df, _ = clean_accepted_chunk(mock_chunk, SUBGRADE_TO_KEY)
    
    # First execution
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        insert_accepted_batch(conn, fact_df, profile_df)
        
    # Second execution (exact duplicate)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        insert_accepted_batch(conn, fact_df, profile_df)
        
    with engine.connect() as conn:
        fact_rows = conn.execute(text("SELECT COUNT(*) FROM fact_accepted_loans;")).scalar()
        profile_rows = conn.execute(text("SELECT COUNT(*) FROM dim_borrower_credit_profile;")).scalar()
        
    assert fact_rows == 1, "Idempotency failed: duplicate loan row was inserted!"
    assert profile_rows == 1, "Idempotency failed: duplicate profile row was inserted!"


def test_financial_reconciliation(memory_db):
    """Tests the automated reconciliation logic against known baseline figures."""
    engine, _ = memory_db
    
    # Insert 1 known loan
    mock_chunk = pd.DataFrame([{
        "id": "77001",
        "loan_amnt": 20000.0,
        "funded_amnt": 20000.0,
        "funded_amnt_inv": 20000.0,
        "term": " 36 months",
        "int_rate": 12.0,
        "installment": 660.0,
        "grade": "C",
        "sub_grade": "C1",
        "emp_length": "2 years",
        "home_ownership": "RENT",
        "annual_inc": 60000.0,
        "verification_status": "Verified",
        "issue_d": "Dec-2015",
        "loan_status": "Fully Paid",
        "addr_state": "TX",
        "dti": 18.0,
        "fico_range_low": 680,
        "fico_range_high": 684,
        "open_acc": 8,
        "pub_rec": 0,
        "revol_bal": 15000.0,
        "revol_util": 50.0,
        "total_acc": 15,
        "total_pymnt": 22000.0,
        "total_rec_prncp": 20000.0,
        "total_rec_int": 2000.0,
        "total_rec_late_fee": 0.0,
        "recoveries": 0.0,
        "collection_recovery_fee": 0.0,
        "last_pymnt_amnt": 660.0,
        "policy_code": 1
    }])
    
    fact_df, profile_df, _ = clean_accepted_chunk(mock_chunk, SUBGRADE_TO_KEY)
    with engine.begin() as conn:
        insert_accepted_batch(conn, fact_df, profile_df)
        
    # Matching reconciliation -> PASS
    recon_pass = reconcile_warehouse(
        engine=engine,
        expected_rows=1,
        expected_loan_amnt=20000.0,
        expected_total_pymnt=22000.0
    )
    assert recon_pass["status"] == "PASS"
    assert recon_pass["row_count_variance"] == 0
    assert recon_pass["loan_amnt_variance"] == 0.0
    
    # Mismatched reconciliation -> FAIL
    recon_fail = reconcile_warehouse(
        engine=engine,
        expected_rows=2,  # Variance = -1
        expected_loan_amnt=40000.0,
        expected_total_pymnt=44000.0
    )
    assert recon_fail["status"] == "FAIL"
    assert recon_fail["row_count_variance"] == -1


def test_sqlite_foreign_key_pragma_enforcement(memory_db):
    """
    Verifies that foreign key enforcement is actively turned on for SQLAlchemy connections.
    Attempts to insert an orphan fact loan with a non-existent grade_key must raise an IntegrityError.
    """
    engine, _ = memory_db
    
    with engine.connect() as conn:
        fk_status = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert fk_status == 1, "PRAGMA foreign_keys must be active (= 1) on every connection."

    # Attempt to insert an orphan loan referencing a non-existent grade_key (9999)
    with pytest.raises(Exception) as exc_info:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO fact_accepted_loans (
                    loan_id, issue_date_key, grade_key, state_code,
                    loan_amnt, funded_amnt, funded_amnt_inv, term_months,
                    int_rate, installment, loan_status, is_seasoned_closed
                ) VALUES (
                    'ORPHAN_FK_TEST', 20151201, 9999, 'CA',
                    10000.0, 10000.0, 10000.0, 36,
                    10.0, 300.0, 'Fully Paid', 1
                );
            """))
    assert "FOREIGN KEY constraint failed" in str(exc_info.value) or "IntegrityError" in type(exc_info.value).__name__


def test_clean_rejected_chunk_transformation():
    """
    Tests rejected applications chunk transformations:
    - Stripping '%' from DTI ratio
    - Date string parsing to dimensional integer keys
    - Risk score NULL preservation
    - Sequential 1-indexed source_row_num generation
    - Flagging non-positive requested amounts
    """
    mock_rejected = pd.DataFrame([
        {
            "Amount Requested": "15000.0",
            "Application Date": "2016-05-18",
            "Loan Title": "Debt consolidation",
            "Risk_Score": "645.0",
            "Debt-To-Income Ratio": "18.5%",
            "Zip Code": "941xx",
            "State": "CA",
            "Employment Length": "3 years",
            "Policy Code": "0"
        },
        {
            "Amount Requested": "5000.0",
            "Application Date": "2017-11-02",
            "Loan Title": "Major purchase",
            "Risk_Score": None,  # Un-pulled risk score
            "Debt-To-Income Ratio": "0%",
            "Zip Code": "100xx",
            "State": "NY",
            "Employment Length": "< 1 year",
            "Policy Code": "0"
        },
        {
            "Amount Requested": "0.0",  # Non-positive amount
            "Application Date": "2018-01-10",
            "Loan Title": "Other",
            "Risk_Score": "580.0",
            "Debt-To-Income Ratio": "45.2%",
            "Zip Code": "750xx",
            "State": "TX",
            "Employment Length": "10+ years",
            "Policy Code": "0"
        }
    ])

    cleaned_df, flagged = clean_rejected_chunk(mock_rejected, start_row_num=501)

    assert len(cleaned_df) == 3
    # 1. Sequential source row numbers
    assert list(cleaned_df["source_row_num"]) == [501, 502, 503]

    # 2. Date key parsing
    assert cleaned_df.loc[0, "app_date_key"] == 20160518
    assert cleaned_df.loc[1, "app_date_key"] == 20171102

    # 3. DTI ratio stripping
    assert cleaned_df.loc[0, "dti_ratio"] == 18.5
    assert cleaned_df.loc[1, "dti_ratio"] == 0.0

    # 4. Risk score NULL preservation
    assert cleaned_df.loc[0, "risk_score"] == 645.0
    assert pd.isna(cleaned_df.loc[1, "risk_score"])

    # 5. Flagged rows
    assert len(flagged) == 1
    assert flagged[0]["source_row_num"] == 503
    assert flagged[0]["reason"] == "Non-positive amount requested"


def test_rejected_independent_batch_insertion(memory_db):
    """
    Confirms that rejected applications can be ingested completely independently
    into fact_rejected_applications without requiring any accepted loan data.
    """
    engine, _ = memory_db

    mock_rejected = pd.DataFrame([
        {
            "Amount Requested": "10000.0",
            "Application Date": "2015-06-20",
            "Loan Title": "credit_card",
            "Risk_Score": "680.0",
            "Debt-To-Income Ratio": "22.4%",
            "Zip Code": "900xx",
            "State": "CA",
            "Employment Length": "5 years",
            "Policy Code": "0"
        },
        {
            "Amount Requested": "25000.0",
            "Application Date": "2016-09-15",
            "Loan Title": "home_improvement",
            "Risk_Score": None,
            "Debt-To-Income Ratio": "12.0%",
            "Zip Code": "606xx",
            "State": "IL",
            "Employment Length": "10+ years",
            "Policy Code": "0"
        }
    ])

    cleaned_df, _ = clean_rejected_chunk(mock_rejected, start_row_num=1)
    
    with engine.begin() as conn:
        insert_rejected_batch(conn, cleaned_df, chunk_index=0)

    # Reconcile rejected data
    recon = reconcile_rejected_warehouse(engine=engine, expected_rows=2)
    assert recon["status"] == "PASS"
    assert recon["fact_rejected_applications_count"] == 2
    assert recon["duplicate_source_rows"] == 0
    assert recon["orphan_date_keys"] == 0
    assert recon["orphan_state_codes"] == 0
    assert recon["total_amount_requested"] == 35000.0
    assert recon["null_risk_score_count"] == 1


def test_ignored_records_and_collision_audit(memory_db):
    """
    Verifies that duplicate records are audited and logged to reports/ignored_records.log
    without being silently dropped, distinguishing LEGITIMATE_RERUN from DATA_COLLISION.
    """
    engine, _ = memory_db

    # Clean prior ignored log entries if any
    if os.path.exists(IGNORED_LOG_PATH):
        try:
            os.remove(IGNORED_LOG_PATH)
        except Exception:
            pass

    # 1. Insert initial batch
    mock_chunk_1 = pd.DataFrame([
        {
            "id": "AUDIT_101", "loan_amnt": 10000.0, "funded_amnt": 10000.0, "funded_amnt_inv": 10000.0,
            "term": " 36 months", "int_rate": 10.0, "installment": 322.0, "grade": "B", "sub_grade": "B2",
            "emp_length": "4 years", "home_ownership": "MORTGAGE", "annual_inc": 75000.0,
            "verification_status": "Verified", "issue_d": "Jan-2015", "loan_status": "Fully Paid",
            "addr_state": "NY", "dti": 15.0, "fico_range_low": 700, "fico_range_high": 704,
            "open_acc": 10, "pub_rec": 0, "revol_bal": 12000.0, "revol_util": 40.0, "total_acc": 20,
            "total_pymnt": 11500.0, "total_rec_prncp": 10000.0, "total_rec_int": 1500.0,
            "total_rec_late_fee": 0.0, "recoveries": 0.0, "collection_recovery_fee": 0.0,
            "last_pymnt_amnt": 322.0, "policy_code": 1
        }
    ])
    fact_df_1, profile_df_1, _ = clean_accepted_chunk(mock_chunk_1, SUBGRADE_TO_KEY)
    with engine.begin() as conn:
        insert_accepted_batch(conn, fact_df_1, profile_df_1, chunk_index=1)

    # 2. Re-insert identical batch (Simulating idempotent re-run)
    with engine.begin() as conn:
        insert_accepted_batch(conn, fact_df_1, profile_df_1, chunk_index=1)

    # 3. Insert batch with intra-chunk duplicate and 1 collision + 1 new
    mock_chunk_2 = pd.DataFrame([
        {
            "id": "AUDIT_101",  # Existing collision
            "loan_amnt": 10000.0, "funded_amnt": 10000.0, "funded_amnt_inv": 10000.0,
            "term": " 36 months", "int_rate": 10.0, "installment": 322.0, "grade": "B", "sub_grade": "B2",
            "emp_length": "4 years", "home_ownership": "MORTGAGE", "annual_inc": 75000.0,
            "verification_status": "Verified", "issue_d": "Jan-2015", "loan_status": "Fully Paid",
            "addr_state": "NY", "dti": 15.0, "fico_range_low": 700, "fico_range_high": 704,
            "open_acc": 10, "pub_rec": 0, "revol_bal": 12000.0, "revol_util": 40.0, "total_acc": 20,
            "total_pymnt": 11500.0, "total_rec_prncp": 10000.0, "total_rec_int": 1500.0,
            "total_rec_late_fee": 0.0, "recoveries": 0.0, "collection_recovery_fee": 0.0,
            "last_pymnt_amnt": 322.0, "policy_code": 1
        },
        {
            "id": "AUDIT_102",  # New record
            "loan_amnt": 15000.0, "funded_amnt": 15000.0, "funded_amnt_inv": 15000.0,
            "term": " 36 months", "int_rate": 8.5, "installment": 473.0, "grade": "A", "sub_grade": "A4",
            "emp_length": "7 years", "home_ownership": "OWN", "annual_inc": 90000.0,
            "verification_status": "Source Verified", "issue_d": "Mar-2016", "loan_status": "Current",
            "addr_state": "TX", "dti": 12.0, "fico_range_low": 750, "fico_range_high": 754,
            "open_acc": 12, "pub_rec": 0, "revol_bal": 8000.0, "revol_util": 25.0, "total_acc": 18,
            "total_pymnt": 5000.0, "total_rec_prncp": 4000.0, "total_rec_int": 1000.0,
            "total_rec_late_fee": 0.0, "recoveries": 0.0, "collection_recovery_fee": 0.0,
            "last_pymnt_amnt": 473.0, "policy_code": 1
        },
        {
            "id": "AUDIT_102",  # In-chunk duplicate of AUDIT_102
            "loan_amnt": 15000.0, "funded_amnt": 15000.0, "funded_amnt_inv": 15000.0,
            "term": " 36 months", "int_rate": 8.5, "installment": 473.0, "grade": "A", "sub_grade": "A4",
            "emp_length": "7 years", "home_ownership": "OWN", "annual_inc": 90000.0,
            "verification_status": "Source Verified", "issue_d": "Mar-2016", "loan_status": "Current",
            "addr_state": "TX", "dti": 12.0, "fico_range_low": 750, "fico_range_high": 754,
            "open_acc": 12, "pub_rec": 0, "revol_bal": 8000.0, "revol_util": 25.0, "total_acc": 18,
            "total_pymnt": 5000.0, "total_rec_prncp": 4000.0, "total_rec_int": 1000.0,
            "total_rec_late_fee": 0.0, "recoveries": 0.0, "collection_recovery_fee": 0.0,
            "last_pymnt_amnt": 473.0, "policy_code": 1
        }
    ])
    fact_df_2, profile_df_2, _ = clean_accepted_chunk(mock_chunk_2, SUBGRADE_TO_KEY)
    with engine.begin() as conn:
        insert_accepted_batch(conn, fact_df_2, profile_df_2, chunk_index=2)

    # 4. Verify ignored_records.log contents
    assert os.path.exists(IGNORED_LOG_PATH), "ignored_records.log must be created."
    with open(IGNORED_LOG_PATH, "r", encoding="utf-8") as f:
        log_content = f.read()

    assert "LEGITIMATE_RERUN" in log_content, "Must log LEGITIMATE_RERUN for identical re-execution."
    assert "INTRA_CHUNK_DUPLICATE" in log_content, "Must log INTRA_CHUNK_DUPLICATE for in-chunk duplicate."
    assert "DATA_COLLISION" in log_content, "Must log DATA_COLLISION for partial key overlap."
    assert "AUDIT_101" in log_content, "Colliding loan_id AUDIT_101 must be explicitly recorded."

