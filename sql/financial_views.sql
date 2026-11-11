-- ==============================================================================
-- Financial Analytics and Risk Reporting System (DA-04)
-- Component: SQL Analytical Reporting Layer (Views)
-- Engine: SQLite 3 / ANSI SQL Compatible
-- Reference: REQ-2 (P&L), REQ-3 (Balance Sheet / Solvency), REQ-4 (Vintage / Cohorts)
-- Approved Framing: "Loan Portfolio Financial Statement & Solvency Report"
-- ==============================================================================

DROP VIEW IF EXISTS vw_portfolio_pnl_monthly;
DROP VIEW IF EXISTS vw_portfolio_balance_sheet_summary;
DROP VIEW IF EXISTS vw_portfolio_vintage_performance;

-- ------------------------------------------------------------------------------
-- 1. Monthly Portfolio P&L View (Origination-Vintage Aggregation)
-- Aggregates monthly vintage cash inflows, realized interest income, late fees,
-- confirmed defaults, gross charge-offs, recoveries, and net cashflow.
-- ------------------------------------------------------------------------------
CREATE VIEW vw_portfolio_pnl_monthly AS
SELECT 
    d.year_month                                                            AS year_month,
    d.year                                                                  AS issue_year,
    d.quarter                                                               AS issue_quarter,
    d.month                                                                 AS issue_month,
    COUNT(f.loan_id)                                                        AS loan_count,
    SUM(f.funded_amnt)                                                      AS funded_amount,
    SUM(f.total_rec_prncp)                                                  AS principal_received,
    SUM(f.total_rec_int)                                                    AS interest_income,
    SUM(f.total_rec_late_fee)                                               AS late_fee_income,
    SUM(f.recoveries)                                                       AS gross_recoveries,
    SUM(f.collection_cost)                                                  AS collection_cost,
    SUM(f.recoveries - f.collection_cost)                                   AS net_recoveries,
    SUM(CASE WHEN f.is_confirmed_default = 1 THEN 1 ELSE 0 END)             AS confirmed_default_count,
    SUM(CASE WHEN f.is_confirmed_default = 1 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END)                                                  AS gross_charge_off_principal,
    SUM(CASE WHEN f.is_confirmed_default = 1 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END) 
        - SUM(f.recoveries - f.collection_cost)                             AS net_realized_credit_loss,
    SUM(f.total_pymnt)                                                      AS total_cash_received,
    SUM(f.total_pymnt - f.collection_cost)                                  AS net_cash_after_collection_cost,
    SUM(f.int_rate * f.funded_amnt) / NULLIF(SUM(f.funded_amnt), 0)         AS weighted_avg_interest_rate
FROM fact_accepted_loans f
JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
GROUP BY d.year_month, d.year, d.quarter, d.month
ORDER BY d.year_month;

-- ------------------------------------------------------------------------------
-- 2. Portfolio Balance Sheet Summary View (Solvency & Asset Carrying Value)
-- Captures total funded principal, cumulative amortized principal, active gross
-- loans outstanding, non-performing loans (NPL >= 31 DPD), NPL ratio,
-- analytical loss reserve (derived from dim_loan_grade illustrative loss caps),
-- and net loan portfolio carrying value.
-- ------------------------------------------------------------------------------
CREATE VIEW vw_portfolio_balance_sheet_summary AS
SELECT 
    SUM(f.funded_amnt)                                                      AS total_funded_amount,
    SUM(f.total_rec_prncp)                                                  AS cumulative_principal_received,
    SUM(CASE WHEN f.is_seasoned_closed = 0 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END)                                                  AS active_gross_loan_outstanding,
    SUM(CASE WHEN f.is_seasoned_closed = 0 AND f.delinquency_tier = 'Severe Late (31-120)' 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END)                                                  AS NPL_balance,
    100.0 * SUM(CASE WHEN f.is_seasoned_closed = 0 AND f.delinquency_tier = 'Severe Late (31-120)' 
                     THEN (f.funded_amnt - f.total_rec_prncp) 
                     ELSE 0.0 END) / 
    NULLIF(SUM(CASE WHEN f.is_seasoned_closed = 0 
                    THEN (f.funded_amnt - f.total_rec_prncp) 
                    ELSE 0.0 END), 0)                                       AS NPL_ratio,
    SUM(CASE WHEN f.is_seasoned_closed = 0 
             THEN (f.funded_amnt - f.total_rec_prncp) * g.illustrative_target_loss_cap 
             ELSE 0.0 END)                                                  AS analytical_loss_reserve,
    SUM(CASE WHEN f.is_seasoned_closed = 0 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END) - 
    SUM(CASE WHEN f.is_seasoned_closed = 0 
             THEN (f.funded_amnt - f.total_rec_prncp) * g.illustrative_target_loss_cap 
             ELSE 0.0 END)                                                  AS net_loan_portfolio_carrying_value
