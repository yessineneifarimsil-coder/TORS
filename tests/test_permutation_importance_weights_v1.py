from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "permutation_importance_weights_v1.py"
spec = importlib.util.spec_from_file_location(
    "permutation_importance_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load permutation_importance_weights_v1.py for tests.")
pi = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pi
spec.loader.exec_module(pi)


class LinearPredictor:
    def __init__(self, coefficients=None, intercept=0.17):
        if coefficients is None:
            coefficients = [0.65, 0.0, 0.31, 0.0, 0.18, 0.0, 0.11, 0.0, 0.07, 0.0]
        self.coefficients = np.asarray(coefficients, dtype=float)
        self.intercept = float(intercept)

    def predict(self, x):
        return self.intercept + np.asarray(x, dtype=float) @ self.coefficients


class ConstantPredictor:
    def __init__(self, value=0.0):
        self.value = float(value)

    def predict(self, x):
        return np.full(len(x), self.value)


def make_n25_rows(replication_seed=21001):
    records = []
    coefficients = LinearPredictor().coefficients
    for context_number in range(1, 26):
        partition = "weight" if context_number % 5 == 0 else "fit"
        for alternative_number in range(1, 7):
            record = {
                "context_id": f"ctx_{context_number:04d}",
                "context_number": context_number,
                "replication_seed": replication_seed,
                "partition": partition,
                "alternative_id": f"A{alternative_number}",
                "rho": 0.4,
                "c": 0.5,
                "lambda": 0.5,
            }
            feature_values = []
            for criterion in range(1, 11):
                raw = (
                    0.043 * context_number
                    + 0.071 * alternative_number
                    + 0.013 * criterion
                    + 0.0021 * context_number * criterion
                    + 0.0031 * alternative_number * criterion
                )
                value = float((raw % 1.0) * 0.8 + 0.1)
                record[f"g_C{criterion}"] = value
                feature_values.append(value)
            record["Y"] = float(
                0.17
                + np.asarray(feature_values) @ coefficients
                + 0.018 * np.sin(context_number + 2 * alternative_number)
            )
            records.append(record)

    # FIT is outside PI evaluation; its scientific contents must not be read.
    for record in records:
        if record["partition"] == "fit":
            record["replication_seed"] = np.nan
            record["Y"] = np.nan
            for feature in pi.FEATURES:
                record[feature] = np.nan

    for alternative_number in range(1, 7):
        record = {
            "context_id": "ctx_1001",
            "context_number": 1001,
            "replication_seed": 99999,
            "partition": "test",
            "alternative_id": f"A{alternative_number}",
            "Y": np.inf,
        }
        for feature in pi.FEATURES:
            record[feature] = np.inf
        records.append(record)
    return pd.DataFrame.from_records(records)


def independent_derangements(replication_seed, n_contexts, context_count):
    rng = np.random.default_rng(
        np.random.SeedSequence([replication_seed, 84001, n_contexts])
    )
    accepted = []
    seen = set()
    draws = 0
    positions = np.arange(context_count)
    while len(accepted) < 20 and draws < 100000:
        draws += 1
        candidate = rng.permutation(context_count)
        key = tuple(int(value) for value in candidate)
        if np.any(candidate == positions) or key in seen:
            continue
        seen.add(key)
        accepted.append(key)
    return tuple(accepted), draws


def independent_compute(rows, model, replication_seed=21001, n_contexts=25):
    selected = rows.loc[
        rows["context_number"].le(n_contexts) & rows["partition"].eq("weight")
    ].sort_values(["context_number", "alternative_id"], kind="stable")
    x = selected.loc[:, pi.FEATURES].to_numpy(float)
    y = selected["Y"].to_numpy(float)
    m = selected["context_number"].nunique()
    permutations, draws = independent_derangements(replication_seed, n_contexts, m)
    baseline = float(np.mean((y - model.predict(x)) ** 2))
    repeat = np.empty((10, 20))
    for j in range(10):
        blocks = x[:, j].reshape(m, 6)
        for b, permutation in enumerate(permutations):
            challenged = x.copy()
            challenged[:, j] = blocks[np.asarray(permutation)].reshape(-1)
            repeat[j, b] = np.mean((y - model.predict(challenged)) ** 2) - baseline
    means = repeat.mean(axis=1)
    sd = repeat.std(axis=1, ddof=1)
    nonnegative = np.maximum(means, 0.0)
    if np.any(means > 0.0):
        weights = nonnegative / nonnegative.sum()
        fallback = False
    else:
        weights = np.full(10, 0.1)
        fallback = True
    return baseline, repeat, means, sd, weights, fallback, permutations, draws


