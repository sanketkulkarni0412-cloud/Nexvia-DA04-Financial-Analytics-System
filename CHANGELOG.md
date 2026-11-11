# Changelog

All notable changes to the **Financial Analytics and Risk Reporting System (DA-04)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.8.0] - 2026-11-11

### Added & Validated — Step 6 / Task 5: Power Automate Monthly Board Report + PDF Automation Pipeline
- **Headless PDF Generation Pipeline (`power_automation/generate_monthly_packet.py`):**
  - Engineered an automated, headless reporting engine querying authoritative SQL views (`vw_portfolio_pnl_monthly`, `vw_portfolio_balance_sheet_summary`) and Task 3 model governance JSON (`reports/credit_risk_final_scorecard.json`).
  - Implemented publication-grade vector PDF rendering with matplotlib's Agg backend, generating a 2-page executive board report (`power_automation/output/monthly_board_report.pdf`, 68,217 bytes):
    - *Page 1:* Executive Overview, 6 KPI Headline Cards ($34.00B Funded, $9.51B Active Gross, $8.74B Net Carrying Value, $5.50B Interest Income, 2.5683% NPL Ratio, $772.88M Loss Reserve), Cumulative P&L Cash Flow Table, and Balance Sheet Solvency Waterfall.
    - *Page 2:* Credit Risk Scorecard Architecture, 10 Predictor WOE/IV & Model Coefficients Table, 2016 Out-of-Time Decile Calibration Table (AUC 0.6770, KS 25.15%), and Model Risk Management (SR 11-7) Compliance Callout.
- **Enterprise Email Dispatcher with Dry-Run Safety (`power_automation/email_dispatcher.py`):**
  - Built an auditable email distribution module supporting SMTP and Office 365 Exchange relays.
  - Implemented default dry-run mode (`dry_run=True`), ensuring no accidental external transmissions during test execution.
  - Developed strict credential masking (`mask_credential()`) to prevent secrets or passwords from appearing in stdout, logs, or error dumps.
  - Built fail-safe fallback logic producing structured operational status (`DRY RUN`, `READY TO SEND`, `CONFIGURATION ERROR`).
- **Microsoft Power Automate Cloud Flow Blueprint (`power_automation/power_automate_flow_spec.md`):**
  - Authored a comprehensive cloud architecture specification defining monthly recurrence trigger (1st of month at 06:00 UTC), Azure Automation/Desktop execution step, PDF validation condition, SharePoint document library archival, Office 365 Outlook email dispatch, and Microsoft Teams leadership feed notification.
  - Configured `run-after hasFailed` error handling scopes, P1 alerting, and explicit disclosure: `DESIGN/SPECIFICATION — LIVE CLOUD FLOW NOT EXECUTED IN THIS LOCAL ENVIRONMENT`.
- **Comprehensive Documentation (`power_automation/README.md`):**
  - Authored detailed operations guide covering architecture, local execution instructions, dry-run testing, environment variable configuration, and security guidelines.
- **Automated Test Suite Expansion (`tests/test_power_automation.py`):**
  - Added 7 comprehensive test cases verifying metric extraction against authoritative views, valid vector PDF generation (>25 KB with `%PDF-` signature), dry-run safety, credential masking, missing configuration handling, and flow spec completeness (100% pass in 84.17s).
- **Machine-Readable Validation Audit (`reports/task6_power_automation_validation.json`):**
  - Generated audit artifact detailing PDF size, included KPIs, email dispatcher validation, and governance disclosures.

---

## [0.7.0] - 2026-11-11

