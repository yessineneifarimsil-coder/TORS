from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "moora_topsis_v1.py"
spec = importlib.util.spec_from_file_location("moora_topsis_v1_test_module", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load moora_topsis_v1.py.")
mcdm = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mcdm
spec.loader.exec_module(mcdm)


def toy_matrix():
    return np.asarray([
        [0.9, 0.2, 0.4, 0.5, 0.7, 0.1, 0.3, 0.8, 0.6, 0.2],
        [0.7, 0.5, 0.6, 0.4, 0.2, 0.9, 0.4, 0.3, 0.8, 0.5],
        [0.4, 0.8, 0.2, 0.7, 0.5, 0.6, 0.9, 0.2, 0.3, 0.8],
        [0.6, 0.3, 0.9, 0.2, 0.8, 0.4, 0.5, 0.7, 0.1, 0.6],
        [0.2, 0.7, 0.5, 0.9, 0.3, 0.8, 0.2, 0.4, 0.7, 0.1],
        [0.5, 0.6, 0.7, 0.3, 0.9, 0.2, 0.8, 0.5, 0.4, 0.7],
    ], dtype=float)


def weights():
    return np.asarray([0.20, 0.15, 0.10, 0.10, 0.10, 0.08, 0.08, 0.07, 0.07, 0.05])


def make_test_rows():
    records = []
    for context_number in (1001, 1002):
        matrix = toy_matrix() + (context_number - 1001) * 0.01
        for row_index, alternative_id in enumerate(mcdm.ALTERNATIVE_IDS):
            record = {
                "context_id": f"ctx_{context_number}",
                "context_number": context_number,
                "partition": "test",
                "alternative_id": alternative_id,
                "Y": np.nan,
                "U_star": np.nan,
            }
            for j, feature in enumerate(mcdm.FEATURES):
                record[feature] = matrix[row_index, j]
            records.append(record)
    # Non-TEST scientific content must be ignored by downstream scoring.
    record = {"context_id": "fit_1", "context_number": 1, "partition": "fit", "alternative_id": "A1"}
    for feature in mcdm.FEATURES:
        record[feature] = np.nan
    records.append(record)
    return pd.DataFrame.from_records(records)


def test_frozen_constants():
    assert mcdm.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert mcdm.ALTERNATIVE_IDS == tuple(f"A{i}" for i in range(1, 7))
    assert mcdm.EPSILON == 1e-12
    assert mcdm.SCORE_TIE_ABSOLUTE_TOLERANCE == 1e-12


def test_vector_normalization_matches_hand_formula():
    g = toy_matrix()
    observed = mcdm.vector_normalize_benefit_matrix(g)
    expected = g / (np.sqrt(np.sum(g ** 2, axis=0)) + 1e-12)
    np.testing.assert_allclose(observed, expected, atol=0.0, rtol=0.0)


def test_zero_column_normalizes_to_zero():
    g = toy_matrix()
    g[:, 3] = 0.0
    normalized = mcdm.vector_normalize_benefit_matrix(g)
    np.testing.assert_array_equal(normalized[:, 3], np.zeros(6))


def test_moora_matches_hand_formula():
    g = toy_matrix()
    w = weights()
    observed = mcdm.compute_moora_context(g, w)
    normalized = g / (np.sqrt(np.sum(g ** 2, axis=0)) + 1e-12)
    expected = normalized @ w
    np.testing.assert_allclose(observed.normalized_matrix, normalized, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(observed.scores, expected, atol=2e-16, rtol=0.0)
    assert observed.ranking.selected_top1 == mcdm.ALTERNATIVE_IDS[int(np.argmax(expected))]


def test_topsis_matches_hand_formula():
    g = toy_matrix()
    w = weights()
    observed = mcdm.compute_topsis_context(g, w)
    normalized = g / (np.sqrt(np.sum(g ** 2, axis=0)) + 1e-12)
    v = normalized * w
    positive = v.max(axis=0)
    negative = v.min(axis=0)
    d_plus = np.sqrt(np.sum((v - positive) ** 2, axis=1))
    d_minus = np.sqrt(np.sum((v - negative) ** 2, axis=1))
    expected = d_minus / (d_plus + d_minus)
    np.testing.assert_allclose(observed.weighted_matrix, v, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(observed.positive_ideal, positive, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(observed.negative_ideal, negative, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(observed.closeness, expected, atol=2e-16, rtol=0.0)


def test_topsis_identical_alternatives_use_closeness_half():
    g = np.full((6, 10), 0.4)
    result = mcdm.compute_topsis_context(g, weights())
    np.testing.assert_array_equal(result.closeness, np.full(6, 0.5))
    np.testing.assert_array_equal(result.zero_distance_sum_mask, np.ones(6, dtype=bool))
    assert result.ranking.selected_top1 == "A1"
    assert set(result.ranking.ranks_by_alternative.values()) == {3.5}


def test_moora_identical_alternatives_all_tie():
    result = mcdm.compute_moora_context(np.full((6, 10), 0.2), weights())
    assert result.ranking.top_tie_set == mcdm.ALTERNATIVE_IDS
    assert result.ranking.selected_top1 == "A1"
    assert set(result.ranking.ranks_by_alternative.values()) == {3.5}


def test_anchor_ties_do_not_chain():
    scores = np.asarray([1.0, 1.0 - 0.75e-12, 1.0 - 1.5e-12, 0.7, 0.6, 0.5])
    ranking = mcdm.rank_scores_anchor_ties(scores, mcdm.ALTERNATIVE_IDS)
    assert ranking.ranks_by_alternative["A1"] == 1.5
    assert ranking.ranks_by_alternative["A2"] == 1.5
    assert ranking.ranks_by_alternative["A3"] == 3.0
    assert ranking.top_tie_set == ("A1", "A2")
    assert ranking.selected_top1 == "A1"


def test_top1_tie_break_uses_alternative_id_not_input_order():
    ids = ("A6", "A5", "A4", "A3", "A2", "A1")
    ranking = mcdm.rank_scores_anchor_ties(np.ones(6), ids)
    assert ranking.selected_top1 == "A1"
    assert ranking.ordered_alternatives == mcdm.ALTERNATIVE_IDS


def test_context_row_order_is_canonicalized():
    order = np.asarray([5, 3, 1, 4, 2, 0])
    first = mcdm.compute_moora_context(toy_matrix(), weights())
    second = mcdm.compute_moora_context(
        toy_matrix()[order], weights(), alternative_ids=np.asarray(mcdm.ALTERNATIVE_IDS)[order]
    )
    np.testing.assert_allclose(first.scores, second.scores, atol=0.0, rtol=0.0)
    assert first.ranking == second.ranking


def test_weight_mapping_uses_frozen_feature_order():
    mapping = {feature: value for feature, value in zip(reversed(mcdm.FEATURES), reversed(weights()))}
    np.testing.assert_array_equal(mcdm.coerce_weights(mapping), weights())


def test_score_test_contexts_moora_matches_context_calls():
    rows = make_test_rows().sample(frac=1.0, random_state=17)
    batch = mcdm.score_test_contexts(rows, weights(), method="MOORA")
    assert len(batch.scored_rows) == 12
    assert batch.scored_rows.groupby("context_number")["is_selected_top1"].sum().eq(1).all()
    first_group = rows.loc[rows["context_number"].eq(1001)].sort_values("alternative_id")
    expected = mcdm.compute_moora_context(
        first_group.loc[:, mcdm.FEATURES].to_numpy(), weights()
    )
    observed = batch.scored_rows.loc[batch.scored_rows["context_number"].eq(1001), "score"]
    np.testing.assert_allclose(observed, expected.scores, atol=0.0, rtol=0.0)


def test_score_test_contexts_topsis_matches_context_calls():
    rows = make_test_rows()
    batch = mcdm.score_test_contexts(rows, weights(), method="TOPSIS")
    first_group = rows.loc[rows["context_number"].eq(1001)].sort_values("alternative_id")
    expected = mcdm.compute_topsis_context(
        first_group.loc[:, mcdm.FEATURES].to_numpy(), weights()
    )
    observed = batch.scored_rows.loc[batch.scored_rows["context_number"].eq(1001), "score"]
    np.testing.assert_allclose(observed, expected.closeness, atol=0.0, rtol=0.0)


def test_batch_ignores_target_oracle_and_non_test_rows():
    rows = make_test_rows()
    first = mcdm.score_test_contexts(rows, weights(), method="MOORA")
    changed = rows.copy()
    changed["Y"] = np.inf
    changed["U_star"] = -np.inf
    second = mcdm.score_test_contexts(changed, weights(), method="MOORA")
    pd.testing.assert_frame_equal(first.scored_rows, second.scored_rows)


@pytest.mark.parametrize("method", ["MOORA", "TOPSIS"])
def test_batch_diagnostics_close_estimation_and_metrics_firewalls(method):
    d = mcdm.score_test_contexts(make_test_rows(), weights(), method=method).diagnostics
    assert d["evaluation_partition"] == "test"
    assert d["contexts_scored"] == 2
    assert d["rows_scored"] == 12
    assert d["benefit_oriented_features_only"] is True
    assert d["weight_estimation_executed"] is False
    assert d["target_Y_used"] is False
    assert d["oracle_utility_used"] is False
    assert d["model_fit_executed"] is False
    assert d["shap_used"] is False
    assert d["decision_metrics_computed"] is False
    assert d["results_written"] is False


@pytest.mark.parametrize("bad", [np.ones(9)/9, np.r_[np.ones(9)/9, np.nan], np.r_[-0.1, np.ones(9)*1.1/9], np.ones(10)*0.09])
def test_rejects_invalid_weights(bad):
    with pytest.raises(ValueError):
        mcdm.compute_moora_context(toy_matrix(), bad)


def test_rejects_wrong_weight_mapping_keys():
    mapping = {feature: 0.1 for feature in mcdm.FEATURES}
    mapping.pop("g_C10")
    mapping["wrong"] = 0.1
    with pytest.raises(ValueError, match="weight keys"):
        mcdm.coerce_weights(mapping)


@pytest.mark.parametrize("shape", [(5,10), (6,9), (7,10)])
def test_rejects_wrong_matrix_shape(shape):
    with pytest.raises(ValueError, match="shape"):
        mcdm.compute_moora_context(np.zeros(shape), weights())


@pytest.mark.parametrize("value,message", [(np.nan, "non-finite"), (1.2, r"\[0,1\]")])
def test_rejects_invalid_g_values(value, message):
    g = toy_matrix()
    g[0,0] = value
    with pytest.raises(ValueError, match=message):
        mcdm.compute_topsis_context(g, weights())


def test_rejects_missing_or_duplicate_alternative():
    ids = list(mcdm.ALTERNATIVE_IDS)
    ids[-1] = "A5"
    with pytest.raises(ValueError, match="unique"):
        mcdm.compute_moora_context(toy_matrix(), weights(), alternative_ids=ids)


def test_rejects_unknown_batch_method():
    with pytest.raises(ValueError, match="MOORA or TOPSIS"):
        mcdm.score_test_contexts(make_test_rows(), weights(), method="WASPAS")


def test_rejects_missing_test_rows():
    rows = make_test_rows()
    rows["partition"] = "fit"
    with pytest.raises(ValueError, match="No external TEST"):
        mcdm.score_test_contexts(rows, weights(), method="MOORA")


def test_rejects_incomplete_test_context():
    rows = make_test_rows()
    rows = rows.drop(index=rows.index[rows["context_number"].eq(1001)][0])
    with pytest.raises(ValueError):
        mcdm.score_test_contexts(rows, weights(), method="TOPSIS")
