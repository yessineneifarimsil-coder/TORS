from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import nnls
from sklearn.model_selection import GroupKFold


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "ridge_plus_weights_v1.py"

spec = importlib.util.spec_from_file_location(
    "ridge_plus_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load ridge_plus_weights_v1.py for tests.")
ridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ridge
spec.loader.exec_module(ridge)


def make_n25_rows(replication_seed: int = 21001) -> pd.DataFrame:
    records = []
    for context_number in range(1, 26):
        partition = "weight" if context_number % 5 == 0 else "fit"
        for alternative_number in range(1, 7):
            row = {
                "context_id": f"ctx_{context_number:04d}",
                "context_number": context_number,
                "replication_seed": replication_seed,
                "partition": partition,
                "alternative_id": f"A{alternative_number}",
            }
            values = []
            for j in range(1, 11):
                raw = (
                    0.031 * context_number
                    + 0.067 * alternative_number
                    + 0.019 * j
                    + 0.0025 * context_number * j
                )
                value = float((raw % 1.0) * 0.8 + 0.1)
                row[f"g_C{j}"] = value
                values.append(value)
            row["Y"] = float(
                0.42 * values[0]
                + 0.27 * values[3]
                + 0.18 * values[7]
                + 0.04 * np.sin(context_number + alternative_number)
            )
            records.append(row)

    for alternative_number in range(1, 7):
        row = {
            "context_id": "ctx_1001",
            "context_number": 1001,
            "replication_seed": 99999,
            "partition": "test",
            "alternative_id": f"A{alternative_number}",
            "Y": np.nan,
        }
        for j in range(1, 11):
            row[f"g_C{j}"] = np.nan
        records.append(row)
    return pd.DataFrame.from_records(records)


def independent_fit(x: np.ndarray, y: np.ndarray, tau: float):
    x_mean = np.mean(x, axis=0)
    x_sd = np.std(x, axis=0, ddof=0)
    active = x_sd > 1e-12
    xz = np.zeros_like(x)
    xz[:, active] = (x[:, active] - x_mean[active]) / x_sd[active]
    y_mean = float(np.mean(y))
    y_sd = float(np.std(y, ddof=0))
    beta = np.zeros(10)
    if y_sd > 1e-12 and np.any(active):
        yz = (y - y_mean) / y_sd
        active_index = np.flatnonzero(active)
        design = np.vstack([xz[:, active], np.sqrt(tau) * np.eye(len(active_index))])
        target = np.r_[yz, np.zeros(len(active_index))]
        beta[active], _ = nnls(design, target)
    return beta, x_mean, x_sd, active, y_mean, y_sd