### Added & Validated — Step 3: Budget vs. Actual Variance Engine & Rate-Volume Decomposition
- **Governance Audit & Disclosure:** Validated that table `dim_financial_budget` in `warehouse.db` has 0 rows (official corporate budgets were not provided in the Lending Club dataset). In strict adherence to assessment rules against fabricating corporate figures, built an auditable, clearly labeled `ILLUSTRATIVE SCENARIO — NOT OFFICIAL BUDGET` planning framework.
- **Dynamic Actuals Ingestion (`financial_reports/budget_variance.py`):** Developed variance engine reading monthly actual cash flows and loan volumes dynamically from authoritative SQL reporting views (`vw_portfolio_pnl_monthly` and `vw_portfolio_vintage_performance`). Zero financial totals are hardcoded.
- **Directional Variance Analysis:** Calculated absolute dollar variances ($\Delta M = \text{Actual} - \text{Budget}$) and percentage variances ($\Delta M / |\text{Budget}| \times 100\%$) with automated safe division-by-zero protection. Classified directional performance as Favorable or Unfavorable based on financial taxonomy (Revenues vs Costs).
- **Rate-Volume-Mix Driver Decomposition:** Implemented 3-factor mathematical decomposition for Interest Income and Credit Losses:
  - Volume Variance: $(\Delta V) \times R_{\text{budget}}$
  - Rate/Yield Variance: $V_{\text{budget}} \times (\Delta R)$
  - Mix/Interaction Variance: $(\Delta V) \times (\Delta R)$
  - Reconciled identity verified: $\Delta V_{\text{vol}} + \Delta V_{\text{rate}} + \Delta V_{\text{mix}} \equiv \text{Total Variance}$ ($0.00 difference).
