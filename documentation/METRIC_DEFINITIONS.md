# Financial & Risk Metric Definitions

**Project Name:** Financial Analytics and Risk Reporting System  
**Project ID:** DA-04  
**Classification:** Financial Accounting, Regulatory Compliance & Risk Modeling Standards  
**Document Version:** 1.0  

---

## 1. Overview

This document provides mathematically rigorous definitions, formulas, and business interpretations for all key metrics computed within the **Financial Analytics and Risk Reporting System**. Metrics are organized across four core functional areas:
1. **Profit & Loss (P&L) Statement Metrics**
2. **Balance Sheet & Solvency Metrics**
3. **Budget vs. Actual Variance Metrics**
4. **Credit Risk Scorecard & Basel II / IFRS 9 Metrics**

---

## 2. Profit & Loss (Income Statement) Metrics

### 2.1 Gross Interest Income (GII)
- **Business Interpretation:** Total interest earned from borrowers on active, performing, and amortizing loans during the accounting period.
- **Formula:**
  $$\text{GII} = \sum_{i=1}^{N} \text{interest\_received}_i$$

### 2.2 Interest Expense (Cost of Funds - CoF)
- **Business Interpretation:** The financing cost paid to capital providers (institutional debt, bank credit lines, or investor noteholders) to fund loan originations.
- **Formula:**
  $$\text{Interest Expense} = \text{Average Borrowed Liabilities} \times r_{\text{borrowing}}$$
  *(Typically modeled at a benchmark spread, e.g., SOFR + 2.50%).*

### 2.3 Net Interest Income (NII)
- **Business Interpretation:** The core fundamental earnings generated from the spread between lending yields and borrowing financing costs.
- **Formula:**
  $$\text{NII} = \text{Gross Interest Income} - \text{Interest Expense}$$

### 2.4 Net Interest Margin (NIM)
- **Business Interpretation:** An industry-standard measure of the profitability of an institution's earning assets relative to their financing cost.
- **Formula:**
  $$\text{NIM} = \frac{\text{Net Interest Income}}{\text{Average Earning Assets}} \times 100\%$$

### 2.5 Non-Interest Income (Fee Revenue)
- **Business Interpretation:** Ancillary revenues earned outside of base interest, including origination fees, loan servicing fees, and late payment penalties.
- **Formula:**
  $$\text{Non-Interest Income} = \sum (\text{origination\_fees} + \text{late\_fees\_received} + \text{prepayment\_penalties})$$

### 2.6 Cost of Risk (Provision for Credit Losses - PCL)
- **Business Interpretation:** Non-cash operational expense recognized on the P&L to establish or replenish the loan loss reserve for anticipated borrower defaults.
- **Formula:**
  $$\text{PCL} = \Delta \text{Allowance for Loan and Lease Losses (ALLL)} + \text{Gross Charge-Offs} - \text{Recoveries}$$

### 2.7 Operating Expenses (OpEx)
- **Business Interpretation:** Ongoing operational overhead, including loan underwriting, technology infrastructure, compliance, and servicing costs.
- **Formula:**
  $$\text{OpEx} = \text{Underwriting Costs} + \text{Servicing Costs} + \text{General \& Administrative (G\&A)}$$

### 2.8 Net Income (Bottom Line)
- **Business Interpretation:** The net residual profit generated after accounting for all revenues, financing costs, credit provisions, operating expenses, and taxes.
- **Formula:**
  $$\text{Net Income} = (\text{NII} + \text{Non-Interest Income} - \text{PCL} - \text{OpEx}) \times (1 - t_{\text{effective}})$$
  *Where $t_{\text{effective}}$ represents the effective corporate income tax rate (e.g., 21%).*

### 2.9 Return on Assets (ROA) & Return on Equity (ROE)
- **Formulas:**
  $$\text{ROA} = \frac{\text{Net Income}}{\text{Total Assets}} \times 100\%, \quad \text{ROE} = \frac{\text{Net Income}}{\text{Total Equity}} \times 100\%$$

---

## 3. Balance Sheet & Solvency Metrics

### 3.1 Gross Loan Portfolio (Gross Loans Outstanding)
- **Business Interpretation:** The aggregate principal balance owed by active borrowers before deducting loss allowances.
- **Formula:**
  $$\text{Gross Loans} = \sum_{j \in \text{Active Loans}} \text{outstanding\_principal}_j$$

### 3.2 Allowance for Loan and Lease Losses (ALLL / Loss Reserves)
- **Business Interpretation:** A contra-asset account established on the balance sheet to absorb expected credit defaults, complying with IFRS 9 forward-looking Expected Credit Loss (ECL) frameworks.
- **Formula:**
  $$\text{ALLL} = \sum_{\text{Stage 1}} \text{ECL}_{12\text{-month}} + \sum_{\text{Stage 2 \& 3}} \text{ECL}_{\text{Lifetime}}$$

