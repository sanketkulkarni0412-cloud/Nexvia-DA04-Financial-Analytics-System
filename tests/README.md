# Quality Assurance & Financial Testing Suite

This directory contains automated test suites executed via `pytest` to guarantee accounting precision, mathematical correctness, and data pipeline integrity.

## Planned Test Suites (Phase 7)
- `test_data_cleaning.py`: Validates date parsing, range constraints, and missing-value handling.
- `test_sql_reconciliation.py`: Reconciles raw cash flow totals against SQL warehouse facts and views.
- `test_financial_metrics.py`: Asserts mathematical identities:
  - $NII = Gross\ Interest\ Income - Interest\ Expense$
  - $Assets = Liabilities + Equity$
  - Budget Rate-Volume variance reconciliation.
- `test_scorecard.py`: Tests Weight of Evidence monotonicity, score scaling bounds, and expected loss positivity ($EL \ge 0$).
