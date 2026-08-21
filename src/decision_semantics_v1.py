from __future__ import annotations

"""Frozen common decision-ranking semantics.

Pure utilities implementing the prospectively frozen score-tie and deterministic
Top-1 rules used by the weighting/MCDM benchmark.

This module does not load benchmark data, fit models, compute SHAP values,
estimate weights, run MCDM, inspect TEST partitions, or write result files.
"""

from collections.abc import Sequence

import numpy as np


SCORE_TIE_ATOL = 1.0e-12
SCORE_TIE_RTOL = 0.0


def _validated_inputs(
    scores: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str],
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Return validated one-dimensional scores and alternative IDs."""
    values = np.asarray(scores, dtype=float)
    ids = tuple(str(x) for x in alternative_ids)

    if values.ndim != 1:
        raise ValueError("scores must be one-dimensional.")
    if len(values) == 0:
        raise ValueError("At least one alternative is required.")
    if len(ids) != len(values):
        raise ValueError("scores and alternative_ids must have equal length.")
    if len(set(ids)) != len(ids):
        raise ValueError("alternative_ids must be unique.")
    if not np.isfinite(values).all():
        raise ValueError("scores must be finite.")

    return values, ids


def _descending_indices(
    scores: np.ndarray,
    alternative_ids: tuple[str, ...],
) -> list[int]:
    """Sort by raw score descending, then alternative_id ascending."""
    return sorted(
        range(len(scores)),
        key=lambda i: (-float(scores[i]), alternative_ids[i]),
    )


def average_ranks_descending(
    scores: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str],
) -> np.ndarray:
    """Return one-based average ranks using frozen anchor-based ties.

    The highest unassigned score is the tie-group anchor. Every remaining
    alternative whose absolute score difference from that anchor is at most
    ``1e-12`` joins the group. The group receives the average of the occupied
    one-based rank positions. Ties are not chained through adjacent pairwise
    similarities.

    The returned array follows the caller's original alternative order.
    """
    values, ids = _validated_inputs(scores, alternative_ids)
    order = _descending_indices(values, ids)

    ranks = np.empty(len(values), dtype=float)
    cursor = 0

    while cursor < len(order):
        anchor_index = order[cursor]
        anchor_score = float(values[anchor_index])

        end = cursor + 1
        while end < len(order):
            candidate_index = order[end]
            difference = abs(float(values[candidate_index]) - anchor_score)
            if difference <= SCORE_TIE_ATOL:
                end += 1
            else:
                break

        average_rank = ((cursor + 1) + end) / 2.0
        for position in range(cursor, end):
            ranks[order[position]] = average_rank

        cursor = end

    return ranks


def deterministic_top1(
    scores: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str],
) -> str:
    """Return frozen deterministic Top-1 alternative.

    The top tie set contains every alternative satisfying
    ``max_score - score <= 1e-12``. The selected member is the ascending
    ``alternative_id`` minimum. Relative tolerance is exactly zero.
    """
    values, ids = _validated_inputs(scores, alternative_ids)
    maximum = float(np.max(values))

    tied = [
        ids[i]
        for i, score in enumerate(values)
        if maximum - float(score) <= SCORE_TIE_ATOL
    ]
    if not tied:
        raise AssertionError("Top-1 tie set unexpectedly empty.")

    return min(tied)
