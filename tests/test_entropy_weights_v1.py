from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "entropy_weights_v1.py"

spec = importlib.util.spec_from_file_location(
    "entropy_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load entropy_weights_v1.py for tests.")

entropy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = entropy
spec.loader.exec_module(entropy)


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
            for j in range(1, 11):
                raw = (
                    0.037 * context_number
                    + 0.083 * alternative_number
                    + 0.021 * j
                    + 0.003 * context_number * j
                )
                row[f"g_C{j}"] = float((raw % 1.0) * 0.9 + 0.05)
            records.append(row)

    # Deliberately invalid TEST content must remain outside the Entropy scope.
    for alternative_number in range(1, 7):
        row = {
            "context_id": "ctx_1001",
            "context_number": 1001,
            "replication_seed": 99999,
            "partition": "test",
            "alternative_id": f"A{alternative_number}",
        }
        for j in range(1, 11):
            row[f"g_C{j}"] = np.nan
        records.append(row)

    return pd.DataFrame.from_records(records)


def independent_entropy(matrix: np.ndarray):
    x = np.asarray(matrix, dtype=float)
    n = x.shape[0]
    minimum = np.min(x, axis=0)
    maximum = np.max(x, axis=0)
    ranges = maximum - minimum
    constant = ranges < 1e-12

    normalized = np.zeros_like(x)
    nonconstant = np.flatnonzero(~constant)
    normalized[:, nonconstant] = (
        x[:, nonconstant] - minimum[nonconstant]
    ) / (ranges[nonconstant] + 1e-12)

    column_sum = np.sum(normalized, axis=0)
    zero_information = constant | (column_sum <= 1e-12)
    entropy_values = np.ones(10)

    for j in np.flatnonzero(~zero_information):
        p = normalized[:, j] / column_sum[j]
        positive = p > 0.0
        entropy_values[j] = -np.sum(p[positive] * np.log(p[positive])) / np.log(n)

    diversification = 1.0 - entropy_values
    diversification[zero_information] = 0.0
    total = float(diversification.sum())
    if total <= 1e-12:
        weights = np.full(10, 0.1)
        fallback = True
    else:
        weights = diversification / total
        fallback = False

    return (
        weights,
        entropy_values,
        diversification,
        column_sum,
        constant,
        zero_information,
        fallback,
    )


def test_frozen_constants_and_feature_order():
    assert entropy.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert entropy.N_CRITERIA == 10
    assert entropy.EPSILON == 1e-12
    assert entropy.EQUAL_WEIGHT == 0.1


def test_primary_weight_scope_uses_exact_n25_rows():
    rows = make_n25_rows()
    selected = entropy.prepare_entropy_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )
    assert len(selected) == 30
    assert set(selected["partition"]) == {"weight"}
    assert selected["context_number"].max() <= 25


def test_secondary_fit_plus_weight_scope_uses_exact_n25_rows():
    rows = make_n25_rows()
    selected = entropy.prepare_entropy_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="fit_plus_weight",
    )
    assert len(selected) == 150
    assert set(selected["partition"]) == {"fit", "weight"}
    assert selected["context_number"].max() <= 25


def test_core_matches_independent_minmax_then_shannon_calculation():
    rng = np.random.default_rng(12345)
    matrix = rng.uniform(0.05, 0.95, size=(73, 10))
    observed = entropy.compute_entropy_from_matrix(matrix)
    expected = independent_entropy(matrix)

    np.testing.assert_allclose(observed.weights, expected[0], atol=1e-14, rtol=0.0)
    np.testing.assert_allclose(observed.entropy, expected[1], atol=1e-14, rtol=0.0)
    np.testing.assert_allclose(
        observed.diversification,
        expected[2],
        atol=1e-14,
        rtol=0.0,
    )
    np.testing.assert_allclose(
        observed.normalized_column_sum,
        expected[3],
        atol=1e-14,
        rtol=0.0,
    )
    np.testing.assert_array_equal(observed.constant_mask, expected[4])
    np.testing.assert_array_equal(observed.zero_information_mask, expected[5])
    assert observed.fallback_used is expected[6]


def test_entropy_uses_all_selected_rows_in_log_n_and_zero_log_zero():
    matrix = np.full((5, 10), 0.4)
    matrix[:, 0] = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    result = entropy.compute_entropy_from_matrix(matrix)

    normalized = matrix[:, 0] / (1.0 + 1e-12)
    p = normalized / normalized.sum()
    positive = p > 0.0
    expected = -np.sum(p[positive] * np.log(p[positive])) / np.log(5)

    assert np.isfinite(result.entropy[0])
    assert result.entropy[0] == pytest.approx(expected, abs=1e-15)


def test_correct_entropy_mechanism_rewards_concentration_not_uniformity():
    matrix = np.full((50, 10), 0.4)
    matrix[:, 0] = np.r_[np.zeros(49), 1.0]
    matrix[:, 1] = np.r_[0.0, np.ones(49)]

    result = entropy.compute_entropy_from_matrix(matrix)

    assert result.entropy[0] == pytest.approx(0.0, abs=1e-15)
    assert result.entropy[1] == pytest.approx(np.log(49) / np.log(50))
    assert result.diversification[0] > result.diversification[1]
    assert result.weights[0] > result.weights[1]


def test_strict_constant_boundary_uses_range_less_than_epsilon():
    matrix = np.full((20, 10), 0.4)
    below = np.nextafter(1e-12, 0.0)
    matrix[:, 0] = np.linspace(0.0, below, 20)
    matrix[:, 1] = np.linspace(0.0, 1e-12, 20)

    result = entropy.compute_entropy_from_matrix(matrix)

    assert bool(result.constant_mask[0]) is True
    assert bool(result.constant_mask[1]) is False
    assert result.diversification[0] == 0.0


