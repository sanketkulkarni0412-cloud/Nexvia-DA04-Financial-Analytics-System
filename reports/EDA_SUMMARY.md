# Exploratory Data Analysis (EDA) Summary Report

**Project Name:** Financial Analytics and Risk Reporting System  
**Project ID:** DA-04  
**Assessment Phase:** Phase 2 — Data Acquisition & Exploratory Data Analysis  
**Official Assessment Resource:** [Kaggle Lending Club Loan Data](https://www.kaggle.com/datasets/wordsforthewise/lending-club) (`wordsforthewise/lending-club`)  
**Current Dataset Analysed:** Authentic Lending Club Loan Sample (`dataset/raw/lending_club_loans.csv`)  
**Sample Record Count:** 51,072 loans ($767.1M funded volume) | **Total Features:** 151 attributes  
**Migration Specification:** [`documentation/DATASET_MIGRATION_PLAN.md`](file:///d:/nexvia%20-%201/Financial-Analytics-System/documentation/DATASET_MIGRATION_PLAN.md)  

---

## 1. Executive Summary, Data Provenance & Scope

In Phase 2 of the Financial Analytics system, we acquired and audited an authentic institutional sample of **51,072 historical loans** from the Lending Club platform (spanning 151 financial, borrower, and transactional columns).

### Data Provenance & Official Source Alignment:
- **Official Master Archive:** The official assessment resource is the Kaggle Lending Club dataset (`wordsforthewise/lending-club`) consisting of `accepted_2007_to_2018Q4.csv.gz` (~2.26M loans) and `rejected_2007_to_2018Q4.csv.gz` (~27.6M applications).
- **Current Sample Scope:** The 51,072 records analyzed here were drawn from the raw accepted loans archive and possess **100% schema parity** across all 151 columns.
- **Known Sample Limitations:**
  1. *Vintage Concentration:* The sample represents Q4 2015 originations (`Nov-2015` and `Dec-2015`). While highly seasoned (permitting rigorous default and recovery modeling), it does not cover the complete 2007–2018 macro cycle.
  2. *Rejection Funnel:* Does not yet include the 27.6M rejected applicant file, which will be integrated during full-scale data warehouse ingestion.
  3. *Preservation:* This sample is preserved in `dataset/raw/` to serve as a fast local testing benchmark.

### Key Integrity Findings:
- **Completeness of Core Financial Attributes:** Fundamental fields (`loan_amnt`, `int_rate`, `grade`, `loan_status`, `term`, `installment`, `total_pymnt`) have **0.0% missing values**.
- **Duplicate Records:** **0 duplicate records** detected (0.00% duplicates), confirming record-level uniqueness across loans.
- **Historical Default Rate:** The portfolio exhibits an overall default rate of **18.57%** (9,483 bad loans), and a seasoned/closed loan default rate of **20.98%**.

---

## 2. Statistical Distribution of Key Financial Metrics

The empirical summary statistics for core continuous financial variables are tabulated below:

| Financial Metric | Mean | Std Dev | Min | 25% | Median (50%) | 75% | 99th Pct | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`loan_amnt` ($)** | $15,020.22 | $8,670.20 | $1,000.00 | $8,000.00 | $14,000.00 | $20,000.00 | $35,000.00 | $35,000.00 |
| **`int_rate` (%)** | 12.24% | 4.19% | 5.32% | 9.17% | 11.99% | 14.48% | 23.99% | 28.99% |
| **`annual_inc` ($)** | $79,107.89 | $100,479.13 | $0.00 | $48,000.00 | $66,000.00 | $95,000.00 | $263,580.00 | $9,000,000.00 |
| **`dti` (%)** | 19.34% | 9.79% | 0.00% | 12.68% | 18.82% | 25.62% | 38.44% | 999.00% |
| **`fico_range_low`** | 694.4 | 30.9 | 660 | 670 | 685 | 710 | 800 | 845 |
| **`installment` ($)** | $434.11 | $247.32 | $14.77 | $255.31 | $378.15 | $573.58 | $1,172.39 | $1,354.66 |
| **`total_pymnt` ($)** | $15,022.63 | $9,716.30 | $0.00 | $7,427.97 | $12,894.68 | $20,750.24 | $42,395.96 | $57,291.00 |

### Key Statistical Observations:
1. **Loan Sizes:** The average loan balance is **$15,020.22** with a median of **$14,000.00**. Loan originations range from a minimum of **$1,000** to an institutional maximum of **$35,000**.
2. **Interest Rates:** The portfolio average interest yield is **12.24%**, ranging between **5.32%** and **28.99%**.
3. **Borrower Annual Income:** Demonstrates severe positive skewness. While the median borrower earns **$66,000**, the mean is elevated to **$79,107.89** with a 99th percentile of **$263,580**. Robust scaling or winsorization will be applied during Phase 3 feature engineering.
4. **FICO Scores:** Borrower credit scores at origination average **694** (median **685**), with an observed minimum of **660** (Lending Club underwriting floor).

---

## 3. Credit Risk Segmentation & Default Roll-Rates

### 3.1 Loan Volume and Default Distribution by Credit Grade

| Loan Grade | Loan Count | Share of Portfolio | Bad Loans (Defaults) | Default Rate (%) | Average Interest Rate (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Grade A** | 8,810 | 17.3% | 465 | **5.42%** | 6.80% |
| **Grade B** | 15,583 | 30.5% | 1,997 | **14.03%** | 9.93% |
| **Grade C** | 14,843 | 29.1% | 3,030 | **24.07%** | 13.11% |
| **Grade D** | 7,022 | 13.7% | 2,098 | **35.80%** | 16.71% |
| **Grade E** | 3,578 | 7.0% | 1,318 | **45.73%** | 19.16% |
| **Grade F** | 1,005 | 2.0% | 460 | **53.55%** | 23.50% |
| **Grade G** | 231 | 0.5% | 115 | **57.21%** | 27.51% |

> [!IMPORTANT]
> **Monotonic Risk Pricing Law Verified:** The data empirically proves risk-adjusted pricing. As borrower quality moves from Grade A to Grade G:
> - The Default Rate increases monotonically from **5.42%** (Grade A) to **57.21%** (Grade G).
> - The Interest Rate spread widens from **6.80%** to **27.51%** to compensate for the higher expected credit loss.

---

## 4. Visual Exploratory Analysis

All visual figures have been rendered at institutional 300 DPI and saved to [`reports/eda_charts/`](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/eda_charts):

### Figure 1: Loan Volume by Credit Grade
![Loan Grade Distribution](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/loan_grade_distribution.png)

### Figure 2: Default Rate (%) Across Loan Grades
![Default Rate by Grade](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/default_rate_by_grade.png)

### Figure 3: Loan Amount Distribution & Central Tendencies
![Loan Amount Distribution](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/loan_amount_distribution.png)

### Figure 4: Interest Rate Spread Across Credit Grades
![Interest Rate Distribution](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/interest_rate_distribution.png)

### Figure 5: Portfolio Loan Status Performance Breakdown
![Loan Status Distribution](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/loan_status_distribution.png)

### Figure 6: Inter-Metric Financial Correlation Matrix
![Correlation Heatmap](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/correlation_heatmap.png)

### Figure 7: Default Rate by Borrower Employment Tenure
![Default Rate by Employment Length](file:///D:/nexvia - 1/Financial-Analytics-System/reports/eda_charts/default_rate_by_emp_length.png)

---

## 5. Architectural Implications for Phase 3 (Cleaning & Warehouse)

1. **Star Schema Key Mapping:** `issue_d` will be parsed into `date_key` (YYYYMMDD) linking directly to `dim_calendar_date`. `grade` and `sub_grade` will populate `dim_loan_grade`.
2. **P&L Data Mart Synthesis:** Completed loans will allow retrospective P&L modeling with interest collections mapped to revenue and default write-offs mapped to loan loss provisions.
3. **Scorecard Target Variable:** Binary target `is_default` successfully isolates regulatory defaults with clean separation for logistic regression modeling in Phase 5.

---
*Report automatically compiled via `data_cleaning/profile_dataset.py`.*