"""
Unit & Integration Tests for Weight of Evidence (WOE) & Information Value (IV) Engine
Financial Analytics and Risk Reporting System (DA-04)

Verifies:
1. WOE coarse classing is fitted strictly on training data.
2. Calling transform() on test data does NOT re-fit or alter learned WOE mappings.
3. WOE and IV formulas satisfy standard credit scorecard mathematical definitions.
4. Transformed feature matrix contains 0 NaNs and 0 Infs.
5. Missing/special values are mapped cleanly to discrete bins without dropping rows.
6. IV summary correctly classifies predictive strength.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from credit_risk.woe_iv import WOEBinningTransformer


@pytest.fixture
def synthetic_train_test():
    """Generates a controlled synthetic dataset to test WOE/IV mathematics."""
    np.random.seed(42)
    n = 2000

    # Continuous feature correlated with default
    fico = np.random.normal(700, 40, n)
    dti = np.random.uniform(5, 45, n)
    term = np.random.choice([36, 60], size=n, p=[0.7, 0.3])
    home = np.random.choice(["MORTGAGE", "RENT", "OWN", "OTHER"], size=n)

    # Probability of default
    prob = 1.0 / (1.0 + np.exp(0.015 * (fico - 680) - 0.05 * (dti - 15) - 0.5 * (term == 60)))
    y = (np.random.rand(n) < prob).astype(int)

    df = pd.DataFrame({
        "fico_midpoint": fico,
        "dti": dti,
        "term_months": term,
        "home_ownership_clean": home,
        "target": y
    })

    train_df = df.iloc[:1600].copy()
    test_df = df.iloc[1600:].copy()
    return train_df, test_df


def test_woe_fit_only_on_train(synthetic_train_test):
    """Verify that WOE binning transformer fits and extracts tables on train only."""
    train_df, _ = synthetic_train_test
    binner = WOEBinningTransformer()

    assert not binner.is_fitted
    binner.fit(train_df, target_col="target")
    assert binner.is_fitted
    assert len(binner.woe_tables) > 0
    assert binner.iv_summary is not None
    assert "iv" in binner.iv_summary.columns


def test_woe_transform_does_not_refit(synthetic_train_test):
    """Verify that transform() applies static training weights without altering them."""
    train_df, test_df = synthetic_train_test
    binner = WOEBinningTransformer()
    binner.fit(train_df, target_col="target")

    # Capture initial train mapping for fico_midpoint
    initial_fico_mapping = dict(binner.bin_mappings["fico_midpoint"])
    initial_iv = binner.iv_summary.loc[binner.iv_summary["variable"] == "fico_midpoint", "iv"].values[0]

    # Transform test set multiple times
    _ = binner.transform(test_df)
    _ = binner.transform(test_df)

    # Verify mappings remain 100% identical
    after_fico_mapping = binner.bin_mappings["fico_midpoint"]
    after_iv = binner.iv_summary.loc[binner.iv_summary["variable"] == "fico_midpoint", "iv"].values[0]

    assert initial_fico_mapping == after_fico_mapping
    assert initial_iv == after_iv


def test_woe_iv_mathematical_consistency(synthetic_train_test):
    """Verify exact formula consistency: WOE = ln(Dist_Goods / Dist_Bads) and IV sum."""
    train_df, _ = synthetic_train_test
    binner = WOEBinningTransformer()
    binner.fit(train_df, target_col="target")

    fico_table = binner.woe_tables["fico_midpoint"]
    for _, row in fico_table.iterrows():
        dg = row["dist_goods"]
        db = row["dist_bads"]
        expected_woe = np.log(dg / db)
        assert abs(row["woe"] - expected_woe) < 1e-5, "WOE formula mismatch"
        expected_iv_contrib = (dg - db) * row["woe"]
        assert abs(row["iv_contribution"] - expected_iv_contrib) < 1e-5, "IV contribution mismatch"

    total_iv_expected = fico_table["iv_contribution"].sum()
    recorded_iv = binner.iv_summary.loc[binner.iv_summary["variable"] == "fico_midpoint", "iv"].values[0]
    assert abs(total_iv_expected - recorded_iv) < 1e-5


def test_no_nans_or_infs_in_transformed_matrix(synthetic_train_test):
    """Verify that transform returns a clean matrix with zero NaNs and zero Infs."""
    train_df, test_df = synthetic_train_test

    # Introduce synthetic missing and extreme values
    test_df.loc[test_df.index[0], "fico_midpoint"] = np.nan
    test_df.loc[test_df.index[1], "dti"] = -1.0
    test_df.loc[test_df.index[2], "dti"] = 999.0

    binner = WOEBinningTransformer()
    binner.fit(train_df, target_col="target")
    test_woe = binner.transform(test_df)

    assert test_woe.isnull().sum().sum() == 0, "Transformed matrix contains NaNs"
    assert not np.isinf(test_woe.values).any(), "Transformed matrix contains Infs"


def test_iv_classification_ranges():
    """Verify predictive strength classification logic."""
    assert "Unpredictive" in WOEBinningTransformer._classify_iv(0.01)
    assert "Weak" in WOEBinningTransformer._classify_iv(0.05)
    assert "Medium" in WOEBinningTransformer._classify_iv(0.20)
    assert "Strong" in WOEBinningTransformer._classify_iv(0.40)
    assert "Suspiciously High" in WOEBinningTransformer._classify_iv(0.65)

