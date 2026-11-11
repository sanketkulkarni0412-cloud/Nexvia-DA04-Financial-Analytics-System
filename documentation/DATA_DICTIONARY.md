# Financial Analytics Data Dictionary

**Project Name:** Financial Analytics and Risk Reporting System  
**Project ID:** DA-04  
**Official Assessment Resource:** [Kaggle Lending Club Loan Data](https://www.kaggle.com/datasets/wordsforthewise/lending-club) (`wordsforthewise/lending-club`)  
**Underlying Archives:** `accepted_2007_to_2018Q4.csv.gz` (~2.26M rows) & `rejected_2007_to_2018Q4.csv.gz` (~27.6M rows)  
**Sample Profiled:** 51,072 Validated Records × 151 Columns (Identical Schema)  
**Migration Specification:** [`documentation/DATASET_MIGRATION_PLAN.md`](file:///d:/nexvia%20-%201/Financial-Analytics-System/documentation/DATASET_MIGRATION_PLAN.md)  

---

## 1. Overview & Business Taxonomy

This data dictionary formally documents the core transactional, credit risk, and financial accounting fields utilized in the **Financial Analytics and Risk Reporting System (DA-04)**. Each variable is mapped to its data type, business significance, and portfolio missingness percentage.

> [!NOTE]
> **Provenance & Sample Scope:** The metrics below were profiled against an authentic 51,072-record slice of the official `accepted_2007_to_2018Q4.csv` master file. All field definitions, data types, and business meanings are 100% applicable to both this sample and the full 2.26-million-loan Kaggle master archive.

---

## 2. Core Financial & Credit Risk Data Dictionary

| Field Name | Storage Data Type | Description | Financial / Business Meaning | Missing Values | Missing (%) |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `loan_amnt` | Continuous / Float | The listed amount of the loan applied for by the borrower. | Core earning asset on Balance Sheet; basis for installment computation. | 0 | 0.00% |
| `funded_amnt` | Continuous / Float | The total amount committed to that loan at that point in time. | Gross Loan asset balance committed at origination. | 0 | 0.00% |
| `funded_amnt_inv` | Continuous / Float | The total amount committed by individual retail/institutional investors. | Funding liability / institutional investor syndication balance. | 0 | 0.00% |
| `term` | Categorical / String | The number of scheduled monthly payments (36 or 60 months). | Maturity horizon; longer terms exhibit higher default risk. | 0 | 0.00% |
| `int_rate` | Continuous / Float | Contractual annual interest rate charged on the loan. | Top-line Gross Interest Income driver on Profit & Loss statement. | 0 | 0.00% |
| `installment` | Continuous / Float | The monthly payment owed by the borrower if the loan originates. | Monthly cash inflow covering principal amortization and interest revenue. | 0 | 0.00% |
| `grade` | Categorical / Ordinal | Lending Club assigned credit risk rating (A through G). | Primary credit tier; dictates interest pricing and regulatory risk-weighting. | 0 | 0.00% |
| `sub_grade` | Categorical / Ordinal | Granular credit risk sub-rating (A1 to G5). | Refined risk segmentation for Probability of Default (PD) scorecards. | 0 | 0.00% |
| `emp_length` | Categorical / Ordinal | Employment duration in years (< 1 year to 10+ years). | Underwriting stability indicator; borrower repayment capacity proxy. | 3,069 | 6.01% |
| `home_ownership` | Categorical / Nominal | Home ownership status (RENT, OWN, MORTGAGE, OTHER). | Borrower collateral / asset profile indicator. | 0 | 0.00% |
| `annual_inc` | Continuous / Float | Self-reported annual income of the borrower. | Cash flow capacity baseline; denominator in Debt-to-Income (DTI). | 0 | 0.00% |
| `verification_status` | Categorical / Nominal | Indicates if income was verified by LC, not verified, or source verified. | Underwriting information quality / operational risk indicator. | 0 | 0.00% |
| `issue_d` | Date / String | The calendar month and year which the loan was funded. | Vintage origination cohort date; links to dim_calendar_date in Star Schema. | 0 | 0.00% |
| `loan_status` | Categorical / Nominal | Current performance status (Fully Paid, Charged Off, Current, Late). | Fundamental accounting status; defines IFRS 9 staging and P&L provisioning. | 0 | 0.00% |
| `purpose` | Categorical / Nominal | Borrower provided category for the loan request (debt_consolidation, etc.). | Concentration risk driver for portfolio diversification. | 0 | 0.00% |
| `addr_state` | Categorical / Nominal | Borrower home state code (US 2-letter state code). | Geographical risk dimension for dim_geography mapping. | 0 | 0.00% |
| `dti` | Continuous / Float | Debt-to-income ratio (excluding mortgage and requested loan). | Core credit metric measuring existing debt burden relative to gross income. | 1 | 0.00% |
| `fico_range_low` | Integer / Float | The lower boundary of the borrower's FICO credit score pull. | External regulatory credit benchmark; strong negative predictor of default. | 0 | 0.00% |
| `fico_range_high` | Integer / Float | The upper boundary of the borrower's FICO credit score pull. | External credit benchmark complementary to fico_range_low. | 0 | 0.00% |
| `open_acc` | Integer / Float | The number of open credit lines in the borrower's credit file. | Credit depth and active credit facility exposure. | 0 | 0.00% |
| `pub_rec` | Integer / Float | Number of derogatory public records (bankruptcies, tax liens). | Adverse credit event indicator; severe default risk signal. | 0 | 0.00% |
| `revol_bal` | Continuous / Float | Total credit revolving balance across cards and revolving accounts. | Active consumer debt utilization volume. | 0 | 0.00% |
| `revol_util` | Continuous / Float | Revolving line utilization rate (balance / credit limit). | Liquidity strain signal; high utilization correlates with insolvency. | 24 | 0.05% |
| `total_acc` | Integer / Float | The total number of credit lines currently in the borrower's credit file. | Borrower credit history depth and seasoned credit experience. | 0 | 0.00% |
| `total_pymnt` | Continuous / Float | Payments received to date for total amount funded. | Realized cash flow on P&L; used to compute realized yield and recoveries. | 0 | 0.00% |
| `total_rec_prncp` | Continuous / Float | Principal received to date. | Cash recovery reducing Balance Sheet Gross Loan Asset carrying balance. | 0 | 0.00% |
| `total_rec_int` | Continuous / Float | Interest received to date. | Realized Gross Interest Income on Profit & Loss statement. | 0 | 0.00% |
| `total_rec_late_fee` | Continuous / Float | Late fees received to date. | Ancillary Non-Interest Income on Profit & Loss statement. | 0 | 0.00% |
| `recoveries` | Continuous / Float | Post charge-off gross recovery payments collected. | Offset against gross charge-offs, reducing net Provision for Credit Losses. | 0 | 0.00% |
| `collection_recovery_fee` | Continuous / Float | Collection agency fees incurred during recoveries. | Servicing expense deducted from recoveries on P&L. | 0 | 0.00% |
| `last_pymnt_d` | Date / String | Month and year the last payment was received. | Cash flow timing marker; determines delinquency transition timing. | 34 | 0.07% |

---

## 3. Missing Value Taxonomy & Treatment Protocol

| Missingness Tier | Missingness Range | Identified Features | Remediation Strategy in Phase 3 |
| :--- | :---: | :--- | :--- |
| **Zero Missing** | 0.0% | `loan_amnt`, `funded_amnt`, `int_rate`, `grade`, `loan_status`, `term`, `installment` | None required; pristine financial anchors. |
| **Low Missing** | < 2.0% | `annual_inc`, `dti`, `revol_util`, `open_acc` | Group-median imputation segmented by `grade` and `emp_length`. |
| **Moderate Missing** | 2.0% - 15.0% | `emp_length` (6.2%) | Encoded with explicit `'Unknown / Missing'` category to prevent bias in credit scorecards. |
| **High Missing** | > 70.0% | Secondary applicant fields (`annual_inc_joint`, `dti_joint`, `sec_b_fico`) | Filtered or handled via indicator flags (`is_joint_application`). |

---
*Data dictionary generated automatically by `data_cleaning/profile_dataset.py`.*