from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "critic_weights_v1.py"

spec = importlib.util.spec_from_file_location(
    "critic_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load critic_weights_v1.py for tests.")

critic = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = critic
spec.loader.exec_module(critic)


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

    for alternative_number in range(1, 7):
        row = {
            "context_id": "ctx_1001",
            "context_number": 1001,
            "replication_seed": replication_seed,
            "partition": "test",
            "alternative_id": f"A{alternative_number}",
        }
        for j in range(1, 11):
            row[f"g_C{j}"] = 0.99
        records.append(row)

    return pd.DataFrame.from_records(records)


def independent_critic(matrix: np.ndarray):
    x = np.asarray(matrix, dtype=float)
    minimum = np.min(x, axis=0)
    maximum = np.max(x, axis=0)
    ranges = maximum - minimum
    constant = ranges < 1e-12

    normalized = np.zeros_like(x)
    nonconstant = np.flatnonzero(~constant)
    normalized[:, nonconstant] = (
        x[:, nonconstant] - minimum[nonconstant]
    ) / (ranges[nonconstant] + 1e-12)

    sd = np.std(normalized, axis=0, ddof=0)
    sd[constant] = 0.0

    info = np.zeros(10)
    if len(nonconstant):
        corr = np.corrcoef(normalized[:, nonconstant], rowvar=False)
        corr = np.atleast_2d(corr)
        conflict = np.sum(1.0 - corr, axis=1)
        info[nonconstant] = sd[nonconstant] * conflict

    total = float(info.sum())
    if total <= 1e-12:
        weights = np.full(10, 0.1)
        fallback = True
    else:
        weights = info / total
        fallback = False
    return weights, info, sd, constant, fallback


def test_primary_weight_scope_uses_exact_n25_rows():
    rows = make_n25_rows()
    selected = critic.prepare_critic_rows(
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
    selected = critic.prepare_critic_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="fit_plus_weight",
    )
    assert len(selected) == 150
    assert set(selected["partition"]) == {"fit", "weight"}
    assert selected["context_number"].max() <= 25


def test_core_matches_independent_critic_calculation():
    rng = np.random.default_rng(12345)
    matrix = rng.uniform(0.05, 0.95, size=(73, 10))

    observed = critic.compute_critic_from_matrix(matrix)
    weights, info, sd, constant, fallback = independent_critic(matrix)

    np.testing.assert_allclose(observed.weights, weights, atol=1e-14, rtol=0.0)
    np.testing.assert_allclose(observed.information, info, atol=1e-14, rtol=0.0)
    np.testing.assert_allclose(
        observed.standard_deviation,
        sd,
        atol=1e-14,
        rtol=0.0,
    )
    np.testing.assert_array_equal(observed.constant_mask, constant)
    assert observed.fallback_used is fallback


def test_population_standard_deviation_ddof_zero_is_used():
    matrix = np.tile(np.linspace(0.1, 0.9, 8)[:, None], (1, 10))
    matrix[:, 1] = np.linspace(0.9, 0.2, 8)
    result = critic.compute_critic_from_matrix(matrix)

    ranges = np.ptp(matrix, axis=0)
    normalized_c1 = (matrix[:, 0] - matrix[:, 0].min()) / (
        ranges[0] + 1e-12
    )
    expected_ddof0 = float(np.std(normalized_c1, ddof=0))
    expected_ddof1 = float(np.std(normalized_c1, ddof=1))

    assert result.standard_deviation[0] == pytest.approx(expected_ddof0)
    assert abs(result.standard_deviation[0] - expected_ddof1) > 1e-4


def test_range_strictly_below_epsilon_is_constant_and_information_zero():
    matrix = np.full((20, 10), 0.4)
    matrix[:, 0] = np.linspace(0.4, 0.4 + 0.5e-12, 20)
    matrix[:, 1] = np.linspace(0.1, 0.9, 20)
    matrix[:, 2] = np.linspace(0.9, 0.1, 20)

    result = critic.compute_critic_from_matrix(matrix)

    assert bool(result.constant_mask[0]) is True
    assert result.standard_deviation[0] == 0.0
    assert result.information[0] == 0.0


def test_nonconstant_columns_use_range_plus_epsilon_normalization():
    matrix = np.full((4, 10), 0.2)
    matrix[:, 0] = np.array([0.1, 0.2, 0.5, 0.9])
    matrix[:, 1] = np.array([0.9, 0.7, 0.4, 0.1])

    observed = critic.compute_critic_from_matrix(matrix)

    normalized_c1 = (matrix[:, 0] - 0.1) / ((0.9 - 0.1) + 1e-12)
    expected_sd = np.std(normalized_c1, ddof=0)
    assert observed.standard_deviation[0] == pytest.approx(expected_sd)


