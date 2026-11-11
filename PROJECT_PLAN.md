# Project Development Plan & Assessment Roadmap

**Project Name:** Financial Analytics and Risk Reporting System  
**Project ID:** DA-04  
**Project Deadline:** 20 November 2026  
**Status:** In Progress (Phase 1 Initialized)  

---

## 1. Assessment Objectives & Requirement Mapping

The assessment mandates an end-to-end financial analytics ecosystem addressing seven core requirements:

| Ref | Assessment Requirement | Technical Implementation | Target Milestone | Deliverable Artifacts |
| :---: | :--- | :--- | :--- | :--- |
| **REQ-1** | **Financial Data Pipeline & Schema Design** | Python cleaning, schema validation, and SQL Star Schema data warehousing | Phase 2 & 3 | `dataset/`, `data_cleaning/`, `sql/schema.sql` |
| **REQ-2** | **Profit & Loss (P&L) Reporting** | SQL aggregation & Python financial statement generation | Phase 4 | `financial_reports/p_and_l_engine.py`, P&L tables |
| **REQ-3** | **Balance Sheet Summaries** | Balance sheet generation, asset/liability grouping, capital adequacy | Phase 4 | `financial_reports/balance_sheet_engine.py`, BS schedules |
| **REQ-4** | **Budget vs. Actual Variance Analysis** | Budget target integration, variance calculations ($ and %), and heatmaps | Phase 4 | `financial_reports/budget_variance.py`, Excel variance model |
| **REQ-5** | **Credit Risk Scorecard & Default Modeling** | WoE/IV transformation, Logistic Regression, Scorecard scaling, PD/LGD/EAD/EL | Phase 5 | `credit_risk/scorecard_model.py`, scorecard tables |
| **REQ-6** | **Interactive Qlik Sense & BI Dashboards** | Associative data model, executive KPIs, vintage analysis, risk drill-downs | Phase 6 | `qlik_dashboard/`, QVF/QVS scripts, Power Pivot models |
| **REQ-7** | **Automated Monthly Distribution & Auditing** | Power Automate workflow, Python report dispatcher, and automated test suite | Phase 7 | `power_automation/`, `tests/`, final monthly packages |

---

## 2. Multi-Phase Development Roadmap

### Phase 1: Environment Audit & Project Initialization (Current Phase)
- **Scope:**
  - Audit Windows OS environment: Python, Git, VS Code, SQL engines, Excel capabilities.
  - Formulate dependency manifests (`requirements.txt`).
  - Establish project directory structure.
  - Deliver core architecture documentation and metric formulas.
  - Recommend and justify the optimal dataset (Lending Club).
- **Exit Criteria:** All project folders initialized, environment audit completed, and review approved by the client/assessor.

---

### Phase 2: Data Acquisition, Ingestion & Exploratory Data Analysis (EDA)
- **Scope:**
  - Ingest the Lending Club loan dataset into `dataset/raw/`.
  - Perform preliminary data profiling: shape, data types, null counts, duplicate records.
  - Implement Exploratory Data Analysis (EDA) scripts analyzing loan distributions, interest rate spreads, default distributions, and loan grades (A through G).
  - Produce an EDA summary report with statistical distribution tables.
- **Exit Criteria:** Documented dataset profile, confirmed data dictionary, and clean understanding of missing values.

---

### Phase 3: Data Cleaning, Feature Engineering & SQL Data Warehouse Schema
- **Scope:**
  - Build automated Python cleaning pipeline (`data_cleaning/clean_pipeline.py`).
  - Standardize date formats (`issue_d`, `earliest_cr_line`, `last_pymnt_d`).
  - Handle categorical features (employment length normalization, debt-to-income cleaning).
  - Construct SQL Star Schema in SQLite / PostgreSQL:
    - `fact_loan_origination`
    - `fact_loan_repayment`
    - `dim_borrower`
    - `dim_loan_grade`
    - `dim_geography`
    - `dim_calendar_date`
    - `dim_financial_budget`
  - Populate warehouse tables via SQLAlchemy bulk loaders with transaction integrity.
- **Exit Criteria:** Production-grade SQL schema script (`sql/create_star_schema.sql`), fully loaded data mart, and SQL indexing for high-performance querying.

---

### Phase 4: Financial Statements Engine (P&L, Balance Sheet, Budget vs. Actual)
- **Scope:**
  - **Profit & Loss Engine (`financial_reports/p_and_l_engine.py`):**
    - Calculate Interest Income from repayments.
    - Calculate Non-Interest Income (late fees, origination fees).
    - Model Cost of Funds and Cost of Risk (provision for credit losses / charge-offs).
    - Compute Net Interest Margin (NIM), Operating Profit, and Net Income.
  - **Balance Sheet Engine (`financial_reports/balance_sheet_engine.py`):**
    - Structure Assets: Performing loans, non-performing loans, and Allowance for Loan and Lease Losses (ALLL - contra asset).
    - Structure Liabilities: Investor capital, institutional debt, and accumulated reserves.
    - Compute Liquidity, Non-Performing Loan (NPL) Ratio, and Provision Coverage Ratio (PCR).
  - **Budget vs. Actual Engine (`financial_reports/budget_variance.py`):**
    - Synthesize institutional budget benchmarks (origination volume, targeted yield, maximum default rate).
    - Calculate absolute variance ($) and relative percentage variance (%).
    - Perform Rate-Volume variance decomposition.