- **Machine-Readable Audit Report:** Generated [`reports/budget_variance_analysis.json`](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/budget_variance_analysis.json) containing annual and cumulative variance summaries, driver decompositions, assumptions, and limitations.
- **Exhaustive Documentation:** Authored [`documentation/BUDGET_VARIANCE.md`](file:///d:/nexvia%20-%201/Financial-Analytics-System/documentation/BUDGET_VARIANCE.md) explaining variance concepts, mathematical equations, and governance disclosures.
- **Automated Test Suite Expansion (`tests/test_budget_variance.py`):** Added 6 automated tests validating actual reconciliation, zero division handling, variance arithmetic, directional logic, driver identities, and official budget flag verification (100% pass in 22.21s).

---

## [0.6.0] - 2026-11-11

### Added & Validated — Task 4: Interactive BI & Qlik Sense Dashboard (Modular Dual-Delivery)
- **Local Environment Audit & Disclosure:** Verified that Qlik Sense Desktop is not installed on the local execution machine. Implemented the approved modular dual-delivery strategy delivering production Qlik script assets alongside a zero-dependency interactive browser BI dashboard.
- **Authoritative Data Extraction Engine (`qlik_dashboard/export_qlik_data.py`):** Developed automated extractor generating 6 lightweight, indexed CSV datasets in `qlik_dashboard/data/` sourced directly from SQLite views (`vw_portfolio_vintage_performance`, `vw_portfolio_balance_sheet_summary`, `fact_accepted_loans`) and Task 3 scorecard outputs:
  - `qlik_portfolio_summary.csv` (1,677 monthly-grade-term cohort rows)
  - `qlik_vintage_performance.csv` (2,735 vintage sub-grade cohort rows)
  - `qlik_scorecard_bands.csv` (6 neutral risk tiers)
  - `qlik_scorecard_points.csv` (38 feature-bin integer points)
  - `qlik_oot_metrics.csv` (2012–2015 train vs 2016 OOT holdout)
  - `qlik_geo_summary.csv` (51 US states and census regions)
- **Production Qlik Sense Load Script (`qlik_dashboard/load_script.qvs`):** Authored syntactically realistic Qlik Sense load script with synthetic keys (`%Key_Cohort`, `%Key_Grade`, `%Key_State`, `%Key_RiskTier`), Master Calendar autogeneration, set analysis variables, and configurable data paths.
- **Data Model Architecture Specification (`qlik_dashboard/data_model_spec.md`):** Formally documented table lineages, grains, key associations, metric definitions, and explicit negative finding documenting that `loan_purpose` is omitted from the accepted warehouse.
- **Standalone Interactive BI Application (`qlik_dashboard/interactive_dashboard.html`):** Developed zero-dependency, browser-based executive dashboard featuring dark/light theme toggling, interactive cross-filtering, and 3 tab modules:
  - *Tab 1: Executive Portfolio & Solvency:* $34.00B Funded, $9.51B Active, 2.57% NPL, $772.88M Reserve, $8.74B Carrying Value, Annual Volume & WAC, Grade Distribution, and Solvency Waterfall.
  - *Tab 2: Vintage Performance & Cash Flow:* $27.31B Cash Inflows, Monthly Cash Trajectory (138 cohorts), Vintage Default Rates, and Net Cash Margins.
  - *Tab 3: Credit Risk Scorecard:* In-Time AUC 0.6828, In-Time KS 26.08%, Brier 0.1484, 2016 OOT AUC 0.6770, OOT KS 25.15%, 6-Band Risk Calibration, and Feature Points Allocation.
- **Automated Validation Suite (`tests/test_qlik_dashboard.py`):** Added 7 comprehensive test cases verifying asset existence, CSV schema, financial metric reconciliation, risk band monotonicity, and HTML dashboard structure.
- **Project Test Suite Status:** Executed full test suite; **97 of 97 tests passed cleanly (100% pass in 220s)**.
- **Compliance & Data Preservation:** Confirmed `warehouse.db`, raw datasets, Task 2 Excel workbook, and Task 3 credit risk reports remain completely unchanged. Validation report saved to `reports/task4_qlik_dashboard_validation.json`.

---

## [Unreleased]

### Planned for Phase 3 Step 3 (Full Database Ingestion)
- Execution of `--mode full` for accepted loans (2,260,668 records) and rejected applications (27,648,741 records).
- Pre-aggregation of `fact_underwriting_funnel_monthly`.
- Comprehensive production reconciliation suite verifying zero variance across multi-billion-dollar portfolio cash flows.

## [0.3.2] - 2026-10-31

### Added & Validated — Phase 3: Step 2 (Pipeline Implementation & Sample Benchmark Ingestion)
- **Cleaning Pipeline (`data_cleaning/clean_pipeline.py`):** Built robust transformation functions for chunked CSV cleaning, date parsing to integer keys, numeric casting with native NULL preservation, loan status classification (`is_confirmed_default` and `delinquency_tier`), and safe non-loan partition row filtering.
- **Warehouse Loader (`sql/load_warehouse.py`):** Developed SQLAlchemy-based ingestion engine targeting `warehouse.db` with WAL mode pragmas, atomic transactions, checkpoint tracking via `etl_ingestion_checkpoints`, idempotent `INSERT OR IGNORE` deduplication, and error logging.
- **Reference Dimension Seeding:** Automated seeding of `dim_calendar_date` (11,324 daily records covering 2000–2030), `dim_loan_grade` (35 sub-grades A1–G5), and `dim_geography` (51 US states + territory fallback).
- **Sample Benchmark Ingestion (`--mode sample`):** Executed sample ingestion using `dataset/raw/lending_club_loans.csv`. Safely inserted exactly 51,072 loan contracts and 51,072 borrower credit profiles into `warehouse.db` (file size: 22.16 MB) in ~8.5 seconds.
- **Financial Reconciliation Assertion Passed:** Reconciled sample totals: SUM(loan_amnt) = $767,112,825.00 ($0.00 variance), SUM(total_pymnt) = $767,235,505.08 ($0.00 variance), 0 duplicate PKs, 0 orphan FKs. Machine-readable audit saved to `reports/sample_ingestion_reconciliation.json`.
- **Idempotent Re-execution Verified:** Tested repeated execution of sample ingestion with and without resume flags; confirmed that subsequent executions gracefully skip or ignore duplicate records with 0 row inflation.
- **Automated Test Suite Expansion (`tests/test_phase3_step2_pipeline.py`):** Added 8 automated tests covering cleaning transformations, default logic, footers, batch insertion, checkpoints, rollback on failure, idempotency, and reconciliation. Total passing tests: 22 of 22 (100% pass in 5.50s).
- **Strict Compliance Maintained:** Zero raw files altered (byte-verified); `--mode full` not executed; 27.6M rejections not loaded; budget metrics preserved as NULL.

## [0.3.1] - 2026-10-31

### Verified & Hardened — Phase 3: Step 1 (Final Architecture Technical Review)
- **Individual Audit of All 33 Excluded Lines:** Scanned all 23 chunks in `accepted_2007_to_2018Q4.csv`; compiled exhaustive inventory of all 33 partition lines (32 quarterly footers + 1 section header at CSV line 1,651,667). Proved that in all 33 lines, 150 of 151 fields are completely NULL and only `id` is populated. Confirmed 0 legitimate loans are removed; confirmed exactly 2,260,668 valid loans. Detailed audit logged to `reports/exhaustive_footer_audit.json`.
- **Rejected Application Uniqueness Enforcement:** Added `UNIQUE` constraint to `source_row_num` in both SQLite and PostgreSQL schemas to ensure 100% strict backward physical file line uniqueness and native idempotency.
- **Ingestion Resilience & Checkpoints (`etl_ingestion_checkpoints`):** Added dedicated checkpoint tracking table to the schema supporting idempotent resume, transaction rollback recovery, and error logging without duplicate records.
- **Sample Benchmark Parity Audit:** Profiled `dataset/raw/lending_club_loans.csv`; confirmed 51,072 rows, 0 null loan amounts, 0 non-numeric IDs, $767,112,825.00 loan volume, and 100% column parity with the production schema.
- **Automated Test Expansion:** Added `test_rejected_source_row_num_uniqueness` and checkpoint table assertion to test suite. 14 of 14 tests passed in `pytest`.

## [0.3.0] - 2026-10-31

### Added & Refined — Phase 3: Step 1 (SQL Database Architecture & Engineering Design)
- **Borrower Identification Audit & Decision:** Empirically verified across all 2,260,701 rows that `member_id` is 100.0% NULL (stripped for privacy). Modeled borrower underwriting snapshot as `dim_borrower_credit_profile` keyed by `loan_id` (1-to-1 extension) avoiding synthetic borrower linkages.
- **Credit Risk Classification Matrix:** Standardized non-overlapping status classification (`is_confirmed_default` and `delinquency_tier`). Confirmed defaults ('Charged Off', 'Default') isolated from performing loans ('Current') and ongoing delinquency ('Late (31-120 days)', 'In Grace Period'). Severe late loans kept as `NULL` default flag to avoid conflating delinquency with write-offs.
- **Exhaustive Partition Filter Audit (33 Non-Loan Rows):** Identified and logged all 33 partition dividers in `accepted_2007_to_2018Q4.csv` (16 pairs of quarterly "Total amount funded" lines + 1 section header line "Loans that do not meet the credit policy" at index 1,651,665), leaving 2,260,668 net valid loans.
- **Independent Empirical Financial Reconciliation:** Computed exact raw figures: Stated volume = $34,016,115,925.00, Funded balance = $34,004,208,600.00, Cumulative collections = $27,314,649,582.62, Realized interest = $5,496,560,266.06.
- **Rejected Application Backward Traceability:** Added `source_row_num` to `fact_rejected_applications` recording the 1-indexed line number in `rejected_2007_to_2018Q4.csv`.
- **Budget Data Governance:** Documented that no budget data was supplied; all budget metrics in `dim_financial_budget` default to NULL/UNAVAILABLE with `is_approved_assumption = 0`.
- **Illustrative Regulatory Assumptions:** Marked Basel II weights and target loss caps in `dim_loan_grade` as illustrative analytical heuristics with explicit regulatory disclaimer.
- **Architecture Test Suite (`tests/test_phase3_architecture.py`):** Added automated tests verifying primary-key uniqueness, foreign-key integrity under `PRAGMA foreign_keys = ON`, default classification logic, and footer filtering. All 13 tests passed in `pytest`.


## [0.2.3] - 2026-10-31

### Validated & Profiled
- **Independent Pandas Chunk-Based Audit (`chunksize=100,000`):** Executed full stream validation script (`data_cleaning/deep_validation_audit.py`) independently processing both official CSV files:
  - `accepted_2007_to_2018Q4.csv`: Processed across 23 chunks in 26.00s; verified 2,260,701 parsed rows with 0 bad lines. Reconciled 32 footer summary rows at EOF, leaving 2,260,669 net active loan records.
  - `rejected_2007_to_2018Q4.csv`: Processed across 277 chunks in 16.75s; verified 27,648,741 parsed rows with 0 bad lines (100% clean parsing).
- **Record Reconciliation:** Proved 0 discrepancy between newline-based data lines and parsed pandas rows across both master archives.
- **Full Dataset Missing Value Audit:** Profiled missingness across all 2.26M accepted loans and 27.6M rejected applications (e.g. `loan_amnt`, `int_rate`, `grade`, `loan_status` are 99.999% complete; `Risk_Score` missing in 66.90% of early-stage rejected applicants).
- **Dataset Isolation Confirmed:** Validated that `accepted_2007_to_2018Q4.csv`, `rejected_2007_to_2018Q4.csv`, and `lending_club_loans.csv` remain separate, unmerged, and untouched.

---

## [0.2.2] - 2026-10-31

### Verified & Audited
- **Official Raw Archive Verification:** Audited official Kaggle files delivered to `dataset/raw/`:
  - `accepted_2007_to_2018Q4.csv`: 1,675,133,810 bytes (1.560 GB), exactly 2,260,701 data records, 151 columns.
  - `rejected_2007_to_2018Q4.csv`: 1,782,281,620 bytes (1.660 GB), exactly 27,648,741 data records, 9 columns.
  - `lending_club_loans.csv`: 36,699,575 bytes (35.00 MB), exactly 51,072 data records, 151 columns (preserved intact).
- **Zero RAM Overhead Streaming:** Executed non-destructive verification script (`data_cleaning/audit_official_dataset.py`) using buffered binary chunking (8MB buffers) to count exact records and test middle-slice readability without memory spikes.
- **Schema Parity Confirmed:** Verified 100% exact column match between `accepted_2007_to_2018Q4.csv` and `lending_club_loans.csv` across all 151 columns, ensuring full forward code reusability.
- **Data Preservation Compliance:** All raw master files and development samples preserved untouched; zero records deleted, modified, or extracted.
- **Migration Plan Updated:** Updated `documentation/DATASET_MIGRATION_PLAN.md` with verified file sizes, exact row counts, and chunked pipeline specifications.

---

## [0.2.1] - 2026-10-31

### Changed & Clarified
- **Official Dataset Source Alignment:** Formally documented the official assessment resource as the complete [Kaggle Lending Club Loan Data](https://www.kaggle.com/datasets/wordsforthewise/lending-club) (`wordsforthewise/lending-club`) comprising `accepted_2007_to_2018Q4.csv.gz` (~2.26M loans) and `rejected_2007_to_2018Q4.csv.gz` (~27.6M applications).
- **Dataset Audit & Local Search:** Audited local drives and downloads; confirmed the multi-gigabyte master archive is not yet present on the local machine.
- **Migration & Ingestion Blueprint (`documentation/DATASET_MIGRATION_PLAN.md`):** Authored detailed migration specification defining dual-mode pipeline execution (sample mode vs. full production mode) and chunked ingestion strategies (`chunksize=100000`) to process multi-gigabyte files without out-of-memory errors.
- **Sample Scope & Provenance Transparency:** Documented that the existing 51,072-record file in `dataset/raw/lending_club_loans.csv` has 100% schema and column parity with `accepted_2007_to_2018Q4.csv`, preserves the Q4 2015 vintage, and will be preserved as a fast unit-testing benchmark.
- **Documentation Updates:** Updated `README.md`, `documentation/DATA_DICTIONARY.md`, and `reports/EDA_SUMMARY.md` with official source citations, sample limitations, and manual Kaggle download procedures.

---

## [0.2.0] - 2026-10-31

### Added
- **Python Virtual Environment (`.venv`):** Initialized isolated virtual environment running Python 3.13.1.
- **Dependency Installation & Verification:** Verified compatibility and installed compatible versions of:
  - `pandas` (3.1.0)
  - `numpy` (2.5.4)
  - `scipy` (1.18.1)
  - `scikit-learn` (1.9.1)
  - `matplotlib` (3.11.2)
  - `seaborn` (0.13.2)
  - `openpyxl` (3.1.5)
  - `xlsxwriter` (3.3.1)
  - `sqlalchemy` (2.1.6)
  - `pytest` (9.2.0)
  - `pyarrow` (26.0.0)
- **Dataset Acquisition (`data_cleaning/download_dataset.py`):** Ingested authentic Lending Club loan dataset (51,072 rows × 151 columns, 35.00 MB) into `dataset/raw/lending_club_loans.csv` sourced from Kaggle/HuggingFace accepted loans.
- **Statistical Profiling Engine (`data_cleaning/profile_dataset.py`):** Developed complete data profiling engine measuring missingness, zero duplicates, loan amounts, interest spreads, FICO distributions, and loan statuses.
- **Exploratory Data Analysis (EDA) Charts:** Rendered 7 institutional high-resolution charts in `reports/eda_charts/`:
  - `loan_grade_distribution.png`
  - `default_rate_by_grade.png`
  - `loan_amount_distribution.png`
  - `interest_rate_distribution.png`
  - `loan_status_distribution.png`
  - `correlation_heatmap.png`
  - `default_rate_by_emp_length.png`
- **Formal Data Dictionary (`documentation/DATA_DICTIONARY.md`):** Complete taxonomy documenting field names, data types, descriptions, financial interpretations, and missing value percentages.
- **EDA Summary Report (`reports/EDA_SUMMARY.md`):** Comprehensive empirical analysis documenting key statistical findings, credit grade default rates, and architectural implications for Phase 3.
- **Automated Test Suite (`tests/test_phase2_eda.py`):** 5 automated test cases executed via `pytest` achieving 100% pass rate.
- **Environment Verification Test (`tests/verify_environment.py`):** Automated dependency validation script verifying Python 3.13.1 imports.

## [0.1.0] - 2026-10-31

### Added
- **Environment Audit:** Inspected host Windows development environment (Python 3.13.1, Git 2.50.1, VS Code 1.142.0, Microsoft Excel 2016+, built-in SQLite, SQLAlchemy 2.0.51, psycopg2 2.9.12).
- **Dependency Audit:** Identified missing data science and reporting libraries (`pandas`, `numpy`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`, `openpyxl`, `xlsxwriter`, `pytest`).
- **Project Structure:** Created root directory `Financial-Analytics-System/` and ten subdirectories:
  - `dataset/`
  - `data_cleaning/`
  - `sql/`
  - `financial_reports/`
  - `credit_risk/`
  - `qlik_dashboard/`
  - `power_automation/`
  - `documentation/`
  - `tests/`
  - `reports/`
- **Initial Documentation Suite:**
  - `README.md`: High-level system architecture, deliverables, and technology overview.
  - `PROJECT_PLAN.md`: Comprehensive 7-phase assessment roadmap, milestone breakdown, and risk matrix.
  - `documentation/PROJECT_ARCHITECTURE.md`: Technical blueprint, data pipeline flow, and dimensional Star Schema design.
  - `documentation/METRIC_DEFINITIONS.md`: Complete mathematical formulas and business rationale for P&L, Balance Sheet, Budget vs. Actual, and Credit Risk metrics.
  - `requirements.txt`: Curated dependency specification with package-level justifications.
  - `.gitignore`: Production-grade exclusion rules for Python caches, virtual environments, data files, and temporary Excel lock files.
- **Strategic Dataset Recommendation:** Selected and justified the Lending Club loan dataset as the primary financial and credit risk data engine.