FROM fact_accepted_loans f
JOIN dim_loan_grade g ON f.grade_key = g.grade_key;

-- ------------------------------------------------------------------------------
-- 3. Portfolio Vintage Performance View (Multi-Dimensional Cohort Analysis)
-- Groups performance by issue_year, issue_year_month, grade, sub_grade, term_months.
-- ------------------------------------------------------------------------------
CREATE VIEW vw_portfolio_vintage_performance AS
SELECT 
    d.year                                                                  AS issue_year,
    d.year_month                                                            AS issue_year_month,
    g.grade                                                                 AS grade,
    g.sub_grade                                                             AS sub_grade,
    f.term_months                                                           AS term_months,
    COUNT(f.loan_id)                                                        AS loan_count,
    SUM(f.funded_amnt)                                                      AS funded_amount,
    AVG(f.funded_amnt)                                                      AS avg_loan_amount,
    SUM(f.int_rate * f.funded_amnt) / NULLIF(SUM(f.funded_amnt), 0)         AS weighted_avg_interest_rate,
    SUM(f.total_rec_prncp)                                                  AS principal_received,
    SUM(f.total_rec_int)                                                    AS interest_income,
    SUM(f.total_rec_late_fee)                                               AS late_fee_income,
    SUM(f.recoveries)                                                       AS gross_recoveries,
    SUM(f.collection_cost)                                                  AS collection_cost,
    SUM(f.recoveries - f.collection_cost)                                   AS net_recoveries,
    SUM(CASE WHEN f.is_confirmed_default = 1 THEN 1 ELSE 0 END)             AS confirmed_default_count,
    100.0 * SUM(CASE WHEN f.is_confirmed_default = 1 THEN 1 ELSE 0 END) 
        / NULLIF(COUNT(f.loan_id), 0)                                      AS default_rate_pct,
    SUM(CASE WHEN f.is_confirmed_default = 1 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END)                                                  AS gross_charge_off_principal,
    SUM(CASE WHEN f.is_confirmed_default = 1 
             THEN (f.funded_amnt - f.total_rec_prncp) 
             ELSE 0.0 END) 
        - SUM(f.recoveries - f.collection_cost)                             AS net_realized_credit_loss,
    100.0 * SUM(f.total_rec_prncp) / NULLIF(SUM(f.funded_amnt), 0)         AS principal_recovery_rate_pct,
    SUM(f.total_pymnt)                                                      AS total_cash_received,
    SUM(f.total_pymnt - f.collection_cost)                                  AS net_cash_after_collection_cost,
    100.0 * (SUM(f.total_pymnt - f.collection_cost) - SUM(f.funded_amnt)) 
        / NULLIF(SUM(f.funded_amnt), 0)                                     AS net_cash_margin_pct
FROM fact_accepted_loans f
JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
JOIN dim_loan_grade g ON f.grade_key = g.grade_key
GROUP BY d.year, d.year_month, g.grade, g.sub_grade, f.term_months
ORDER BY d.year_month, g.grade, g.sub_grade, f.term_months;
