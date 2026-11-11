"""
Master Pipeline Runner: Task 3 Phase 2B Final Scorecard & OOT Validation
Financial Analytics and Risk Reporting System (DA-04)

Component: Task 3 Phase 2B
Executes:
1. Model Governance & Multicollinearity Review (VIF, correlation, sign checks).
2. Refined WOE Binning & Final Logistic Regression on 80% Train.
3. Scorecard Scaling (600 base score @ 50:1 odds, PDO=20, integer points table).
4. In-Time Test Validation on untouched 20% holdout (AUC, Gini, KS, PR-AUC, Brier, Deciles).
5. 6 Neutral Risk Bands calculation and distribution.
6. Adverse Action Reason Codes generation on sample profiles.
7. Out-of-Time (OOT) Vintage Validation (2012–2015 Train vs 2016 OOT Test).
8. Exports all authoritative report artifacts to reports/ directory.
"""

import os
import sys
import json
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.scorecard_preprocessing import ScorecardDataPreprocessor
from credit_risk.woe_iv import WOEBinningTransformer
from credit_risk.governance_review import ModelGovernanceReviewer
from credit_risk.final_scorecard import FinalScorecardModel
from credit_risk.oot_validation import OOTScorecardValidator


def run_phase2b_pipeline():
    print("================================================================================")
    print("NEXVIA DA-04: TASK 3 PHASE 2B — FINAL SCORECARD ENGINEERING & OOT VALIDATION")
    print("================================================================================")

    reports_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # 1. Load Data
    print("\n[Step 1/6] Loading development population and preparing 80/20 train/test split...")
    preprocessor = ScorecardDataPreprocessor()
    train_df, test_df, metadata = preprocessor.prepare_train_test_split(test_size=0.20, random_state=42)
    print(f"  Total Closed Loans: {metadata['total_records']:,}")
    print(f"  Train Set:          {metadata['train_records']:,} loans (Bad Rate: {metadata['train_bad_rate']:.4%})")
    print(f"  Holdout Test Set:   {metadata['test_records']:,} loans (Bad Rate: {metadata['test_bad_rate']:.4%})")

    # 2. Model Governance Review
    print("\n[Step 2/6] Conducting Model Governance & Multicollinearity Review...")
    temp_transformer = WOEBinningTransformer()
    temp_transformer.fit(train_df, target_col="target")
    gov_reviewer = ModelGovernanceReviewer(random_state=42)
    gov_report = gov_reviewer.run_review(train_df, temp_transformer)

    gov_json_path = os.path.join(reports_dir, "credit_risk_governance_review.json")
    gov_reviewer.export_report(gov_report, gov_json_path)
    print(f"  Saved governance review to: {gov_json_path}")
    print("  Multicollinearity resolution summary:")
    for r in gov_report["rationalization_details"]:
        print(f"    - Excluded {r['excluded_variable']}: Original coef {r['original_multivariate_coef']:+.4f}, VIF {r['vif_in_9_model']:.2f}")

    # 3. Train Final Scorecard Model
    print("\n[Step 3/6] Fitting Final Scorecard Model (7 Approved Predictors) on Train...")
    scorecard = FinalScorecardModel(c_param=1.0, solver="lbfgs", max_iter=1000, random_state=42)
    scorecard.fit(train_df, target_col="target")

    print(f"  Intercept: {scorecard.intercept_:.4f}")
    print("  Feature Coefficients:")
    for feat, coef in scorecard.coefficients_.items():
        print(f"    {feat:28s}: {coef:+.4f}")

    # Export Points Table & Bin Summary
    points_csv_path = os.path.join(reports_dir, "credit_risk_scorecard_points.csv")
    scorecard.scaler.export_points_csv(points_csv_path)
    print(f"  Saved points table to: {points_csv_path}")

    bins_csv_path = os.path.join(reports_dir, "credit_risk_scorecard_bins.csv")
    scorecard.transformer.export_woe_summary(bins_csv_path)
    print(f"  Saved bin summary to: {bins_csv_path}")

    # 4. In-Time Test Set Evaluation
    print("\n[Step 4/6] Evaluating In-Time Holdout Test Set (20% sample, n = 269,620)...")
    test_eval = scorecard.evaluate(test_df, target_col="target")
    discrim = test_eval["discrimination_metrics"]
    calib = test_eval["calibration_metrics"]

    print(f"  ROC-AUC:   {discrim['roc_auc']:.4f}")
    print(f"  Gini:      {discrim['gini']:.4f}")
    print(f"  KS Stat:   {discrim['ks_statistic_pct']:.2f}%")
    print(f"  PR-AUC:    {discrim['pr_auc']:.4f}")
    print(f"  Brier:     {calib['brier_score']:.4f}")

    metrics_json_path = os.path.join(reports_dir, "credit_risk_model_metrics.json")
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(test_eval, f, indent=2)
    print(f"  Saved test metrics and deciles to: {metrics_json_path}")

    risk_bands_json_path = os.path.join(reports_dir, "credit_risk_risk_bands.json")
    with open(risk_bands_json_path, "w", encoding="utf-8") as f:
        json.dump(test_eval["risk_band_distribution"], f, indent=2)
    print(f"  Saved 6 neutral risk bands distribution to: {risk_bands_json_path}")

    # 5. Adverse Reason Codes on Sample Profiles
    print("\n[Step 5/6] Demonstrating Adverse Action Reason Codes on Sample Profiles...")
    sample_profiles = [
        {
            "name": "Subprime High-Risk Profile",
            "term_months": 60,
            "fico_midpoint": 665.0,
            "installment_to_income": 18.5,
            "dti": 34.0,
            "verification_status": "Verified",
            "home_ownership_clean": "RENT",
            "annual_inc": 32000.0
        },
        {
            "name": "Moderate-Risk Profile",
            "term_months": 36,
            "fico_midpoint": 695.0,
            "installment_to_income": 11.0,
            "dti": 22.0,
            "verification_status": "Source Verified",
            "home_ownership_clean": "MORTGAGE",
            "annual_inc": 58000.0
        },
        {
            "name": "Prime Low-Risk Profile",
            "term_months": 36,
            "fico_midpoint": 765.0,
            "installment_to_income": 4.5,
            "dti": 8.0,
            "verification_status": "Not Verified",
            "home_ownership_clean": "MORTGAGE",
            "annual_inc": 115000.0
        }
    ]

    sample_explanations = []
    for sp in sample_profiles:
        name = sp.pop("name")
        explanation = scorecard.explain_adverse_action(sp, top_n=4)
        explanation["profile_name"] = name
        sample_explanations.append(explanation)
        print(f"\n  Profile: {name}")
        print(f"    Score: {explanation['credit_score']} | Risk Band: {explanation['risk_band']} | Modeled PD: {explanation['probability_of_default']:.2%}")
        print("    Top Adverse Action Reasons:")
        for r in explanation["adverse_action_reasons"]:
            print(f"      [{r['code']}] {r['reason_name']:24s}: Lost {r['points_lost']} pts (Assigned: {r['assigned_points']}/{r['maximum_points']}) - {r['narrative']}")

    # 6. Out-of-Time (OOT) Validation
    print("\n[Step 6/6] Executing Out-of-Time (OOT) Vintage Temporal Validation...")
    oot_validator = OOTScorecardValidator(preprocessor=preprocessor)
    oot_report = oot_validator.run_oot_validation()

    oot_json_path = os.path.join(reports_dir, "credit_risk_oot_validation.json")
    oot_validator.export_report(oot_report, oot_json_path)
    print(f"  Saved OOT validation report to: {oot_json_path}")
    print(f"  OOT Train (2012-2015): {oot_report['training_cohort_summary']['total_loans']:,} loans (Bad Rate: {oot_report['training_cohort_summary']['bad_rate']:.4%})")
    print(f"  OOT Test (2016):       {oot_report['oot_testing_cohort_summary']['total_loans']:,} loans (Bad Rate: {oot_report['oot_testing_cohort_summary']['bad_rate']:.4%})")
    print(f"  OOT ROC-AUC:           {oot_report['oot_test_metrics']['roc_auc']:.4f} (In-Sample: {oot_report['in_sample_train_metrics']['roc_auc']:.4f}, Delta: {oot_report['temporal_stability_deltas']['roc_auc_delta']:+.4f})")
    print(f"  OOT Gini:              {oot_report['oot_test_metrics']['gini']:.4f}")
    print(f"  OOT KS Stat:           {oot_report['oot_test_metrics']['ks_statistic_pct']:.2f}%")
    print(f"  OOT Brier Score:       {oot_report['oot_calibration_metrics']['brier_score']:.4f}")

    # Consolidated Final Scorecard Report
    final_scorecard_summary = {
        "model_title": "Nexvia Technologies Credit Risk Scorecard & Probability of Default Model",
        "regulatory_governance_statement": (
            "Analytical credit risk scorecard developed for portfolio analytics and risk-based underwriting. "
            "Does not constitute statutory Basel IRB capital model approval or third-party credit bureau endorsement."
        ),
        "development_population": {
            "source": "fact_accepted_loans (is_seasoned_closed = 1)",
            "total_contracts": metadata["total_records"],
            "train_contracts": metadata["train_records"],
            "test_contracts": metadata["test_records"],
            "empirical_prior_bad_rate": metadata["overall_bad_rate"],
            "class_distribution": {
                "goods": metadata["train_good_count"] + metadata["test_good_count"],
                "bads": metadata["train_bad_count"] + metadata["test_bad_count"]
            }
        },
        "scorecard_scaling": {
            "base_score": scorecard.scaler.base_score,
            "base_odds": scorecard.scaler.base_odds,
            "pdo": scorecard.scaler.pdo,
            "factor": round(scorecard.scaler.factor, 4),
            "offset": round(scorecard.scaler.offset, 4),
            "base_points_per_feature": round(scorecard.scaler.base_points_per_feature_, 4),
            "score_range": {
                "theoretical_min": int(scorecard.scaler.points_table_.groupby("feature")["points"].min().sum()),
                "theoretical_max": int(scorecard.scaler.points_table_.groupby("feature")["points"].max().sum())
            }
        },
        "model_specification": {
            "model_type": "Multivariate Logistic Regression on WOE Bins",
            "regularization": "L2 (C=1.0)",
            "solver": "lbfgs",
            "intercept": round(scorecard.intercept_, 4),
            "coefficients": {k: round(v, 4) for k, v in scorecard.coefficients_.items()}
        },
        "in_time_test_metrics": test_eval["discrimination_metrics"],
        "in_time_calibration_metrics": test_eval["calibration_metrics"],
        "oot_validation_summary": {
            "oot_cohort": "2016 Mature Closed Loans (n=293,105)",
            "oot_bad_rate": oot_report["oot_testing_cohort_summary"]["bad_rate"],
            "oot_roc_auc": oot_report["oot_test_metrics"]["roc_auc"],
            "oot_gini": oot_report["oot_test_metrics"]["gini"],
            "oot_ks_pct": oot_report["oot_test_metrics"]["ks_statistic_pct"],
            "oot_brier": oot_report["oot_calibration_metrics"]["brier_score"],
            "auc_degradation": oot_report["temporal_stability_deltas"]["roc_auc_delta"]
        },
        "risk_bands": test_eval["risk_band_distribution"],
        "sample_adverse_action_explanations": sample_explanations
    }

    final_json_path = os.path.join(reports_dir, "credit_risk_final_scorecard.json")
    with open(final_json_path, "w", encoding="utf-8") as f:
        json.dump(final_scorecard_summary, f, indent=2)
    print(f"\n  Saved master scorecard specification to: {final_json_path}")

    print("\n================================================================================")
    print("PHASE 2B PIPELINE COMPLETED SUCCESSFULLY")
    print("================================================================================")


if __name__ == "__main__":
    run_phase2b_pipeline()

