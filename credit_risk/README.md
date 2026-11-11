# Credit Risk Scorecard & Basel II / IFRS 9 Engine

This directory houses the statistical credit risk modeling pipeline, aligning with Basel II / III Internal Ratings-Based (IRB) standards and IFRS 9 Expected Credit Loss (ECL).

## Planned Modules (Phase 5)
- `woe_iv_transformer.py`: Continuous feature discretization, coarse classing, Weight of Evidence (WoE) and Information Value (IV) computation.
- `scorecard_model.py`: Logistic Regression classifier estimating Probability of Default (PD).
- `score_scaling.py`: Linear transformation of log-odds into standard Credit Scorecard points ($Score = Offset + Factor \times \ln(Odds)$).
- `expected_loss.py`: Calculation of Loss Given Default (LGD), Exposure at Default (EAD), and portfolio Expected Loss ($EL = PD \times LGD \times EAD$).
- `model_validation.py`: Performance metrics computation (ROC-AUC, Gini, Kolmogorov-Smirnov (KS) statistic, and calibration curves).