def test_constant_columns_are_zero_information_and_excluded_from_conflict_sum():
    x = np.linspace(0.1, 0.9, 25)
    matrix = np.full((25, 10), 0.5)
    matrix[:, 0] = x
    matrix[:, 1] = 1.0 - x
    matrix[:, 2] = x ** 2

    result = critic.compute_critic_from_matrix(matrix)
    _, expected_info, _, expected_constant, _ = independent_critic(matrix)

    np.testing.assert_array_equal(
        result.constant_mask,
        expected_constant,
    )
    np.testing.assert_allclose(
        result.information,
        expected_info,
        atol=1e-14,
        rtol=0.0,
    )
    assert np.all(result.information[3:] == 0.0)


def test_all_constant_matrix_uses_equal_fallback():
    matrix = np.full((30, 10), 0.5)
    result = critic.compute_critic_from_matrix(matrix)

    np.testing.assert_array_equal(result.weights, np.full(10, 0.1))
    assert np.all(result.information == 0.0)
    assert np.all(result.constant_mask)
    assert result.fallback_used is True


def test_identical_nonconstant_columns_have_zero_conflict_and_equal_fallback():
    column = np.linspace(0.1, 0.9, 30)
    matrix = np.tile(column[:, None], (1, 10))
    result = critic.compute_critic_from_matrix(matrix)

    assert result.fallback_used is True
    np.testing.assert_allclose(result.weights, np.full(10, 0.1), atol=1e-15)
    np.testing.assert_allclose(result.information, np.zeros(10), atol=1e-15)


def test_non_degenerate_weights_are_nonnegative_and_sum_to_one():
    rows = make_n25_rows()
    result = critic.compute_critic_weights(
        rows,
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
    primary = critic.compute_critic_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )
    robustness = critic.compute_critic_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="fit_plus_weight",
    )

    assert primary.partition_scope == "weight"
    assert primary.diagnostics["rows_used"] == 30
    assert robustness.partition_scope == "fit_plus_weight"
    assert robustness.diagnostics["rows_used"] == 150


def test_external_test_content_cannot_change_critic_weights():
    rows = make_n25_rows()
    baseline = critic.compute_critic_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )

    modified = rows.copy()
    test_mask = modified["partition"].eq("test")
    modified.loc[test_mask, "g_C1"] = np.nan
    modified.loc[test_mask, "replication_seed"] = 99999
    modified = pd.concat(
        [modified, modified.loc[test_mask].iloc[[0]]],
        ignore_index=True,
    )

    challenged = critic.compute_critic_weights(
        modified,
        replication_seed=21001,
        n_contexts=25,
        partition_scope="weight",
    )

    assert challenged.weights_by_feature == pytest.approx(
        baseline.weights_by_feature
    )
    assert challenged.information_by_feature == pytest.approx(
        baseline.information_by_feature
    )
    assert challenged.diagnostics["external_test_rows_used"] == 0


def test_Y_or_oracle_utility_are_not_required_inputs():
    rows = make_n25_rows()
    assert "Y" not in rows.columns
    assert "U_star" not in rows.columns

    result = critic.compute_critic_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    assert result.diagnostics["target_Y_used"] is False
    assert result.diagnostics["oracle_utility_used"] is False


@pytest.mark.parametrize("bad_scope", ["fit", "test", "all", ""])
def test_invalid_partition_scope_fails_closed(bad_scope):
    rows = make_n25_rows()
    with pytest.raises(ValueError):
        critic.compute_critic_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
            partition_scope=bad_scope,
        )


def test_wrong_replication_seed_fails_closed():
    rows = make_n25_rows()
    with pytest.raises(ValueError):
        critic.compute_critic_weights(
            rows,
            replication_seed=21002,
            n_contexts=25,
        )


def test_nonfinite_nested_feature_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "g_C4"] = np.nan
    with pytest.raises(ValueError):
        critic.compute_critic_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_out_of_range_nested_feature_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "g_C4"] = 1.1
    with pytest.raises(ValueError):
        critic.compute_critic_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_duplicate_nested_context_alternative_fails_closed():
    rows = make_n25_rows()
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        critic.compute_critic_weights(
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
        critic.compute_critic_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
            partition_scope="weight",
        )


def test_matrix_shape_and_finiteness_fail_closed():
    with pytest.raises(ValueError):
        critic.compute_critic_from_matrix(np.ones((5, 9)))
    with pytest.raises(ValueError):
        critic.compute_critic_from_matrix(np.ones((0, 10)))

    matrix = np.ones((5, 10))
    matrix[0, 0] = np.nan
    with pytest.raises(ValueError):
        critic.compute_critic_from_matrix(matrix)
