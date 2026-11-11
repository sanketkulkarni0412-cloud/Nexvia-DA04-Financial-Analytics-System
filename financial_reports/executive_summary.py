"""
Portfolio Executive Summary Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: REQ-2 & REQ-3 (Executive KPI Reporting)
Framing: Loan Portfolio Financial Statement & Solvency Report
Data Source: SQLite Data Warehouse (warehouse.db views)

Features:
1. Connects to warehouse.db strictly in read-only mode.
2. Queries the authoritative SQL reporting views:
   - vw_portfolio_pnl_monthly
   - vw_portfolio_balance_sheet_summary
3. Dynamically computes the 10 executive KPIs:
   - total_loans
   - total_funded_amount
   - interest_income
   - net_realized_credit_loss
   - active_portfolio_outstanding
   - NPL_balance
   - NPL_ratio
   - analytical_reserve
   - net_carrying_value
   - principal_recovery_rate
4. Zero hard-coded values; 100% dynamic calculation from the database.
"""

import os
import sys
import sqlite3
import argparse
import json
from datetime import datetime, timezone

# Add project root to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "warehouse.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


class PortfolioExecutiveSummaryEngine:
    """
    Engine for generating executive KPI summaries across portfolio P&L and Balance Sheet views.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Warehouse database not found: {self.db_path}")
        self.uri = f"file:///{self.db_path.replace(os.sep, '/')}?mode=ro"

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a read-only SQLite connection."""
        return sqlite3.connect(self.uri, uri=True)

    def get_executive_kpis(self) -> dict:
        """
        Dynamically calculates the 10 core executive portfolio KPIs directly
        from vw_portfolio_pnl_monthly and vw_portfolio_balance_sheet_summary.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()

            # 1. Query P&L view totals
            cur.execute("""
                SELECT 
                    SUM(loan_count)                     AS total_loans,
                    SUM(funded_amount)                  AS total_funded_amount,
                    SUM(principal_received)              AS principal_received,
                    SUM(interest_income)                AS interest_income,
                    SUM(net_realized_credit_loss)       AS net_realized_credit_loss
                FROM vw_portfolio_pnl_monthly;
            """)
            pnl_row = cur.fetchone()
            total_loans = int(pnl_row[0]) if pnl_row[0] is not None else 0
            funded_from_pnl = float(pnl_row[1]) if pnl_row[1] is not None else 0.0
            principal_received = float(pnl_row[2]) if pnl_row[2] is not None else 0.0
            interest_income = float(pnl_row[3]) if pnl_row[3] is not None else 0.0
            net_credit_loss = float(pnl_row[4]) if pnl_row[4] is not None else 0.0

            # 2. Query Balance Sheet view metrics
            cur.execute("""
                SELECT 
                    total_funded_amount,
                    active_gross_loan_outstanding,
                    NPL_balance,
                    NPL_ratio,
                    analytical_loss_reserve,
                    net_loan_portfolio_carrying_value
                FROM vw_portfolio_balance_sheet_summary;
            """)
            bs_row = cur.fetchone()
            if not bs_row:
                raise ValueError("vw_portfolio_balance_sheet_summary returned no data.")

            total_funded_amount = float(bs_row[0])
            active_portfolio_outstanding = float(bs_row[1])
            npl_balance = float(bs_row[2])
            npl_ratio = float(bs_row[3])
            analytical_reserve = float(bs_row[4])
            net_carrying_value = float(bs_row[5])

        # Principal recovery rate (%)
        recovery_rate = (principal_received / total_funded_amount * 100.0) if total_funded_amount > 0 else 0.0

        return {
            "framing": "Loan Portfolio Financial Statement & Solvency Report",
            "as_of_date": datetime.now(timezone.utc).isoformat(),
            "total_loans": total_loans,
            "total_funded_amount": round(total_funded_amount, 2),
            "interest_income": round(interest_income, 2),
            "net_realized_credit_loss": round(net_credit_loss, 2),
            "active_portfolio_outstanding": round(active_portfolio_outstanding, 2),
            "NPL_balance": round(npl_balance, 2),
            "NPL_ratio": round(npl_ratio, 4),
            "analytical_reserve": round(analytical_reserve, 2),
            "analytical_reserve_label": "Model-Based Analytical Reserve — Not Statutory ALLL/CECL",
            "net_carrying_value": round(net_carrying_value, 2),
            "principal_recovery_rate": round(recovery_rate, 2),
            "source_views": [
                "vw_portfolio_pnl_monthly",
                "vw_portfolio_balance_sheet_summary"
            ]
        }

    def export_summary(self, output_dir: str = REPORTS_DIR) -> str:
        """
        Exports the executive KPI summary to reports/portfolio_executive_kpis.json.
        """
        os.makedirs(output_dir, exist_ok=True)
        summary = self.get_executive_kpis()
        out_path = os.path.join(output_dir, "portfolio_executive_kpis.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return out_path


def main():
    parser = argparse.ArgumentParser(description="Portfolio Executive Summary Engine (DA-04)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite warehouse")
    parser.add_argument("--export", action="store_true", help="Export summary JSON to reports/")
    args = parser.parse_args()

    engine = PortfolioExecutiveSummaryEngine(db_path=args.db_path)
    kpis = engine.get_executive_kpis()

    print("=" * 70)
    print("LOAN PORTFOLIO FINANCIAL STATEMENT & SOLVENCY REPORT: EXECUTIVE KPIS")
    print("=" * 70)
    for k, v in kpis.items():
        if isinstance(v, float) and "rate" not in k and "ratio" not in k:
            print(f"  {k:<32}: ${v:>18,.2f}")
        elif "rate" in k or "ratio" in k:
            print(f"  {k:<32}: {v:>18.4f}%")
        else:
            print(f"  {k:<32}: {str(v)}")
    print("=" * 70)

    if args.export:
        path = engine.export_summary()
        print(f"Exported executive KPI summary to: {path}")


if __name__ == "__main__":
    main()

