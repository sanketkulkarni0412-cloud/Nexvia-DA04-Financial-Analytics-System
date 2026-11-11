-- ==============================================================================
-- Financial Analytics and Risk Reporting System (DA-04)
-- Component: Enterprise Dimensional Data Warehouse Schema (Star Schema)
-- Engine Compatibility: ANSI SQL / PostgreSQL / Modern Relational Warehouses
-- Documentation Ref: documentation/SQL_DATABASE_DESIGN.md
-- ==============================================================================

-- ==============================================================================
-- 1. DIMENSION TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1.1 Calendar Date Dimension
-- Continuous temporal hierarchy spanning 2007 through 2026.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_calendar_date (
    date_key                    INTEGER PRIMARY KEY,             -- Format: YYYYMMDD (e.g., 20151201)
    full_date                   DATE NOT NULL,                   -- Exact calendar date
    year                        INTEGER NOT NULL,                -- e.g., 2015
    quarter                     INTEGER NOT NULL,                -- 1, 2, 3, 4
    month                       INTEGER NOT NULL,                -- 1 to 12
    month_name                  VARCHAR(15) NOT NULL,            -- 'January', 'December', etc.
    year_month                  VARCHAR(7) NOT NULL,             -- '2015-12'
    year_quarter                VARCHAR(7) NOT NULL,             -- '2015-Q4'
    fiscal_year                 INTEGER NOT NULL,                -- e.g., 2015
    fiscal_quarter              VARCHAR(6) NOT NULL              -- 'FY15-Q4'
);

-- ------------------------------------------------------------------------------
-- 1.2 Loan Grade & Risk Rating Dimension
-- Encapsulates Lending Club underwriting tiers and illustrative risk benchmarks.
-- NOTE: Basel risk weights and target loss caps are illustrative analytical assumptions,
-- NOT official statutory requirements or Lending Club contractual stipulations.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_loan_grade (
    grade_key                   INTEGER PRIMARY KEY,             -- Surrogate key (1 to 35)
    grade                       CHAR(1) NOT NULL,                -- Primary credit tier: 'A' through 'G'
    sub_grade                   VARCHAR(2) NOT NULL UNIQUE,      -- Granular subgrade: 'A1' through 'G5'
    grade_rank                  INTEGER NOT NULL,                -- Ordinal rank (1 for A1, 35 for G5)
    regulatory_tier             VARCHAR(20) NOT NULL,            -- 'Prime', 'Near-Prime', 'Subprime', 'High-Risk'
    illustrative_basel_weight   NUMERIC(5,2) NOT NULL,           -- Illustrative Basel II credit risk weight (e.g., 20.00%, 150.00%)
    illustrative_target_loss_cap NUMERIC(5,2) NOT NULL,          -- Illustrative annual default rate threshold (%)
    CONSTRAINT chk_grade CHECK (grade IN ('A', 'B', 'C', 'D', 'E', 'F', 'G'))
);

-- ------------------------------------------------------------------------------
-- 1.3 Geography Dimension
-- Regional classification covering all US states, territories, and census divisions.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_geography (
    state_code                  CHAR(2) PRIMARY KEY,             -- US 2-letter state abbreviation ('CA', 'NY', etc.)
    state_name                  VARCHAR(50) NOT NULL,            -- 'California', 'New York', etc.
    census_region               VARCHAR(20) NOT NULL,            -- 'West', 'Northeast', 'Midwest', 'South'
    economic_division           VARCHAR(30) NOT NULL,            -- 'Pacific', 'Middle Atlantic', etc.
    is_active_lending           SMALLINT NOT NULL DEFAULT 1      -- Flag indicating regulatory lending permission
);