def test_frozen_constants():
    assert pi.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert pi.MASTER_SEED == 84001
    assert pi.REPEATS == 20
    assert pi.MAX_CANDIDATE_DRAWS == 100000
    assert pi.SD_DDOF == 1
    assert pi.ALTERNATIVES_PER_CONTEXT == 6
    assert pi.EXPECTED_WEIGHT_CONTEXTS == {25: 5, 50: 10, 100: 20, 250: 50, 1000: 200}


def test_prepare_exact_weight_scope_and_order():
    rows = make_n25_rows().sample(frac=1.0, random_state=8).reset_index(drop=True)
    selected = pi.prepare_pi_weight_rows(rows, replication_seed=21001, n_contexts=25)
    assert len(selected) == 30
    assert selected["context_id"].nunique() == 5
    assert selected["partition"].eq("weight").all()
    assert selected["context_number"].tolist() == sorted(selected["context_number"].tolist())
    for _, block in selected.groupby("context_number", sort=False):
        assert block["alternative_id"].tolist() == ["A1", "A2", "A3", "A4", "A5", "A6"]


def test_fit_and_external_test_scientific_values_are_not_used():
    selected = pi.prepare_pi_weight_rows(make_n25_rows(), replication_seed=21001, n_contexts=25)
    assert np.isfinite(selected.loc[:, pi.FEATURES].to_numpy()).all()
    assert np.isfinite(selected["Y"].to_numpy()).all()


def test_derangements_match_independent_seedsequence_reconstruction():
    plan = pi.generate_context_derangements(replication_seed=21001, n_contexts=25, context_count=5)
    expected, draws = independent_derangements(21001, 25, 5)
    assert plan.permutations == expected
    assert plan.candidate_draws == draws
    assert len(plan.permutations) == 20
    assert len(set(plan.permutations)) == 20
    assert all(all(source != destination for destination, source in enumerate(p)) for p in plan.permutations)


def test_derangement_identity_hash_is_canonical():
    plan = pi.generate_context_derangements(replication_seed=21001, n_contexts=25, context_count=5)
    payload = "\n".join(",".join(str(v) for v in item) for item in plan.permutations)
    assert plan.identity_sha256 == hashlib.sha256(payload.encode("ascii")).hexdigest()


def test_derangements_are_deterministic_and_separate_by_n():
    first = pi.generate_context_derangements(replication_seed=21002, n_contexts=25, context_count=5)
    second = pi.generate_context_derangements(replication_seed=21002, n_contexts=25, context_count=5)
    larger = pi.generate_context_derangements(replication_seed=21002, n_contexts=50, context_count=10)
    assert first == second
    assert first.identity_sha256 != larger.identity_sha256


def test_block_mapping_direction_and_only_one_feature_changes():
    x = np.arange(30 * 10, dtype=float).reshape(30, 10)
    permutation = (1, 2, 3, 4, 0)
    changed = pi.permute_context_feature_blocks(
        x, feature_index=3, permutation=permutation, context_count=5
    )
    np.testing.assert_array_equal(changed[:, :3], x[:, :3])
    np.testing.assert_array_equal(changed[:, 4:], x[:, 4:])
    source_blocks = x[:, 3].reshape(5, 6)
    np.testing.assert_array_equal(changed[:, 3].reshape(5, 6), source_blocks[list(permutation)])


