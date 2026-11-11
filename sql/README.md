# SQL Data Warehouse & Queries

This directory houses SQL scripts for the dimensional Star Schema, materialized financial views, analytical queries, and database population routines.

## Planned Scripts (Phase 3 & Phase 4)
- `schema.sql`: Data Definition Language (DDL) creating Fact and Dimension tables (`fact_loan_origination`, `fact_loan_repayment`, `dim_borrower`, `dim_loan_grade`, `dim_calendar_date`, `dim_geography`, `dim_financial_budget`).
- `indexes.sql`: Performance indexes on foreign keys, dates, and loan statuses.
- `financial_views.sql`: SQL views aggregating monthly interest income, principal cash flows, and default roll rates.
- `budget_actual_queries.sql`: Analytical queries joining actual performance with budget targets for variance analysis.