### 3.3 Net Loan Portfolio (Net Loans)
- **Business Interpretation:** The carrying book value of loans expected to be realized in cash.
- **Formula:**
  $$\text{Net Loans} = \text{Gross Loans} - \text{ALLL}$$

### 3.4 Non-Performing Loan (NPL) Ratio
- **Business Interpretation:** The proportion of total loans that are past due 90+ days, in foreclosure, or legally charged off.
- **Formula:**
  $$\text{NPL Ratio} = \frac{\sum \text{Principal of Loans } (\ge 90 \text{ DPD} + \text{Charged Off})}{\text{Gross Loan Portfolio}} \times 100\%$$

### 3.5 Provision Coverage Ratio (PCR)
- **Business Interpretation:** Measures how adequately the accumulated loss reserve covers existing non-performing and distressed loans.
- **Formula:**
  $$\text{PCR} = \frac{\text{Allowance for Loan and Lease Losses (ALLL)}}{\text{Total Non-Performing Loans (NPL)}} \times 100\%$$
  *(A ratio $\ge 100\%$ indicates full reserve coverage of distressed debt).*

### 3.6 Balance Sheet Equation (Identity Proof)
- **Fundamental Identity:**
  $$\text{Total Assets} \equiv \text{Total Liabilities} + \text{Total Equity}$$
  Where:
  - $\text{Total Assets} = \text{Cash} + \text{Net Loans} + \text{Other Assets}$
  - $\text{Total Liabilities} = \text{Credit Facilities} + \text{Notes Payable} + \text{Accrued Expenses}$
  - $\text{Total Equity} = \text{Contributed Capital} + \text{Retained Earnings}$

---

## 4. Budget vs. Actual Variance Metrics

### 4.1 Dollar Variance ($\Delta\$$)
- **Business Interpretation:** The absolute financial gap between actual performance and targeted financial plan.
- **Formula:**
  $$\text{Dollar Variance } (\Delta\$) = \text{Actual Value} - \text{Budget Value}$$
  - For Revenues: $\Delta\$ > 0$ is **Favorable (F)**, $\Delta\$ < 0$ is **Unfavorable (U)**.
  - For Expenses: $\Delta\$ < 0$ is **Favorable (F)**, $\Delta\$ > 0$ is **Unfavorable (U)**.

### 4.2 Percentage Variance ($\% \Delta$)
- **Business Interpretation:** The relative percentage deviation from the budget baseline.
- **Formula:**
  $$\text{Percentage Variance } (\% \Delta) = \left( \frac{\text{Actual Value} - \text{Budget Value}}{\text{Budget Value}} \right) \times 100\%$$

### 4.3 Rate-Volume Variance Decomposition
- **Business Interpretation:** Deconstructs revenue deviations into effects caused by changing interest rates versus effects caused by lending volume.
- **Formulas:**
  $$\text{Volume Variance} = (\text{Actual Volume} - \text{Budget Volume}) \times \text{Budget Interest Rate}$$
  $$\text{Rate Variance} = \text{Actual Volume} \times (\text{Actual Interest Rate} - \text{Budget Interest Rate})$$
  $$\text{Total Variance} = \text{Volume Variance} + \text{Rate Variance}$$

---

## 5. Credit Risk Scorecard & Basel II / IFRS 9 Metrics

### 5.1 Probability of Default (PD)
- **Business Interpretation:** The statistical likelihood that a borrower will fail to meet contractual obligations within a given time horizon (e.g., 12 months or lifetime).
- **Modeling:** Modeled via binary logistic regression on historical performance:
  $$P(\text{Default}=1 | X) = \frac{1}{1 + e^{-(\beta_0 + \sum \beta_i X_i)}}$$

### 5.2 Weight of Evidence (WoE)
- **Business Interpretation:** Measures the predictive separation power of a specific bin or category $i$ for an independent feature.
- **Formula:**
  $$\text{WoE}_i = \ln \left( \frac{\% \text{ Non-Defaults}_i}{\% \text{ Defaults}_i} \right) = \ln \left( \frac{G_i / G_{\text{total}}}{B_i / B_{\text{total}}} \right)$$
  *Where $G$ represents "Good" borrowers (non-defaults) and $B$ represents "Bad" borrowers (defaults).*

### 5.3 Information Value (IV)
- **Business Interpretation:** Measures the overall predictive strength of an independent feature across all its bins.
- **Formula:**
  $$\text{IV} = \sum_{i=1}^{k} \left( \frac{G_i}{G_{\text{total}}} - \frac{B_i}{B_{\text{total}}} \right) \times \text{WoE}_i$$