- **Exit Criteria:** Exportable Excel financial models (`.xlsx` formatted with professional styling), automated PDF summary generation, and verified balance sheet balance ($Assets = Liabilities + Equity$).

---

### Phase 5: Credit Risk Scorecard & Default Modeling
- **Scope:**
  - Define regulatory default definition (e.g., 90+ days past due, Charged Off, Default).
  - Implement Weight of Evidence (WoE) and Information Value (IV) transformation for continuous and categorical variables.
  - Train a regularized Logistic Regression model for Probability of Default (PD).
  - Scale regression coefficients into an institutional Credit Scorecard:
    $$\text{Score} = \text{Offset} + \text{Factor} \times \ln(\text{Odds})$$
  - Model Loss Given Default (LGD) and Exposure at Default (EAD).
  - Compute Expected Loss ($EL = PD \times LGD \times EAD$) across cohorts and grades.
  - Validate model performance: ROC-AUC curve, Gini coefficient, and Kolmogorov-Smirnov (KS) test.
- **Exit Criteria:** Calibrated Credit Risk Scorecard table, model validation metrics report ($AUC > 0.70$), and portfolio Expected Loss allocations.

---

### Phase 6: Interactive Qlik Sense Dashboards & Excel Power Pivot Models
- **Scope:**
  - **Qlik Sense Dashboard:**
    - Develop Qlik Sense Load Script (`qlik_dashboard/load_script.qvs`) connecting to the SQL data warehouse.
    - Build associative data model linking financial facts with borrower dimensions.
    - Create Executive Overview Sheet: Portfolio KPIs (Total Originations, Yield, NPL %, Total Expected Loss).
    - Create Credit Risk & Scorecard Sheet: Vintage curves, score distributions, and default probabilities.
    - Create Financial Statement Sheet: Interactive P&L and Balance Sheet with drill-downs by Grade, Term, and Geography.
  - **Excel Power Pivot Alternative:**
    - Construct an `.xlsx` workbook embedding Data Model, DAX measures, and interactive Pivot Tables for environments without Qlik Sense desktop licenses.
- **Exit Criteria:** Tested and functional Qlik Sense app / load scripts, DAX measurement suite, and interactive dashboard user documentation.

---

### Phase 7: Monthly Report Automation, Testing & Final Assessment Packaging
- **Scope:**
  - Develop Python automated reporting pipeline (`power_automation/generate_monthly_packet.py`).
  - Build Microsoft Power Automate Desktop flow / script for scheduled execution, file archival, and notification triggers.
  - Implement comprehensive test suite in `tests/`:
    - `test_data_cleaning.py`: Missing value and data integrity checks.
    - `test_sql_reconciliation.py`: GL balance reconciliation and row-count verification.
    - `test_financial_metrics.py`: Mathematical accuracy of P&L and Balance Sheet equations.
    - `test_scorecard.py`: WoE monotonicity and score range constraints.
  - Generate final portfolio showcase package: executive summary presentation, technical user manual, and code repository audit.
- **Exit Criteria:** 100% test pass rate in `pytest`, scheduled automated execution demonstration, and final assessment sign-off.

---

## 3. Risk Management & Technical Mitigation Matrix

| Risk Category | Identified Risk | Impact | Probability | Mitigation Strategy |
| :--- | :--- | :---: | :---: | :--- |
| **Data Sizing** | Lending Club datasets can exceed 1M rows, challenging in-memory processing. | High | High | Implement chunked reading, selective column parsing, and SQL database offloading with optimized indexing. |
| **Python 3.13 Compatibility** | Python 3.13 is a very recent release; some C-extension wheels (`scipy`, `scikit-learn`) might require specific compatible versions. | Medium | Medium | Verify pre-built binary wheels on PyPI; fall back to well-supported compiler flags or an isolated virtualenv if necessary. |
| **Software Licensing** | Qlik Sense Desktop may require enterprise credentials or active desktop trial. | Medium | Medium | Provide modular dual-delivery: (1) Standard Qlik Sense load scripts (`.qvs`) and app specs, and (2) Production Excel Power Pivot + DAX data model providing identical analytical capability. |
| **Data Quality** | Real-world loan data contains missing borrower fields (e.g., employment length, debt-to-income). | Medium | High | Rigorous domain-specific imputation (median grouping by loan grade, explicit "Unknown" categories) rather than arbitrary dropna. |
| **Model Calibration** | Severe class imbalance in default rates (~15-20% default rate). | High | High | Utilize balanced class weighting in logistic regression, stratified k-fold cross-validation, and evaluate with PR-AUC / ROC-AUC rather than raw accuracy. |

---

## 4. Definition of Done (DoD)

A milestone is considered complete only when:
1. **Source Code:** Written adhering to PEP 8 standards, fully documented with type hints and docstrings.
2. **Execution:** Code executes end-to-end without unhandled exceptions or runtime warnings.
3. **Automated Testing:** Accompanied by unit and reconciliation tests in `tests/` that pass with zero failures.
4. **Documentation:** Accompanied by markdown documentation detailing inputs, outputs, and financial interpretations.
5. **Auditing:** Verified against real financial and risk metrics with zero synthetic or fabricated numbers.