-- ------------------------------------------------------------------------------
-- 1.4 Borrower Credit Profile Dimension (Loan-Level Origination Snapshot)
-- IMPORTANT ARCHITECTURAL DECISION:
-- In raw Lending Club datasets, member_id is 100.0% NULL (stripped for privacy).
-- Borrower identity across multiple loans cannot be established without fabricating linkages.
-- This table records the credit profile snapshot at origination, uniquely anchored by loan_id.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_borrower_credit_profile (
    loan_id                     VARCHAR(32) PRIMARY KEY,         -- Natural Lending Club loan identifier
    annual_inc                  NUMERIC(14,2),                   -- Stated gross annual income ($)
    emp_length                  VARCHAR(20),                     -- Stated employment length category ('< 1 year', '10+ years')
    emp_length_years            SMALLINT,                        -- Clean ordinal numeric years (0 to 10)
    home_ownership              VARCHAR(20),                     -- 'RENT', 'MORTGAGE', 'OWN', 'OTHER'
    verification_status         VARCHAR(30),                     -- 'Verified', 'Source Verified', 'Not Verified'
    dti                         NUMERIC(7,2),                    -- Debt-to-income ratio (percentage)
    fico_range_low              INTEGER,                         -- Lower FICO bureau score bound
    fico_range_high             INTEGER,                         -- Upper FICO bureau score bound
    fico_midpoint               INTEGER,                         -- Derived FICO score: (low + high) / 2
    open_acc                    INTEGER,                         -- Count of open credit lines
    pub_rec                     INTEGER,                         -- Count of derogatory public records
    revol_bal                   NUMERIC(14,2),                   -- Total revolving credit balance ($)
    revol_util                  NUMERIC(6,2),                    -- Revolving line utilization percentage (%)
    total_acc                   INTEGER,                         -- Total credit lines in borrower credit history
    earliest_cr_line            VARCHAR(15),                     -- Date/Month of earliest credit line
    CONSTRAINT chk_fico_valid CHECK (fico_range_low IS NULL OR (fico_range_low >= 300 AND fico_range_low <= 850))
);

-- ------------------------------------------------------------------------------
-- 1.5 Financial Budget Structure (Managerial Variance Inputs)
-- IMPORTANT ARCHITECTURAL DECISION:
-- No actual budget dataset has been supplied in the raw Lending Club archive.
-- All numeric budget metrics default to NULL (marked UNAVAILABLE) until official data
-- is supplied or specific illustrative figures are explicitly approved.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_financial_budget (
    budget_id                   SERIAL PRIMARY KEY,
    year_month                  VARCHAR(7) NOT NULL,             -- Planning month (YYYY-MM)
    grade                       CHAR(1) NOT NULL,                -- Target credit grade ('A' through 'G')
    budgeted_volume             NUMERIC(14,2) DEFAULT NULL,      -- Budgeted origination target ($) [NULL until supplied]
    targeted_yield              NUMERIC(6,4) DEFAULT NULL,       -- Target gross portfolio yield (%) [NULL until supplied]
    loss_provision_cap          NUMERIC(14,2) DEFAULT NULL,      -- Planned credit loss reserve budget ($) [NULL until supplied]
    budgeted_opex               NUMERIC(14,2) DEFAULT NULL,      -- Operating expense budget ($) [NULL until supplied]
    is_approved_assumption      SMALLINT NOT NULL DEFAULT 0,     -- 0 = Pending Official Supply, 1 = Approved Assumption
    notes                       VARCHAR(255) DEFAULT 'Budget data pending official supply',
    CONSTRAINT chk_budget_grade CHECK (grade IN ('A', 'B', 'C', 'D', 'E', 'F', 'G'))
);

