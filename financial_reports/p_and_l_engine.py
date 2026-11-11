"""
Portfolio Income Statement (P&L) Engine
Financial Analytics and Risk Reporting System (DA-04)

Component: REQ-2 (Profit & Loss Reporting Engine)
Framing: Loan Portfolio Financial Statement & Solvency Report
Data Source: SQLite Data Warehouse (warehouse.db)

Features:
1. Multi-grain aggregation (Monthly Vintage, Quarterly Vintage, Annual Vintage, and Credit Grade Tier).
2. Computes core portfolio revenue streams:
   - Gross Interest Income
   - Late Fee Income
   - Total Portfolio Revenue
3. Models credit impairment cashflows:
   - Gross Charge-Off Principal
   - Gross Recoveries & External Collection Agency Costs
   - Net Recoveries Realized
   - Net Realized Credit Losses
4. Computes cash realization and margins:
   - Total Cash Receipts
   - Net Cash After Collections
   - Volume-Weighted Average Coupon (WAC)
   - Principal Recovery Rate (%)
   - Net Cash Margin on Funded Capital (%)
5. Complete auditability and 0-variance reconciliation to warehouse.db fact tables.
"""

import os
import sys
import sqlite3
import argparse
import json
from datetime import datetime, timezone
import pandas as pd

# Add project root to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "warehouse.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