- **Regulatory Rule of Thumb:**
  - $\text{IV} < 0.02$: Unpredictive; exclude.
  - $0.02 \le \text{IV} < 0.10$: Weak predictive power.
  - $0.10 \le \text{IV} < 0.30$: Medium predictive power; candidate for scorecard.
  - $0.30 \le \text{IV} \le 0.50$: Strong predictive power.
  - $\text{IV} > 0.50$: Suspiciously high; check for target leakage.

### 5.4 Credit Score Scaling Formula
- **Business Interpretation:** Maps logistic regression log-odds linearly into standard credit score points (e.g., FICO scale 300 to 850).
- **Formula:**
  $$\text{Score} = \text{Offset} + \text{Factor} \times \ln(\text{Odds})$$
  Where $\text{Odds} = \frac{P(\text{Non-Default})}{P(\text{Default})}$.
- **Scaling Parameters:**
  Given target score $S_0$ at odds $\theta_0$, and Points to Double the Odds ($\text{PDO}$):
  $$\text{Factor} = \frac{\text{PDO}}{\ln(2)}$$
  $$\text{Offset} = S_0 - \text{Factor} \times \ln(\theta_0)$$
  *(Standard calibration: $S_0 = 600$ points at $\text{Odds} = 50:1$, with $\text{PDO} = 20$).*

### 5.5 Loss Given Default (LGD)
- **Business Interpretation:** The economic loss percentage incurred on the exposure when a borrower defaults, after subtracting net recoveries.
- **Formula:**
  $$\text{LGD} = 1 - \text{Recovery Rate} = 1 - \frac{\text{Net Recoveries}}{\text{Exposure at Default (EAD)}}$$

### 5.6 Exposure at Default (EAD)
- **Business Interpretation:** The gross dollar amount at risk at the moment the default occurs.
- **Formula for Amortizing Loans:**
  $$\text{EAD} = \text{Outstanding Balance} + (\text{Undrawn Credit Line} \times \text{Credit Conversion Factor (CCF)})$$

### 5.7 Expected Loss (EL)
- **Business Interpretation:** The core regulatory metric under Basel II / Basel III and IFRS 9 quantifying anticipated portfolio losses.
- **Formula:**
  $$\text{EL} = \text{PD} \times \text{LGD} \times \text{EAD}$$


---

## 6. Task 2 SQL Analytical Reporting Layer Metrics & Formulas

