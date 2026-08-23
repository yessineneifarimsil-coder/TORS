from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.stats import kendalltau


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "decision_fidelity_metrics_v1.py"
spec = importlib.util.spec_from_file_location("decision_fidelity_metrics_v1_test_module", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load decision_fidelity_metrics_v1.py.")
metrics = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = metrics
spec.loader.exec_module(metrics)


def make_tables():
    method_records = []
    oracle_records = []
    oracle_values = {
        1001: [0.9, 0.7, 0.5, 0.3, 0.2, 0.1],
        1002: [0.2, 0.4, 0.6, 0.8, 0.7, 0.1],
    }
    method_values = {
        1001: [0.8, 0.6, 0.5, 0.3, 0.2, 0.1],
        1002: [0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
    }
    for context_number in (1001, 1002):
        for index, alternative_id in enumerate(metrics.ALTERNATIVE_IDS):
            common = {
                "context_id": f"ctx_{context_number}",
                "context_number": context_number,
                "alternative_id": alternative_id,
            }
            method_records.append({**common, "method": "MOORA", "score": method_values[context_number][index]})
            oracle_records.append({**common, "partition": "test", "U_star": oracle_values[context_number][index], "Y": np.nan})
    return pd.DataFrame(method_records), pd.DataFrame(oracle_records)


def test_frozen_constants():
    assert metrics.ALTERNATIVE_IDS == tuple(f"A{i}" for i in range(1, 7))
    assert metrics.EPSILON == 1e-12
    assert metrics.SCORE_TIE_ABSOLUTE_TOLERANCE == 1e-12
    assert metrics.REGRET_QUANTILE_METHOD == "linear"


def test_anchor_ties_average_ranks_without_chaining():
    scores = np.asarray([1.0, 1.0 - 0.75e-12, 1.0 - 1.5e-12, 0.7, 0.6, 0.5])
    result = metrics.rank_scores_anchor_ties(scores)
    assert result.ranks_by_alternative["A1"] == 1.5
    assert result.ranks_by_alternative["A2"] == 1.5
    assert result.ranks_by_alternative["A3"] == 3.0
    assert result.top_tie_set == ("A1", "A2")
    assert result.selected_top1 == "A1"


def test_top1_tie_break_is_ascending_id_independent_of_input_order():
    ids = tuple(reversed(metrics.ALTERNATIVE_IDS))
    result = metrics.rank_scores_anchor_ties(np.ones(6), ids)
    assert result.selected_top1 == "A1"
    assert result.top_tie_set == metrics.ALTERNATIVE_IDS


@pytest.mark.parametrize(
    "first,second",
    [
        ([1,2,3,4,5,6], [1,2,3,4,5,6]),
        ([1,2,3,4,5,6], [6,5,4,3,2,1]),
        ([1.5,1.5,3,4,5,6], [1,2,3,4,5,6]),
        ([1.5,1.5,3.5,3.5,5,6], [1,2.5,2.5,4,5,6]),
    ],
)
def test_kendall_tau_b_matches_scipy(first, second):
    observed = metrics.kendall_tau_b_from_ranks(first, second)
    expected = float(kendalltau(first, second, variant="b").statistic)
    assert observed == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("first,second", [([1,1,1,1,1,1], [1,2,3,4,5,6]), ([1,1,1,1,1,1], [2,2,2,2,2,2])])
def test_kendall_tau_b_undefined_is_explicit(first, second):
    assert metrics.kendall_tau_b_from_ranks(first, second) is None


def test_perfect_context_metrics():
    oracle = np.asarray([0.9,0.8,0.7,0.6,0.5,0.4])
    result = metrics.evaluate_context_decision_fidelity(oracle, oracle)
    assert result.kendall_tau_b == 1.0
    assert result.kendall_tau_b_defined is True
    assert result.top1_correct is True
    assert result.normalized_oracle_regret == 0.0
    assert result.oracle_decision_margin == pytest.approx(0.1/(0.5+1e-12))


def test_reversed_context_metrics_and_regret_formula():
    oracle = np.asarray([0.9,0.8,0.7,0.6,0.5,0.4])
    method = oracle[::-1]
    result = metrics.evaluate_context_decision_fidelity(method, oracle)
    assert result.kendall_tau_b == -1.0
    assert result.top1_correct is False
    assert result.method_ranking.selected_top1 == "A6"
    assert result.oracle_ranking.selected_top1 == "A1"
    assert result.normalized_oracle_regret == pytest.approx(0.5/(0.5+1e-12))


def test_oracle_top_tie_uses_deterministic_ascending_id():
    oracle = np.asarray([0.9, 0.9 - 0.5e-12, 0.7, 0.6, 0.5, 0.4])
    method = np.asarray([0.8, 0.95, 0.7, 0.6, 0.5, 0.4])
    result = metrics.evaluate_context_decision_fidelity(method, oracle)
    assert result.oracle_ranking.top_tie_set == ("A1", "A2")
    assert result.oracle_ranking.selected_top1 == "A1"
    assert result.method_ranking.selected_top1 == "A2"
    assert result.top1_correct is False
    assert result.normalized_oracle_regret < 2e-12


def test_constant_oracle_has_zero_regret_and_margin():
    oracle = np.full(6, 0.5)
    method = np.arange(6.0)
    result = metrics.evaluate_context_decision_fidelity(method, oracle)
    assert result.kendall_tau_b is None
    assert result.normalized_oracle_regret == 0.0
    assert result.oracle_decision_margin == 0.0
    assert result.regret_denominator == 1e-12


def test_decision_margin_uses_raw_largest_and_second_largest():
    oracle = np.asarray([0.95,0.75,0.70,0.4,0.3,0.1])
    result = metrics.evaluate_context_decision_fidelity(oracle, oracle)
    assert result.oracle_decision_margin == pytest.approx(0.20/(0.85+1e-12))


def test_context_result_is_input_order_invariant():
    ids = np.asarray(metrics.ALTERNATIVE_IDS)
    oracle = np.asarray([0.9,0.8,0.7,0.6,0.5,0.4])
    method = np.asarray([0.3,0.8,0.6,0.5,0.4,0.2])
    order = np.asarray([5,2,4,0,3,1])
    first = metrics.evaluate_context_decision_fidelity(method, oracle)
    second = metrics.evaluate_context_decision_fidelity(method[order], oracle[order], alternative_ids=ids[order])
    assert first == second


def test_batch_context_metrics_and_summary():
    method, oracle = make_tables()
    result = metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA")
    assert len(result.context_metrics) == 2
    assert result.context_metrics.loc[0, "top1_correct"]
    assert not result.context_metrics.loc[1, "top1_correct"]
    assert result.summary["contexts"] == 2
    assert result.summary["top1_accuracy"] == 0.5
    regrets = result.context_metrics["normalized_oracle_regret"].to_numpy()
    assert result.summary["mean_normalized_oracle_regret"] == np.mean(regrets)
    assert result.summary["median_normalized_oracle_regret"] == np.median(regrets)
    assert result.summary["p95_normalized_oracle_regret"] == np.quantile(regrets, 0.95, method="linear")
    assert result.summary["kendall_tau_b_defined_contexts"] == 2
    assert result.summary["kendall_tau_b_undefined_contexts"] == 0


def test_batch_recomputes_ranking_from_raw_scores():
    method, oracle = make_tables()
    method["rank"] = 99.0
    method["is_selected_top1"] = False
    first = metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA")
    second = metrics.evaluate_decision_fidelity_batch(method.drop(columns=["rank","is_selected_top1"]), oracle, method="MOORA")
    pd.testing.assert_frame_equal(first.context_metrics, second.context_metrics)


def test_batch_is_row_order_invariant():
    method, oracle = make_tables()
    first = metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA")
    second = metrics.evaluate_decision_fidelity_batch(
        method.sample(frac=1.0, random_state=3),
        oracle.sample(frac=1.0, random_state=4),
        method="MOORA",
    )
    pd.testing.assert_frame_equal(first.context_metrics, second.context_metrics)


def test_batch_diagnostics_close_upstream_and_write_firewalls():
    method, oracle = make_tables()
    d = metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA").diagnostics
    assert d["evaluation_partition"] == "test"
    assert d["method_scores_used"] is True
    assert d["oracle_U_star_used_for_evaluation"] is True
    assert d["target_Y_used"] is False
    assert d["model_fit_executed"] is False
    assert d["weight_estimation_executed"] is False
    assert d["mcdm_executed"] is False
    assert d["method_tuning_executed"] is False
    assert d["bootstrap_executed"] is False
    assert d["results_written"] is False


def test_identity_only_top1_reference_metrics():
    _, oracle = make_tables()
    predictions = pd.DataFrame({
        "context_id": ["ctx_1001", "ctx_1002"],
        "context_number": [1001,1002],
        "predicted_alternative_id": ["A1","A1"],
    })
    result = metrics.evaluate_top1_reference_batch(predictions, oracle, reference="MajorityWinner")
    assert result.summary["top1_accuracy"] == 0.5
    assert "mean_kendall_tau_b_defined_contexts" not in result.summary
    assert result.diagnostics["kendall_tau_b_not_computed_without_scores"] is True
    assert result.context_metrics["reference"].eq("MajorityWinner").all()


@pytest.mark.parametrize("bad", [np.ones(5), np.r_[np.ones(5),np.nan]])
def test_rejects_invalid_context_scores(bad):
    with pytest.raises(ValueError):
        metrics.evaluate_context_decision_fidelity(bad, np.ones(6)*0.5)


def test_rejects_out_of_range_oracle_utility():
    oracle = np.asarray([1.2,0.8,0.7,0.6,0.5,0.4])
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        metrics.evaluate_context_decision_fidelity(np.arange(6.0), oracle)


def test_batch_rejects_method_label_mismatch():
    method, oracle = make_tables()
    with pytest.raises(ValueError, match="label"):
        metrics.evaluate_decision_fidelity_batch(method, oracle, method="TOPSIS")


def test_batch_rejects_context_set_mismatch():
    method, oracle = make_tables()
    method = method.loc[method["context_number"].eq(1001)]
    with pytest.raises(ValueError, match="context sets differ"):
        metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA")


def test_batch_rejects_incomplete_context():
    method, oracle = make_tables()
    method = method.drop(index=0)
    with pytest.raises(ValueError, match="six alternatives"):
        metrics.evaluate_decision_fidelity_batch(method, oracle, method="MOORA")


def test_top1_reference_rejects_unknown_alternative():
    _, oracle = make_tables()
    predictions = pd.DataFrame({
        "context_id": ["ctx_1001", "ctx_1002"],
        "context_number": [1001,1002],
        "predicted_alternative_id": ["A7","A1"],
    })
    with pytest.raises(ValueError, match="outside A1..A6"):
        metrics.evaluate_top1_reference_batch(predictions, oracle, reference="Bad")


def test_top1_reference_rejects_out_of_range_oracle_utility():
    _, oracle = make_tables()
    oracle.loc[0, "U_star"] = 1.2
    predictions = pd.DataFrame({
        "context_id": ["ctx_1001", "ctx_1002"],
        "context_number": [1001,1002],
        "predicted_alternative_id": ["A1","A1"],
    })
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        metrics.evaluate_top1_reference_batch(predictions, oracle, reference="MajorityWinner")
