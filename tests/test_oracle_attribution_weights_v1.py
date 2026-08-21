from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import itertools
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oracle_attribution_weights_v1.py"

spec = importlib.util.spec_from_file_location(
    "oracle_attribution_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load oracle_attribution_weights_v1.py for tests.")

oracle_attr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oracle_attr
spec.loader.exec_module(oracle_attr)


@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    beta: float


@dataclass(frozen=True)
class Spec:
    alphas: dict[str, float]
    interactions: tuple[Edge, ...]


def make_spec() -> Spec:
    alphas = {
        "C1": 0.11,
        "C2": 0.04,
        "C3": 0.05,
        "C4": 0.07,
        "C5": 0.10,
        "C6": 0.14,
        "C7": 0.12,
        "C8": 0.16,
        "C9": 0.08,
        "C10": 0.13,
    }
    interactions = (
        Edge("C1", "C2", 0.20),
        Edge("C3", "C7", 0.20),
        Edge("C4", "C5", 0.20),
        Edge("C6", "C10", 0.20),
        Edge("C8", "C9", 0.20),
    )
    return Spec(alphas=alphas, interactions=interactions)


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
                    0.07 * context_number
                    + 0.11 * alternative_number
                    + 0.03 * j
                    + 0.01 * context_number * ((j % 3) + 1)
                )
                row[f"q_C{j}"] = float((raw % 1.0) * 0.9 + 0.05)
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
            row[f"q_C{j}"] = 0.99
        records.append(row)

    return pd.DataFrame.from_records(records)


def utility_from_q(z: np.ndarray, oracle_spec: Spec, lam: float) -> np.ndarray:
    idx = {f"C{i}": i - 1 for i in range(1, 11)}
    alpha = np.array([oracle_spec.alphas[f"C{i}"] for i in range(1, 11)])
    main = z @ alpha
    inter = np.zeros(z.shape[0], dtype=float)
    for edge in oracle_spec.interactions:
        inter += edge.beta * z[:, idx[edge.left]] * z[:, idx[edge.right]]
    return (main + lam * inter) / (1.0 + lam)


def exhaustive_interventional_shapley(
    observed_z: np.ndarray,
    background_z: np.ndarray,
    oracle_spec: Spec,
    lam: float,
) -> np.ndarray:
    p = observed_z.size
    features = tuple(range(p))

    def value(subset: frozenset[int]) -> float:
        mixed = background_z.copy()
        if subset:
            cols = list(sorted(subset))
            mixed[:, cols] = observed_z[cols]
        return float(np.mean(utility_from_q(mixed, oracle_spec, lam)))

    cache = {
        frozenset(subset): value(frozenset(subset))
        for r in range(p + 1)
        for subset in itertools.combinations(features, r)
    }

    phi = np.zeros(p, dtype=float)
    denom = math.factorial(p)
    for j in features:
        others = [k for k in features if k != j]
        for r in range(p):
            coefficient = (
                math.factorial(r)
                * math.factorial(p - r - 1)
                / denom
            )
            for subset_tuple in itertools.combinations(others, r):
                subset = frozenset(subset_tuple)
                phi[j] += coefficient * (
                    cache[subset | {j}] - cache[subset]
                )
    return phi


def test_prepare_n25_rows_uses_exact_fit_and_weight_counts_and_excludes_test():
    rows = make_n25_rows()
    fit, weight = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    assert len(fit) == 120
    assert len(weight) == 30
    assert set(fit["partition"]) == {"fit"}
    assert set(weight["partition"]) == {"weight"}
    assert fit["context_number"].max() <= 25
    assert weight["context_number"].max() <= 25


def test_fit_joint_moment_is_same_row_product_not_product_of_marginals():
    rows = make_n25_rows()
    fit, _ = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    moments = oracle_attr.compute_fit_background_moments(
        fit,
        oracle_spec=make_spec(),
    )

    q1 = fit["q_C1"].to_numpy()
    q2 = fit["q_C2"].to_numpy()
    expected_joint = float(np.mean(q1 * q2))
    product_marginals = float(np.mean(q1) * np.mean(q2))

    assert moments.joint_by_pair["C1|C2"] == pytest.approx(expected_joint)
    assert abs(expected_joint - product_marginals) > 1e-6


