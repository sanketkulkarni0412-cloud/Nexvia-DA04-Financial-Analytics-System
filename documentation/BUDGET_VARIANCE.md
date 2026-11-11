# Nexvia DA-04: Budget vs. Actual Variance & Driver Decomposition Engine

**Component:** Step 3 / Task 2 Financial Reporting Engine  
**Project:** Financial Analytics and Risk Reporting System (DA-04)  
**Authoritative Source:** [`warehouse.db`](file:///d:/nexvia%20-%201/Financial-Analytics-System/warehouse.db) (SQLite 3, `vw_portfolio_pnl_monthly`, read-only mode `mode=ro`)  
**Engine Implementation:** [`financial_reports/budget_variance.py`](file:///d:/nexvia%20-%201/Financial-Analytics-System/financial_reports/budget_variance.py)  
**Machine-Readable Report:** [`reports/budget_variance_analysis.json`](file:///d:/nexvia%20-%201/Financial-Analytics-System/reports/budget_variance_analysis.json)  

---

## 1. Executive Summary & Governance Notice

> [!IMPORTANT]
> **GOVERNANCE NOTICE: OFFICIAL BUDGET DATA UNAVAILABLE**  
> In accordance with strict assessment integrity standards:
> 1. The official Lending Club assessment dataset is an archive of consumer loan originations, borrower profiles, and cash repayments. It does **not** contain official corporate accounting budget benchmarks or executive financial plans.
> 2. Database table `dim_financial_budget` in `warehouse.db` is intentionally unpopulated (0 rows), preserving the empirical ground truth.
> 3. To satisfy the assessment requirement for **Budget vs. Actual Variance Analysis and Driver Decomposition** without fabricating corporate records, this engine implements an **Illustrative Planning Scenario Framework**.
> 4. All scenario targets are explicitly labeled throughout code, data structures, and reports as:  
>    **`ILLUSTRATIVE SCENARIO — NOT OFFICIAL BUDGET`**.
> 5. Actual portfolio results are dynamically queried from the authoritative Task 2 SQL reporting views (`vw_portfolio_pnl_monthly` and `vw_portfolio_vintage_performance`) with zero hardcoding.

---

## 2. Actual Data Sources & Reconciliation

Actual performance metrics are queried directly from the frozen, audited Task 2 reporting views:

```
┌───────────────────────────────────────┬────────────────────────┬────────────────────────┬──────────────┬────────────┐
│ Portfolio Metric                      │ Task 2 Authoritative   │ Engine Actual Query    │ Variance     │ Audit      │
├───────────────────────────────────────┼────────────────────────┼────────────────────────┼──────────────┼────────────┤
│ Total Cumulative Funded Amount        │ $34,004,208,600.00     │ $34,004,208,600.00     │ $0.00        │ RECONCILED │
│ Cumulative Principal Received         │ $21,489,393,643.58     │ $21,489,393,643.58     │ $0.00        │ RECONCILED │
│ Cumulative Interest Income            │ $5,496,560,266.06      │ $5,496,560,266.06      │ $0.00        │ RECONCILED │
│ Total Late Fee Income                 │ $3,432,718.19          │ $3,432,718.19          │ $0.00        │ RECONCILED │
│ Gross Recoveries                      │ $325,262,956.86        │ $325,262,956.86        │ $0.00        │ RECONCILED │
│ Collection Costs (Agency Fees)        │ $54,216,619.20         │ $54,216,619.20         │ $0.00        │ RECONCILED │
│ Net Recoveries                        │ $271,046,337.67        │ $271,046,337.67        │ $0.00        │ RECONCILED │
│ Net Realized Credit Loss              │ $2,733,766,666.67      │ $2,733,766,666.67      │ $0.00        │ RECONCILED │
│ Total Cash Received                   │ $27,314,649,582.62     │ $27,314,649,582.62     │ $0.00        │ RECONCILED │
└───────────────────────────────────────┴────────────────────────┴────────────────────────┴──────────────┴────────────┘
```

---

## 3. Illustrative Scenario Planning Assumptions

To demonstrate institutional FP&A variance analysis, a standardized institutional planning baseline was established:

- **Scenario Name:** `ILLUSTRATIVE SCENARIO — NOT OFFICIAL BUDGET`
- **Volume Target ($V_{\text{budget}}$):** Modeled at an institutional target expansion of **+2.93%** over actuals ($\approx \$35.00\text{B}$ cumulative funded volume target vs. $\$34.004\text{B}$ actual).
- **Target Contractual Interest Yield ($Y_{\text{budget}}$):** Targeted at **`16.50%`** (vs actual effective yield of `16.1644%`).
- **Target Net Credit Loss Rate ($L_{\text{budget}}$):** Capped at **`7.50%`** of funded principal (vs actual realized loss rate of `8.0395%`).

---

## 4. Mathematical Methodology: Rate-Volume Variance Decomposition

In corporate banking and financial planning, aggregate dollar variances for volume-rate products (such as loan portfolios) must be decomposed into operational drivers rather than reported as simple gross differences.

### 4.1 Variance Formulation
For any metric $M$:
$$\text{Absolute Variance } (\Delta M) = M_{\text{actual}} - M_{\text{budget}}$$

$$\text{Percentage Variance } (\Delta M\%) = \frac{M_{\text{actual}} - M_{\text{budget}}}{|M_{\text{budget}}|} \times 100\%$$

### 4.2 Favorable / Unfavorable Directional Classification
- **Revenues / Income / Inflows** (`funded_amount`, `interest_income`, `total_cash_received`):
  $$\text{If } \Delta M \ge 0 \implies \text{Favorable (F)}, \quad \text{If } \Delta M < 0 \implies \text{Unfavorable (U)}$$
- **Costs / Write-offs / Credit Losses** (`collection_cost`, `gross_charge_off_principal`, `net_realized_credit_loss`):
  $$\text{If } \Delta M \le 0 \implies \text{Favorable (F)}, \quad \text{If } \Delta M > 0 \implies \text{Unfavorable (U)}$$

### 4.3 Three-Factor Driver Decomposition
Let:
- $V_{\text{actual}}, V_{\text{budget}}$ = Funded Principal Volume
- $R_{\text{actual}}, R_{\text{budget}}$ = Effective Rate or Yield (e.g., $\text{Interest Income} / V$)
- $T_{\text{actual}} = V_{\text{actual}} \times R_{\text{actual}}$, $T_{\text{budget}} = V_{\text{budget}} \times R_{\text{budget}}$

$$\text{Total Variance } (\Delta T) = T_{\text{actual}} - T_{\text{budget}}$$

The total variance decomposes into three orthogonal components:

1. **Volume Variance ($\Delta T_{\text{vol}}$):**  
   Measures the financial impact attributable purely to originating more or less principal volume at the budgeted yield:
   $$\Delta T_{\text{vol}} = (V_{\text{actual}} - V_{\text{budget}}) \times R_{\text{budget}}$$

2. **Rate / Yield Variance ($\Delta T_{\text{rate}}$):**  
   Measures the financial impact attributable purely to higher or lower achieved pricing/yield on the budgeted volume:
   $$\Delta T_{\text{rate}} = V_{\text{budget}} \times (R_{\text{actual}} - R_{\text{budget}})$$

3. **Mix / Interaction Variance ($\Delta T_{\text{mix}}$):**  
   Captures the cross-product interaction between simultaneous volume and rate movements:
   $$\Delta T_{\text{mix}} = (V_{\text{actual}} - V_{\text{budget}}) \times (R_{\text{actual}} - R_{\text{budget}})$$

$$\text{Reconciliation Check: } \Delta T_{\text{vol}} + \Delta T_{\text{rate}} + \Delta T_{\text{mix}} \equiv \Delta T$$

---

## 5. Variance Results & Driver Interpretation

### Cumulative Portfolio Summary

```
┌───────────────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┬────────────┬────────────────────────┐
│ Line Item                     │ Actual Value         │ Illustrative Budget  │ Absolute Variance    │ Var %      │ Directional Status     │
├───────────────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┼────────────┼────────────────────────┤
│ Funded Principal Volume       │ $34,004,208,600.00   │ $35,000,531,912.01   │ -$996,323,312.01     │ -2.85%     │ Unfavorable (Volume)   │
│ Cumulative Interest Income    │ $5,496,560,266.06    │ $5,775,087,765.49    │ -$278,527,499.43     │ -4.82%     │ Unfavorable (Yield)    │
│ Net Realized Credit Loss      │ $2,733,766,666.67    │ $2,625,039,893.39    │ +$108,726,773.28     │ +4.14%     │ Unfavorable (Losses)   │
│ Total Cash Received           │ $27,314,649,582.62   │ $27,894,120,642.82   │ -$579,471,060.20     │ -2.08%     │ Unfavorable (Inflow)   │
└───────────────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┴────────────┴────────────────────────┘
```

### Cumulative Interest Income Driver Decomposition

- **Total Variance ($\Delta T$):** **`-$278,527,499.43`**
- **1. Volume Driver:** **`-$164,393,346.48`** (59.0% of total variance)  
  *Interpretation:* Originating \$34.00B versus the \$35.00B illustrative target accounted for \$164.39M of lost interest revenue at the baseline 16.50% yield.
- **2. Rate / Yield Driver:** **`-$117,478,283.63`** (42.2% of total variance)  
  *Interpretation:* The achieved effective interest yield (16.1644%) trailed the 16.50% pricing target by 33.6 basis points, generating an unfavorable yield variance of \$117.48M on the planned baseline.
- **3. Mix / Interaction Effect:** **`+$3,344,130.68`** (-1.2% interaction offset)
- **Mathematical Identity:**
  $$\Delta T_{\text{vol}} + \Delta T_{\text{rate}} + \Delta T_{\text{mix}} = -164,393,346.48 - 117,478,283.63 + 3,344,130.68 = \mathbf{-278,527,499.43}$$
  *(Variance reconciliation verified: \$0.00 difference).*

---

## 6. Annual Variance Breakdown Summary

```
┌──────┬──────────────────────┬──────────────────────┬──────────────────────┬────────────────────────────────────────────────────────┐
│ Year │ Funded Volume Var    │ Interest Income Var  │ Net Credit Loss Var  │ Primary Interest Income Driver                         │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ 2007 │ -$145,773.00 (-2.85%)│ -$10,542.47 (-1.55%) │ -$6,634.34 (Fav)     │ Rate Variance ($13,546 Fav offset by Volume Var)       │
│ 2008 │ -$620,131.00 (-2.85%)│ -$119,796.53 (-3.48%)│ -$27,243.34 (Fav)    │ Volume Variance (-$102,322)                            │
│ 2009 │ -$1,520,387.00 (-2.8)│ -$383,283.95 (-4.18%)│ -$198,393.99 (Fav)   │ Volume Variance (-$250,864)                            │
│ 2010 │ -$3,865,038.00 (-2.8)│ -$669,183.74 (-3.11%)│ -$317,660.10 (Fav)   │ Volume Variance (-$637,731)                            │
│ 2011 │ -$7,665,992.00 (-2.8)│ -$1,419,258.91 (-3.1)│ -$465,581.50 (Fav)   │ Volume Variance (-$1,264,889)                          │
│ 2012 │ -$20,958,284.00 (-2.8)│ -$3,595,787.97 (-3.0)│ -$890,729.98 (Fav)   │ Volume Variance (-$3,458,117)                          │
│ 2013 │ -$58,074,743.00 (-2.8)│ -$12,963,086.09 (-3.7)│ -$715,649.34 (Fav)   │ Volume Variance (-$9,582,333)                          │
│ 2014 │ -$102,683,169.00 (-2)│ -$34,228,817.07 (-5.7)│ +$26,056,275.98 (Unfav) Volume (-$16.94M) & Rate (-$17.78M)             │
│ 2015 │ -$188,095,958.00 (-2)│ -$68,690,443.51 (-6.3)│ +$77,061,906.94 (Unfav) Volume (-$31.04M) & Rate (-$38.74M)             │
│ 2016 │ -$188,485,739.00 (-2)│ -$68,614,047.85 (-6.2)│ +$88,574,863.66 (Unfav) Volume (-$31.10M) & Rate (-$38.43M)             │
│ 2017 │ -$210,039,076.00 (-2)│ -$51,691,192.67 (-4.8)│ +$37,014,359.81 (Unfav) Volume (-$34.66M) & Rate (-$17.53M)             │
│ 2018 │ -$214,169,021.00 (-2)│ -$36,142,059.67 (-3.3)│ -$109,249,740.50 (Fav) Volume (-$35.34M)                               │
└──────┴──────────────────────┴──────────────────────┴──────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 7. Automated Testing & Verification

The budget variance engine is accompanied by comprehensive automated tests in [`tests/test_budget_variance.py`](file:///d:/nexvia%20-%201/Financial-Analytics-System/tests/test_budget_variance.py), verifying:
1. Reconciles actual portfolio totals to Task 2 authoritative numbers ($34.00B funded, $5.50B interest, $2.73B credit loss).
2. Rate-Volume-Mix decomposition identity holds with zero discrepancy.
3. Zero-division and null budget protections operate safely.
4. Correct directional classification (Favorable vs Unfavorable) for revenues and costs.
5. Official budget flag remains `False`, proving no fabricated corporate records.