def test_frozen_constants_grid_and_feature_order():
    assert ridge.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert ridge.CANDIDATE_TAU == (0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
    assert ridge.CV_FOLDS == 5
    assert ridge.EPSILON == 1e-12
    assert ridge.TIE_ABSOLUTE_TOLERANCE == 1e-12


def test_prepare_uses_exact_fit_rows_and_context_groups():
    selected = ridge.prepare_ridge_fit_rows(
        make_n25_rows(),
        replication_seed=21001,
        n_contexts=25,
    )
    assert len(selected) == 120
    assert selected["context_id"].nunique() == 20
    assert set(selected["partition"]) == {"fit"}
    assert selected.groupby("context_id").size().eq(6).all()


def test_weight_and_test_scientific_values_cannot_change_fit_rows():
    rows = make_n25_rows()
    baseline = ridge.prepare_ridge_fit_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    changed = rows.copy()
    excluded = changed["partition"].isin(["weight", "test"])
    changed.loc[excluded, list(ridge.FEATURES)] = np.nan
    changed.loc[excluded, "Y"] = np.nan
    challenged = ridge.prepare_ridge_fit_rows(
        changed,
        replication_seed=21001,
        n_contexts=25,
    )
    pd.testing.assert_frame_equal(baseline, challenged)


def test_standardized_nnls_matches_independent_augmented_solution():
    rng = np.random.default_rng(4321)
    x = rng.normal(size=(80, 10))
    y = 0.8 * x[:, 0] + 0.4 * x[:, 3] + 0.2 * x[:, 8] + rng.normal(0, 0.05, 80)
    observed = ridge.fit_standardized_nnls(x, y, tau=0.1)
    expected = independent_fit(x, y, 0.1)
    np.testing.assert_allclose(observed.coefficients, expected[0], atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(observed.x_mean, expected[1], atol=1e-15, rtol=0.0)
    np.testing.assert_allclose(observed.x_sd, expected[2], atol=1e-15, rtol=0.0)
    np.testing.assert_array_equal(observed.active_feature_mask, expected[3])
    assert observed.y_mean == pytest.approx(expected[4])
    assert observed.y_sd == pytest.approx(expected[5])


def test_prediction_returns_to_original_y_scale_without_intercept_parameter():
    rng = np.random.default_rng(8)
    x = rng.uniform(-2.0, 3.0, size=(60, 10))
    y = 17.0 + 5.0 * x[:, 0] + 2.0 * x[:, 2]
    model = ridge.fit_standardized_nnls(x, y, tau=0.0001)
    prediction = ridge.predict_original_scale(model, x)
    manual_x = (x - model.x_mean) / model.x_sd
    manual = model.y_mean + model.y_sd * (manual_x @ model.coefficients)
    np.testing.assert_allclose(prediction, manual, atol=1e-12, rtol=0.0)
    assert not hasattr(model, "intercept")


def test_population_sd_ddof_zero_is_used():
    x = np.tile(np.arange(6.0)[:, None], (1, 10))
    y = np.arange(6.0)
    model = ridge.fit_standardized_nnls(x, y, tau=0.1)
    assert model.x_sd[0] == pytest.approx(np.std(x[:, 0], ddof=0))
    assert abs(model.x_sd[0] - np.std(x[:, 0], ddof=1)) > 0.1
    assert model.y_sd == pytest.approx(np.std(y, ddof=0))


def test_zero_variance_feature_is_fixed_to_zero():
    rng = np.random.default_rng(9)
    x = rng.normal(size=(50, 10))
    x[:, 4] = 0.7
    y = x[:, 0] + 0.2 * x[:, 1]
    model = ridge.fit_standardized_nnls(x, y, tau=0.01)
    assert bool(model.active_feature_mask[4]) is False
    assert model.coefficients[4] == 0.0


def test_constant_y_produces_zero_coefficients_and_constant_predictions():
    rng = np.random.default_rng(10)
    x = rng.normal(size=(40, 10))
    y = np.full(40, 3.25)
    model = ridge.fit_standardized_nnls(x, y, tau=0.01)
    prediction = ridge.predict_original_scale(model, x[:7])
    assert model.y_constant is True
    assert np.all(model.coefficients == 0.0)
    np.testing.assert_array_equal(prediction, np.full(7, 3.25))


def test_grouped_cv_matches_independent_fold_local_reconstruction():
    selected = ridge.prepare_ridge_fit_rows(
        make_n25_rows(),
        replication_seed=21001,
        n_contexts=25,
    )
    x = selected.loc[:, ridge.FEATURES].to_numpy(float)
    y = selected["Y"].to_numpy(float)
    groups = selected["context_id"].to_numpy()
    observed = ridge.select_ridge_tau(x, y, groups)

    splitter = GroupKFold(n_splits=5)
    expected = {tau: [] for tau in ridge.CANDIDATE_TAU}
    for train, valid in splitter.split(x, y, groups=groups):
        assert not (set(groups[train]) & set(groups[valid]))
        for tau in ridge.CANDIDATE_TAU:
            beta, mean, sd, active, y_mean, y_sd = independent_fit(x[train], y[train], tau)
            xz = np.zeros_like(x[valid])
            xz[:, active] = (x[valid][:, active] - mean[active]) / sd[active]
            pred = y_mean + y_sd * (xz @ beta)
            expected[tau].append(float(np.sqrt(np.mean((y[valid] - pred) ** 2))))

    for tau in ridge.CANDIDATE_TAU:
        np.testing.assert_allclose(observed.fold_rmse_by_tau[tau], expected[tau], atol=1e-12)
        assert observed.mean_rmse_by_tau[tau] == pytest.approx(np.mean(expected[tau]))
    minimum = min(np.mean(expected[tau]) for tau in ridge.CANDIDATE_TAU)
    tied = [tau for tau in ridge.CANDIDATE_TAU if np.mean(expected[tau]) <= minimum + 1e-12]
    assert observed.selected_tau == min(tied)


def test_constant_y_cv_tie_selects_smallest_tau():
    rng = np.random.default_rng(11)
    x = rng.normal(size=(50, 10))
    y = np.full(50, 2.0)
    groups = np.repeat(np.arange(10), 5)
    result = ridge.select_ridge_tau(x, y, groups)
    assert result.selected_tau == min(ridge.CANDIDATE_TAU)
    assert max(result.mean_rmse_by_tau.values()) - min(result.mean_rmse_by_tau.values()) == 0.0


def test_full_result_weights_nonnegative_sum_one_and_record_semantics():
    result = ridge.compute_ridge_plus_weights(
        make_n25_rows(),
        replication_seed=21001,
        n_contexts=25,
    )
    weights = np.array(list(result.weights_by_feature.values()))
    coefficients = np.array(list(result.coefficients_by_feature.values()))
    assert np.all(weights >= 0.0)
    assert np.all(coefficients >= 0.0)
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    assert result.selected_tau in ridge.CANDIDATE_TAU
    assert result.diagnostics["partition"] == "fit"
    assert result.diagnostics["rows_used"] == 120
    assert result.diagnostics["intercept_in_standardized_space"] is False
    assert result.diagnostics["cv_statistics_fit_within_each_training_fold"] is True
    assert result.diagnostics["cv_metric"] == "RMSE_on_original_Y_scale"


def test_constant_y_full_result_uses_recorded_equal_fallback():
    rows = make_n25_rows()
    rows.loc[rows["partition"].eq("fit"), "Y"] = 4.0
    result = ridge.compute_ridge_plus_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    assert result.weights_by_feature == {f"g_C{i}": 0.1 for i in range(1, 11)}
    assert all(value == 0.0 for value in result.coefficients_by_feature.values())
    assert result.diagnostics["fallback_used"] is True
    assert result.diagnostics["y_constant"] is True


def test_row_order_cannot_change_ridge_result():
    rows = make_n25_rows()
    baseline = ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)
    shuffled = rows.sample(frac=1.0, random_state=19).reset_index(drop=True)
    challenged = ridge.compute_ridge_plus_weights(
        shuffled, replication_seed=21001, n_contexts=25
    )
    assert challenged.selected_tau == baseline.selected_tau
    assert challenged.weights_by_feature == pytest.approx(baseline.weights_by_feature, abs=0.0)
    assert challenged.mean_cv_rmse_by_tau == pytest.approx(baseline.mean_cv_rmse_by_tau, abs=0.0)


def test_weight_and_test_rows_cannot_change_ridge_result():
    rows = make_n25_rows()
    baseline = ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)
    changed = rows.copy()
    excluded = changed["partition"].isin(["weight", "test"])
    changed.loc[excluded, list(ridge.FEATURES)] = np.nan
    changed.loc[excluded, "Y"] = np.nan
    challenged = ridge.compute_ridge_plus_weights(
        changed, replication_seed=21001, n_contexts=25
    )
    assert challenged.weights_by_feature == pytest.approx(baseline.weights_by_feature)
    assert challenged.diagnostics["weight_rows_used"] == 0
    assert challenged.diagnostics["external_test_rows_used"] == 0