@pytest.mark.parametrize("lam", [0.0, 0.5, 1.0])
def test_closed_form_matches_independent_exhaustive_interventional_enumeration(lam):
    rows = make_n25_rows()
    fit, weight = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    oracle_spec = make_spec()
    moments = oracle_attr.compute_fit_background_moments(
        fit,
        oracle_spec=oracle_spec,
    )

    sample = weight.iloc[[0, 7]].copy()
    closed = oracle_attr.closed_form_oracle_shapley(
        sample,
        oracle_spec=oracle_spec,
        lambda_value=lam,
        background_moments=moments,
    )

    background_z = fit.loc[:, oracle_attr.Q_COLUMNS].to_numpy(dtype=float)
    observed = sample.loc[:, oracle_attr.Q_COLUMNS].to_numpy(dtype=float)

    for row_index in range(len(sample)):
        enumerated = exhaustive_interventional_shapley(
            observed[row_index],
            background_z,
            oracle_spec,
            lam,
        )
        assert float(np.max(np.abs(closed[row_index] - enumerated))) < 1e-10


@pytest.mark.parametrize("lam", [0.0, 0.5, 1.0])
def test_closed_form_satisfies_shapley_efficiency(lam):
    rows = make_n25_rows()
    fit, weight = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    oracle_spec = make_spec()
    moments = oracle_attr.compute_fit_background_moments(
        fit,
        oracle_spec=oracle_spec,
    )

    sample = weight.iloc[[2, 11, 24]].copy()
    phi = oracle_attr.closed_form_oracle_shapley(
        sample,
        oracle_spec=oracle_spec,
        lambda_value=lam,
        background_moments=moments,
    )

    bg_z = fit.loc[:, oracle_attr.Q_COLUMNS].to_numpy(dtype=float)
    sample_z = sample.loc[:, oracle_attr.Q_COLUMNS].to_numpy(dtype=float)

    expected_background_utility = float(np.mean(utility_from_q(bg_z, oracle_spec, lam)))
    observed_utility = utility_from_q(sample_z, oracle_spec, lam)
    reconstructed = expected_background_utility + phi.sum(axis=1)

    np.testing.assert_allclose(
        reconstructed,
        observed_utility,
        atol=1e-12,
        rtol=0.0,
    )


def test_global_importance_is_mean_absolute_local_attribution_and_normalizes():
    rows = make_n25_rows()
    oracle_spec = make_spec()
    result = oracle_attr.compute_oracle_attribution_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )
    fit, weight = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )
    moments = oracle_attr.compute_fit_background_moments(
        fit,
        oracle_spec=oracle_spec,
    )
    phi = oracle_attr.closed_form_oracle_shapley(
        weight,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
        background_moments=moments,
    )
    expected_importance = np.mean(np.abs(phi), axis=0)

    assert result.weights_defined is True
    assert result.weights_by_feature is not None

    for j, feature in enumerate(oracle_attr.FEATURES):
        assert result.importance_by_feature[feature] == pytest.approx(
            expected_importance[j]
        )

    assert sum(result.weights_by_feature.values()) == pytest.approx(
        1.0,
        abs=1e-12,
    )
    assert result.diagnostics["equal_weight_fallback_used"] is False
    assert result.diagnostics["external_test_rows_used_for_background"] == 0
    assert result.diagnostics["external_test_rows_used_for_global_oracle_weights"] == 0


def test_zero_total_importance_is_undefined_without_equal_fallback():
    rows = make_n25_rows()
    for q_column in oracle_attr.Q_COLUMNS:
        rows.loc[rows["context_number"] <= 25, q_column] = 0.5

    result = oracle_attr.compute_oracle_attribution_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=make_spec(),
        lambda_value=0.5,
    )

    assert result.weights_defined is False
    assert result.weights_by_feature is None
    assert result.diagnostics["undefined_oracle_attribution_weight_vector"] is True
    assert result.diagnostics["equal_weight_fallback_used"] is False
    assert result.diagnostics["total_importance"] <= 1e-12