The following metrics are implemented as high-performance SQL analytical views in [`sql/financial_views.sql`](file:///d:/nexvia%20-%201/Financial-Analytics-System/sql/financial_views.sql) and queryable in `warehouse.db`.

### 6.1 Monthly Portfolio P&L View (`vw_portfolio_pnl_monthly`)
Grain: Monthly origination cohort vintage (`year_month`).
- **`funded_amount`**: Aggregate principal committed and disbursed across loans originated in the vintage month:
  $$\text{Funded Amount} = \sum \text{funded\_amnt}$$
- **`principal_received`**: Cumulative principal amortized and recovered to date from borrowers:
  $$\text{Principal Received} = \sum \text{total\_rec\_prncp}$$
- **`interest_income`**: Cumulative contractual gross interest cash collected to date:
  $$\text{Interest Income} = \sum \text{total\_rec\_int}$$
- **`late_fee_income`**: Cumulative penalty fee revenue collected from overdue borrowers:
  $$\text{Late Fee Income} = \sum \text{total\_rec\_late\_fee}$$
- **`gross_recoveries`**: Total cash recovered post-charge-off through asset sales and legal collections:
  $$\text{Gross Recoveries} = \sum \text{recoveries}$$
- **`collection_cost`**: Fees paid to third-party collection agencies on recovered balances:
  $$\text{Collection Cost} = \sum \text{collection\_cost}$$
- **`net_recoveries`**: Net post-default recovery proceeds realized:
  $$\text{Net Recoveries} = \text{Gross Recoveries} - \text{Collection Cost}$$
- **`confirmed_default_count`**: Total loans flagged as statutory/contractual defaults (`is_confirmed_default = 1`):
  $$\text{Default Count} = \sum \mathbf{1}_{\{\text{is\_confirmed\_default} = 1\}}$$
- **`gross_charge_off_principal`**: Total unamortized principal written off on defaulted contracts:
  $$\text{Gross Charge-Off Principal} = \sum_{i \in \text{Defaults}} (\text{funded\_amnt}_i - \text{total\_rec\_prncp}_i)$$
- **`net_realized_credit_loss`**: Economic credit loss sustained after liquidating recoveries:
  $$\text{Net Realized Credit Loss} = \text{Gross Charge-Off Principal} - \text{Net Recoveries}$$
- **`total_cash_received`**: Aggregate gross cash payments collected across all categories:
  $$\text{Total Cash Received} = \sum \text{total\_pymnt}$$
- **`net_cash_after_collection_cost`**: Gross cash received net of collection agency fees:
  $$\text{Net Cash} = \sum (\text{total\_pymnt} - \text{collection\_cost})$$
- **`weighted_avg_interest_rate`**: Volume-weighted nominal interest rate of the vintage:
  $$\text{WAC} = \frac{\sum (\text{int\_rate} \times \text{funded\_amnt})}{\sum \text{funded\_amnt}}$$

### 6.2 Portfolio Balance Sheet Summary View (`vw_portfolio_balance_sheet_summary`)
Grain: Macro-portfolio solvency summary.
- **`total_funded_amount`**: Lifetime capital deployed across the entire loan portfolio (\$34,004,208,600.00).
- **`cumulative_principal_received`**: Total principal returned to date (\$21,489,393,643.58).
- **`active_gross_loan_outstanding`**: Principal balance currently remaining on active, non-closed loan contracts (`is_seasoned_closed = 0`):
  $$\text{Active Gross Loans} = \sum_{j \in \text{Active}} (\text{funded\_amnt}_j - \text{total\_rec\_prncp}_j) = \$9,510,001,923.03$$
- **`NPL_balance`**: Principal outstanding on non-performing loans severely delinquent ($\ge 31$ days past due, `delinquency_tier = 'Severe Late (31-120)'`):
  $$\text{NPL Balance} = \sum_{k \in \text{NPL}} (\text{funded\_amnt}_k - \text{total\_rec\_prncp}_k) = \$244,246,366.02$$
- **`NPL_ratio`**: Proportion of active portfolio principal currently in non-performing status:
  $$\text{NPL Ratio} = \frac{\text{NPL Balance}}{\text{Active Gross Loans}} \times 100\% = 2.5683\%$$
- **`analytical_loss_reserve`**: Model-based reserve estimation derived from the approved illustrative target loss caps pre-seeded in `dim_loan_grade` applied to active loans:
  $$\text{Analytical Loss Reserve} = \sum_{j \in \text{Active}} (\text{funded\_amnt}_j - \text{total\_rec\_prncp}_j) \times \text{loss\_cap}_j = \$772,880,427.48$$
  *(Note: This is an analytical credit reserve benchmark based on approved rating-tier loss parameters; it is NOT a statutory ALLL/CECL general ledger reserve).*
- **`net_loan_portfolio_carrying_value`**: Net estimated carrying asset value of active portfolio:
  $$\text{Net Carrying Value} = \text{Active Gross Loans} - \text{Analytical Loss Reserve} = \$8,737,121,495.55$$

### 6.3 Portfolio Vintage Performance View (`vw_portfolio_vintage_performance`)
Grain: Multi-dimensional cohort grouping by (`issue_year`, `issue_year_month`, `grade`, `sub_grade`, `term_months`).
- **`default_rate_pct`**: Cohort default rate:
  $$\text{Default Rate } (\%) = \frac{\text{Confirmed Defaults}}{\text{Total Loans Originated}} \times 100\%$$
- **`principal_recovery_rate_pct`**: Capital return percentage:
  $$\text{Recovery Rate } (\%) = \frac{\text{Principal Received}}{\text{Funded Amount}} \times 100\%$$
- **`net_cash_margin_pct`**: Net cash return on deployed capital:
  $$\text{Net Cash Margin } (\%) = \frac{\text{Net Cash Received} - \text{Funded Amount}}{\text{Funded Amount}} \times 100\%$$

---

## 7. Accounting Scope and Limitations

> ### IMPORTANT COMPLIANCE NOTICE: LOAN PORTFOLIO REPORTING VS. CORPORATE FINANCIAL STATEMENTS
> 
> 1. **Nature of the Underlying Data**:  
>    The Lending Club dataset is a **loan-level servicing, cash-flow, and performance ledger**, recording individual borrower contracts, payments, defaults, and recoveries. It is **NOT** a corporate double-entry General Ledger (GL) trial balance.
> 
> 2. **Corporate Financial Items Unavailable**:  
>    The dataset does not contain:
>    - Corporate treasury cash, operating bank accounts, or central reserve deposits.
>    - Corporate liabilities, institutional credit facilities, notes payable, or corporate debt obligations.
>    - Shareholders' equity, contributed capital, common/preferred stock, or retained earnings.
>    - Corporate Operating Expenses (OpEx): executive salaries, customer acquisition costs (CAC), technology infrastructure, legal overhead, or facility leases.
>    - Corporate income tax calculations and corporate statutory Net Income.
> 
> 3. **Mandatory Reporting Framing**:  
>    In strict adherence to financial integrity standards, these statements are formally presented as a:  
>    **"Loan Portfolio Financial Statement & Solvency Report"**  
>    This format accurately reflects the financial performance and asset solvency of the loan book (comparable to an institutional credit asset manager, loan trust, or securitization SPV report) without improperly representing Lending Club Corporation's consolidated statutory financial position.