def test_target_and_scientific_firewalls_are_recorded():
    result = ridge.compute_ridge_plus_weights(
        make_n25_rows(), replication_seed=21001, n_contexts=25
    )
    d = result.diagnostics
    assert d["target_Y_used"] is True
    assert d["oracle_utility_used"] is False
    assert d["shap_used"] is False
    assert d["mcdm_executed"] is False
    assert d["winner_inspected"] is False


def test_fewer_than_five_cv_groups_fails_closed():
    rng = np.random.default_rng(12)
    with pytest.raises(ValueError):
        ridge.select_ridge_tau(
            rng.normal(size=(20, 10)),
            rng.normal(size=20),
            np.repeat(np.arange(4), 5),
        )


def test_wrong_replication_seed_fails_closed():
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(
            make_n25_rows(), replication_seed=21002, n_contexts=25
        )


@pytest.mark.parametrize("column", ["g_C4", "Y"])
def test_nonfinite_fit_value_fails_closed(column):
    rows = make_n25_rows()
    rows.loc[0, column] = np.nan
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)


def test_out_of_range_fit_feature_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "g_C4"] = 1.1
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)


def test_duplicate_fit_identity_fails_closed():
    rows = make_n25_rows()
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)


def test_wrong_fit_row_count_fails_closed():
    rows = make_n25_rows().drop(index=0).reset_index(drop=True)
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)


def test_missing_required_column_fails_closed():
    rows = make_n25_rows().drop(columns=["Y"])
    with pytest.raises(ValueError):
        ridge.compute_ridge_plus_weights(rows, replication_seed=21001, n_contexts=25)


def test_array_shapes_finiteness_and_tau_fail_closed():
    with pytest.raises(ValueError):
        ridge.fit_standardized_nnls(np.ones((5, 9)), np.ones(5), tau=0.1)
    with pytest.raises(ValueError):
        ridge.fit_standardized_nnls(np.ones((1, 10)), np.ones(1), tau=0.1)
    with pytest.raises(ValueError):
        ridge.fit_standardized_nnls(np.ones((5, 10)), np.ones(4), tau=0.1)
    with pytest.raises(ValueError):
        ridge.fit_standardized_nnls(np.ones((5, 10)), np.ones(5), tau=0.0)
    x = np.ones((5, 10))
    x[0, 0] = np.nan
    with pytest.raises(ValueError):
        ridge.fit_standardized_nnls(x, np.ones(5), tau=0.1)
