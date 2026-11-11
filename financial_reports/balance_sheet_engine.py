"""
Portfolio Balance Sheet & Solvency Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: REQ-3 (Balance Sheet Schedules & Solvency Analysis)
Framing: Loan Portfolio Financial Statement & Solvency Report
Data Source: SQLite Data Warehouse (warehouse.db)

Features:
1. Connects to warehouse.db strictly in read-only mode.
2. Reads from vw_portfolio_balance_sheet_summary as the authoritative source.
3. Generates a structured portfolio solvency report:
   - total funded amount
   - cumulative principal received
   - active gross loan outstanding
   - NPL balance
   - NPL ratio
   - analytical loss reserve (clearly labeled as model-based)
   - net loan portfolio carrying value
4. Explicitly excludes and documents unavailable corporate balance-sheet items:
   - corporate cash
   - corporate debt
   - shareholder equity
   - retained earnings
   - corporate operating expenses
   - income tax.
5. All calculations are dynamic and reproducible with zero hard-coded totals.
"""

import os
import sys
import sqlite3
import argparse
import json
from datetime import datetime, timezone
import pandas as pd

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "warehouse.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


class PortfolioBalanceSheetEngine:
    """
    Engine for generating loan portfolio balance sheet statements and solvency schedules.
    Uses strictly read-only SQLite URI connections to guarantee database integrity.
    """

    UNAVAILABLE_CORPORATE_ITEMS = [
        "corporate_cash",
        "corporate_debt",
        "shareholder_equity",
        "retained_earnings",
        "corporate_operating_expenses",
        "income_tax"
    ]

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Warehouse database not found: {self.db_path}")
        self.uri = f"file:///{self.db_path.replace(os.sep, '/')}?mode=ro"

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a read-only SQLite connection."""
        return sqlite3.connect(self.uri, uri=True)

    def get_solvency_summary(self) -> dict:
        """
        Retrieves macro portfolio solvency metrics dynamically from vw_portfolio_balance_sheet_summary.
        """
        query = "SELECT * FROM vw_portfolio_balance_sheet_summary;"
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            if not row:
                raise ValueError("vw_portfolio_balance_sheet_summary returned no records.")
            data = dict(zip(cols, row))

        total_funded = float(data["total_funded_amount"])
        principal_received = float(data["cumulative_principal_received"])
        active_gross = float(data["active_gross_loan_outstanding"])
        npl_bal = float(data["NPL_balance"])
        npl_ratio = float(data["NPL_ratio"])
        analytical_reserve = float(data["analytical_loss_reserve"])
        net_carrying = float(data["net_loan_portfolio_carrying_value"])
        pcr = (analytical_reserve / npl_bal * 100.0) if npl_bal > 0 else 0.0

        return {
            "framing": "Loan Portfolio Financial Statement & Solvency Report",
            "as_of_date": datetime.now(timezone.utc).isoformat(),
            "total_funded_amount": round(total_funded, 2),
            "cumulative_principal_received": round(principal_received, 2),
            "active_gross_loan_outstanding": round(active_gross, 2),
            "NPL_balance": round(npl_bal, 2),
            "NPL_ratio": round(npl_ratio, 4),
            "analytical_loss_reserve": round(analytical_reserve, 2),
            "analytical_loss_reserve_label": "Model-Based Analytical Reserve — Not Statutory ALLL/CECL",
            "reserve_coverage_ratio_pct": round(pcr, 2),
            "net_loan_portfolio_carrying_value": round(net_carrying, 2),
            "unavailable_corporate_items": self.UNAVAILABLE_CORPORATE_ITEMS,
            "accounting_note": "This is a loan portfolio asset solvency report derived from loan-level servicing records. Conventional corporate balance sheet items (corporate cash, credit facilities, equity, and retained earnings) are unavailable and not fabricated."
        }

    def get_asset_status_schedule(self) -> pd.DataFrame:
        """
        Categorizes portfolio contracts across life-cycle asset classes:
        - Active Performing (Current, Grace Period, Late 16-30)
        - Non-Performing (Late 31-120)
        - Default / Charged Off
        - Fully Paid
        """
        query = """
            SELECT 
                CASE 
                    WHEN f.loan_status = 'Fully Paid' THEN 'Fully Paid'
                    WHEN f.loan_status = 'Does not meet the credit policy. Status:Fully Paid' THEN 'Fully Paid (Legacy Policy)'
                    WHEN f.is_confirmed_default = 1 THEN 'Default / Charged Off'
                    WHEN f.delinquency_tier = 'Severe Late (31-120)' THEN 'Non-Performing Loans (31-120 DPD)'
                    WHEN f.delinquency_tier IN ('Late (16-30)', 'Grace Period') THEN 'Underperforming / Early Delinquent'
                    ELSE 'Active Performing / Current'
                END                                                         AS asset_classification,
                f.is_seasoned_closed                                        AS is_closed_flag,
                COUNT(f.loan_id)                                            AS loan_count,
                ROUND(SUM(f.funded_amnt), 2)                                AS funded_amount,
                ROUND(SUM(f.total_rec_prncp), 2)                            AS principal_repaid,
                ROUND(SUM(CASE WHEN f.is_seasoned_closed = 0 
                               THEN (f.funded_amnt - f.total_rec_prncp) 
                               ELSE 0.0 END), 2)                            AS active_outstanding_principal,
                ROUND(SUM(CASE WHEN f.is_confirmed_default = 1 
                               THEN (f.funded_amnt - f.total_rec_prncp) 
                               ELSE 0.0 END), 2)                            AS gross_default_principal,
                ROUND(SUM(f.total_rec_int), 2)                              AS interest_received,
                ROUND(SUM(f.total_rec_late_fee), 2)                         AS late_fees_received,
                ROUND(SUM(f.recoveries), 2)                                 AS gross_recoveries,
                ROUND(SUM(f.recoveries - f.collection_cost), 2)             AS net_recoveries,
                ROUND(SUM(f.total_pymnt), 2)                                AS total_cash_collected
            FROM fact_accepted_loans f
            GROUP BY 1, 2
            ORDER BY is_closed_flag ASC, funded_amount DESC;
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df

    def get_delinquency_aging_schedule(self) -> pd.DataFrame:
        """
        Detailed delinquency aging schedule across all 912,569 active contracts.
        """
        query = """
            SELECT 
                f.delinquency_tier                                          AS delinquency_bracket,
                f.loan_status                                               AS contract_status,
                COUNT(f.loan_id)                                            AS active_loan_count,
                ROUND(SUM(f.funded_amnt), 2)                                AS original_funded_principal,
                ROUND(SUM(f.total_rec_prncp), 2)                            AS cumulative_principal_amortized,
                ROUND(SUM(f.funded_amnt - f.total_rec_prncp), 2)            AS active_carrying_principal,
                ROUND(AVG(f.funded_amnt - f.total_rec_prncp), 2)            AS avg_carrying_balance,
                ROUND(SUM(f.int_rate * f.funded_amnt) / SUM(f.funded_amnt), 2) AS wac_interest_rate,
                ROUND(SUM(f.total_rec_int), 2)                              AS cumulative_interest_collected,
                ROUND(SUM(f.total_rec_late_fee), 2)                         AS cumulative_late_fees_collected
            FROM fact_accepted_loans f
            WHERE f.is_seasoned_closed = 0
            GROUP BY f.delinquency_tier, f.loan_status
            ORDER BY active_carrying_principal DESC;
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        total_active_prncp = df["active_carrying_principal"].sum()
        df["pct_of_active_portfolio"] = (df["active_carrying_principal"] / total_active_prncp * 100.0).round(2)
        return df

    def get_solvency_by_grade(self) -> pd.DataFrame:
        """
        Evaluates active loan solvency, analytical reserves, and illustrative Basel II RWA by Credit Grade (A-G).
        """
        query = """
            SELECT 
                g.grade                                                     AS credit_grade,
                g.regulatory_tier                                           AS regulatory_tier,
                AVG(g.illustrative_basel_weight)                            AS illustrative_basel_weight,
                AVG(g.illustrative_target_loss_cap)                         AS avg_target_loss_cap,
                COUNT(f.loan_id)                                            AS active_loan_count,
                ROUND(SUM(f.funded_amnt), 2)                                AS original_funded_amount,
                ROUND(SUM(f.total_rec_prncp), 2)                            AS principal_amortized,
                ROUND(SUM(f.funded_amnt - f.total_rec_prncp), 2)            AS active_gross_loan_outstanding,
                ROUND(SUM((f.funded_amnt - f.total_rec_prncp) * g.illustrative_target_loss_cap), 2) AS analytical_loss_reserve,
                ROUND(SUM(f.funded_amnt - f.total_rec_prncp) - 
                      SUM((f.funded_amnt - f.total_rec_prncp) * g.illustrative_target_loss_cap), 2) AS net_carrying_value,
                ROUND(SUM((f.funded_amnt - f.total_rec_prncp) * g.illustrative_basel_weight), 2)    AS illustrative_rwa_volume
            FROM fact_accepted_loans f
            JOIN dim_loan_grade g ON f.grade_key = g.grade_key
            WHERE f.is_seasoned_closed = 0
            GROUP BY g.grade, g.regulatory_tier
            ORDER BY g.grade;
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        total_active = df["active_gross_loan_outstanding"].sum()
        df["portfolio_share_pct"] = (df["active_gross_loan_outstanding"] / total_active * 100.0).round(2)
        df["reserve_rate_pct"] = (df["analytical_loss_reserve"] / df["active_gross_loan_outstanding"] * 100.0).round(2)
        return df

    def export_reports(self, output_dir: str = REPORTS_DIR) -> dict:
        """
        Exports Balance Sheet summary, asset status, delinquency aging, and grade solvency to CSV and JSON formats.
        """
        os.makedirs(output_dir, exist_ok=True)
        summary = self.get_solvency_summary()
        asset_schedule = self.get_asset_status_schedule()
        aging = self.get_delinquency_aging_schedule()
        grades = self.get_solvency_by_grade()

        paths = {
            "solvency_summary_json": os.path.join(output_dir, "balance_sheet_solvency_summary.json"),
            "asset_status_csv": os.path.join(output_dir, "balance_sheet_asset_status_schedule.csv"),
            "delinquency_aging_csv": os.path.join(output_dir, "balance_sheet_delinquency_aging.csv"),
            "solvency_by_grade_csv": os.path.join(output_dir, "balance_sheet_solvency_by_grade.csv")
        }

        with open(paths["solvency_summary_json"], "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        asset_schedule.to_csv(paths["asset_status_csv"], index=False)
        aging.to_csv(paths["delinquency_aging_csv"], index=False)
        grades.to_csv(paths["solvency_by_grade_csv"], index=False)

        return paths


def main():
    parser = argparse.ArgumentParser(description="Portfolio Balance Sheet & Solvency Engine (DA-04)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite warehouse")
    parser.add_argument("--export", action="store_true", help="Export Balance Sheet schedule files to reports/")
    args = parser.parse_args()

    engine = PortfolioBalanceSheetEngine(db_path=args.db_path)
    summary = engine.get_solvency_summary()

    print("=" * 75)
    print("LOAN PORTFOLIO FINANCIAL STATEMENT & SOLVENCY REPORT: BALANCE SHEET SUMMARY")
    print("=" * 75)
    for k, v in summary.items():
        if isinstance(v, float) and "pct" not in k and "ratio" not in k:
            print(f"  {k:<35}: ${v:>18,.2f}")
        elif "pct" in k or "ratio" in k:
            print(f"  {k:<35}: {v:>18.4f}%")
        else:
            print(f"  {k:<35}: {str(v)}")
    print("=" * 75)

    if args.export:
        paths = engine.export_reports()
        print("Exported Balance Sheet schedule files:")
        for name, path in paths.items():
            print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
