from __future__ import annotations

"""Frozen benefit-oriented MOORA and TOPSIS decision operators.

Both operators use the same per-context vector-normalized G matrix and the
same frozen anchor-based average-rank and deterministic Top-1 conventions.
This module consumes already-estimated weights. It does not estimate weights,
fit models, inspect oracle utility/target Y, compute decision-fidelity metrics,
or write results.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
N_ALTERNATIVES = 6
EPSILON = 1.0e-12
SCORE_TIE_ABSOLUTE_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class ScoreRanking:
    scores_by_alternative: dict[str, float]
    ranks_by_alternative: dict[str, float]
    ordered_alternatives: tuple[str, ...]
    top_tie_set: tuple[str, ...]
    selected_top1: str


@dataclass(frozen=True)
class MOORAContextResult:
    alternative_ids: tuple[str, ...]
    weights: np.ndarray
    normalized_matrix: np.ndarray
    scores: np.ndarray
    ranking: ScoreRanking
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class TOPSISContextResult:
    alternative_ids: tuple[str, ...]
    weights: np.ndarray
    normalized_matrix: np.ndarray
    weighted_matrix: np.ndarray
    positive_ideal: np.ndarray
    negative_ideal: np.ndarray
    positive_distance: np.ndarray
    negative_distance: np.ndarray
    closeness: np.ndarray
    zero_distance_sum_mask: np.ndarray
    ranking: ScoreRanking
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class MCDMBatchResult:
    method: str
    weights_by_feature: dict[str, float]
    scored_rows: pd.DataFrame
    diagnostics: dict[str, Any]


def coerce_weights(
    weights: Mapping[str, float] | Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Return the frozen ten-feature weight order after strict validation."""
    if isinstance(weights, Mapping):
        if set(weights) != set(FEATURES):
            missing = sorted(set(FEATURES) - set(weights))
            extra = sorted(set(weights) - set(FEATURES))
            raise ValueError(f"MCDM weight keys differ; missing={missing}, extra={extra}.")
        values = np.asarray([weights[feature] for feature in FEATURES], dtype=float)
    else:
        values = np.asarray(weights, dtype=float)
    if values.shape != (N_CRITERIA,):
        raise ValueError("MCDM weights must contain exactly 10 values.")
    if not np.isfinite(values).all():
        raise ValueError("MCDM weights contain non-finite values.")
    if np.any(values < 0.0):
        raise ValueError("MCDM weights must be nonnegative.")
    if not np.isclose(float(np.sum(values)), 1.0, atol=EPSILON, rtol=0.0):
        raise ValueError("MCDM weights must sum to one within absolute tolerance 1e-12.")
    return values.copy()


def _canonicalize_context(
    g_matrix: np.ndarray,
    alternative_ids: Sequence[str],
) -> tuple[np.ndarray, tuple[str, ...]]:
    values = np.asarray(g_matrix, dtype=float)
    ids = tuple(str(value) for value in alternative_ids)
    if values.shape != (N_ALTERNATIVES, N_CRITERIA):
        raise ValueError("MCDM context matrix must have shape (6,10).")
    if len(ids) != N_ALTERNATIVES or len(set(ids)) != N_ALTERNATIVES:
        raise ValueError("MCDM alternative IDs must be six unique values.")
    if set(ids) != set(ALTERNATIVE_IDS):
        raise ValueError("MCDM context must contain A1..A6 exactly once.")
    if not np.isfinite(values).all():
        raise ValueError("MCDM benefit-oriented G contains non-finite values.")
    if np.any(values < -EPSILON) or np.any(values > 1.0 + EPSILON):
        raise ValueError("MCDM benefit-oriented G must lie in [0,1].")
    order = np.argsort(np.asarray(ids), kind="stable")
    return values[order].copy(), tuple(ids[index] for index in order)


def vector_normalize_benefit_matrix(g_matrix: np.ndarray) -> np.ndarray:
    """Apply g_asj/(sqrt(sum_a g_asj^2)+epsilon) criterionwise."""
    values = np.asarray(g_matrix, dtype=float)
    if values.shape != (N_ALTERNATIVES, N_CRITERIA):
        raise ValueError("MCDM context matrix must have shape (6,10).")
    if not np.isfinite(values).all():
        raise ValueError("MCDM benefit-oriented G contains non-finite values.")
    denominator = np.sqrt(np.sum(values * values, axis=0)) + EPSILON
    normalized = values / denominator
    if not np.isfinite(normalized).all():
        raise FloatingPointError("MCDM vector normalization became non-finite.")
    return normalized


