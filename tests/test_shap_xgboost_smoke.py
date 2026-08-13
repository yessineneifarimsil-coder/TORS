"""
Compatibility smoke test for XGBoost + interventional TreeSHAP.

This is NOT part of the scientific experiment.
Its only purpose is to verify that the installed software stack
can fit an XGBoost regression model and compute interventional
TreeSHAP values satisfying local accuracy.
"""

from __future__ import annotations

import numpy as np
import shap
import xgboost
from xgboost import XGBRegressor


SEED = 12345
N_SAMPLES = 300
N_FEATURES = 10

BACKGROUND_SIZE = 50
N_EVAL = 20

ATOL = 1e-5
RTOL = 1e-5


def generate_smoke_data() -> tuple[np.ndarray, np.ndarray]:
    """Generate a small nonlinear regression dataset."""

    rng = np.random.default_rng(SEED)

    X = rng.uniform(
        low=0.0,
        high=1.0,
        size=(N_SAMPLES, N_FEATURES),
    )

    y = (
        0.20 * X[:, 0]
        + 0.15 * X[:, 1]
        + 0.10 * np.log1p(2.0 * X[:, 2])
        + 0.15 * X[:, 3] * X[:, 4]
        + 0.10 * X[:, 5]
        + 0.10 * X[:, 6] * X[:, 7]
        + 0.05 * X[:, 8]
        + 0.05 * X[:, 9]
    )

    y += rng.normal(
        loc=0.0,
        scale=0.01,
        size=N_SAMPLES,
    )

    return X, y


def test_interventional_treeshap_local_accuracy() -> None:
    """
    Check that:

        prediction ~= expected_value + sum(SHAP values)

    for interventional TreeSHAP.
    """

    X, y = generate_smoke_data()

    X_train = X[:220]
    y_train = y[:220]

    X_eval = X[220 : 220 + N_EVAL]

    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_alpha=0.0,
        reg_lambda=1.0,
        random_state=SEED,
        n_jobs=1,
        verbosity=0,
    )

    model.fit(X_train, y_train)

    background = X_train[:BACKGROUND_SIZE]

    explainer = shap.TreeExplainer(
        model=model,
        data=background,
        feature_perturbation="interventional",
        model_output="raw",
    )

    explanation = explainer(X_eval)

    shap_values = np.asarray(
        explanation.values,
        dtype=float,
    )

    base_values = np.asarray(
        explanation.base_values,
        dtype=float,
    ).reshape(-1)

    predictions = np.asarray(
        model.predict(X_eval),
        dtype=float,
    )

    assert shap_values.shape == (
        N_EVAL,
        N_FEATURES,
    )

    assert base_values.shape == (N_EVAL,)

    assert np.all(np.isfinite(shap_values))
    assert np.all(np.isfinite(base_values))
    assert np.all(np.isfinite(predictions))

    reconstructed = (
        base_values
        + shap_values.sum(axis=1)
    )

    np.testing.assert_allclose(
        reconstructed,
        predictions,
        rtol=RTOL,
        atol=ATOL,
        err_msg=(
            "TreeSHAP local accuracy failed: "
            "base value + sum(SHAP values) "
            "does not reproduce the XGBoost prediction."
        ),
    )


if __name__ == "__main__":

    print("=" * 70)
    print("XGBoost + TreeSHAP compatibility smoke test")
    print("=" * 70)

    print(f"NumPy   : {np.__version__}")
    print(f"XGBoost : {xgboost.__version__}")
    print(f"SHAP    : {shap.__version__}")

    X, y = generate_smoke_data()

    X_train = X[:220]
    y_train = y[:220]
    X_eval = X[220 : 220 + N_EVAL]

    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_alpha=0.0,
        reg_lambda=1.0,
        random_state=SEED,
        n_jobs=1,
        verbosity=0,
    )

    model.fit(X_train, y_train)

    background = X_train[:BACKGROUND_SIZE]

    explainer = shap.TreeExplainer(
        model=model,
        data=background,
        feature_perturbation="interventional",
        model_output="raw",
    )

    explanation = explainer(X_eval)

    reconstructed = (
        np.asarray(explanation.base_values).reshape(-1)
        + np.asarray(explanation.values).sum(axis=1)
    )

    predictions = model.predict(X_eval)

    errors = np.abs(
        reconstructed - predictions
    )

    print(
        "Maximum local-accuracy error:",
        f"{errors.max():.12e}",
    )

    print(
        "Mean local-accuracy error   :",
        f"{errors.mean():.12e}",
    )

    test_interventional_treeshap_local_accuracy()

    print()
    print("SMOKE TEST PASSED")
    print("=" * 70)