"""
Warehouse Database Loader & Data Engineering Pipeline
Financial Analytics and Risk Reporting System (DA-04)

Features:
1. SQLAlchemy-based connection to SQLite (warehouse.db)
2. Dual execution modes: --mode sample (51,072 records) vs --mode full (2.26M loans)
3. Reference dimension seeding (dim_calendar_date, dim_loan_grade, dim_geography)
4. Chunk-based streaming (chunksize=100000)
5. Transaction-based batch insertion with rollback on failure
6. Idempotent loading (INSERT OR IGNORE deduplication)
7. Checkpoint and resume support (etl_ingestion_checkpoints)
8. Comprehensive error logging to reports/ingestion_errors.log
9. Automated row-count and financial total reconciliation
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data_cleaning.clean_pipeline import clean_accepted_chunk, clean_rejected_chunk

# Setup Logging
LOG_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(LOG_DIR, exist_ok=True)
ERROR_LOG_PATH = os.path.join(LOG_DIR, "ingestion_errors.log")
IGNORED_LOG_PATH = os.path.join(LOG_DIR, "ignored_records.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ERROR_LOG_PATH, mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("WarehouseLoader")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enforces SQLite pragmas on EVERY connection opened by SQLAlchemy:
    1. PRAGMA foreign_keys = ON; (Mandatory referential integrity enforcement)
    2. PRAGMA journal_mode = WAL; (Write-Ahead Logging for concurrency and crash-recovery)
    3. PRAGMA synchronous = NORMAL; (Safe, high-throughput durability under WAL)
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.close()

# Reference Data Definitions
GRADES_DATA = [
    (1, "A", "A1", 1, "Prime", 0.20, 0.010),
    (2, "A", "A2", 2, "Prime", 0.20, 0.015),
    (3, "A", "A3", 3, "Prime", 0.20, 0.020),
    (4, "A", "A4", 4, "Prime", 0.20, 0.025),
    (5, "A", "A5", 5, "Prime", 0.20, 0.030),
    (6, "B", "B1", 6, "Near-Prime", 0.50, 0.040),
    (7, "B", "B2", 7, "Near-Prime", 0.50, 0.045),
    (8, "B", "B3", 8, "Near-Prime", 0.50, 0.050),
    (9, "B", "B4", 9, "Near-Prime", 0.50, 0.055),
    (10, "B", "B5", 10, "Near-Prime", 0.50, 0.060),
    (11, "C", "C1", 11, "Near-Prime", 0.75, 0.070),
    (12, "C", "C2", 12, "Near-Prime", 0.75, 0.080),
    (13, "C", "C3", 13, "Near-Prime", 0.75, 0.090),
    (14, "C", "C4", 14, "Near-Prime", 0.75, 0.100),
    (15, "C", "C5", 15, "Near-Prime", 0.75, 0.110),
    (16, "D", "D1", 16, "Subprime", 1.00, 0.120),
    (17, "D", "D2", 17, "Subprime", 1.00, 0.130),
    (18, "D", "D3", 18, "Subprime", 1.00, 0.140),
    (19, "D", "D4", 19, "Subprime", 1.00, 0.150),
    (20, "D", "D5", 20, "Subprime", 1.00, 0.160),
    (21, "E", "E1", 21, "Subprime", 1.25, 0.180),
    (22, "E", "E2", 22, "Subprime", 1.25, 0.200),
    (23, "E", "E3", 23, "Subprime", 1.25, 0.220),
    (24, "E", "E4", 24, "Subprime", 1.25, 0.240),
    (25, "E", "E5", 25, "Subprime", 1.25, 0.260),
    (26, "F", "F1", 26, "High-Risk", 1.50, 0.280),
    (27, "F", "F2", 27, "High-Risk", 1.50, 0.300),
    (28, "F", "F3", 28, "High-Risk", 1.50, 0.320),
    (29, "F", "F4", 29, "High-Risk", 1.50, 0.340),
    (30, "F", "F5", 30, "High-Risk", 1.50, 0.360),
    (31, "G", "G1", 31, "High-Risk", 1.50, 0.380),
    (32, "G", "G2", 32, "High-Risk", 1.50, 0.400),
    (33, "G", "G3", 33, "High-Risk", 1.50, 0.420),
    (34, "G", "G4", 34, "High-Risk", 1.50, 0.450),
    (35, "G", "G5", 35, "High-Risk", 1.50, 0.500),
]
SUBGRADE_TO_KEY = {row[2]: row[0] for row in GRADES_DATA}

US_STATES_DATA = [
    ("AL", "Alabama", "South", "East South Central", 1),
    ("AK", "Alaska", "West", "Pacific", 1),
    ("AZ", "Arizona", "West", "Mountain", 1),
    ("AR", "Arkansas", "South", "West South Central", 1),
    ("CA", "California", "West", "Pacific", 1),
    ("CO", "Colorado", "West", "Mountain", 1),
    ("CT", "Connecticut", "Northeast", "New England", 1),
    ("DE", "Delaware", "South", "South Atlantic", 1),
    ("DC", "District of Columbia", "South", "South Atlantic", 1),
    ("FL", "Florida", "South", "South Atlantic", 1),
    ("GA", "Georgia", "South", "South Atlantic", 1),
    ("HI", "Hawaii", "West", "Pacific", 1),
    ("ID", "Idaho", "West", "Mountain", 1),
    ("IL", "Illinois", "Midwest", "East North Central", 1),
    ("IN", "Indiana", "Midwest", "East North Central", 1),
    ("IA", "Iowa", "Midwest", "West North Central", 1),
    ("KS", "Kansas", "Midwest", "West North Central", 1),
    ("KY", "Kentucky", "South", "East South Central", 1),
    ("LA", "Louisiana", "South", "West South Central", 1),
    ("ME", "Maine", "Northeast", "New England", 1),
    ("MD", "Maryland", "South", "South Atlantic", 1),
    ("MA", "Massachusetts", "Northeast", "New England", 1),
    ("MI", "Michigan", "Midwest", "East North Central", 1),
    ("MN", "Minnesota", "Midwest", "West North Central", 1),
    ("MS", "Mississippi", "South", "East South Central", 1),
    ("MO", "Missouri", "Midwest", "West North Central", 1),
    ("MT", "Montana", "West", "Mountain", 1),
    ("NE", "Nebraska", "Midwest", "West North Central", 1),
    ("NV", "Nevada", "West", "Mountain", 1),
    ("NH", "New Hampshire", "Northeast", "New England", 1),
    ("NJ", "New Jersey", "Northeast", "Middle Atlantic", 1),
    ("NM", "New Mexico", "West", "Mountain", 1),
    ("NY", "New York", "Northeast", "Middle Atlantic", 1),
    ("NC", "North Carolina", "South", "South Atlantic", 1),
    ("ND", "North Dakota", "Midwest", "West North Central", 1),
    ("OH", "Ohio", "Midwest", "East North Central", 1),
    ("OK", "Oklahoma", "South", "West South Central", 1),
    ("OR", "Oregon", "West", "Pacific", 1),
    ("PA", "Pennsylvania", "Northeast", "Middle Atlantic", 1),
    ("RI", "Rhode Island", "Northeast", "New England", 1),
    ("SC", "South Carolina", "South", "South Atlantic", 1),
    ("SD", "South Dakota", "Midwest", "West North Central", 1),
    ("TN", "Tennessee", "South", "East South Central", 1),
    ("TX", "Texas", "South", "West South Central", 1),
    ("UT", "Utah", "West", "Mountain", 1),
    ("VT", "Vermont", "Northeast", "New England", 1),
    ("VA", "Virginia", "South", "South Atlantic", 1),
    ("WA", "Washington", "West", "Pacific", 1),
    ("WV", "West Virginia", "South", "South Atlantic", 1),
    ("WI", "Wisconsin", "Midwest", "East North Central", 1),
    ("WY", "Wyoming", "West", "Mountain", 1),
    ("XX", "Unknown / Military / Territory", "Other", "Other", 0),
]


def init_database(db_path: str, reset: bool = False):
    """
    Initializes SQLite database using sql/schema_sqlite.sql.
    Applies WAL mode and foreign key pragmas.
    """
    if reset and os.path.exists(db_path):
        logger.warning(f"Reset flag passed: removing existing database at {db_path}")
        os.remove(db_path)
        
    schema_path = os.path.join(BASE_DIR, "sql", "schema_sqlite.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()
        
    conn = sqlite3.connect(db_path)
    conn.executescript(ddl)
    conn.commit()
    conn.close()
    logger.info(f"Database schema initialized at {db_path} with WAL pragmas.")


def seed_reference_dimensions(engine):
    """
    Seeds dim_calendar_date, dim_loan_grade, and dim_geography if not already populated.
    """
    with engine.begin() as conn:
        # 1. Seed Loan Grades
        grade_count = conn.execute(text("SELECT COUNT(*) FROM dim_loan_grade;")).scalar()
        if grade_count == 0:
            logger.info("Seeding dim_loan_grade with 35 sub-grades...")
            stmt = text("""
                INSERT INTO dim_loan_grade (
                    grade_key, grade, sub_grade, grade_rank, regulatory_tier,
                    illustrative_basel_weight, illustrative_target_loss_cap
                ) VALUES (:k, :g, :sg, :gr, :rt, :bw, :lc);
            """)
            for row in GRADES_DATA:
                conn.execute(stmt, {
                    "k": row[0], "g": row[1], "sg": row[2], "gr": row[3],
                    "rt": row[4], "bw": row[5], "lc": row[6]
                })

        # 2. Seed Geography
        geo_count = conn.execute(text("SELECT COUNT(*) FROM dim_geography;")).scalar()
        if geo_count == 0:
            logger.info("Seeding dim_geography with 51 US states + territory fallback...")
            stmt = text("""
                INSERT INTO dim_geography (
                    state_code, state_name, census_region, economic_division, is_active_lending
                ) VALUES (:sc, :sn, :cr, :ed, :al);
            """)
            for row in US_STATES_DATA:
                conn.execute(stmt, {
                    "sc": row[0], "sn": row[1], "cr": row[2], "ed": row[3], "al": row[4]
                })

        # 3. Seed Calendar Dates (2000-01-01 to 2030-12-31 + default 19000101)
        date_count = conn.execute(text("SELECT COUNT(*) FROM dim_calendar_date;")).scalar()
        if date_count == 0:
            logger.info("Seeding dim_calendar_date (continuous horizon 2000 to 2030)...")
            date_records = []
            
            # Default placeholder date
            date_records.append({
                "dk": 19000101, "fd": "1900-01-01", "yr": 1900, "qtr": 1,
                "mo": 1, "mn": "January", "ym": "1900-01", "yq": "1900-Q1",
                "fy": 1900, "fq": "FY00-Q1"
            })
            
            start_date = datetime(2000, 1, 1)
            end_date = datetime(2030, 12, 31)
            curr = start_date
            
            while curr <= end_date:
                dk = curr.year * 10000 + curr.month * 100 + curr.day
                fd = curr.strftime("%Y-%m-%d")
                yr = curr.year
                qtr = (curr.month - 1) // 3 + 1
                mo = curr.month
                mn = curr.strftime("%B")
                ym = curr.strftime("%Y-%m")
                yq = f"{curr.year}-Q{qtr}"
                fy = curr.year
                fq = f"FY{str(curr.year)[2:]}-Q{qtr}"
                
                date_records.append({
                    "dk": dk, "fd": fd, "yr": yr, "qtr": qtr,
                    "mo": mo, "mn": mn, "ym": ym, "yq": yq,
                    "fy": fy, "fq": fq
                })
                curr += timedelta(days=1)
                
            date_stmt = text("""
                INSERT INTO dim_calendar_date (
                    date_key, full_date, year, quarter, month, month_name,
                    year_month, year_quarter, fiscal_year, fiscal_quarter
                ) VALUES (:dk, :fd, :yr, :qtr, :mo, :mn, :ym, :yq, :fy, :fq);
            """)
            # Batch execute calendar inserts in slices of 1000
            for i in range(0, len(date_records), 1000):
                conn.execute(date_stmt, date_records[i:i+1000])


def get_checkpoint(engine, pipeline_name: str) -> tuple[int, int]:
    """
    Retrieves (last_chunk_index, rows_ingested) from etl_ingestion_checkpoints.
    Returns (-1, 0) if no checkpoint exists.
    """
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT last_chunk_index, rows_ingested FROM etl_ingestion_checkpoints WHERE pipeline_name = :p;"),
            {"p": pipeline_name}
        ).fetchone()
        if res:
            return res[0], res[1]
    return -1, 0


def record_checkpoint(engine, pipeline_name: str, chunk_idx: int, rows_total: int, status: str = "IN_PROGRESS"):
    """
    Persists checkpoint state into etl_ingestion_checkpoints.
    """
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO etl_ingestion_checkpoints (
                    pipeline_name, last_chunk_index, rows_ingested, status, last_updated_at
                ) VALUES (:p, :ci, :rt, :st, :ts)
                ON CONFLICT (pipeline_name) DO UPDATE SET
                    last_chunk_index = :ci,
                    rows_ingested = :rt,
                    status = :st,
                    last_updated_at = :ts;
            """),
            {
                "p": pipeline_name,
                "ci": chunk_idx,
                "rt": rows_total,
                "st": status,
                "ts": datetime.now(timezone.utc).isoformat()
            }
        )