def rank_scores_anchor_ties(
    scores: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str],
) -> ScoreRanking:
    """Rank descending with non-chained anchor ties and deterministic Top-1."""
    values = np.asarray(scores, dtype=float)
    ids = tuple(str(value) for value in alternative_ids)
    if values.shape != (N_ALTERNATIVES,):
        raise ValueError("Ranking requires exactly six scores.")
    if len(ids) != N_ALTERNATIVES or len(set(ids)) != N_ALTERNATIVES:
        raise ValueError("Ranking requires six unique alternative IDs.")
    if set(ids) != set(ALTERNATIVE_IDS):
        raise ValueError("Ranking alternatives must be A1..A6.")
    if not np.isfinite(values).all():
        raise ValueError("Ranking scores contain non-finite values.")

    score_by_id = {alternative_id: float(score) for alternative_id, score in zip(ids, values, strict=True)}
    ordered = tuple(sorted(ids, key=lambda alternative_id: (-score_by_id[alternative_id], alternative_id)))
    ranks: dict[str, float] = {}
    cursor = 0
    while cursor < N_ALTERNATIVES:
        anchor_id = ordered[cursor]
        anchor = score_by_id[anchor_id]
        group_end = cursor + 1
        while group_end < N_ALTERNATIVES:
            candidate = score_by_id[ordered[group_end]]
            if abs(anchor - candidate) > SCORE_TIE_ABSOLUTE_TOLERANCE:
                break
            group_end += 1
        average_rank = float(((cursor + 1) + group_end) / 2.0)
        for position in range(cursor, group_end):
            ranks[ordered[position]] = average_rank
        cursor = group_end

    maximum = max(score_by_id.values())
    top_tie_set = tuple(sorted(
        alternative_id for alternative_id in ids
        if maximum - score_by_id[alternative_id] <= SCORE_TIE_ABSOLUTE_TOLERANCE
    ))
    selected_top1 = top_tie_set[0]
    return ScoreRanking(
        scores_by_alternative={alternative_id: score_by_id[alternative_id] for alternative_id in ALTERNATIVE_IDS},
        ranks_by_alternative={alternative_id: ranks[alternative_id] for alternative_id in ALTERNATIVE_IDS},
        ordered_alternatives=ordered,
        top_tie_set=top_tie_set,
        selected_top1=selected_top1,
    )


def compute_moora_context(
    g_matrix: np.ndarray,
    weights: Mapping[str, float] | Sequence[float] | np.ndarray,
    *,
    alternative_ids: Sequence[str] = ALTERNATIVE_IDS,
) -> MOORAContextResult:
    """Compute frozen benefit-only MOORA for one six-alternative context."""
    canonical_g, ids = _canonicalize_context(g_matrix, alternative_ids)
    weight_values = coerce_weights(weights)
    normalized = vector_normalize_benefit_matrix(canonical_g)
    scores = normalized @ weight_values
    if not np.isfinite(scores).all():
        raise FloatingPointError("MOORA scores became non-finite.")
    ranking = rank_scores_anchor_ties(scores, ids)
    diagnostics = {
        "method": "MOORA",
        "role": "primary_mcdm",
        "input": "benefit_oriented_G",
        "vector_normalization": "g/(sqrt(sum_squares)+1e-12)",
        "score": "sum_j_w_j_r_asj",
        "ranking": "descending_score",
        "rank_ties": "anchor_based_average_ranks_no_chaining",
        "top1_tie_break": "alternative_id_ascending",
        "weight_estimation_executed": False,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "decision_metrics_computed": False,
    }
    return MOORAContextResult(ids, weight_values, normalized, scores, ranking, diagnostics)


