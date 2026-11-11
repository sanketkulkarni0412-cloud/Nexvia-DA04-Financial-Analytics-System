# Financial Reports Engine

This directory contains the core Python modules and Excel generation scripts that produce primary corporate financial statements and variance analysis.

## Planned Modules (Phase 4)
- `p_and_l_engine.py`: Computes Gross Interest Income, Cost of Funds, Net Interest Income (NII), Net Interest Margin (NIM), Operating Expenses, Cost of Risk (Provisions), and Net Income.
- `balance_sheet_engine.py`: Constructs the Balance Sheet statement, computing Gross Loans, ALLL contra-asset reserves under IFRS 9, Net Loan Portfolio, Liabilities, and Equity.
- `budget_variance.py`: Calculates absolute ($) and percentage (%) variance against institutional targets, performing Rate-Volume decomposition.
- `excel_report_builder.py`: Exports publication-ready `.xlsx` workbooks with professional accounting formatting, freeze panes, formulas, and visual conditional formatting.
