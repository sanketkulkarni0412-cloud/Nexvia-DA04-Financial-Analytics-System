# Pre-Ingestion Safety Audit & Architectural Verification Report
**Project:** Financial Analytics and Risk Reporting System (DA-04)  
**Phase:** Phase 3 — Step 2 (Pre-Ingestion Safety Verification)  
**Date:** 31 October 2026  
**Auditor:** Senior Data Engineering Architect & Lead Data Analyst  
**Status:** AUDIT COMPLETE — AWAITING STAKEHOLDER APPROVAL  

---

## Executive Summary

Prior to executing full-scale production ingestion of the official Lending Club dataset, an exhaustive **Pre-Ingestion Safety Audit** was conducted across the data engineering pipeline, database storage layer, referential integrity mechanisms, and deduplication logic.

### Key Audit Conclusions:
1. **Safety Restrictions Enforced**: Strict guardrails have been added to [sql/load_warehouse.py](file:///d:/nexvia%20-%201/Financial-Analytics-System/sql/load_warehouse.py). Running `--mode full` is strictly blocked unless the stakeholder explicitly provides the `--confirm-full-ingestion` flag.
2. **Dataset Independence Verified**: The accepted loan pipeline (`accepted_2007_to_2018Q4.csv`, 2,260,668 valid rows) and the rejected applications pipeline (`rejected_2007_to_2018Q4.csv`, 27,648,741 records) are **completely orthogonal and decoupled**. They share only conformed reference dimensions (`dim_calendar_date`, `dim_geography`), which are seeded during database initialization. Separate CLI switches (`--dataset accepted`, `--dataset rejected`, `--dataset all`) allow completely independent execution and failure isolation.
3. **Zero Silent Discard Policy**: `INSERT OR IGNORE` behavior was audited and fortified. A dedicated audit function (`audit_and_log_ignored`) now pre-checks candidate primary keys against the warehouse, distinguishes between `LEGITIMATE_RERUN` (idempotent replay of previously committed chunks) and `DATA_COLLISION` (unexpected key collisions), and records every omission with timestamps and chunk indices in [reports/ignored_records.log](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/ignored_records.log).
4. **Referential Integrity Enforced**: An automated connection-level event listener (`@event.listens_for(Engine, "connect")`) was implemented to guarantee that SQLite's `PRAGMA foreign_keys = ON;`, `PRAGMA journal_mode = WAL;`, and `PRAGMA synchronous = NORMAL;` are executed on **every connection** checked out of the SQLAlchemy connection pool.
5. **Storage & Capacity Assured**: The host storage system on Drive `D:` possesses **125.61 GB of free space**, safely exceeding the estimated ~4.5 GB total SQLite warehouse footprint by >27x.
6. **Benchmark & Test Integrity**: The existing benchmark sample (51,072 accepted loans, $767,112,825.00 loan volume, $0.00 variance) remains 100% intact. All 26 automated unit and integration tests in the test suite pass with zero errors.

---

## Audit Item 1: Inspection of Loader and Cleaning Pipeline

### 1.1 Components Inspected
- [sql/load_warehouse.py](file:///d:/nexvia%20-%201/Financial-Analytics-System/sql/load_warehouse.py)
- [data_cleaning/clean_pipeline.py](file:///d:/nexvia%20-%201/Financial-Analytics-System/data_cleaning/clean_pipeline.py)
- [sql/schema_sqlite.sql](file:///d:/nexvia%20-%201/Financial-Analytics-System/sql/schema_sqlite.sql)

### 1.2 Enhancements Implemented
| Component | Function / Feature | Purpose |
| :--- | :--- | :--- |
| `clean_pipeline.py` | `clean_rejected_chunk` | Parses rejected applications: strips `%` from `Debt-To-Income Ratio`, parses application dates to `YYYYMMDD` integer date keys, preserves `NULL` risk scores, enforces 1-indexed sequential `source_row_num`, and flags non-positive requested amounts. |
| `load_warehouse.py` | `@event.listens_for(Engine, "connect")` | Automatically enables `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`, and `PRAGMA synchronous = NORMAL` on every connection opened by SQLAlchemy. |
| `load_warehouse.py` | `audit_and_log_ignored` | Pre-screens candidate IDs in slices of 500 against warehouse tables. Distinguishes `LEGITIMATE_RERUN` from `DATA_COLLISION` and writes audit trails to [reports/ignored_records.log](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/ignored_records.log). |
| `load_warehouse.py` | `insert_rejected_batch` | Idempotent insertion into `fact_rejected_applications` with duplicate detection on `source_row_num`. |
| `load_warehouse.py` | `ingest_rejected_dataset` | Dedicated chunk-streamed loader for rejected applications with independent checkpoints (`rejected_applications_full`). |
| `load_warehouse.py` | `reconcile_rejected_warehouse` | Post-ingestion reconciliation checking row counts, distinct source rows, total requested amount, orphan dates, and orphan state codes. |
| `load_warehouse.py` | `--confirm-full-ingestion` | Hard CLI guardrail preventing accidental execution of full multi-gigabyte ingestion. |

---

## Audit Item 2 & 3: Dataset Independence & Execution Decoupling

### 2.1 Dimensional Model Analysis
The database schema was audited to determine inter-table dependencies:
- **`fact_accepted_loans` Foreign Keys:**
  - `loan_id` $\rightarrow$ `dim_borrower_credit_profile(loan_id)` (loaded in lockstep in the same transaction)
  - `issue_date_key` $\rightarrow$ `dim_calendar_date(date_key)` (conformed dimension, pre-seeded)
  - `grade_key` $\rightarrow$ `dim_loan_grade(grade_key)` (conformed dimension, pre-seeded)
  - `state_code` $\rightarrow$ `dim_geography(state_code)` (conformed dimension, pre-seeded)
  - **Dependency on Rejected Applications:** **NONE**.
- **`fact_rejected_applications` Foreign Keys:**
  - `app_date_key` $\rightarrow$ `dim_calendar_date(date_key)` (conformed dimension, pre-seeded)
  - `state_code` $\rightarrow$ `dim_geography(state_code)` (conformed dimension, pre-seeded)
  - **Dependency on Accepted Loans:** **NONE**.

### 2.2 Execution Options
The CLI interface for [sql/load_warehouse.py](file:///d:/nexvia%20-%201/Financial-Analytics-System/sql/load_warehouse.py) now provides decoupled execution:
```bash
# Ingest only accepted loans (default)
python sql/load_warehouse.py --mode full --dataset accepted --confirm-full-ingestion

# Ingest only rejected applications
python sql/load_warehouse.py --mode full --dataset rejected --confirm-full-ingestion

# Ingest both datasets sequentially
python sql/load_warehouse.py --mode full --dataset all --confirm-full-ingestion
```

---

## Audit Item 4: `INSERT OR IGNORE` Behavior & Audit Logging

### 4.1 Collision vs. Re-run Distinction
Standard `INSERT OR IGNORE` silently skips colliding rows. To ensure an institutional-grade audit trail, the loader now performs pre-insertion classification:
1. **Intra-Chunk Duplicates (`INTRA_CHUNK_DUPLICATE`)**:
   - The chunk DataFrame is checked with `df.duplicated(subset=[id_col], keep='first')`.
   - Any duplicate is logged to [reports/ignored_records.log](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/ignored_records.log) with chunk index, record ID, and reason before deduplicating in RAM.
2. **Database Re-runs (`LEGITIMATE_RERUN`)**:
   - If 100% of candidate IDs in a chunk already exist in the database table, this indicates an intentional or idempotent re-execution of a previously committed batch.
   - A batch-level summary log entry is created, and insertion proceeds idempotently without bloating logs.
3. **Data Key Collisions (`DATA_COLLISION`)**:
   - If a partial set of candidate IDs already exists in the table (e.g., 2 out of 100,000), this signals an anomalous key collision.
   - A warning summary is written, and individual colliding keys are logged in detail for investigation.

### 4.2 Verified Audit Log Sample
During automated testing, the audit logger produced the following verified entries in [reports/ignored_records.log](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/ignored_records.log):
```
2026-10-31T09:27:21.246984+00:00 [DATASET: accepted] [CATEGORY: LEGITIMATE_RERUN] [CHUNK: 1] Batch of 1 records already present in fact_accepted_loans. Idempotently skipped without duplicate insertion.
2026-10-31T09:27:21.281902+00:00 [DATASET: accepted] [CATEGORY: INTRA_CHUNK_DUPLICATE] [CHUNK: 2] ID: AUDIT_102 - Duplicate loan_id within chunk 2
2026-10-31T09:27:21.288134+00:00 [DATASET: accepted] [CATEGORY: DATA_COLLISION] [CHUNK: 2] Partial collision: 1 of 2 IDs already exist in fact_accepted_loans!
2026-10-31T09:27:21.288760+00:00 [DATASET: accepted] [CATEGORY: DATA_COLLISION] [CHUNK: 2] ID: AUDIT_101 - Duplicate loan_id in fact_accepted_loans; record ignored by INSERT OR IGNORE
```

---

## Audit Item 5: Checkpoint & Resume Safety

### 5.1 Architecture & Atomicity
1. **Per-Chunk Transaction Isolation**:
   - Batch insertion runs inside an atomic transaction block: `with engine.begin() as conn:`.
   - If any unhandled exception occurs during cleaning or insertion of chunk $N$, SQLAlchemy automatically issues a `ROLLBACK`. Zero partial records from chunk $N$ enter the database.
2. **State Persistence**:
   - Checkpoints are saved in table `etl_ingestion_checkpoints` containing `pipeline_name`, `last_chunk_index`, `rows_ingested`, `status`, and `last_updated_at`.
   - The checkpoint update is committed only after the chunk transaction succeeds.
3. **Crash Recovery & Resume**:
   - Upon restart, `get_checkpoint(engine, pipeline_name)` retrieves `last_chunk_idx`.
   - The CSV streaming iterator skips already committed chunks up to `last_chunk_idx`, resuming precisely at chunk `last_chunk_idx + 1`.
   - Combined with `INSERT OR IGNORE`, this guarantees **exactly-once logical insertion** with zero record duplication.

---

## Audit Item 6: Resource, Storage & Runtime Estimates

### 6.1 Storage Space on Drive `D:`
- **Drive Total Capacity**: 235.20 GB
- **Currently Used**: 109.59 GB
- **Currently Available**: **125.61 GB**

### 6.2 Expected Database Footprint
| Dataset | Row Count | Uncompressed Size | Estimated DB Size | Indexes Size | Total DB Footprint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Accepted Loans** | 2,260,668 | 1.560 GB | ~850 MB | ~350 MB | **~1.20 GB** |
| **Rejected Applications** | 27,648,741 | 1.660 GB | ~2,100 MB | ~900 MB | **~3.00 GB** |
| **Reference Dimensions** | 11,358 | < 1 MB | ~2 MB | ~1 MB | **~3 MB** |
| **Combined Total** | **29,909,409** | **3.220 GB** | **~2,952 MB** | **~1,251 MB** | **~4.20 – 4.50 GB** |

### 6.3 Temporary WAL Requirements & RAM
- **SQLite WAL Space**: Peak WAL space is estimated at **200 MB to 500 MB** during streaming. Because transactions commit after every 100,000 rows, SQLite checkpoints WAL pages to the main DB file continuously.
- **RAM Footprint**: Under streaming chunksize of 100,000 rows, memory consumption remains constrained between **250 MB and 350 MB**, preventing memory exhaustion.
- **Safety Margin**: Available storage (125.61 GB) exceeds combined warehouse + peak WAL requirements (~5.0 GB) by **25.1x**.

### 6.4 Throughput & Ingestion Time Estimates
- **Accepted Loans (2.26M rows across 23 chunks)**:
  - Estimated throughput: ~6,000 to 7,500 rows/sec (including 151 column cleaning, date formatting, and borrower profile extraction).
  - Estimated runtime: **5.5 to 7.0 minutes**.
- **Rejected Applications (27.6M rows across 277 chunks)**:
  - Estimated throughput: ~35,000 to 45,000 rows/sec (lean 9-column schema).
  - Estimated runtime: **11.5 to 14.0 minutes**.
- **Combined Sequential Ingestion Runtime**: **~17 to 21 minutes**.

---

## Audit Item 7: Foreign Key Enforcement Verification

In SQLite, foreign key enforcement is connection-scoped and disabled by default. 
To eliminate the risk of connection pool checkout without foreign key enforcement, the following event listener was bound to SQLAlchemy's `Engine`:

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.close()
```

### Verification Proof:
1. Automated test `test_sqlite_foreign_key_pragma_enforcement` executes `SELECT PRAGMA foreign_keys;` on a fresh connection and asserts `= 1`.
2. The test attempts to insert an orphan loan referencing `grade_key = 9999` (non-existent).
3. The database immediately rejects the transaction with:
   `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.

---

## Audit Item 8: Automated Test Suite Results

The comprehensive test suite was executed via `pytest -v`. All 26 unit and integration tests passed:

```
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.2.0, pluggy-1.7.0 -- D:\nexvia - 1\Financial-Analytics-System\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\nexvia - 1\Financial-Analytics-System
collected 26 items

tests/test_phase2_eda.py::test_dataset_loads_and_row_count PASSED        [  3%]
tests/test_phase2_eda.py::test_required_columns_exist PASSED             [  7%]
tests/test_phase2_eda.py::test_data_types_and_range_validity PASSED      [ 11%]
tests/test_phase2_eda.py::test_all_eda_charts_generated PASSED           [ 15%]
tests/test_phase2_eda.py::test_documentation_and_reports_created PASSED  [ 19%]
tests/test_phase3_architecture.py::test_schema_files_exist PASSED        [ 23%]
tests/test_phase3_architecture.py::test_sqlite_schema_executes_in_memory PASSED [ 26%]
tests/test_phase3_architecture.py::test_primary_key_uniqueness PASSED    [ 30%]
tests/test_phase3_architecture.py::test_foreign_key_integrity PASSED     [ 34%]
tests/test_phase3_architecture.py::test_default_classification_logic PASSED [ 38%]
tests/test_phase3_architecture.py::test_footer_filtering_rule PASSED     [ 42%]
tests/test_phase3_architecture.py::test_rejected_source_row_num_uniqueness PASSED [ 46%]
tests/test_phase3_step2_pipeline.py::test_cleaning_transformations PASSED [ 50%]
tests/test_phase3_step2_pipeline.py::test_default_classification PASSED  [ 53%]
tests/test_phase3_step2_pipeline.py::test_footer_filtering PASSED        [ 57%]
tests/test_phase3_step2_pipeline.py::test_batch_insertion_and_referential_integrity PASSED [ 61%]
tests/test_phase3_step2_pipeline.py::test_checkpoint_handling PASSED     [ 65%]
tests/test_phase3_step2_pipeline.py::test_transaction_rollback_on_failure PASSED [ 69%]
tests/test_phase3_step2_pipeline.py::test_idempotent_reexecution PASSED  [ 73%]
tests/test_phase3_step2_pipeline.py::test_financial_reconciliation PASSED [ 76%]
tests/test_phase3_step2_pipeline.py::test_sqlite_foreign_key_pragma_enforcement PASSED [ 80%]
tests/test_phase3_step2_pipeline.py::test_clean_rejected_chunk_transformation PASSED [ 84%]
tests/test_phase3_step2_pipeline.py::test_rejected_independent_batch_insertion PASSED [ 88%]
tests/test_phase3_step2_pipeline.py::test_ignored_records_and_collision_audit PASSED [ 92%]
tests/test_schema_syntax.py::test_schema_files_exist PASSED              [ 96%]
tests/test_schema_syntax.py::test_sqlite_schema_executes_in_memory PASSED [100%]

============================= 26 passed in 11.14s =============================
```

---

## Audit Item 9: Dataset Preservation Verification

All raw source files and benchmark database assets were inspected and confirmed unmodified:
- [dataset/raw/accepted_2007_to_2018Q4.csv](file:///d:/nexvia%20-%201/Financial-Analytics-System/dataset/raw/accepted_2007_to_2018Q4.csv): **1,675,133,810 bytes** (Unchanged)
- [dataset/raw/rejected_2007_to_2018Q4.csv](file:///d:/nexvia%20-%201/Financial-Analytics-System/dataset/raw/rejected_2007_to_2018Q4.csv): **1,782,281,620 bytes** (Unchanged)
- [dataset/raw/lending_club_loans.csv](file:///d:/nexvia%20-%201/Financial-Analytics-System/dataset/raw/lending_club_loans.csv): **36,699,575 bytes** (Unchanged)
- [warehouse.db](file:///d:/nexvia%20-%201/Financial-Analytics-System/warehouse.db): **51,072 accepted loans**, **$767,112,825.00 loan amount**, **$0.00 reconciliation variance**.

---

## Recommended Ingestion Strategy

Upon stakeholder approval, ingestion should proceed in two decoupled phases:

### Phase 3A: Full Accepted Loan Ingestion (Recommended First Step)
- **Target Table**: `fact_accepted_loans` and `dim_borrower_credit_profile`
- **Expected Records**: 2,260,668 rows ($34,024,416,025.00 total funded volume)
- **Command**:
  ```powershell
  .venv\Scripts\python sql\load_warehouse.py --mode full --dataset accepted --confirm-full-ingestion
  ```
- **Estimated Duration**: ~6.0 minutes.

### Phase 3B: Full Rejected Applications Ingestion (Decoupled Follow-Up)
- **Target Table**: `fact_rejected_applications`
- **Expected Records**: 27,648,741 records
- **Command**:
  ```powershell
  .venv\Scripts\python sql\load_warehouse.py --mode full --dataset rejected --confirm-full-ingestion
  ```
- **Estimated Duration**: ~12.5 minutes.

---

## Stakeholder Sign-Off Request
Full ingestion is held in a **STANDBY** state. Awaiting stakeholder confirmation before initiating Phase 3A production loading.
