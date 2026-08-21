from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "decision_semantics_v1.py"

spec = importlib.util.spec_from_file_location(
    "decision_semantics_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load decision_semantics_v1.py for tests.")

decision_semantics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decision_semantics)

SCORE_TIE_ATOL = decision_semantics.SCORE_TIE_ATOL
SCORE_TIE_RTOL = decision_semantics.SCORE_TIE_RTOL
average_ranks_descending = decision_semantics.average_ranks_descending
deterministic_top1 = decision_semantics.deterministic_top1


def test_frozen_tolerances_are_exact():
    assert SCORE_TIE_ATOL == 1.0e-12
    assert SCORE_TIE_RTOL == 0.0


def test_strict_descending_scores_receive_one_based_ranks():
    ranks = average_ranks_descending(
        [0.9, 0.7, 0.2],
        ["A1", "A2", "A3"],
    )
    np.testing.assert_array_equal(ranks, np.array([1.0, 2.0, 3.0]))


def test_exact_tie_receives_average_rank():
    ranks = average_ranks_descending(
        [0.8, 0.8, 0.1],
        ["A2", "A1", "A3"],
    )
    np.testing.assert_array_equal(ranks, np.array([1.5, 1.5, 3.0]))


def test_anchor_ties_do_not_chain():
    ranks = average_ranks_descending(
        [1.0, 1.0 - 0.75e-12, 1.0 - 1.50e-12],
        ["A1", "A2", "A3"],
    )
    np.testing.assert_array_equal(ranks, np.array([1.5, 1.5, 3.0]))


def test_tie_boundary_is_inclusive():
    ranks = average_ranks_descending(
        [1.0, 1.0 - SCORE_TIE_ATOL, 0.0],
        ["A1", "A2", "A3"],
    )
    np.testing.assert_array_equal(ranks, np.array([1.5, 1.5, 3.0]))


def test_top1_uses_maximum_based_tie_set_then_ascending_id():
    winner = deterministic_top1(
        [1.0, 1.0 - 0.5e-12, 0.2],
        ["A3", "A1", "A2"],
    )
    assert winner == "A1"


def test_top1_does_not_chain_from_nonmaximal_member():
    winner = deterministic_top1(
        [1.0, 1.0 - 0.75e-12, 1.0 - 1.50e-12],
        ["A3", "A2", "A1"],
    )
    assert winner == "A2"


@pytest.mark.parametrize(
    "scores,alternative_ids",
    [
        ([], []),
        ([1.0, 2.0], ["A1"]),
        ([1.0, 2.0], ["A1", "A1"]),
        ([1.0, np.nan], ["A1", "A2"]),
        ([1.0, np.inf], ["A1", "A2"]),
        ([[1.0, 2.0]], ["A1", "A2"]),
    ],
)
def test_invalid_inputs_fail_closed(scores, alternative_ids):
    with pytest.raises(ValueError):
        average_ranks_descending(scores, alternative_ids)
    with pytest.raises(ValueError):
        deterministic_top1(scores, alternative_ids)