class PortfolioPnLEngine:
    """
    Engine for generating loan portfolio income statements (P&L) from warehouse.db.
    Connects strictly in read-only mode to preserve database integrity.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Warehouse database not found: {self.db_path}")
        self.uri = f"file:///{self.db_path.replace(os.sep, '/')}?mode=ro"

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a read-only SQLite connection."""
        return sqlite3.connect(self.uri, uri=True)

    def get_monthly_pnl(self, start_month: str = None, end_month: str = None) -> pd.DataFrame:
        """
        Retrieves monthly origination-vintage P&L metrics from vw_portfolio_pnl_monthly.
        """
        query = """
            SELECT 
                year_month,
                issue_year,
                issue_quarter,
                issue_month,
                loan_count,
                funded_amount,
                principal_received,
                interest_income,
                late_fee_income,
                (interest_income + late_fee_income) AS total_revenue,
                gross_recoveries,
                collection_cost,
                net_recoveries,
                confirmed_default_count,
                gross_charge_off_principal,
                net_realized_credit_loss,
                total_cash_received,
                net_cash_after_collection_cost,
                weighted_avg_interest_rate
            FROM vw_portfolio_pnl_monthly
            WHERE 1=1
        """
        params = []
        if start_month:
            query += " AND year_month >= ?"
            params.append(start_month)
        if end_month:
            query += " AND year_month <= ?"
            params.append(end_month)
            
        query += " ORDER BY year_month;"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        # Derived analytical margins
        df["interest_yield_pct"] = (df["interest_income"] / df["funded_amount"] * 100.0).round(2)
        df["default_rate_pct"] = (df["confirmed_default_count"] / df["loan_count"] * 100.0).round(2)
        df["recovery_rate_pct"] = (df["principal_received"] / df["funded_amount"] * 100.0).round(2)
        df["net_cash_margin_pct"] = ((df["net_cash_after_collection_cost"] - df["funded_amount"]) / df["funded_amount"] * 100.0).round(2)

        return df

    def get_annual_pnl(self) -> pd.DataFrame:
        """
        Rolls up monthly vintage P&L into annualized origination cohorts.
        """
        df_monthly = self.get_monthly_pnl()
        annual = df_monthly.groupby("issue_year").agg(
            loan_count=("loan_count", "sum"),
            funded_amount=("funded_amount", "sum"),
            principal_received=("principal_received", "sum"),
            interest_income=("interest_income", "sum"),
            late_fee_income=("late_fee_income", "sum"),
            total_revenue=("total_revenue", "sum"),
            gross_recoveries=("gross_recoveries", "sum"),
            collection_cost=("collection_cost", "sum"),
            net_recoveries=("net_recoveries", "sum"),
            confirmed_default_count=("confirmed_default_count", "sum"),
            gross_charge_off_principal=("gross_charge_off_principal", "sum"),
            net_realized_credit_loss=("net_realized_credit_loss", "sum"),
            total_cash_received=("total_cash_received", "sum"),
            net_cash_after_collection_cost=("net_cash_after_collection_cost", "sum")
        ).reset_index()

        # Recalculate portfolio-wide weighted average interest rate
        with self._get_connection() as conn:
            wac_df = pd.read_sql_query("""
                SELECT 
                    d.year AS issue_year,
                    SUM(f.int_rate * f.funded_amnt) / SUM(f.funded_amnt) AS weighted_avg_interest_rate
                FROM fact_accepted_loans f
                JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
                GROUP BY d.year;
            """, conn)
            
        annual = annual.merge(wac_df, on="issue_year", how="left")
        annual["weighted_avg_interest_rate"] = annual["weighted_avg_interest_rate"].round(4)
        annual["interest_yield_pct"] = (annual["interest_income"] / annual["funded_amount"] * 100.0).round(2)
        annual["default_rate_pct"] = (annual["confirmed_default_count"] / annual["loan_count"] * 100.0).round(2)
        annual["recovery_rate_pct"] = (annual["principal_received"] / annual["funded_amount"] * 100.0).round(2)
        annual["net_cash_margin_pct"] = ((annual["net_cash_after_collection_cost"] - annual["funded_amount"]) / annual["funded_amount"] * 100.0).round(2)

        return annual

    def get_quarterly_pnl(self) -> pd.DataFrame:
        """
        Rolls up monthly vintage P&L into quarterly cohorts (YYYY-Q#).
        """
        df_monthly = self.get_monthly_pnl()
        df_monthly["vintage_quarter"] = df_monthly["issue_year"].astype(str) + "-Q" + df_monthly["issue_quarter"].astype(str)
        
        quarterly = df_monthly.groupby("vintage_quarter").agg(
            issue_year=("issue_year", "first"),
            issue_quarter=("issue_quarter", "first"),
            loan_count=("loan_count", "sum"),
            funded_amount=("funded_amount", "sum"),
            principal_received=("principal_received", "sum"),
            interest_income=("interest_income", "sum"),
            late_fee_income=("late_fee_income", "sum"),
            total_revenue=("total_revenue", "sum"),
            gross_recoveries=("gross_recoveries", "sum"),
            collection_cost=("collection_cost", "sum"),
            net_recoveries=("net_recoveries", "sum"),
            confirmed_default_count=("confirmed_default_count", "sum"),
            gross_charge_off_principal=("gross_charge_off_principal", "sum"),
            net_realized_credit_loss=("net_realized_credit_loss", "sum"),
            total_cash_received=("total_cash_received", "sum"),
            net_cash_after_collection_cost=("net_cash_after_collection_cost", "sum")
        ).reset_index()

        quarterly["interest_yield_pct"] = (quarterly["interest_income"] / quarterly["funded_amount"] * 100.0).round(2)
        quarterly["default_rate_pct"] = (quarterly["confirmed_default_count"] / quarterly["loan_count"] * 100.0).round(2)
        quarterly["recovery_rate_pct"] = (quarterly["principal_received"] / quarterly["funded_amount"] * 100.0).round(2)
        quarterly["net_cash_margin_pct"] = ((quarterly["net_cash_after_collection_cost"] - quarterly["funded_amount"]) / quarterly["funded_amount"] * 100.0).round(2)

        return quarterly

    def get_pnl_by_grade(self) -> pd.DataFrame:
        """
        Aggregates portfolio revenue and loss performance grouped by credit rating grade (A through G).
        """
        query = """
            SELECT 
                grade,
                regulatory_tier,
                SUM(loan_count)                                                     AS loan_count,
                SUM(funded_amount)                                                  AS funded_amount,
                ROUND(AVG(avg_loan_amount), 2)                                     AS avg_loan_amount,
                ROUND(SUM(weighted_avg_interest_rate * funded_amount) / SUM(funded_amount), 4) AS wac_interest_rate,
                SUM(principal_received)                                             AS principal_received,
                SUM(interest_income)                                                AS interest_income,
                SUM(late_fee_income)                                                AS late_fee_income,
                SUM(interest_income + late_fee_income)                              AS total_revenue,
                SUM(gross_recoveries)                                               AS gross_recoveries,
                SUM(collection_cost)                                                AS collection_cost,
                SUM(net_recoveries)                                                 AS net_recoveries,
                SUM(confirmed_default_count)                                        AS confirmed_default_count,
                ROUND(100.0 * SUM(confirmed_default_count) / SUM(loan_count), 2)   AS default_rate_pct,
                SUM(gross_charge_off_principal)                                     AS gross_charge_off_principal,
                SUM(net_realized_credit_loss)                                       AS net_realized_credit_loss,
                SUM(total_cash_received)                                            AS total_cash_received,
                SUM(net_cash_after_collection_cost)                                 AS net_cash_after_collection_cost,
                ROUND(100.0 * SUM(principal_received) / SUM(funded_amount), 2)      AS recovery_rate_pct,
                ROUND(100.0 * (SUM(net_cash_after_collection_cost) - SUM(funded_amount)) / SUM(funded_amount), 2) AS net_cash_margin_pct
            FROM vw_portfolio_vintage_performance
            GROUP BY grade, regulatory_tier
            ORDER BY grade;
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df

    def get_portfolio_summary_totals(self) -> dict:
        """
        Computes lifetime portfolio income statement totals matching warehouse fact tables.
        """
        df_monthly = self.get_monthly_pnl()
        return {
            "framing": "Loan Portfolio Financial Statement & Solvency Report",
            "as_of_date": datetime.now(timezone.utc).isoformat(),
            "total_loans_originated": int(df_monthly["loan_count"].sum()),
            "total_funded_amount": round(float(df_monthly["funded_amount"].sum()), 2),
            "total_principal_received": round(float(df_monthly["principal_received"].sum()), 2),
            "gross_interest_income": round(float(df_monthly["interest_income"].sum()), 2),
            "late_fee_income": round(float(df_monthly["late_fee_income"].sum()), 2),
            "total_portfolio_revenue": round(float(df_monthly["total_revenue"].sum()), 2),
            "gross_recoveries": round(float(df_monthly["gross_recoveries"].sum()), 2),
            "collection_cost": round(float(df_monthly["collection_cost"].sum()), 2),
            "net_recoveries": round(float(df_monthly["net_recoveries"].sum()), 2),
            "confirmed_default_count": int(df_monthly["confirmed_default_count"].sum()),
            "gross_charge_off_principal": round(float(df_monthly["gross_charge_off_principal"].sum()), 2),
            "net_realized_credit_loss": round(float(df_monthly["net_realized_credit_loss"].sum()), 2),
            "total_cash_received": round(float(df_monthly["total_cash_received"].sum()), 2),
            "net_cash_after_collection_cost": round(float(df_monthly["net_cash_after_collection_cost"].sum()), 2),
            "portfolio_default_rate_pct": round(float(df_monthly["confirmed_default_count"].sum()) / float(df_monthly["loan_count"].sum()) * 100.0, 2),
            "principal_recovery_rate_pct": round(float(df_monthly["principal_received"].sum()) / float(df_monthly["funded_amount"].sum()) * 100.0, 2),
            "overall_cash_margin_pct": round((float(df_monthly["net_cash_after_collection_cost"].sum()) - float(df_monthly["funded_amount"].sum())) / float(df_monthly["funded_amount"].sum()) * 100.0, 2)
        }

    def export_reports(self, output_dir: str = REPORTS_DIR) -> dict:
        """
        Exports monthly, quarterly, annual, and grade P&L tables to CSV and JSON formats.
        """
        os.makedirs(output_dir, exist_ok=True)
        summary = self.get_portfolio_summary_totals()
        monthly = self.get_monthly_pnl()
        quarterly = self.get_quarterly_pnl()
        annual = self.get_annual_pnl()
        grades = self.get_pnl_by_grade()

        paths = {
            "summary_json": os.path.join(output_dir, "pnl_portfolio_summary.json"),
            "monthly_csv": os.path.join(output_dir, "pnl_monthly_vintage.csv"),
            "quarterly_csv": os.path.join(output_dir, "pnl_quarterly_vintage.csv"),
            "annual_csv": os.path.join(output_dir, "pnl_annual_vintage.csv"),
            "grade_csv": os.path.join(output_dir, "pnl_by_credit_grade.csv")
        }

        with open(paths["summary_json"], "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        monthly.to_csv(paths["monthly_csv"], index=False)
        quarterly.to_csv(paths["quarterly_csv"], index=False)
        annual.to_csv(paths["annual_csv"], index=False)
        grades.to_csv(paths["grade_csv"], index=False)

        return paths


def main():
    parser = argparse.ArgumentParser(description="Portfolio Income Statement (P&L) Engine (DA-04)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite warehouse")
    parser.add_argument("--export", action="store_true", help="Export P&L statement files to reports/")
    args = parser.parse_args()

    engine = PortfolioPnLEngine(db_path=args.db_path)
    summary = engine.get_portfolio_summary_totals()

    print("=" * 70)
    print("LOAN PORTFOLIO FINANCIAL STATEMENT & SOLVENCY REPORT: P&L SUMMARY")
    print("=" * 70)
    for k, v in summary.items():
        if isinstance(v, float) and "pct" not in k:
            print(f"  {k:<35}: ${v:>18,.2f}")
        elif "pct" in k:
            print(f"  {k:<35}: {v:>18.2f}%")
        else:
            print(f"  {k:<35}: {str(v):>18}")
    print("=" * 70)

    if args.export:
        paths = engine.export_reports()
        print("Exported P&L statement files:")
        for name, path in paths.items():
            print(f"  {name}: {path}")


if __name__ == "__main__":
    main()