-- ==============================================================================
-- 2. FACT TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 2.1 Accepted Loan Contracts Fact Table
-- Tracks 2,260,668 validated loan originations ($34,016,115,925.00 funded balance).
-- ------------------------------------------------------------------------------
CREATE TABLE fact_accepted_loans (
    loan_id                     VARCHAR(32) PRIMARY KEY,         -- Natural Lending Club loan identifier
    issue_date_key              INTEGER NOT NULL,                -- Foreign key to dim_calendar_date
    grade_key                   INTEGER NOT NULL,                -- Foreign key to dim_loan_grade
    state_code                  CHAR(2) NOT NULL,                -- Foreign key to dim_geography
    
    -- Principal & Contract Terms
    loan_amnt                   NUMERIC(12,2) NOT NULL,          -- Stated principal requested ($)
    funded_amnt                 NUMERIC(12,2) NOT NULL,          -- Principal committed by Lending Club ($)
    funded_amnt_inv             NUMERIC(12,2) NOT NULL,          -- Principal funded by syndication investors ($)
    term_months                 INTEGER NOT NULL,                -- Amortization term: 36 or 60 months
    int_rate                    NUMERIC(6,4) NOT NULL,           -- Contractual interest rate percentage (e.g., 14.4900)
    installment                 NUMERIC(10,2) NOT NULL,          -- Scheduled monthly repayment obligation ($)
    
    -- Realized Cash Collections & P&L Drivers
    total_pymnt                 NUMERIC(14,2) NOT NULL DEFAULT 0.00, -- Cumulative total cash payments received ($)
    total_rec_prncp             NUMERIC(14,2) NOT NULL DEFAULT 0.00, -- Realized principal cash collected ($)
    total_rec_int               NUMERIC(14,2) NOT NULL DEFAULT 0.00, -- Realized interest income earned ($)
    total_rec_late_fee          NUMERIC(10,2) NOT NULL DEFAULT 0.00, -- Realized late fee penalty income ($)
    recoveries                  NUMERIC(12,2) NOT NULL DEFAULT 0.00, -- Post charge-off asset recoveries collected ($)
    collection_cost             NUMERIC(10,2) NOT NULL DEFAULT 0.00, -- Collection agency recovery fees ($)
    last_pymnt_amnt             NUMERIC(10,2) DEFAULT 0.00,      -- Cash amount of last received payment ($)
    
    -- Status & Credit Risk Performance Classification
    loan_status                 VARCHAR(50) NOT NULL,            -- Raw Lending Club status string
    is_confirmed_default        SMALLINT DEFAULT NULL,           -- 1 = Charged Off / Default; 0 = Fully Paid; NULL = Ongoing/Unresolved
    delinquency_tier            VARCHAR(30) NOT NULL,            -- 'Closed Good', 'Closed Default', 'Current', 'Grace Period', 'Late (16-30)', 'Severe Late (31-120)'
    is_seasoned_closed          SMALLINT NOT NULL,               -- 1 = Seasoned completed loan (Fully Paid, Charged Off), 0 = Active
    last_pymnt_d                VARCHAR(15),                     -- Month and year of last cash collection (Mon-YYYY)
    last_credit_pull_d          VARCHAR(15),                     -- Date of most recent credit bureau inquiry
    policy_code                 SMALLINT DEFAULT 1,              -- 1 = Publicly available, 2 = New product
    
    -- Referential Integrity Constraints
    CONSTRAINT fk_loan_profile FOREIGN KEY (loan_id) REFERENCES dim_borrower_credit_profile (loan_id),
    CONSTRAINT fk_issue_date FOREIGN KEY (issue_date_key) REFERENCES dim_calendar_date (date_key),
    CONSTRAINT fk_loan_grade FOREIGN KEY (grade_key) REFERENCES dim_loan_grade (grade_key),
    CONSTRAINT fk_loan_state FOREIGN KEY (state_code) REFERENCES dim_geography (state_code),
    
    -- Accounting & Domain Constraints
    CONSTRAINT chk_loan_positive CHECK (loan_amnt > 0 AND funded_amnt > 0),
    CONSTRAINT chk_loan_term CHECK (term_months IN (36, 60)),
    CONSTRAINT chk_int_rate_pos CHECK (int_rate >= 0.0000)
);

-- ------------------------------------------------------------------------------
-- 2.2 Rejected Credit Applications Fact Table
-- Tracks 27,648,741 rejected credit submissions.
-- NOTE: rejection_surrogate_id is a database-generated autoincrement sequence.
-- Source row number in rejected_2007_to_2018Q4.csv is preserved in source_row_num.
-- ------------------------------------------------------------------------------
CREATE TABLE fact_rejected_applications (
    rejection_surrogate_id      BIGSERIAL PRIMARY KEY,           -- Database-generated surrogate identifier
    source_row_num              INTEGER NOT NULL UNIQUE,         -- 1-indexed line number in rejected_2007_to_2018Q4.csv (Strictly Unique)
    app_date_key                INTEGER NOT NULL,                -- Foreign key to dim_calendar_date
    application_date            DATE NOT NULL,                   -- Stated calendar application date
    amount_requested            NUMERIC(12,2) NOT NULL,          -- Principal applied for ($)
    risk_score                  NUMERIC(6,1) DEFAULT NULL,       -- Credit score proxy (NULL in ~66.9% of rejections)
    dti_ratio                   NUMERIC(7,2) DEFAULT NULL,       -- Debt-to-income percentage (%)
    state_code                  CHAR(2),                         -- Foreign key to dim_geography (nullable)
    zip_code                    VARCHAR(10),                     -- Masked 3-digit zip code
    emp_length_raw              VARCHAR(20),                     -- Stated applicant employment tenure string
    loan_title                  VARCHAR(150),                    -- Stated borrowing purpose
    policy_code                 SMALLINT DEFAULT 0,              -- Lending Club underwriting policy code
    
    CONSTRAINT fk_rej_date FOREIGN KEY (app_date_key) REFERENCES dim_calendar_date (date_key),
    CONSTRAINT fk_rej_state FOREIGN KEY (state_code) REFERENCES dim_geography (state_code)
);