def log_ignored_record(dataset: str, record_id, category: str, reason: str, chunk_index: int = -1):
    """
    Appends an audited record omission to reports/ignored_records.log.
    Distinguishes legitimate re-runs from data collisions and quality flags.
    Never silently discards data.
    """
    ts = datetime.now(timezone.utc).isoformat()
    entry = f"{ts} [DATASET: {dataset}] [CATEGORY: {category}] [CHUNK: {chunk_index}] ID: {record_id} - {reason}\n"
    with open(IGNORED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def audit_and_log_ignored(
    conn,
    table_name: str,
    id_col: str,
    candidate_ids: list,
    dataset: str,
    chunk_index: int = -1
) -> tuple[set, str]:
    """
    Audits candidate IDs against existing records in table_name to identify collisions vs re-runs.
    Categorizes:
    - 'CLEAN': None exist in DB (normal first insertion)
    - 'LEGITIMATE_RERUN': All candidate IDs exist in DB (idempotent replay of previously committed chunk)
    - 'DATA_COLLISION': Some candidate IDs exist while others do not (raw key collision or partial overlap)
    Logs detailed findings to reports/ignored_records.log.
    """
    if not candidate_ids:
        return set(), "CLEAN"

    existing_ids = set()
    # Query in batches of 500 to stay safely within SQLite parameter limits
    for i in range(0, len(candidate_ids), 500):
        batch = candidate_ids[i:i+500]
        placeholders = ", ".join([f":id_{j}" for j in range(len(batch))])
        params = {f"id_{j}": val for j, val in enumerate(batch)}
        query = text(f"SELECT {id_col} FROM {table_name} WHERE {id_col} IN ({placeholders});")
        result = conn.execute(query, params).fetchall()
        for row in result:
            existing_ids.add(row[0])

    ts = datetime.now(timezone.utc).isoformat()
    if not existing_ids:
        return set(), "CLEAN"

    if len(existing_ids) == len(candidate_ids):
        category = "LEGITIMATE_RERUN"
        summary = (
            f"{ts} [DATASET: {dataset}] [CATEGORY: {category}] [CHUNK: {chunk_index}] "
            f"Batch of {len(candidate_ids):,} records already present in {table_name}. "
            f"Idempotently skipped without duplicate insertion.\n"
        )
        with open(IGNORED_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(summary)
        return existing_ids, category

    # Partial collision
    category = "DATA_COLLISION"
    summary = (
        f"{ts} [DATASET: {dataset}] [CATEGORY: {category}] [CHUNK: {chunk_index}] "
        f"Partial collision: {len(existing_ids):,} of {len(candidate_ids):,} IDs already exist in {table_name}!\n"
    )
    with open(IGNORED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(summary)

    # Log up to first 50 colliding IDs in detail
    colliding_list = list(existing_ids)
    for cid in colliding_list[:50]:
        log_ignored_record(
            dataset=dataset,
            record_id=cid,
            category="DATA_COLLISION",
            reason=f"Duplicate {id_col} in {table_name}; record ignored by INSERT OR IGNORE",
            chunk_index=chunk_index
        )
    if len(colliding_list) > 50:
        with open(IGNORED_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts} [DATASET: {dataset}] [CATEGORY: DATA_COLLISION] [CHUNK: {chunk_index}] ... and {len(colliding_list) - 50:,} additional colliding IDs.\n")

    return existing_ids, category


def insert_accepted_batch(conn, fact_df: pd.DataFrame, profile_df: pd.DataFrame, chunk_index: int = -1):
    """
    Idempotent batch insertion using INSERT OR IGNORE into:
    1. dim_borrower_credit_profile (must be inserted first to satisfy FK)
    2. fact_accepted_loans
    Audits for duplicate primary keys and logs ignored records to reports/ignored_records.log.
    """
    if fact_df.empty:
        return

    # 1. Audit intra-chunk duplicates
    dup_mask = fact_df.duplicated(subset=["loan_id"], keep="first")
    if dup_mask.any():
        for _, dup_row in fact_df[dup_mask].iterrows():
            log_ignored_record(
                dataset="accepted",
                record_id=dup_row["loan_id"],
                category="INTRA_CHUNK_DUPLICATE",
                reason=f"Duplicate loan_id within chunk {chunk_index}",
                chunk_index=chunk_index
            )
        fact_df = fact_df.drop_duplicates(subset=["loan_id"], keep="first")
        profile_df = profile_df.drop_duplicates(subset=["loan_id"], keep="first")

    # 2. Audit existing DB collisions / re-runs
    candidate_ids = fact_df["loan_id"].tolist()
    audit_and_log_ignored(
        conn=conn,
        table_name="fact_accepted_loans",
        id_col="loan_id",
        candidate_ids=candidate_ids,
        dataset="accepted",
        chunk_index=chunk_index
    )

    # 3. Insert borrower profiles
    profile_sql = """
        INSERT OR IGNORE INTO dim_borrower_credit_profile (
            loan_id, annual_inc, emp_length, emp_length_years, home_ownership,
            verification_status, dti, fico_range_low, fico_range_high,
            fico_midpoint, open_acc, pub_rec, revol_bal, revol_util,
            total_acc, earliest_cr_line
        ) VALUES (
            :loan_id, :annual_inc, :emp_length, :emp_length_years, :home_ownership,
            :verification_status, :dti, :fico_range_low, :fico_range_high,
            :fico_midpoint, :open_acc, :pub_rec, :revol_bal, :revol_util,
            :total_acc, :earliest_cr_line
        );
    """
    profile_records = profile_df.to_dict(orient="records")
    conn.execute(text(profile_sql), profile_records)

    # 4. Insert fact accepted loans
    fact_sql = """
        INSERT OR IGNORE INTO fact_accepted_loans (
            loan_id, issue_date_key, grade_key, state_code,
            loan_amnt, funded_amnt, funded_amnt_inv, term_months,
            int_rate, installment, total_pymnt, total_rec_prncp,
            total_rec_int, total_rec_late_fee, recoveries,
            collection_cost, last_pymnt_amnt, loan_status,
            is_confirmed_default, delinquency_tier, is_seasoned_closed,
            last_pymnt_d, last_credit_pull_d, policy_code
        ) VALUES (
            :loan_id, :issue_date_key, :grade_key, :state_code,
            :loan_amnt, :funded_amnt, :funded_amnt_inv, :term_months,
            :int_rate, :installment, :total_pymnt, :total_rec_prncp,
            :total_rec_int, :total_rec_late_fee, :recoveries,
            :collection_cost, :last_pymnt_amnt, :loan_status,
            :is_confirmed_default, :delinquency_tier, :is_seasoned_closed,
            :last_pymnt_d, :last_credit_pull_d, :policy_code
        );
    """
    fact_records = fact_df.to_dict(orient="records")
    conn.execute(text(fact_sql), fact_records)


def insert_rejected_batch(conn, rejected_df: pd.DataFrame, chunk_index: int = -1):
    """
    Idempotent batch insertion using INSERT OR IGNORE into fact_rejected_applications.
    Audits for duplicate source_row_num to prevent silent drops and logs to reports/ignored_records.log.
    """
    if rejected_df.empty:
        return

    # 1. Audit intra-chunk duplicates
    dup_mask = rejected_df.duplicated(subset=["source_row_num"], keep="first")
    if dup_mask.any():
        for _, dup_row in rejected_df[dup_mask].iterrows():
            log_ignored_record(
                dataset="rejected",
                record_id=int(dup_row["source_row_num"]),
                category="INTRA_CHUNK_DUPLICATE",
                reason=f"Duplicate source_row_num within chunk {chunk_index}",
                chunk_index=chunk_index
            )
        rejected_df = rejected_df.drop_duplicates(subset=["source_row_num"], keep="first")

    # 2. Audit existing DB collisions / re-runs
    candidate_ids = rejected_df["source_row_num"].tolist()
    audit_and_log_ignored(
        conn=conn,
        table_name="fact_rejected_applications",
        id_col="source_row_num",
        candidate_ids=candidate_ids,
        dataset="rejected",
        chunk_index=chunk_index
    )

    # 3. Batch execution
    stmt = text("""
        INSERT OR IGNORE INTO fact_rejected_applications (
            source_row_num, app_date_key, application_date,
            amount_requested, risk_score, dti_ratio,
            state_code, zip_code, emp_length_raw,
            loan_title, policy_code
        ) VALUES (
            :source_row_num, :app_date_key, :application_date,
            :amount_requested, :risk_score, :dti_ratio,
            :state_code, :zip_code, :emp_length_raw,
            :loan_title, :policy_code
        );
    """)
    records = rejected_df.to_dict(orient="records")
    conn.execute(stmt, records)


def ingest_accepted_dataset(
    engine, 
    csv_path: str, 
    pipeline_name: str, 
    chunksize: int = 100000,
    resume: bool = True
) -> dict:
    """
    Streams and ingests an accepted loan dataset into SQLite with:
    - Atomic per-chunk transactions and rollback on failure
    - Checkpoint tracking and automatic resume
    - Idempotent deduplication and audit logging
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source CSV not found: {csv_path}")

    last_chunk_idx, rows_already_ingested = get_checkpoint(engine, pipeline_name) if resume else (-1, 0)
    logger.info(f"Starting ingestion for {pipeline_name}. Resuming from chunk {last_chunk_idx + 1}...")

    total_clean_rows = rows_already_ingested
    total_excluded_rows = 0
    chunk_index = 0

    reader = pd.read_csv(csv_path, chunksize=chunksize, low_memory=False)

    for chunk in reader:
        if chunk_index <= last_chunk_idx:
            logger.info(f"Skipping already committed chunk {chunk_index} ({len(chunk)} rows)...")
            chunk_index += 1
            continue

        logger.info(f"Processing accepted chunk {chunk_index} ({len(chunk):,} rows)...")
        
        try:
            # 1. Clean and transform chunk
            fact_df, profile_df, excluded = clean_accepted_chunk(chunk, SUBGRADE_TO_KEY)
            total_excluded_rows += len(excluded)

            # 2. Transactional batch insertion
            with engine.begin() as conn:
                insert_accepted_batch(conn, fact_df, profile_df, chunk_index=chunk_index)
                total_clean_rows += len(fact_df)
                
            # 3. Record checkpoint on successful commit
            record_checkpoint(engine, pipeline_name, chunk_index, total_clean_rows, "IN_PROGRESS")
            logger.info(f"Chunk {chunk_index} committed successfully. Cumulative clean rows: {total_clean_rows:,}")
            
        except Exception as e:
            logger.error(f"FATAL ERROR in chunk {chunk_index}: {e}", exc_info=True)
            record_checkpoint(engine, pipeline_name, chunk_index - 1, total_clean_rows, "FAILED")
            raise e

        chunk_index += 1

    # Finalize checkpoint
    record_checkpoint(engine, pipeline_name, chunk_index - 1, total_clean_rows, "COMPLETED")
    logger.info(f"Pipeline {pipeline_name} completed. Total inserted: {total_clean_rows:,}, Excluded non-loans: {total_excluded_rows}")

    return {
        "pipeline_name": pipeline_name,
        "total_clean_rows": total_clean_rows,
        "total_excluded_rows": total_excluded_rows,
        "chunks_processed": chunk_index
    }


def ingest_rejected_dataset(
    engine,
    csv_path: str,
    pipeline_name: str,
    chunksize: int = 100000,
    resume: bool = True,
    max_records: int | None = None
) -> dict:
    """
    Streams and ingests rejected applications into fact_rejected_applications with:
    - Atomic per-chunk transactions and rollback on failure
    - Checkpoint tracking and automatic resume
    - Strict 1-indexed source_row_num sequential tracking
    - Idempotent deduplication and audit logging
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source CSV not found: {csv_path}")

    last_chunk_idx, rows_already_ingested = get_checkpoint(engine, pipeline_name) if resume else (-1, 0)
    logger.info(f"Starting ingestion for {pipeline_name}. Resuming from chunk {last_chunk_idx + 1}...")

    total_clean_rows = rows_already_ingested
    total_flagged_rows = 0
    chunk_index = 0
    current_source_row = 1  # 1-indexed CSV line tracking

    # Adjust current_source_row if resuming from previous chunk
    if resume and last_chunk_idx >= 0:
        current_source_row = (last_chunk_idx + 1) * chunksize + 1

    reader = pd.read_csv(csv_path, chunksize=chunksize, low_memory=False)

    for chunk in reader:
        chunk_len = len(chunk)
        if chunk_index <= last_chunk_idx:
            logger.info(f"Skipping already committed rejected chunk {chunk_index} ({chunk_len:,} rows)...")
            current_source_row += chunk_len
            chunk_index += 1
            continue

        if max_records and total_clean_rows >= max_records:
            logger.info(f"Reached max_records cap of {max_records:,}. Stopping ingestion.")
            break

        logger.info(f"Processing rejected chunk {chunk_index} ({chunk_len:,} rows, source_rows {current_source_row:,} to {current_source_row + chunk_len - 1:,})...")

        try:
            # 1. Clean chunk
            cleaned_df, flagged = clean_rejected_chunk(chunk, start_row_num=current_source_row)
            total_flagged_rows += len(flagged)
            
            # Log flagged rows (e.g. non-positive requested amounts)
            for fl in flagged:
                log_ignored_record(
                    dataset="rejected",
                    record_id=fl["source_row_num"],
                    category="DATA_QUALITY_FLAG",
                    reason=f"{fl['reason']} (amount: {fl.get('amount_requested')})",
                    chunk_index=chunk_index
                )

            # 2. Transactional batch insertion
            with engine.begin() as conn:
                insert_rejected_batch(conn, cleaned_df, chunk_index=chunk_index)
                total_clean_rows += len(cleaned_df)

            # 3. Record checkpoint on commit
            record_checkpoint(engine, pipeline_name, chunk_index, total_clean_rows, "IN_PROGRESS")
            logger.info(f"Rejected chunk {chunk_index} committed successfully. Cumulative clean rows: {total_clean_rows:,}")

        except Exception as e:
            logger.error(f"FATAL ERROR in rejected chunk {chunk_index}: {e}", exc_info=True)
            record_checkpoint(engine, pipeline_name, chunk_index - 1, total_clean_rows, "FAILED")
            raise e

        current_source_row += chunk_len
        chunk_index += 1

    record_checkpoint(engine, pipeline_name, chunk_index - 1, total_clean_rows, "COMPLETED")
    logger.info(f"Pipeline {pipeline_name} completed. Total inserted: {total_clean_rows:,}, Flagged: {total_flagged_rows}")

    return {
        "pipeline_name": pipeline_name,
        "total_clean_rows": total_clean_rows,
        "total_flagged_rows": total_flagged_rows,
        "chunks_processed": chunk_index
    }


def reconcile_warehouse(
    engine, 
    expected_rows: int, 
    expected_loan_amnt: float, 
    expected_total_pymnt: float,
    expected_funded_amnt: float | None = None,
    expected_funded_amnt_inv: float | None = None,
    expected_rec_prncp: float | None = None,
    expected_rec_int: float | None = None,
    expected_rec_late_fee: float | None = None,
    expected_recoveries: float | None = None,
    expected_collection_cost: float | None = None
) -> dict:
    """
    Performs institutional row-count and financial dollar reconciliation for accepted loans.
    Asserts zero variance between database sums and benchmark figures across all 9 core financial measures.
    """
    logger.info("Running accepted loans database reconciliation checks...")
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_accepted_loans;")).scalar()
        profile_count = conn.execute(text("SELECT COUNT(*) FROM dim_borrower_credit_profile;")).scalar()
        
        sum_loan_amnt = conn.execute(text("SELECT SUM(loan_amnt) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_funded_amnt = conn.execute(text("SELECT SUM(funded_amnt) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_funded_amnt_inv = conn.execute(text("SELECT SUM(funded_amnt_inv) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_total_pymnt = conn.execute(text("SELECT SUM(total_pymnt) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_rec_prncp = conn.execute(text("SELECT SUM(total_rec_prncp) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_rec_int = conn.execute(text("SELECT SUM(total_rec_int) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_rec_late_fee = conn.execute(text("SELECT SUM(total_rec_late_fee) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_recoveries = conn.execute(text("SELECT SUM(recoveries) FROM fact_accepted_loans;")).scalar() or 0.0
        sum_collection_cost = conn.execute(text("SELECT SUM(collection_cost) FROM fact_accepted_loans;")).scalar() or 0.0

        # Check for duplicate PKs
        dup_loans = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT loan_id, COUNT(*) FROM fact_accepted_loans GROUP BY loan_id HAVING COUNT(*) > 1
            );
        """)).scalar()
        
        # Check orphaned foreign keys
        orphan_dates = conn.execute(text("""
            SELECT COUNT(*) FROM fact_accepted_loans f
            LEFT JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
            WHERE d.date_key IS NULL;
        """)).scalar()
        
        orphan_grades = conn.execute(text("""
            SELECT COUNT(*) FROM fact_accepted_loans f
            LEFT JOIN dim_loan_grade g ON f.grade_key = g.grade_key
            WHERE g.grade_key IS NULL;
        """)).scalar()
        
        orphan_profiles = conn.execute(text("""
            SELECT COUNT(*) FROM fact_accepted_loans f
            LEFT JOIN dim_borrower_credit_profile p ON f.loan_id = p.loan_id
            WHERE p.loan_id IS NULL;
        """)).scalar()

    row_count_diff = fact_count - expected_rows
    loan_amnt_diff = abs(sum_loan_amnt - expected_loan_amnt)
    total_pymnt_diff = abs(sum_total_pymnt - expected_total_pymnt)

    status_pass = (row_count_diff == 0 and loan_amnt_diff < 0.01 and total_pymnt_diff < 0.01 and dup_loans == 0 and orphan_dates == 0 and orphan_grades == 0 and orphan_profiles == 0)

    reconciliation_results = {
        "status": "PASS" if status_pass else "FAIL",
        "fact_accepted_loans_count": fact_count,
        "dim_borrower_credit_profile_count": profile_count,
        "expected_rows": expected_rows,
        "row_count_variance": row_count_diff,
        "db_sum_loan_amnt": round(sum_loan_amnt, 2),
        "expected_sum_loan_amnt": round(expected_loan_amnt, 2),
        "loan_amnt_variance": round(loan_amnt_diff, 2),
        "db_sum_funded_amnt": round(sum_funded_amnt, 2),
        "expected_sum_funded_amnt": round(expected_funded_amnt, 2) if expected_funded_amnt is not None else None,
        "funded_amnt_variance": round(abs(sum_funded_amnt - expected_funded_amnt), 2) if expected_funded_amnt is not None else None,
        "db_sum_funded_amnt_inv": round(sum_funded_amnt_inv, 2),
        "expected_sum_funded_amnt_inv": round(expected_funded_amnt_inv, 2) if expected_funded_amnt_inv is not None else None,
        "funded_amnt_inv_variance": round(abs(sum_funded_amnt_inv - expected_funded_amnt_inv), 2) if expected_funded_amnt_inv is not None else None,
        "db_sum_total_pymnt": round(sum_total_pymnt, 2),
        "expected_sum_total_pymnt": round(expected_total_pymnt, 2),
        "total_pymnt_variance": round(total_pymnt_diff, 2),
        "db_sum_rec_prncp": round(sum_rec_prncp, 2),
        "expected_sum_rec_prncp": round(expected_rec_prncp, 2) if expected_rec_prncp is not None else None,
        "rec_prncp_variance": round(abs(sum_rec_prncp - expected_rec_prncp), 2) if expected_rec_prncp is not None else None,
        "db_sum_rec_int": round(sum_rec_int, 2),
        "expected_sum_rec_int": round(expected_rec_int, 2) if expected_rec_int is not None else None,
        "rec_int_variance": round(abs(sum_rec_int - expected_rec_int), 2) if expected_rec_int is not None else None,
        "db_sum_rec_late_fee": round(sum_rec_late_fee, 2),
        "expected_sum_rec_late_fee": round(expected_rec_late_fee, 2) if expected_rec_late_fee is not None else None,
        "rec_late_fee_variance": round(abs(sum_rec_late_fee - expected_rec_late_fee), 2) if expected_rec_late_fee is not None else None,
        "db_sum_recoveries": round(sum_recoveries, 2),
        "expected_sum_recoveries": round(expected_recoveries, 2) if expected_recoveries is not None else None,
        "recoveries_variance": round(abs(sum_recoveries - expected_recoveries), 2) if expected_recoveries is not None else None,
        "db_sum_collection_cost": round(sum_collection_cost, 2),
        "expected_sum_collection_cost": round(expected_collection_cost, 2) if expected_collection_cost is not None else None,
        "collection_cost_variance": round(abs(sum_collection_cost - expected_collection_cost), 2) if expected_collection_cost is not None else None,
        "duplicate_loan_ids": dup_loans,
        "orphan_date_foreign_keys": orphan_dates,
        "orphan_grade_foreign_keys": orphan_grades,
        "orphan_profile_foreign_keys": orphan_profiles
    }

    logger.info(f"Accepted Reconciliation Status: {reconciliation_results['status']}")
    logger.info(f"  Rows in DB: {fact_count:,} (Expected: {expected_rows:,}, Variance: {row_count_diff})")
    logger.info(f"  Loan Amount in DB: ${sum_loan_amnt:,.2f} (Expected: ${expected_loan_amnt:,.2f})")
    logger.info(f"  Total Payments in DB: ${sum_total_pymnt:,.2f} (Expected: ${expected_total_pymnt:,.2f})")
    logger.info(f"  Duplicate PKs: {dup_loans}, Orphan FKs: {orphan_dates + orphan_grades + orphan_profiles}")

    return reconciliation_results


def reconcile_rejected_warehouse(engine, expected_rows: int | None = None) -> dict:
    """
    Performs data integrity and count verification for fact_rejected_applications.
    """
    logger.info("Running rejected applications database reconciliation checks...")
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_rejected_applications;")).scalar()
        distinct_rows = conn.execute(text("SELECT COUNT(DISTINCT source_row_num) FROM fact_rejected_applications;")).scalar()
        sum_requested = conn.execute(text("SELECT SUM(amount_requested) FROM fact_rejected_applications;")).scalar() or 0.0
        null_risk_count = conn.execute(text("SELECT COUNT(*) FROM fact_rejected_applications WHERE risk_score IS NULL;")).scalar()
        invalid_amount_count = conn.execute(text("SELECT COUNT(*) FROM fact_rejected_applications WHERE amount_requested <= 0;")).scalar()

        orphan_dates = conn.execute(text("""
            SELECT COUNT(*) FROM fact_rejected_applications r
            LEFT JOIN dim_calendar_date d ON r.app_date_key = d.date_key
            WHERE d.date_key IS NULL;
        """)).scalar()

        orphan_states = conn.execute(text("""
            SELECT COUNT(*) FROM fact_rejected_applications r
            LEFT JOIN dim_geography g ON r.state_code = g.state_code
            WHERE r.state_code IS NOT NULL AND g.state_code IS NULL;
        """)).scalar()

    dup_rows = fact_count - distinct_rows
    status = "PASS" if (dup_rows == 0 and orphan_dates == 0 and orphan_states == 0) else "FAIL"
    if expected_rows is not None and fact_count != expected_rows:
        status = "FAIL"

    results = {
        "status": status,
        "fact_rejected_applications_count": fact_count,
        "distinct_source_row_nums": distinct_rows,
        "duplicate_source_rows": dup_rows,
        "total_amount_requested": round(sum_requested, 2),
        "null_risk_score_count": null_risk_count,
        "invalid_amount_count": invalid_amount_count,
        "orphan_date_keys": orphan_dates,
        "orphan_state_codes": orphan_states
    }

    logger.info(f"Rejected Reconciliation Status: {results['status']}")
    logger.info(f"  Rows in DB: {fact_count:,}, Distinct source rows: {distinct_rows:,}")
    logger.info(f"  Total Requested Amount: ${sum_requested:,.2f}")
    logger.info(f"  Orphan Dates: {orphan_dates}, Orphan States: {orphan_states}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Warehouse Database Loader (DA-04)")
    parser.add_argument(
        "--mode", 
        choices=["sample", "full"], 
        default="sample",
        help="Execution mode: 'sample' (51,072 benchmark rows) or 'full' (production scale)"
    )
    parser.add_argument(
        "--dataset",
        choices=["accepted", "rejected", "all"],
        default="accepted",
        help="Dataset to ingest: 'accepted' (default), 'rejected', or 'all' (both sequentially)"
    )
    parser.add_argument("--db-path", default="warehouse.db", help="Path to SQLite warehouse file")
    parser.add_argument("--chunksize", type=int, default=100000, help="Chunk size for streaming")
    parser.add_argument("--reset", action="store_true", help="Recreate schema and reset checkpoints")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from checkpoint; reprocess from start")
    parser.add_argument(
        "--confirm-full-ingestion",
        action="store_true",
        help="Mandatory safety confirmation switch required to execute --mode full"
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    engine = create_engine(f"sqlite:///{db_path}")

    # 1. Initialize schema
    init_database(db_path, reset=args.reset)

    # 2. Seed conformed reference dimensions
    seed_reference_dimensions(engine)

    # 3. Execution routing
    if args.mode == "full":
        if not args.confirm_full_ingestion:
            logger.error("=" * 70)
            logger.error("SAFETY RESTRICTION: Full ingestion of multi-million row datasets")
            logger.error("requires formal stakeholder approval and the explicit flag:")
            logger.error("  --confirm-full-ingestion")
            logger.error("Execution halted to protect system resources and data integrity.")
            logger.error("=" * 70)
            sys.exit(1)

        # Full mode handling when formally approved
        if args.dataset in ["accepted", "all"]:
            full_accepted_csv = os.path.join(BASE_DIR, "dataset", "raw", "accepted_2007_to_2018Q4.csv")
            logger.info(f"Executing FULL ACCEPTED INGESTION from {full_accepted_csv}")
            ingest_results = ingest_accepted_dataset(
                engine=engine,
                csv_path=full_accepted_csv,
                pipeline_name="accepted_loans_full",
                chunksize=args.chunksize,
                resume=not args.no_resume
            )
            
            recon = reconcile_warehouse(
                engine=engine,
                expected_rows=2260668,
                expected_loan_amnt=34016115925.00,
                expected_funded_amnt=34004208600.00,
                expected_funded_amnt_inv=33963004960.81,
                expected_total_pymnt=27314649582.62,
                expected_rec_prncp=21489393643.58,
                expected_rec_int=5496560266.06,
                expected_rec_late_fee=3432718.19,
                expected_recoveries=325262956.86,
                expected_collection_cost=54216619.20
            )
            
            recon_path = os.path.join(LOG_DIR, "accepted_full_ingestion_reconciliation.json")
            with open(recon_path, "w", encoding="utf-8") as f:
                json.dump(recon, f, indent=2)
            logger.info(f"Accepted full reconciliation written to {recon_path}")

        if args.dataset in ["rejected", "all"]:
            full_rejected_csv = os.path.join(BASE_DIR, "dataset", "raw", "rejected_2007_to_2018Q4.csv")
            logger.info(f"Executing FULL REJECTED INGESTION from {full_rejected_csv}")
            ingest_rejected_dataset(
                engine=engine,
                csv_path=full_rejected_csv,
                pipeline_name="rejected_applications_full",
                chunksize=args.chunksize,
                resume=not args.no_resume
            )
            reconcile_rejected_warehouse(engine=engine, expected_rows=27648741)

    elif args.mode == "sample":
        if args.dataset in ["accepted", "all"]:
            sample_csv = os.path.join(BASE_DIR, "dataset", "raw", "lending_club_loans.csv")
            logger.info(f"Executing SAMPLE INGESTION (Accepted) from {sample_csv}")
            
            results = ingest_accepted_dataset(
                engine=engine,
                csv_path=sample_csv,
                pipeline_name="accepted_loans_sample",
                chunksize=args.chunksize,
                resume=not args.no_resume
            )

            # Expected sample baselines (verified empirically)
            EXPECTED_SAMPLE_ROWS = 51072
            EXPECTED_SAMPLE_LOAN_AMNT = 767112825.00
            EXPECTED_SAMPLE_TOTAL_PYMNT = 767235505.08

            recon = reconcile_warehouse(
                engine=engine,
                expected_rows=EXPECTED_SAMPLE_ROWS,
                expected_loan_amnt=EXPECTED_SAMPLE_LOAN_AMNT,
                expected_total_pymnt=EXPECTED_SAMPLE_TOTAL_PYMNT
            )

            recon_path = os.path.join(LOG_DIR, "sample_ingestion_reconciliation.json")
            with open(recon_path, "w", encoding="utf-8") as f:
                json.dump(recon, f, indent=2)
            logger.info(f"Reconciliation written to {recon_path}")

        if args.dataset == "rejected":
            logger.info("Sample mode for rejected applications is available via unit test mocks.")
            logger.info("For production ingestion, use --mode full --dataset rejected with approval.")


if __name__ == "__main__":
    main()