def test_all_constant_matrix_uses_equal_fallback():
    matrix = np.full((30, 10), 0.5)
    result = entropy.compute_entropy_from_matrix(matrix)

    np.testing.assert_array_equal(result.weights, np.full(10, 0.1))
    assert np.all(result.entropy == 1.0)
    assert np.all(result.diversification == 0.0)
    assert np.all(result.constant_mask)
    assert np.all(result.zero_information_mask)
    assert result.fallback_used is True


def test_single_informative_criterion_receives_all_weight():
    matrix = np.full((30, 10), 0.5)
    matrix[:, 3] = np.r_[np.zeros(29), 1.0]
    result = entropy.compute_entropy_from_matrix(matrix)

    assert result.fallback_used is False
    np.testing.assert_allclose(result.weights[3], 1.0, atol=1e-15)
    np.testing.assert_allclose(np.delete(result.weights, 3), 0.0, atol=1e-15)


def test_non_degenerate_weights_are_nonnegative_and_sum_to_one():
    result = entropy.compute_entropy_weights(
        make_n25_rows(),
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )
    weights = np.array(list(result.weights_by_feature.values()))
    assert np.all(weights >= 0.0)
    assert float(weights.sum()) == pytest.approx(1.0, abs=1e-12)
    assert result.diagnostics["fallback_used"] is False


def test_primary_and_robustness_scopes_are_recorded_distinctly():
    rows = make_n25_rows()
    primary = entropy.compute_entropy_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )
    robustness = entropy.compute_entropy_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="fit_plus_weight",
    )

    assert primary.partition_scope == "weight"
    assert primary.diagnostics["rows_used"] == 30
    assert robustness.partition_scope == "fit_plus_weight"
    assert robustness.diagnostics["rows_used"] == 150


def test_input_row_order_cannot_change_entropy_result():
    rows = make_n25_rows()
    baseline = entropy.compute_entropy_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    shuffled = rows.sample(frac=1.0, random_state=7).reset_index(drop=True)
    challenged = entropy.compute_entropy_weights(
        shuffled,
        replication_seed=21001,
        n_contexts=25,
    )
    assert challenged.weights_by_feature == pytest.approx(
        baseline.weights_by_feature,
        abs=0.0,
    )


def test_external_test_content_cannot_change_entropy_weights():
    rows = make_n25_rows()
    baseline = entropy.compute_entropy_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    modified = pd.concat(
        [rows, rows.loc[rows["partition"].eq("test")].iloc[[0]]],
        ignore_index=True,
    )
    challenged = entropy.compute_entropy_weights(
        modified,
        replication_seed=21001,
        n_contexts=25,
    )

    assert challenged.weights_by_feature == pytest.approx(
        baseline.weights_by_feature
    )
    assert challenged.diagnostics["external_test_rows_used"] == 0


def test_Y_or_oracle_utility_are_not_required_inputs():
    rows = make_n25_rows()
    assert "Y" not in rows.columns
    assert "U_star" not in rows.columns
    result = entropy.compute_entropy_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    assert result.diagnostics["target_Y_used"] is False
    assert result.diagnostics["oracle_utility_used"] is False
    assert result.diagnostics["shap_used"] is False
    assert result.diagnostics["mcdm_executed"] is False
    assert result.diagnostics["winner_inspected"] is False


def test_diagnostics_record_frozen_entropy_semantics():
    result = entropy.compute_entropy_weights(
        make_n25_rows(),
        replication_seed=21001,
        n_contexts=25,
    )
    diagnostics = result.diagnostics
    assert diagnostics["method"] == "Entropy"
    assert diagnostics["variant"] == "minmax_then_Shannon"
    assert diagnostics["preprocessing"] == "criterionwise_minmax"
    assert diagnostics["zero_log_zero"] is True
    assert diagnostics["n_definition"] == (
        "number_of_alternative_context_rows_in_selected_partition"
    )
    assert diagnostics["all_zero_diversification_fallback"] == "equal_weights"


@pytest.mark.parametrize("bad_scope", ["fit", "test", "all", ""])
def test_invalid_partition_scope_fails_closed(bad_scope):
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            make_n25_rows(),
            replication_seed=21001,
            n_contexts=25,
            partition_scope=bad_scope,
        )


def test_wrong_replication_seed_fails_closed():
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            make_n25_rows(),
            replication_seed=21002,
            n_contexts=25,
        )


def test_nonfinite_nested_feature_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "g_C4"] = np.nan
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_out_of_range_nested_feature_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "g_C4"] = 1.1
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_duplicate_nested_context_alternative_fails_closed():
    rows = make_n25_rows()
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_wrong_primary_row_count_fails_closed():
    rows = make_n25_rows()
    drop_index = rows.index[
        (rows["context_number"] == 5) & (rows["alternative_id"] == "A1")
    ][0]
    rows = rows.drop(drop_index).reset_index(drop=True)
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
            partition_scope="weight",
        )


def test_missing_required_column_fails_closed():
    rows = make_n25_rows().drop(columns=["g_C7"])
    with pytest.raises(ValueError):
        entropy.compute_entropy_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_matrix_shape_size_and_finiteness_fail_closed():
    with pytest.raises(ValueError):
        entropy.compute_entropy_from_matrix(np.ones((5, 9)))
    with pytest.raises(ValueError):
        entropy.compute_entropy_from_matrix(np.ones((0, 10)))
    with pytest.raises(ValueError):
        entropy.compute_entropy_from_matrix(np.ones((1, 10)))

    matrix = np.ones((5, 10))
    matrix[0, 0] = np.nan
    with pytest.raises(ValueError):
        entropy.compute_entropy_from_matrix(matrix)