def compute_topsis_context(
    g_matrix: np.ndarray,
    weights: Mapping[str, float] | Sequence[float] | np.ndarray,
    *,
    alternative_ids: Sequence[str] = ALTERNATIVE_IDS,
) -> TOPSISContextResult:
    """Compute frozen benefit-oriented TOPSIS for one context."""
    canonical_g, ids = _canonicalize_context(g_matrix, alternative_ids)
    weight_values = coerce_weights(weights)
    normalized = vector_normalize_benefit_matrix(canonical_g)
    weighted = normalized * weight_values
    positive_ideal = np.max(weighted, axis=0)
    negative_ideal = np.min(weighted, axis=0)
    positive_distance = np.sqrt(np.sum((weighted - positive_ideal) ** 2, axis=1))
    negative_distance = np.sqrt(np.sum((weighted - negative_ideal) ** 2, axis=1))
    distance_sum = positive_distance + negative_distance
    zero_mask = distance_sum <= EPSILON
    closeness = np.full(N_ALTERNATIVES, 0.5, dtype=float)
    active = ~zero_mask
    closeness[active] = negative_distance[active] / distance_sum[active]
    if not np.isfinite(closeness).all():
        raise FloatingPointError("TOPSIS closeness became non-finite.")
    ranking = rank_scores_anchor_ties(closeness, ids)
    diagnostics = {
        "method": "TOPSIS",
        "role": "robustness_mcdm",
        "input": "benefit_oriented_G",
        "vector_normalization": "g/(sqrt(sum_squares)+1e-12)",
        "weighted_matrix": "v_asj=w_j*r_asj",
        "positive_ideal": "columnwise_max",
        "negative_ideal": "columnwise_min",
        "distance": "Euclidean",
        "closeness": "D_minus/(D_plus+D_minus)",
        "zero_distance_sum_rule": "closeness_0.5",
        "ranking": "descending_closeness",
        "rank_ties": "anchor_based_average_ranks_no_chaining",
        "top1_tie_break": "alternative_id_ascending",
        "weight_estimation_executed": False,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "decision_metrics_computed": False,
    }
    return TOPSISContextResult(
        ids, weight_values, normalized, weighted, positive_ideal, negative_ideal,
        positive_distance, negative_distance, closeness, zero_mask, ranking, diagnostics
    )


def score_test_contexts(
    rows: pd.DataFrame,
    weights: Mapping[str, float] | Sequence[float] | np.ndarray,
    *,
    method: str,
) -> MCDMBatchResult:
    """Score complete external TEST contexts without computing fidelity metrics."""
    method_name = str(method).upper()
    if method_name not in {"MOORA", "TOPSIS"}:
        raise ValueError("MCDM method must be MOORA or TOPSIS.")
    required = {"context_id", "context_number", "partition", "alternative_id", *FEATURES}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"MCDM TEST input is missing columns: {missing}.")
    selected = rows.loc[rows["partition"].eq("test")].copy()
    if selected.empty:
        raise ValueError("No external TEST rows found for MCDM scoring.")
    selected.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate TEST context-alternative identity detected.")
    weight_values = coerce_weights(weights)
    output_records: list[dict[str, Any]] = []
    for context_number, group in selected.groupby("context_number", sort=False):
        if group["context_id"].nunique() != 1:
            raise ValueError("A TEST context number maps to multiple context IDs.")
        ids = tuple(group["alternative_id"].astype(str).tolist())
        g = group.loc[:, FEATURES].to_numpy(dtype=float)
        result = (
            compute_moora_context(g, weight_values, alternative_ids=ids)
            if method_name == "MOORA"
            else compute_topsis_context(g, weight_values, alternative_ids=ids)
        )
        scores = result.scores if method_name == "MOORA" else result.closeness
        for alternative_id, score in zip(result.alternative_ids, scores, strict=True):
            output_records.append({
                "context_id": str(group["context_id"].iloc[0]),
                "context_number": int(context_number),
                "alternative_id": alternative_id,
                "method": method_name,
                "score": float(score),
                "rank": float(result.ranking.ranks_by_alternative[alternative_id]),
                "is_selected_top1": alternative_id == result.ranking.selected_top1,
            })
    scored = pd.DataFrame.from_records(output_records)
    diagnostics = {
        "method": method_name,
        "evaluation_partition": "test",
        "contexts_scored": int(scored["context_number"].nunique()),
        "rows_scored": int(len(scored)),
        "benefit_oriented_features_only": True,
        "weight_estimation_executed": False,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "model_fit_executed": False,
        "shap_used": False,
        "decision_metrics_computed": False,
        "results_written": False,
    }
    return MCDMBatchResult(
        method=method_name,
        weights_by_feature={feature: float(value) for feature, value in zip(FEATURES, weight_values, strict=True)},
        scored_rows=scored,
        diagnostics=diagnostics,
    )
