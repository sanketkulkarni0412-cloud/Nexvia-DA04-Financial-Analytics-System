-- ==============================================================================
-- Financial Analytics and Risk Reporting System (DA-04)
-- Component: Local SQLite Data Warehouse Schema DDL (Refined Architecture)
-- Engine: SQLite 3 (Python Standard Library / Local Development Mart)
-- Documentation Ref: documentation/SQL_DATABASE_DESIGN.md
-- ==============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ==============================================================================
-- 1. DIMENSION TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1.1 Calendar Date Dimension
-- Provides continuous temporal hierarchy spanning origination and repayment periods.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_calendar_date (
    date_key            INTEGER PRIMARY KEY,             -- Format: YYYYMMDD (e.g., 20151201)
    full_date           TEXT NOT NULL,                   -- Exact calendar date (ISO: YYYY-MM-DD)
    year                INTEGER NOT NULL,                -- e.g., 2015
    quarter             INTEGER NOT NULL,                -- 1, 2, 3, 4
    month               INTEGER NOT NULL,                -- 1 to 12
    month_name          TEXT NOT NULL,                   -- 'January', 'December', etc.
    year_month          TEXT NOT NULL,                   -- '2015-12'
    year_quarter        TEXT NOT NULL,                   -- '2015-Q4'
    fiscal_year         INTEGER NOT NULL,                -- e.g., 2015
    fiscal_quarter      TEXT NOT NULL                    -- 'FY15-Q4'
);

-- ------------------------------------------------------------------------------
-- 1.2 Loan Grade Dimension
-- Credit tiers and illustrative risk benchmarks.
-- DISCLAIMER: Risk weights and loss caps are illustrative analytical assumptions,
-- NOT official regulatory mandates or official Lending Club contractual terms.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_loan_grade (
    grade_key                   INTEGER PRIMARY KEY,     -- Surrogate key (1 to 35)
    grade                       TEXT NOT NULL CHECK(grade IN ('A','B','C','D','E','F','G')),
    sub_grade                   TEXT NOT NULL UNIQUE,    -- 'A1' through 'G5'
    grade_rank                  INTEGER NOT NULL,        -- Ordinal rank (1 for A1, 35 for G5)
    regulatory_tier             TEXT NOT NULL,           -- 'Prime', 'Near-Prime', 'Subprime', 'High-Risk'
    illustrative_basel_weight   REAL NOT NULL,           -- Illustrative Basel II risk weight (e.g., 0.20, 1.50)
    illustrative_target_loss_cap REAL NOT NULL           -- Illustrative target default rate threshold (e.g., 0.025)
);

-- ------------------------------------------------------------------------------
-- 1.3 Geography Dimension
-- Regional classification covering all US states and territories.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_geography (
    state_code          TEXT PRIMARY KEY,                -- US 2-letter state abbreviation ('CA', 'NY', etc.)
    state_name          TEXT NOT NULL,                   -- 'California', 'New York', etc.
    census_region       TEXT NOT NULL,                   -- 'West', 'Northeast', 'Midwest', 'South'
    economic_division   TEXT NOT NULL,                   -- 'Pacific', 'Middle Atlantic', etc.
    is_active_lending   INTEGER NOT NULL DEFAULT 1       -- Flag indicating Lending Club operation
);

-- ------------------------------------------------------------------------------
-- 1.4 Borrower Credit Profile Dimension (Loan-Level Snapshot)
-- IMPORTANT: member_id is 100.0% NULL in raw Lending Club datasets.
-- True cross-loan borrower identity cannot be established without inventing data.
-- This table stores the credit profile snapshot strictly at loan origination,
-- uniquely keyed by loan_id (1-to-1 extension with fact_accepted_loans).
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_borrower_credit_profile (
    loan_id             TEXT PRIMARY KEY,                -- Matches loan_id; loan-level profile anchor
    annual_inc          REAL,                            -- Stated gross annual income ($)
    emp_length          TEXT,                            -- Employment tenure string ('< 1 year', '10+ years', etc.)
    emp_length_years    INTEGER,                         -- Parsed numeric employment years (0 to 10)
    home_ownership      TEXT,                            -- 'RENT', 'MORTGAGE', 'OWN', 'OTHER'
    verification_status TEXT,                            -- 'Verified', 'Source Verified', 'Not Verified'
    dti                 REAL,                            -- Debt-to-income ratio (%)
    fico_range_low      INTEGER,                         -- Lower FICO bureau score bound
    fico_range_high     INTEGER,                         -- Upper FICO bureau score bound
    fico_midpoint       INTEGER,                         -- Midpoint score: (low + high) / 2
    open_acc            INTEGER,                         -- Number of open credit lines
    pub_rec             INTEGER,                         -- Number of derogatory public records
    revol_bal           REAL,                            -- Total revolving credit balance ($)
    revol_util          REAL,                            -- Revolving line utilization percentage (%)
    total_acc           INTEGER,                         -- Total credit lines in credit history
    earliest_cr_line    TEXT,                            -- Month of earliest credit line opened
    CHECK (fico_range_low IS NULL OR (fico_range_low >= 300 AND fico_range_low <= 850))
);