-- ------------------------------------------------------------------------------
-- 2.3 Monthly Underwriting Conversion Funnel Summary Fact Table
-- Pre-aggregated analytical table for sub-second executive BI dashboard rendering.
-- ------------------------------------------------------------------------------
CREATE TABLE fact_underwriting_funnel_monthly (
    funnel_key                  SERIAL PRIMARY KEY,
    year_month                  VARCHAR(7) NOT NULL,             -- Cohort month (YYYY-MM)
    state_code                  CHAR(2) NOT NULL,                -- State code
    risk_tier                   VARCHAR(20) NOT NULL,            -- Prime, Near-Prime, Subprime, High-Risk
    total_applications          INTEGER NOT NULL,                -- Accepted + Rejected
    accepted_count              INTEGER NOT NULL,                -- Accepted loans count
    rejected_count              INTEGER NOT NULL,                -- Rejected applications count
    approval_rate_pct           NUMERIC(6,2) NOT NULL,           -- (accepted / total) * 100
    total_requested_amt         NUMERIC(16,2) NOT NULL,          -- Total principal demand ($)
    total_funded_amt            NUMERIC(16,2) NOT NULL,          -- Total funded commitment ($)
    avg_approved_fico           NUMERIC(5,1),                    -- Average FICO of accepted cohort
    avg_rejected_score          NUMERIC(5,1)                     -- Average risk score of rejected cohort
);

-- ==============================================================================
-- 3. INDEXING STRATEGY
-- ==============================================================================

-- Fact Accepted Loans Indexes
CREATE INDEX idx_acc_issue_date ON fact_accepted_loans (issue_date_key);
CREATE INDEX idx_acc_grade_key  ON fact_accepted_loans (grade_key);
CREATE INDEX idx_acc_status     ON fact_accepted_loans (loan_status);
CREATE INDEX idx_acc_state      ON fact_accepted_loans (state_code);
CREATE INDEX idx_acc_default    ON fact_accepted_loans (is_confirmed_default);
CREATE INDEX idx_acc_tier       ON fact_accepted_loans (delinquency_tier);
CREATE INDEX idx_acc_reporting  ON fact_accepted_loans (issue_date_key, grade_key, loan_status, is_confirmed_default);

-- Fact Rejected Applications Indexes
CREATE INDEX idx_rej_app_date   ON fact_rejected_applications (app_date_key);
CREATE INDEX idx_rej_state      ON fact_rejected_applications (state_code);
CREATE INDEX idx_rej_score      ON fact_rejected_applications (risk_score);
CREATE INDEX idx_rej_source_row ON fact_rejected_applications (source_row_num);

-- Borrower Credit Profile Indexes
CREATE INDEX idx_borr_fico      ON dim_borrower_credit_profile (fico_range_low, fico_range_high);
CREATE INDEX idx_borr_income    ON dim_borrower_credit_profile (annual_inc);
CREATE INDEX idx_borr_dti       ON dim_borrower_credit_profile (dti);

-- Dimension Calendar Indexes
CREATE INDEX idx_cal_year_month ON dim_calendar_date (year_month);

-- ==============================================================================
-- 4. INGESTION CHECKPOINTS & AUDIT CONTROLS
-- Supports idempotent execution, transaction rollback recovery, and checkpoint/resume.
-- ==============================================================================
CREATE TABLE etl_ingestion_checkpoints (
    pipeline_name       VARCHAR(50) PRIMARY KEY,         -- 'accepted_loans', 'rejected_applications'
    last_chunk_index    INTEGER NOT NULL,                -- 0-indexed last safely committed chunk
    rows_ingested       INTEGER NOT NULL,                -- Cumulative rows safely committed
    status              VARCHAR(20) NOT NULL,            -- 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    checksum_verified   VARCHAR(64),                     -- SHA256 / row hash
    last_updated_at     TIMESTAMP NOT NULL               -- Timestamp of last transaction commit
);

