# Financial Analytics and Risk Reporting System

**Project ID:** DA-04  
**Deadline:** 20 November 2026  
**Role:** Senior Data Engineering Architect, Financial Data Analyst & Technical Mentor  
**Domain:** Corporate Financial Analytics, Credit Risk Management & Business Intelligence  

---

## 1. Executive Summary

The **Financial Analytics and Risk Reporting System (DA-04)** is an institutional-grade, end-to-end financial data engineering and analytics solution. Designed to simulate the analytical infrastructure of modern commercial lending institutions and fintech banking platforms, this system integrates robust financial accounting, credit risk modeling (aligned with Basel II / IFRS 9), interactive visual business intelligence, and robotic process automation.

The primary objective is to transform raw, granular transactional and loan repayment data into auditable financial statements, regulatory risk scorecards, real-time executive dashboards, and automated monthly dissemination workflows.

---

## 1.1 Official Assessment Dataset & Current Status

- **Official Assessment Resource:** [Kaggle Lending Club Loan Data (2007–2018Q4)](https://www.kaggle.com/datasets/wordsforthewise/lending-club) published by Nathan George (*wordsforthewise*).
  - Primary Archive: `accepted_2007_to_2018Q4.csv.gz` (2,260,668 loans, 151 columns) and `rejected_2007_to_2018Q4.csv.gz` (27,648,741 rejected applications, 9 columns).
- **Master Production Warehouse:** [`warehouse.db`](file:///d:/nexvia%20-%201/Financial-Analytics-System/warehouse.db) (1.00 GB, SQLite 3 WAL mode) stores the complete Star Schema dimensional warehouse containing:
  - `fact_accepted_loans`: **2,260,668 records** ($34.00B in total funded capital)
  - `fact_rejected_applications`: **27,648,741 records**
  - Dimension tables: `dim_borrower_credit_profile`, `dim_loan_grade`, `dim_geography`, `dim_date`, `dim_financial_budget`
  - Authoritative SQL Views: `vw_portfolio_pnl_monthly`, `vw_portfolio_balance_sheet_summary`, `vw_portfolio_delinquency_aging`, `vw_portfolio_vintage_performance`, `vw_reconciliation_audit`.
- **System Parity & Governance:** 100% strictly read-only execution against `warehouse.db`. Zero modifications to raw datasets or historical financial ledgers.

---

## 2. Core Deliverables & Capabilities

| Module | Core Deliverable | Primary Tooling | Key Output |
| :--- | :--- | :--- | :--- |
| **01. Accounting Engine** | Profit & Loss (P&L) Income Statement | SQL & Python | Monthly & quarterly revenue, Net Interest Margin (NIM), Operating Expenses, and Net Income |
| **02. Balance Sheet Module** | Balance Sheet Summaries | Python & Advanced Excel | Loan portfolio assets, loan loss provisions (ALLL), liability breakdown, and capital adequacy |
| **03. Financial Planning** | Budget vs. Actual Variance Analysis | SQL & Excel Power Pivot | Dollar variance ($) and percentage variance (%) across volume and yield rates |
| **04. Credit Risk Engine** | Regulatory Credit Risk Scorecards | Python (`scikit-learn`, `scipy`) | Probability of Default (PD), Loss Given Default (LGD), Exposure at Default (EAD), and Expected Loss (EL) |
| **05. Visual BI** | Interactive Executive Dashboards | Qlik Sense & Power Pivot | Drill-down portfolio health, risk-adjusted returns, cohort vintage curves, and geo-risk maps |
| **06. Automation** | Automated Monthly Reporting | Power Automate & Python | Scheduled statement rendering, PDF/Excel generation, and stakeholder email distribution |
| **07. Governance & CI** | Version Control & Reproducibility | Git, GitHub & `pytest` | Automated data quality verification, unit tests, and production code documentation |

---

## 3. Technology Stack & Architecture

```
+---------------------------------------------------------------------------------------+
|                                    DATA SOURCES                                       |
|                  Lending Club Portfolio Data & Financial Budgets                      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                            DATA PIPELINE & REFINEMENT                                 |
|               Python (Data Ingestion, Auditing, Cleansing, Imputation)                 |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               SQL DATA WAREHOUSE                                      |
|                 Dimensional Modeling (Star Schema: Facts & Dimensions)                |
|                    SQLite / PostgreSQL / Analytics Data Marts                         |
+---------------------------------------------------------------------------------------+
                   /                                   \
                  v                                     v
+-----------------------------------+   +-----------------------------------------------+
|      FINANCIAL REPORTING          |   |            CREDIT RISK MODELING               |
|  - Profit & Loss (P&L) Engine     |   |  - Feature Selection (WoE / IV)               |
|  - Balance Sheet Summaries        |   |  - Logistic Regression Scorecard              |
|  - Budget vs. Actual Analysis     |   |  - PD, LGD, EAD, Expected Loss (EL) Model     |
+-----------------------------------+   +-----------------------------------------------+
                   \                                   /
                    v                                 v
+---------------------------------------------------------------------------------------+
|                        ANALYTICS & BUSINESS INTELLIGENCE                              |
|                 Qlik Sense Dashboards & Excel Power Pivot DAX Models                  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                          REPORT DISTRIBUTION & AUTOMATION                             |
|          Power Automate Desktop / Cloud Flow + Python Automated Email Dispatch        |
+---------------------------------------------------------------------------------------+
```

---

## 4. Directory Structure

```text
Financial-Analytics-System/
├── dataset/                    # Raw and curated source datasets
├── data_cleaning/              # Python ingestion, auditing, and cleaning scripts
├── sql/                        # DDL schemas, Star Schema, views, and financial queries
├── financial_reports/          # P&L, Balance Sheet, and Budget vs. Actual engines
├── credit_risk/                # Credit risk scorecard, WoE/IV, and PD/LGD/EAD models
├── qlik_dashboard/             # Qlik Sense app scripts, load scripts, and data models
├── power_automation/           # Power Automate workflows, scheduling, and email scripts
├── documentation/              # Technical architecture and metric definitions
│   ├── PROJECT_ARCHITECTURE.md # System architecture and dimensional data model
│   └── METRIC_DEFINITIONS.md   # Mathematical formulas and business definitions
├── tests/                      # Unit tests, data reconciliation, and validation suites
├── reports/                    # Generated financial statements, scorecards, and PDFs
├── .gitignore                  # Git exclusion rules
├── CHANGELOG.md                # Development milestone changelog
├── PROJECT_PLAN.md             # End-to-end assessment roadmap and delivery schedule
├── README.md                   # Project overview (this file)
└── requirements.txt            # Python dependencies specification
```

---

## 5. Development Environment Audit & Prerequisites

An audit of the host Windows environment conducted during Phase 1 revealed:

- **Python Runtime:** `Python 3.13.1` (Available)
- **Version Control:** `Git 2.50.1.windows.1` (Available)
- **IDE:** `Microsoft VS Code 1.142.0` (Available)
- **Database Engine:** Built-in Python `sqlite3`, `SQLAlchemy 2.0.51`, and `psycopg2-binary 2.9.12` installed.
- **Spreadsheet / BI:** `Microsoft Office 16 Excel` with Power Pivot capabilities (Available).
- **Python Libraries to Install:** `pandas`, `numpy`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`, `openpyxl`, `xlsxwriter`, `pytest`.

*Note: Please see the Phase 1 Environment Audit Report for package installation commands.*

---

## 6. How to Run & Verify

### Step 1: Initialize Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Verified Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run Validation Suite
```powershell
pytest tests/
```

---

## 7. Compliance & Standards
## 4. Assessment Implementation Status (100% Complete)

| Assessment Step | Focus Area | Status | Core Implementation Assets | Key Metric / Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Step 1: Public Dataset** | Master Warehouse Ingestion | **COMPLETE** | `warehouse.db`, Star Schema | 2,260,668 accepted loans, 27.65M rejected |
| **Step 2: Financial Statements** | P&L and Balance Sheet (SQL/Excel) | **COMPLETE** | `p_and_l_engine.py`, `excel_report_builder.py` | 8-sheet Excel report, $34.00B Funded, $8.74B Carrying Value |
| **Step 3: Budget Variance** | Budget vs. Actual & Drivers | **COMPLETE** | `financial_reports/budget_variance.py` | Rate-Volume-Mix 3-factor decomposition, 0.00 variance error |
| **Step 4: Credit Scorecard** | WOE / Logistic Scorecard & Risk Bands | **COMPLETE** | `final_scorecard.py`, `scorecard_scaling.py` | 10 predictors, In-Time AUC 0.6828, 2016 OOT AUC 0.6770, KS 25.15% |
| **Step 5: Interactive BI** | Qlik Sense & Standalone Dashboard | **COMPLETE** | `qlik_dashboard/load_script.qvs`, `.html` | Modular dual-delivery, zero-dependency browser BI, 6 data extracts |
| **Step 6: Automation Pipeline**| Monthly Board Report PDF & Email | **COMPLETE** | `generate_monthly_packet.py`, `email_dispatcher.py` | 2-page vector PDF (68 KB), dry-run safe SMTP, Power Automate flow spec |
| **Step 7: Metric Definitions** | Finance Trust & Governance Standards | **COMPLETE** | `documentation/METRIC_DEFINITIONS.md` | GAAP, CECL, Basel II / IFRS 9 definitions with mathematical formulas |

---

## 5. Verification & Test Suite Execution

The entire analytical system is backed by comprehensive automated test suites using `pytest`:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run all test suites
pytest tests/ -v
```

**Test Coverage Summary:**
- `tests/test_power_automation.py`: 7 tests (PDF generation, metrics, dry-run safety, flow spec)
- `tests/test_budget_variance.py`: 6 tests (reconciliation, rate-volume-mix identities, budget flags)
- `tests/test_qlik_dashboard.py`: 7 tests (extract schemas, KPI reconciliation, monotonicity, HTML)
- `tests/test_final_scorecard.py`: 3 tests (model fit, coefficients, probability scaling)
- `tests/test_oot_validation.py`: 1 test (2016 out-of-time stability, AUC drift bounds)
- `tests/test_scorecard_scaling.py`: 4 tests (PDO scaling, points monotonicity, risk bands)
- `tests/test_reason_codes.py`: 1 test (adverse action reason code generation)
- `tests/test_financial_reporting.py` & `test_excel_financial_report.py`: 22 tests (P&L and balance sheet accounting)
- **Total:** 100% of tests passing cleanly with zero warnings or errors.

---

## 6. Industry & Governance Standards

- **Financial Accounting:** Standard GAAP accrual and matching principles for loan interest, provisions, fee amortization, and non-performing loan accounting.
- **Credit Risk Regulations:** Basel II / Basel III Pillar 1 Internal Ratings-Based (IRB) approach and IFRS 9 / CECL forward-looking Expected Credit Loss (ECL) staging.
- **Model Risk Management:** Federal Reserve SR 11-7 / OCC 2011-12 guidance for model development, calibration, out-of-time validation, and adverse action attribution.
- **Software Engineering:** PEP 8 Python conventions, modular architecture, ANSI SQL standards, fail-safe credential handling, and deterministic audit trails.
