"""
Credit Risk Scorecard Pipeline Runner (Phase 2A)
Financial Analytics and Risk Reporting System (DA-04)

Executes:
1. Data loading and feature engineering (ScorecardDataPreprocessor)
2. Stratified 80/20 train/test split
3. Coarse classing and WOE/IV calculation on TRAIN only (WOEBinningTransformer)
4. Application of WOE transformation to TEST without refitting
5. Baseline Logistic Regression training on selected WOE predictors
6. Model evaluation on TRAIN and TEST datasets
7. Decile calibration and temporal maturity analysis
8. Exports JSON and CSV artifacts to reports/
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.scorecard_preprocessing import ScorecardDataPreprocessor
from credit_risk.woe_iv import WOEBinningTransformer
from credit_risk.baseline_model import BaselineScorecardModel
from credit_risk.evaluate_model import ScorecardEvaluator

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "warehouse.db")


def run_temporal_analysis(db_path: str = DEFAULT_DB_PATH) -> dict:
    """
    Analyzes vintage seasoning and maturity by origination year to support OOT planning.
    """
    uri = f"file:///{os.path.abspath(db_path).replace(os.sep, '/')}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        df = pd.read_sql_query("""
            SELECT 
                d.year                                                      AS issue_year,
                MIN(d.full_date)                                            AS earliest_date,
                MAX(d.full_date)                                            AS latest_date,
                COUNT(*)                                                    AS total_originated,
                SUM(CASE WHEN f.is_seasoned_closed = 1 THEN 1 ELSE 0 END)   AS closed_loans,
                SUM(CASE WHEN f.is_seasoned_closed = 0 THEN 1 ELSE 0 END)   AS active_loans,
                ROUND(100.0 * SUM(CASE WHEN f.is_seasoned_closed = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_closed,
                SUM(CASE WHEN f.is_confirmed_default = 1 THEN 1 ELSE 0 END) AS default_count,
                ROUND(100.0 * SUM(CASE WHEN f.is_confirmed_default = 1 THEN 1 ELSE 0 END) / 
                      NULLIF(SUM(CASE WHEN f.is_seasoned_closed = 1 THEN 1 ELSE 0 END), 0), 2) AS bad_rate_closed
            FROM fact_accepted_loans f
            JOIN dim_calendar_date d ON f.issue_date_key = d.date_key
            GROUP BY d.year
            ORDER BY d.year;
        """, conn)

    vintages = df.to_dict(orient="records")
    return {
        "earliest_issue_date": str(df["earliest_date"].min()),
        "latest_issue_date": str(df["latest_date"].max()),
        "vintages": vintages,
        "oot_recommendation": (
            "Recommended Out-of-Time (OOT) holdout: 2016 vintage (293,105 closed loans, 67.5% closed, 23.29% bad rate). "
            "Development training window: 2012–2015 vintages (784,820 closed loans, >89% mature). "
            "Avoid 2017–2018 for primary model training due to extreme right-censoring (>61% and >88% unclosed active loans)."
        )
    }


def main():
    print("=" * 75)
    print("NEXVIA DA-04: TASK 3 PHASE 2A — BASELINE SCORECARD PIPELINE")
    print("=" * 75)

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # 1. Preprocessing & Split
    print("\n[Step 1/5] Loading mature closed development cohort from warehouse.db...")
    preprocessor = ScorecardDataPreprocessor()
    train_df, test_df, split_meta = preprocessor.prepare_train_test_split(test_size=0.20, random_state=42)
    print(f"  Total Closed Cohort : {split_meta['total_records']:,} loans")
    print(f"  Train Set (80%)     : {split_meta['train_records']:,} loans (Bad Rate: {split_meta['train_bad_rate']:.4%})")
    print(f"  Test Set (20%)      : {split_meta['test_records']:,} loans (Bad Rate: {split_meta['test_bad_rate']:.4%})")

    # 2. Coarse Classing & WOE/IV on Train
    print("\n[Step 2/5] Fitting coarse classing and calculating WOE/IV on TRAIN only...")
    binner = WOEBinningTransformer()
    binner.fit(train_df, target_col="target")

    woe_csv_path = os.path.join(REPORTS_DIR, "credit_risk_woe_iv.csv")
    binner.export_woe_summary(woe_csv_path)
    print(f"  Exported full bin-level WOE/IV tables to: {woe_csv_path}")

    iv_summary_dict = binner.iv_summary.to_dict(orient="records")
    print("\n  Information Value (IV) Ranking on TRAIN:")
    for row in iv_summary_dict:
        print(f"    {row['variable']:<25}: IV = {row['iv']:.4f}  [{row['predictive_power']}]")

    # 3. Apply WOE Transformation to Train & Test
    print("\n[Step 3/5] Transforming Train and Test datasets using learned WOE mappings...")
    X_train_woe = binner.transform(train_df)
    X_test_woe = binner.transform(test_df)
    y_train = train_df["target"].values
    y_test = test_df["target"].values

    # Select features meeting IV threshold (IV >= 0.02)
    selected_features = [
        f"{row['variable']}_woe"
        for row in iv_summary_dict
        if row["iv"] >= 0.02 and f"{row['variable']}_woe" in X_train_woe.columns
    ]
    print(f"  Selected {len(selected_features)} features with IV >= 0.02:")
    for f in selected_features:
        print(f"    - {f}")

    # 4. Train Baseline Logistic Regression
    print("\n[Step 4/5] Training Baseline Logistic Regression (L2 penalty, lbfgs, C=1.0)...")
    model = BaselineScorecardModel(
        c_param=1.0,
        solver="lbfgs",
        max_iter=1000,
        random_state=42,
        feature_names=selected_features
    )
    model.fit(X_train_woe, y_train)

    coef_table = model.get_coefficient_table()
    print("\n  Model Coefficients:")
    print(coef_table.to_string(index=False))

    # 5. Model Evaluation
    print("\n[Step 5/5] Evaluating discrimination, calibration, and classification metrics...")
    train_probs = model.predict_proba(X_train_woe)
    test_probs = model.predict_proba(X_test_woe)

    evaluator = ScorecardEvaluator()
    train_metrics = evaluator.evaluate_dataset(y_train, train_probs, dataset_name="Train (80%)")
    test_metrics = evaluator.evaluate_dataset(y_test, test_probs, dataset_name="Test (20%)")
    decile_table = evaluator.generate_decile_calibration_table(y_test, test_probs)

    print("\n  TRAIN Performance:")
    print(f"    ROC-AUC    : {train_metrics['roc_auc']:.4f}")
    print(f"    Gini Index : {train_metrics['gini']:.4f}")
    print(f"    KS Stat (%) : {train_metrics['ks_statistic_pct']:.2f}% (Threshold: {train_metrics['ks_optimal_threshold']:.4f})")
    print(f"    PR-AUC     : {train_metrics['pr_auc']:.4f}")
    print(f"    Brier Score: {train_metrics['brier_score']:.4f}")

    print("\n  TEST Performance:")
    print(f"    ROC-AUC    : {test_metrics['roc_auc']:.4f}")
    print(f"    Gini Index : {test_metrics['gini']:.4f}")
    print(f"    KS Stat (%) : {test_metrics['ks_statistic_pct']:.2f}% (Threshold: {test_metrics['ks_optimal_threshold']:.4f})")
    print(f"    PR-AUC     : {test_metrics['pr_auc']:.4f}")
    print(f"    Brier Score: {test_metrics['brier_score']:.4f}")

    print("\n  Decile Calibration Table (Test Set):")
    print(decile_table[["decile", "loan_count", "bad_count", "mean_predicted_prob", "observed_bad_rate", "calibration_ratio", "decile_ks"]].to_string(index=False))

    # Temporal analysis
    temporal_info = run_temporal_analysis()

    # Compile comprehensive reports
    full_report = {
        "report_title": "Nexvia DA-04 Task 3 Phase 2A: Baseline Credit Risk Scorecard Report",
        "development_population": {
            "source_filter": "is_seasoned_closed = 1",
            "total_contracts": split_meta["total_records"],
            "train_contracts": split_meta["train_records"],
            "test_contracts": split_meta["test_records"],
            "train_bad_rate": split_meta["train_bad_rate"],
            "test_bad_rate": split_meta["test_bad_rate"],
            "target_definition": "Y = is_confirmed_default (0 = Good, 1 = Bad)"
        },
        "feature_selection": {
            "candidate_features_evaluated": len(iv_summary_dict),
            "iv_summary": iv_summary_dict,
            "selected_features": selected_features,
            "selection_rationale": "Filtered predictors with IV >= 0.02 and strictly pre-origination availability"
        },
        "model_specification": model.get_model_metadata(),
        "model_coefficients": coef_table.to_dict(orient="records"),
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "decile_calibration": decile_table.to_dict(orient="records"),
        "temporal_maturity_analysis": temporal_info,
        "status": "BASELINE_SCORECARD_COMPLETE"
    }

    report_json_path = os.path.join(REPORTS_DIR, "credit_risk_phase2a_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    test_metrics_path = os.path.join(REPORTS_DIR, "credit_risk_test_metrics.json")
    with open(test_metrics_path, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)

    print(f"\n  Exported complete Phase 2A report to : {report_json_path}")
    print(f"  Exported test metrics to              : {test_metrics_path}")
    print("=" * 75)
    print("TASK 3 PHASE 2A EXECUTION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()