def test_full_pi_matches_independent_reconstruction():
    rows = make_n25_rows()
    model = LinearPredictor()
    observed = pi.compute_permutation_importance_weights(
        rows, fitted_model=model, replication_seed=21001, n_contexts=25
    )
    expected = independent_compute(rows, model)
    assert observed.baseline_mse == pytest.approx(expected[0], abs=1e-16)
    observed_repeat = np.asarray(list(observed.repeat_importance_by_feature.values()))
    observed_means = np.asarray(list(observed.mean_importance_by_feature.values()))
    observed_sd = np.asarray(list(observed.sd_importance_by_feature.values()))
    observed_weights = np.asarray(list(observed.weights_by_feature.values()))
    np.testing.assert_allclose(observed_repeat, expected[1], atol=2e-15, rtol=0.0)
    np.testing.assert_allclose(observed_means, expected[2], atol=2e-15, rtol=0.0)
    np.testing.assert_allclose(observed_sd, expected[3], atol=2e-15, rtol=0.0)
    np.testing.assert_allclose(observed_weights, expected[4], atol=2e-15, rtol=0.0)
    assert observed.fallback_used is expected[5]
    assert observed.derangement_plan.permutations == expected[6]
    assert observed.derangement_plan.candidate_draws == expected[7]


def test_same_plan_reused_for_all_criteria():
    result = pi.compute_permutation_importance_weights(
        make_n25_rows(), fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    lengths = {len(values) for values in result.repeat_importance_by_feature.values()}
    assert lengths == {20}
    assert result.diagnostics["same_20_derangements_reused_across_all_criteria"] is True


def test_rho_c_lambda_do_not_change_derangements_or_pi_values():
    rows = make_n25_rows()
    changed = rows.copy()
    changed["rho"] = 0.9
    changed["c"] = 2.0
    changed["lambda"] = 1.0
    first = pi.compute_permutation_importance_weights(
        rows, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    second = pi.compute_permutation_importance_weights(
        changed, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    assert first.derangement_plan == second.derangement_plan
    assert first.weights_by_feature == second.weights_by_feature


def test_row_order_does_not_change_result():
    rows = make_n25_rows()
    shuffled = rows.sample(frac=1.0, random_state=19).reset_index(drop=True)
    first = pi.compute_permutation_importance_weights(
        rows, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    second = pi.compute_permutation_importance_weights(
        shuffled, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    assert first.repeat_importance_by_feature == second.repeat_importance_by_feature
    assert first.weights_by_feature == second.weights_by_feature


def test_negative_means_are_truncated_before_normalization():
    means = np.asarray([2.0, -5.0, 1.0, 0.0, -0.1, 0.0, 0.0, 0.0, 0.0, 0.0])
    nonnegative, weights, fallback = pi.normalize_pi_importances(means)
    np.testing.assert_array_equal(nonnegative, [2.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(weights, [2/3, 0, 1/3, 0, 0, 0, 0, 0, 0, 0])
    assert fallback is False


@pytest.mark.parametrize("means", [np.zeros(10), -np.arange(1.0, 11.0)])
def test_all_nonpositive_equal_fallback(means):
    nonnegative, weights, fallback = pi.normalize_pi_importances(means)
    np.testing.assert_array_equal(nonnegative, np.zeros(10))
    np.testing.assert_array_equal(weights, np.full(10, 0.1))
    assert fallback is True


def test_constant_predictor_produces_recorded_equal_fallback():
    result = pi.compute_permutation_importance_weights(
        make_n25_rows(), fitted_model=ConstantPredictor(), replication_seed=21001, n_contexts=25
    )
    np.testing.assert_array_equal(list(result.weights_by_feature.values()), np.full(10, 0.1))
    assert result.fallback_used is True
    assert result.diagnostics["fallback_used"] is True


def test_diagnostics_close_scientific_firewalls():
    result = pi.compute_permutation_importance_weights(
        make_n25_rows(), fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    d = result.diagnostics
    assert d["evaluation_partition"] == "weight"
    assert d["weight_rows_used"] == 30
    assert d["weight_contexts_used"] == 5
    assert d["target_Y_used"] is True
    assert d["model_fit_executed_by_pi"] is False
    assert d["fit_rows_used_for_pi_evaluation"] == 0
    assert d["external_test_rows_used"] == 0
    assert d["oracle_utility_used"] is False
    assert d["shap_used"] is False
    assert d["mcdm_executed"] is False
    assert d["winner_inspected"] is False
    assert d["sd_ddof"] == 1


def test_external_test_duplication_is_irrelevant():
    rows = make_n25_rows()
    changed = pd.concat([rows, rows.loc[rows["partition"].eq("test")].iloc[[0]]], ignore_index=True)
    first = pi.compute_permutation_importance_weights(
        rows, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    second = pi.compute_permutation_importance_weights(
        changed, fitted_model=LinearPredictor(), replication_seed=21001, n_contexts=25
    )
    assert first.weights_by_feature == second.weights_by_feature


@pytest.mark.parametrize("n_contexts", [24, 26, 2000])
def test_rejects_nonfrozen_n(n_contexts):
    with pytest.raises(ValueError, match="not a frozen"):
        pi.prepare_pi_weight_rows(make_n25_rows(), replication_seed=21001, n_contexts=n_contexts)


def test_rejects_missing_column():
    with pytest.raises(ValueError, match="missing columns"):
        pi.prepare_pi_weight_rows(
            make_n25_rows().drop(columns="Y"), replication_seed=21001, n_contexts=25
        )


def test_rejects_duplicate_weight_identity():
    rows = make_n25_rows()
    duplicate = rows.loc[rows["partition"].eq("weight")].iloc[[0]]
    with pytest.raises(ValueError, match="Duplicate"):
        pi.prepare_pi_weight_rows(
            pd.concat([rows, duplicate], ignore_index=True), replication_seed=21001, n_contexts=25
        )


@pytest.mark.parametrize("column,value,message", [("Y", np.nan, "target Y"), ("g_C1", np.inf, "feature values"), ("g_C2", 1.5, "lie in")])
def test_rejects_invalid_weight_scientific_values(column, value, message):
    rows = make_n25_rows()
    index = rows.index[rows["partition"].eq("weight")][0]
    rows.loc[index, column] = value
    with pytest.raises(ValueError, match=message):
        pi.prepare_pi_weight_rows(rows, replication_seed=21001, n_contexts=25)


def test_rejects_unexpected_nested_partition():
    rows = make_n25_rows()
    rows.loc[0, "partition"] = "test"
    with pytest.raises(ValueError, match="Unexpected partition"):
        pi.prepare_pi_weight_rows(rows, replication_seed=21001, n_contexts=25)


def test_rejects_wrong_seed_in_weight():
    rows = make_n25_rows()
    index = rows.index[rows["partition"].eq("weight")][0]
    rows.loc[index, "replication_seed"] = 21002
    with pytest.raises(ValueError, match="exactly replication_seed"):
        pi.prepare_pi_weight_rows(rows, replication_seed=21001, n_contexts=25)


def test_rejects_model_without_predict():
    with pytest.raises(TypeError, match="callable predict"):
        pi.compute_permutation_importance_weights(
            make_n25_rows(), fitted_model=object(), replication_seed=21001, n_contexts=25
        )


@pytest.mark.parametrize("prediction", [np.zeros(29), np.full(30, np.nan)])
def test_rejects_invalid_model_predictions(prediction):
    class BadPredictor:
        def predict(self, x):
            return prediction

    with pytest.raises(pi.PermutationImportanceNumericalError):
        pi.compute_permutation_importance_weights(
            make_n25_rows(), fitted_model=BadPredictor(), replication_seed=21001, n_contexts=25
        )


def test_rejects_invalid_block_permutation():
    x = np.zeros((30, 10))
    with pytest.raises(ValueError, match="derangement"):
        pi.permute_context_feature_blocks(
            x, feature_index=0, permutation=(0, 2, 3, 4, 1), context_count=5
        )


def test_rejects_context_count_not_frozen_for_n():
    with pytest.raises(ValueError, match="requires 5"):
        pi.generate_context_derangements(replication_seed=21001, n_contexts=25, context_count=6)