-- ------------------------------------------------------------------------------
-- 1.5 Financial Budget Structure (Managerial Variance Inputs)
-- IMPORTANT: No budget dataset was supplied in official raw data.
-- All numeric budget metrics default to NULL (UNAVAILABLE) until supplied or approved.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_financial_budget (
    budget_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month              TEXT NOT NULL,               -- Budget target month (YYYY-MM)
    grade                   TEXT NOT NULL CHECK(grade IN ('A','B','C','D','E','F','G')),
    budgeted_volume         REAL DEFAULT NULL,           -- Budgeted origination volume ($) [NULL until supplied]
    targeted_yield          REAL DEFAULT NULL,           -- Target gross portfolio yield (%) [NULL until supplied]
    loss_provision_cap      REAL DEFAULT NULL,           -- Planned credit loss reserve ($) [NULL until supplied]
    budgeted_opex           REAL DEFAULT NULL,           -- Operating expense allocation ($) [NULL until supplied]
    is_approved_assumption  INTEGER NOT NULL DEFAULT 0,  -- 0 = Pending/Unavailable, 1 = Formally Approved Assumption
    notes                   TEXT DEFAULT 'Budget data pending official supply'
);

-- ==============================================================================
-- 2. FACT TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 2.1 Accepted Loan Contracts Fact Table
-- Tracks 2,260,668 legitimate loan originations ($34.02B funded volume).
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_accepted_loans (
    loan_id                 TEXT PRIMARY KEY,            -- Natural Lending Club loan identifier
    issue_date_key          INTEGER NOT NULL,            -- FK to dim_calendar_date
    grade_key               INTEGER NOT NULL,            -- FK to dim_loan_grade
    state_code              TEXT NOT NULL,               -- FK to dim_geography
    
    -- Principal & Amortization
    loan_amnt               REAL NOT NULL CHECK(loan_amnt > 0),
    funded_amnt             REAL NOT NULL CHECK(funded_amnt > 0),
    funded_amnt_inv         REAL NOT NULL,
    term_months             INTEGER NOT NULL CHECK(term_months IN (36, 60)),
    int_rate                REAL NOT NULL CHECK(int_rate >= 0),
    installment             REAL NOT NULL,
    
    -- Realized Cash Collections
    total_pymnt             REAL NOT NULL DEFAULT 0.0,
    total_rec_prncp         REAL NOT NULL DEFAULT 0.0,
    total_rec_int           REAL NOT NULL DEFAULT 0.0,
    total_rec_late_fee      REAL NOT NULL DEFAULT 0.0,
    recoveries              REAL NOT NULL DEFAULT 0.0,
    collection_cost         REAL NOT NULL DEFAULT 0.0,
    last_pymnt_amnt         REAL DEFAULT 0.0,
    
    -- Status & Credit Risk Performance Classification
    loan_status             TEXT NOT NULL,               -- Raw Lending Club status string
    is_confirmed_default    INTEGER DEFAULT NULL,        -- 1 = Charged Off / Default; 0 = Fully Paid; NULL = Active/Ongoing
    delinquency_tier        TEXT NOT NULL,               -- 'Closed Good', 'Closed Default', 'Current', 'Grace Period', 'Late (16-30)', 'Severe Late (31-120)'
    is_seasoned_closed      INTEGER NOT NULL,            -- 1 = Closed/Resolved (Fully Paid, Charged Off), 0 = Ongoing
    last_pymnt_d            TEXT,
    last_credit_pull_d      TEXT,
    policy_code             INTEGER DEFAULT 1,
    
    FOREIGN KEY (loan_id) REFERENCES dim_borrower_credit_profile (loan_id),
    FOREIGN KEY (issue_date_key) REFERENCES dim_calendar_date (date_key),
    FOREIGN KEY (grade_key) REFERENCES dim_loan_grade (grade_key),
    FOREIGN KEY (state_code) REFERENCES dim_geography (state_code)
);