def test_external_test_content_cannot_change_oracle_weights():
    rows = make_n25_rows()
    oracle_spec = make_spec()

    baseline = oracle_attr.compute_oracle_attribution_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )

    modified = rows.copy()
    test_mask = modified["partition"].eq("test")
    modified.loc[test_mask, "q_C1"] = np.nan
    modified.loc[test_mask, "replication_seed"] = 99999
    modified = pd.concat(
        [modified, modified.loc[test_mask].iloc[[0]]],
        ignore_index=True,
    )

    challenged = oracle_attr.compute_oracle_attribution_weights(
        modified,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )

    assert challenged.importance_by_feature == pytest.approx(
        baseline.importance_by_feature
    )
    assert challenged.weights_by_feature == pytest.approx(
        baseline.weights_by_feature
    )
    assert challenged.diagnostics["external_test_rows_used_for_background"] == 0
    assert challenged.diagnostics["external_test_rows_used_for_global_oracle_weights"] == 0


def test_Y_and_U_star_are_not_required_inputs():
    rows = make_n25_rows()
    assert "Y" not in rows.columns
    assert "U_star" not in rows.columns

    result = oracle_attr.compute_oracle_attribution_weights(
        rows,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=make_spec(),
        lambda_value=0.5,
    )
    assert result.diagnostics["target_Y_used"] is False


def test_interaction_orientation_is_symmetric():
    rows = make_n25_rows()
    fit, weight = oracle_attr.prepare_oracle_attribution_rows(
        rows,
        replication_seed=21001,
        n_contexts=25,
    )

    spec_a = make_spec()
    spec_b = Spec(
        alphas=spec_a.alphas,
        interactions=tuple(
            Edge(edge.right, edge.left, edge.beta)
            for edge in spec_a.interactions
        ),
    )

    moments_a = oracle_attr.compute_fit_background_moments(fit, oracle_spec=spec_a)
    moments_b = oracle_attr.compute_fit_background_moments(fit, oracle_spec=spec_b)

    phi_a = oracle_attr.closed_form_oracle_shapley(
        weight.iloc[:5],
        oracle_spec=spec_a,
        lambda_value=1.0,
        background_moments=moments_a,
    )
    phi_b = oracle_attr.closed_form_oracle_shapley(
        weight.iloc[:5],
        oracle_spec=spec_b,
        lambda_value=1.0,
        background_moments=moments_b,
    )

    np.testing.assert_allclose(phi_a, phi_b, atol=1e-15, rtol=0.0)


@pytest.mark.parametrize("bad_lambda", [-1.0, 0.25, 0.75, np.nan, np.inf])
def test_nonfrozen_or_nonfinite_lambda_fails_closed(bad_lambda):
    rows = make_n25_rows()
    with pytest.raises(ValueError):
        oracle_attr.compute_oracle_attribution_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
            oracle_spec=make_spec(),
            lambda_value=bad_lambda,
        )


def test_duplicate_context_alternative_rows_fail_closed():
    rows = make_n25_rows()
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        oracle_attr.prepare_oracle_attribution_rows(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_nonfinite_q_fails_closed():
    rows = make_n25_rows()
    rows.loc[0, "q_C4"] = np.nan
    with pytest.raises(ValueError):
        oracle_attr.prepare_oracle_attribution_rows(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_wrong_row_counts_fail_closed():
    rows = make_n25_rows()
    rows = rows.drop(rows.index[0]).reset_index(drop=True)
    with pytest.raises(ValueError):
        oracle_attr.prepare_oracle_attribution_rows(
            rows,
            replication_seed=21001,
            n_contexts=25,
        )


def test_wrong_replication_seed_fails_closed():
    rows = make_n25_rows()
    with pytest.raises(ValueError):
        oracle_attr.prepare_oracle_attribution_rows(
            rows,
            replication_seed=21002,
            n_contexts=25,
        )


def test_bad_oracle_spec_fails_closed():
    rows = make_n25_rows()
    bad_alphas = make_spec().alphas.copy()
    bad_alphas["C1"] += 0.1
    bad_spec = Spec(alphas=bad_alphas, interactions=make_spec().interactions)

    with pytest.raises(ValueError):
        oracle_attr.compute_oracle_attribution_weights(
            rows,
            replication_seed=21001,
            n_contexts=25,
            oracle_spec=bad_spec,
            lambda_value=0.5,
        )
