from __future__ import annotations

import hashlib
import importlib.util
import inspect
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "random_weights_majority_winner_v1.py"
spec = importlib.util.spec_from_file_location(
    "random_weights_majority_winner_v1_test_module", MODULE_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load random_weights_majority_winner_v1.py.")
refs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = refs
spec.loader.exec_module(refs)


def make_rows(replication_seed=12345):
    records = []
    desired_weight_winners = {5: "A2", 10: "A2", 15: "A1", 20: "A1", 25: "A3"}
    for context_number in range(1, 26):
        partition = "weight" if context_number % 5 == 0 else "fit"
        desired = desired_weight_winners.get(context_number, "A6")
        for alternative_number, alternative_id in enumerate(refs.ALTERNATIVE_IDS, start=1):
            utility = 0.1 + 0.05 * alternative_number
            if alternative_id == desired:
                utility = 0.9
            record = {
                "context_id": f"ctx_{context_number:04d}",
                "context_number": context_number,
                "replication_seed": replication_seed,
                "partition": partition,
                "alternative_id": alternative_id,
                "U_star": utility,
                "Y": -999.0,
            }
            records.append(record)
    # Oracle tie in context 5: A2 wins over A3 by ascending ID.
    for record in records:
        if record["context_number"] == 5 and record["alternative_id"] == "A3":
            record["U_star"] = 0.9
    # FIT oracle values/seeds are outside MajorityWinner estimation.
    for record in records:
        if record["partition"] == "fit":
            record["U_star"] = np.nan
            record["replication_seed"] = np.nan
    for context_number in range(1001, 1201):
        for alternative_id in refs.ALTERNATIVE_IDS:
            records.append(
                {
                    "context_id": f"ctx_{context_number:04d}",
                    "context_number": context_number,
                    "replication_seed": replication_seed,
                    "partition": "test",
                    "alternative_id": alternative_id,
                    "U_star": np.nan,
                    "Y": np.nan,
                }
            )
    return pd.DataFrame.from_records(records)


def test_frozen_constants():
    assert refs.ALTERNATIVE_IDS == ("A1", "A2", "A3", "A4", "A5", "A6")
    assert refs.N_CRITERIA == 10
    assert refs.RANDOM_WEIGHT_MASTER_SEED == 81001
    assert refs.RANDOM_WEIGHT_DRAWS == 200
    assert refs.EPSILON == 1e-12
    assert refs.EXPECTED_TEST_CONTEXTS == 200


def test_random_weights_match_independent_seedsequence_draw():
    observed = refs.generate_random_weight_reference(replication_seed=12345)
    expected = np.random.default_rng(
        np.random.SeedSequence([12345, 81001])
    ).dirichlet(np.ones(10), size=200)
    np.testing.assert_array_equal(observed.weights, expected)


def test_random_weights_shape_positive_and_normalized():
    result = refs.generate_random_weight_reference(replication_seed=12345)
    assert result.weights.shape == (200, 10)
    assert np.all(result.weights > 0.0)
    np.testing.assert_allclose(result.weights.sum(axis=1), np.ones(200), atol=1e-12, rtol=0.0)
    assert result.weights.flags.writeable is False


def test_random_weights_hash_uses_little_endian_float64_c_order():
    result = refs.generate_random_weight_reference(replication_seed=12345)
    expected = hashlib.sha256(
        np.asarray(result.weights, dtype="<f8", order="C").tobytes(order="C")
    ).hexdigest()
    assert result.weights_sha256 == expected


def test_random_weights_deterministic_and_seed_specific():
    first = refs.generate_random_weight_reference(replication_seed=12345)
    second = refs.generate_random_weight_reference(replication_seed=12345)
    other = refs.generate_random_weight_reference(replication_seed=12346)
    np.testing.assert_array_equal(first.weights, second.weights)
    assert first.weights_sha256 == second.weights_sha256
    assert first.weights_sha256 != other.weights_sha256


def test_random_weight_api_enforces_reuse_by_accepting_no_condition_arguments():
    parameters = tuple(inspect.signature(refs.generate_random_weight_reference).parameters)
    assert parameters == ("replication_seed",)
    result = refs.generate_random_weight_reference(replication_seed=12345)
    assert result.diagnostics["reuse_same_200_vectors_across_N_rho_c_lambda_for_seed"] is True
    assert result.diagnostics["accepts_condition_arguments"] is False


def test_random_weight_diagnostics_close_execution_firewalls():
    d = refs.generate_random_weight_reference(replication_seed=12345).diagnostics
    assert d["moora_executed"] is False
    assert d["decision_metrics_computed"] is False
    assert d["external_test_rows_used"] == 0
    assert d["oracle_utility_used"] is False
    assert d["target_Y_used"] is False
    assert d["model_fit_executed"] is False
    assert d["shap_used"] is False
    assert d["winner_inspected"] is False


def test_random_weights_reject_negative_seed():
    with pytest.raises(ValueError, match="nonnegative"):
        refs.generate_random_weight_reference(replication_seed=-1)


def test_prepare_majority_uses_exact_weight_scope():
    selected = refs.prepare_majority_weight_rows(
        make_rows().sample(frac=1.0, random_state=4),
        replication_seed=12345,
        n_contexts=25,
    )
    assert len(selected) == 30
    assert selected["context_number"].nunique() == 5
    assert selected["partition"].eq("weight").all()
    assert np.isfinite(selected["U_star"]).all()


def test_majority_oracle_ties_and_modal_count_ties_use_ascending_id():
    result = refs.estimate_majority_winner(
        make_rows(), replication_seed=12345, n_contexts=25
    )
    assert result.winner_by_weight_context_number == {
        5: "A2", 10: "A2", 15: "A1", 20: "A1", 25: "A3"
    }
    assert result.winner_counts_by_alternative == {
        "A1": 2, "A2": 2, "A3": 1, "A4": 0, "A5": 0, "A6": 0
    }
    assert result.modal_winner_id == "A1"
    assert result.modal_winner_count == 2
    assert result.modal_winner_share == pytest.approx(0.4)
    assert result.distinct_oracle_winners == 3


def test_normalized_winner_entropy_uses_log_six():
    result = refs.estimate_majority_winner(
        make_rows(), replication_seed=12345, n_contexts=25
    )
    probabilities = np.asarray([0.4, 0.4, 0.2])
    expected = -np.sum(probabilities * np.log(probabilities)) / np.log(6.0)
    assert result.normalized_winner_entropy == pytest.approx(expected)


def test_unanimous_winner_has_zero_entropy_and_full_share():
    rows = make_rows()
    mask = rows["partition"].eq("weight") & rows["context_number"].le(25)
    rows.loc[mask, "U_star"] = 0.1
    rows.loc[mask & rows["alternative_id"].eq("A6"), "U_star"] = 0.9
    result = refs.estimate_majority_winner(
        rows, replication_seed=12345, n_contexts=25
    )
    assert result.modal_winner_id == "A6"
    assert result.modal_winner_share == 1.0
    assert result.distinct_oracle_winners == 1
    assert result.normalized_winner_entropy == 0.0


def test_majority_is_row_order_invariant():
    rows = make_rows()
    first = refs.estimate_majority_winner(rows, replication_seed=12345, n_contexts=25)
    second = refs.estimate_majority_winner(
        rows.sample(frac=1.0, random_state=91), replication_seed=12345, n_contexts=25
    )
    assert first.modal_winner_id == second.modal_winner_id
    assert first.winner_by_weight_context_number == second.winner_by_weight_context_number


def test_majority_diagnostics_match_frozen_role_and_firewalls():
    d = refs.estimate_majority_winner(
        make_rows(), replication_seed=12345, n_contexts=25
    ).diagnostics
    assert d["winner_estimation_partition"] == "weight"
    assert d["weight_rows_used"] == 30
    assert d["weight_contexts_used"] == 5
    assert d["oracle_optimal_choice"] == "argmax_U_star"
    assert d["oracle_score_tie_absolute_tolerance"] == 1e-12
    assert d["oracle_top1_tie_break"] == "alternative_id_ascending"
    assert d["modal_count_tie_break"] == "alternative_id_ascending"
    assert d["evaluate_on"] == "test"
    assert d["primary_metric"] == "Top1Accuracy"
    assert d["test_oracle_utility_used_for_estimation"] is False
    assert d["test_target_Y_used_for_estimation"] is False
    assert d["fit_rows_used_for_estimation"] == 0
    assert d["mcdm_executed"] is False
    assert d["decision_metrics_computed"] is False


def test_builds_constant_prediction_for_all_fixed_test_contexts():
    rows = make_rows()
    reference = refs.estimate_majority_winner(
        rows, replication_seed=12345, n_contexts=25
    )
    predictions = refs.build_majority_winner_test_predictions(rows, reference=reference)
    assert len(predictions) == 200
    assert predictions["context_number"].tolist() == list(range(1001, 1201))
    assert predictions["predicted_alternative_id"].eq("A1").all()
    assert predictions["reference"].eq("MajorityWinner").all()


def test_test_outcomes_are_not_read_when_building_predictions():
    rows = make_rows()
    reference = refs.estimate_majority_winner(
        rows, replication_seed=12345, n_contexts=25
    )
    first = refs.build_majority_winner_test_predictions(rows, reference=reference)
    changed = rows.copy()
    changed.loc[changed["partition"].eq("test"), "U_star"] = np.inf
    changed.loc[changed["partition"].eq("test"), "Y"] = -np.inf
    second = refs.build_majority_winner_test_predictions(changed, reference=reference)
    pd.testing.assert_frame_equal(first, second)


@pytest.mark.parametrize("n_contexts", [24, 26, 2000])
def test_majority_rejects_nonfrozen_n(n_contexts):
    with pytest.raises(ValueError, match="not a frozen"):
        refs.prepare_majority_weight_rows(
            make_rows(), replication_seed=12345, n_contexts=n_contexts
        )


def test_majority_rejects_missing_column():
    with pytest.raises(ValueError, match="missing columns"):
        refs.prepare_majority_weight_rows(
            make_rows().drop(columns="U_star"), replication_seed=12345, n_contexts=25
        )


def test_majority_rejects_wrong_weight_seed():
    rows = make_rows()
    index = rows.index[rows["partition"].eq("weight")][0]
    rows.loc[index, "replication_seed"] = 12346
    with pytest.raises(ValueError, match="require replication_seed"):
        refs.prepare_majority_weight_rows(rows, replication_seed=12345, n_contexts=25)


def test_majority_rejects_duplicate_weight_identity():
    rows = make_rows()
    duplicate = rows.loc[rows["partition"].eq("weight")].iloc[[0]]
    with pytest.raises(ValueError, match="Duplicate"):
        refs.prepare_majority_weight_rows(
            pd.concat([rows, duplicate], ignore_index=True),
            replication_seed=12345,
            n_contexts=25,
        )


@pytest.mark.parametrize("value,message", [(np.nan, "non-finite"), (1.2, "range")])
def test_majority_rejects_invalid_weight_oracle_utility(value, message):
    rows = make_rows()
    index = rows.index[rows["partition"].eq("weight")][0]
    rows.loc[index, "U_star"] = value
    with pytest.raises(ValueError, match=message):
        refs.prepare_majority_weight_rows(rows, replication_seed=12345, n_contexts=25)


def test_majority_rejects_unexpected_nested_partition():
    rows = make_rows()
    rows.loc[0, "partition"] = "test"
    with pytest.raises(ValueError, match="Unexpected nested partition"):
        refs.prepare_majority_weight_rows(rows, replication_seed=12345, n_contexts=25)


def test_majority_rejects_missing_alternative_in_weight_context():
    rows = make_rows()
    index = rows.index[
        rows["partition"].eq("weight") & rows["context_number"].eq(5)
    ][0]
    rows.loc[index, "alternative_id"] = "A7"
    with pytest.raises(ValueError, match="A1..A6"):
        refs.prepare_majority_weight_rows(rows, replication_seed=12345, n_contexts=25)


def test_test_predictions_reject_incomplete_fixed_pool():
    rows = make_rows()
    reference = refs.estimate_majority_winner(
        rows, replication_seed=12345, n_contexts=25
    )
    shortened = rows.drop(index=rows.index[rows["partition"].eq("test")][0])
    with pytest.raises(ValueError, match="1200 TEST rows"):
        refs.build_majority_winner_test_predictions(shortened, reference=reference)


def test_test_predictions_reject_wrong_seed():
    rows = make_rows()
    reference = refs.estimate_majority_winner(
        rows, replication_seed=12345, n_contexts=25
    )
    index = rows.index[rows["partition"].eq("test")][0]
    rows.loc[index, "replication_seed"] = 12346
    with pytest.raises(ValueError, match="replication seed"):
        refs.build_majority_winner_test_predictions(rows, reference=reference)