-- ------------------------------------------------------------------------------
-- 2.2 Rejected Credit Applications Fact Table
-- Tracks 27,648,741 rejected submissions.
-- NOTE: rejection_surrogate_id is a database-generated autoincrement ID.
-- Source row order in rejected_2007_to_2018Q4.csv is preserved via source_row_num.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_rejected_applications (
    rejection_surrogate_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_row_num          INTEGER NOT NULL UNIQUE,     -- 1-indexed row number in rejected_2007_to_2018Q4.csv (Strictly Unique)
    app_date_key            INTEGER NOT NULL,            -- FK to dim_calendar_date
    application_date        TEXT NOT NULL,               -- Stated ISO application date
    amount_requested        REAL NOT NULL,               -- Principal requested by applicant ($)
    risk_score              REAL DEFAULT NULL,           -- Credit score proxy (NULL in ~66.9% un-pulled cases)
    dti_ratio               REAL DEFAULT NULL,           -- Debt-to-income percentage (%)
    state_code              TEXT,                        -- FK to dim_geography (nullable)
    zip_code                TEXT,                        -- Masked 3-digit zip code
    emp_length_raw          TEXT,                        -- Stated employment tenure string
    loan_title              TEXT,                        -- Stated loan purpose
    policy_code             INTEGER DEFAULT 0,
    
    FOREIGN KEY (app_date_key) REFERENCES dim_calendar_date (date_key),
    FOREIGN KEY (state_code) REFERENCES dim_geography (state_code)
);

-- ------------------------------------------------------------------------------
-- 2.3 Monthly Underwriting Conversion Funnel Summary Fact Table
-- Pre-aggregated analytical table for sub-second executive BI dashboard rendering.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_underwriting_funnel_monthly (
    funnel_key              INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month              TEXT NOT NULL,
    state_code              TEXT NOT NULL,
    risk_tier               TEXT NOT NULL,
    total_applications      INTEGER NOT NULL,
    accepted_count          INTEGER NOT NULL,
    rejected_count          INTEGER NOT NULL,
    approval_rate_pct       REAL NOT NULL,
    total_requested_amt     REAL NOT NULL,
    total_funded_amt        REAL NOT NULL,
    avg_approved_fico       REAL,
    avg_rejected_score      REAL
);

-- ==============================================================================
-- 3. INDEXES
-- ==============================================================================

-- Fact Accepted Loans Indexes
CREATE INDEX IF NOT EXISTS idx_acc_issue_date ON fact_accepted_loans (issue_date_key);
CREATE INDEX IF NOT EXISTS idx_acc_grade_key  ON fact_accepted_loans (grade_key);
CREATE INDEX IF NOT EXISTS idx_acc_status     ON fact_accepted_loans (loan_status);
CREATE INDEX IF NOT EXISTS idx_acc_state      ON fact_accepted_loans (state_code);
CREATE INDEX IF NOT EXISTS idx_acc_default    ON fact_accepted_loans (is_confirmed_default);
CREATE INDEX IF NOT EXISTS idx_acc_tier       ON fact_accepted_loans (delinquency_tier);
CREATE INDEX IF NOT EXISTS idx_acc_reporting  ON fact_accepted_loans (issue_date_key, grade_key, loan_status, is_confirmed_default);

-- Fact Rejected Applications Indexes
CREATE INDEX IF NOT EXISTS idx_rej_app_date   ON fact_rejected_applications (app_date_key);
CREATE INDEX IF NOT EXISTS idx_rej_state      ON fact_rejected_applications (state_code);
CREATE INDEX IF NOT EXISTS idx_rej_score      ON fact_rejected_applications (risk_score);
CREATE INDEX IF NOT EXISTS idx_rej_source_row ON fact_rejected_applications (source_row_num);

-- Borrower Credit Profile Indexes
CREATE INDEX IF NOT EXISTS idx_borr_fico      ON dim_borrower_credit_profile (fico_range_low, fico_range_high);
CREATE INDEX IF NOT EXISTS idx_borr_income    ON dim_borrower_credit_profile (annual_inc);
CREATE INDEX IF NOT EXISTS idx_borr_dti       ON dim_borrower_credit_profile (dti);

-- Dimension Calendar Indexes
CREATE INDEX IF NOT EXISTS idx_cal_year_month ON dim_calendar_date (year_month);

-- ==============================================================================
-- 4. INGESTION CHECKPOINTS & AUDIT CONTROLS
-- Supports idempotent execution, transaction rollback recovery, and checkpoint/resume.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS etl_ingestion_checkpoints (
    pipeline_name       TEXT PRIMARY KEY,                -- 'accepted_loans', 'rejected_applications'
    last_chunk_index    INTEGER NOT NULL,                -- 0-indexed last safely committed chunk
    rows_ingested       INTEGER NOT NULL,                -- Cumulative rows safely committed
    status              TEXT NOT NULL,                   -- 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    checksum_verified   TEXT,                            -- SHA256 / row hash
    last_updated_at     TEXT NOT NULL                    -- ISO timestamp of last commit
);

