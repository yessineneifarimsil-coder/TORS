from __future__ import annotations

"""Frozen context-level and pooled decision-fidelity metrics.

Raw method scores and oracle U_star are ranked using the same absolute 1e-12,
anchor-based, non-chained average-rank convention. Metrics are Kendall tau-b,
deterministic Top-1 match, normalized oracle regret, and oracle decision margin.
The implementation evaluates already-produced TEST decisions only; it does not
fit models, estimate weights, run MCDM, tune methods, bootstrap, or write files.
"""

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd


ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
N_ALTERNATIVES = 6
EPSILON = 1.0e-12
SCORE_TIE_ABSOLUTE_TOLERANCE = 1.0e-12
REGRET_QUANTILE_METHOD = "linear"


@dataclass(frozen=True)
class Ranking:
    scores_by_alternative: dict[str, float]
    ranks_by_alternative: dict[str, float]
    ordered_alternatives: tuple[str, ...]
    top_tie_set: tuple[str, ...]
    selected_top1: str


@dataclass(frozen=True)
class ContextDecisionFidelity:
    method_ranking: Ranking
    oracle_ranking: Ranking
    kendall_tau_b: float | None
    kendall_tau_b_defined: bool
    top1_correct: bool
    normalized_oracle_regret: float
    oracle_decision_margin: float
    oracle_utility_range: float
    regret_denominator: float
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class DecisionFidelityBatchResult:
    method: str
    context_metrics: pd.DataFrame
    summary: dict[str, Any]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class Top1ReferenceBatchResult:
    reference: str
    context_metrics: pd.DataFrame
    summary: dict[str, Any]
    diagnostics: dict[str, Any]


def rank_scores_anchor_ties(
    scores: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str] = ALTERNATIVE_IDS,
) -> Ranking:
    """Apply frozen descending anchor ties, average ranks, and Top-1 rule."""
    values = np.asarray(scores, dtype=float)
    ids = tuple(str(value) for value in alternative_ids)
    if values.shape != (N_ALTERNATIVES,):
        raise ValueError("Decision ranking requires exactly six scores.")
    if len(ids) != N_ALTERNATIVES or len(set(ids)) != N_ALTERNATIVES:
        raise ValueError("Decision ranking requires six unique alternatives.")
    if set(ids) != set(ALTERNATIVE_IDS):
        raise ValueError("Decision ranking alternatives must be A1..A6.")
    if not np.isfinite(values).all():
        raise ValueError("Decision ranking scores contain non-finite values.")

    scores_by_id = {
        alternative_id: float(score)
        for alternative_id, score in zip(ids, values, strict=True)
    }
    ordered = tuple(
        sorted(ids, key=lambda alternative_id: (-scores_by_id[alternative_id], alternative_id))
    )
    ranks: dict[str, float] = {}
    cursor = 0
    while cursor < N_ALTERNATIVES:
        anchor = scores_by_id[ordered[cursor]]
        end = cursor + 1
        while end < N_ALTERNATIVES:
            if abs(anchor - scores_by_id[ordered[end]]) > SCORE_TIE_ABSOLUTE_TOLERANCE:
                break
            end += 1
        average_rank = float(((cursor + 1) + end) / 2.0)
        for index in range(cursor, end):
            ranks[ordered[index]] = average_rank
        cursor = end

    maximum = max(scores_by_id.values())
    top_tie_set = tuple(
        sorted(
            alternative_id
            for alternative_id in ids
            if maximum - scores_by_id[alternative_id] <= SCORE_TIE_ABSOLUTE_TOLERANCE
        )
    )
    return Ranking(
        scores_by_alternative={item: scores_by_id[item] for item in ALTERNATIVE_IDS},
        ranks_by_alternative={item: ranks[item] for item in ALTERNATIVE_IDS},
        ordered_alternatives=ordered,
        top_tie_set=top_tie_set,
        selected_top1=top_tie_set[0],
    )


def kendall_tau_b_from_ranks(
    first_ranks: Sequence[float] | np.ndarray,
    second_ranks: Sequence[float] | np.ndarray,
) -> float | None:
    """Compute tie-corrected Kendall tau-b by exact pair counting."""
    first = np.asarray(first_ranks, dtype=float)
    second = np.asarray(second_ranks, dtype=float)
    if first.shape != (N_ALTERNATIVES,) or second.shape != (N_ALTERNATIVES,):
        raise ValueError("Kendall tau-b requires two six-alternative rank vectors.")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("Kendall rank vectors contain non-finite values.")

    concordant = 0
    discordant = 0
    tied_first_only = 0
    tied_second_only = 0
    for i in range(N_ALTERNATIVES - 1):
        for j in range(i + 1, N_ALTERNATIVES):
            delta_first = first[i] - first[j]
            delta_second = second[i] - second[j]
            first_tie = delta_first == 0.0
            second_tie = delta_second == 0.0
            if first_tie and second_tie:
                continue
            if first_tie:
                tied_first_only += 1
            elif second_tie:
                tied_second_only += 1
            elif delta_first * delta_second > 0.0:
                concordant += 1
            else:
                discordant += 1
    comparable = concordant + discordant
    denominator = float(
        np.sqrt(
            (comparable + tied_first_only)
            * (comparable + tied_second_only)
        )
    )
    if denominator == 0.0:
        return None
    value = float((concordant - discordant) / denominator)
    if not -1.0 <= value <= 1.0:
        raise FloatingPointError("Kendall tau-b escaped [-1,1].")
    return value


def _canonical_values(
    values: Sequence[float] | np.ndarray,
    alternative_ids: Sequence[str],
    *,
    label: str,
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    ids = tuple(str(value) for value in alternative_ids)
    if array.shape != (N_ALTERNATIVES,):
        raise ValueError(f"{label} requires exactly six values.")
    if len(ids) != N_ALTERNATIVES or len(set(ids)) != N_ALTERNATIVES:
        raise ValueError(f"{label} requires six unique alternative IDs.")
    if set(ids) != set(ALTERNATIVE_IDS):
        raise ValueError(f"{label} alternatives must be A1..A6.")
    if not np.isfinite(array).all():
        raise ValueError(f"{label} contains non-finite values.")
    by_id = {alternative_id: float(value) for alternative_id, value in zip(ids, array, strict=True)}
    return np.asarray([by_id[item] for item in ALTERNATIVE_IDS], dtype=float)


def evaluate_context_decision_fidelity(
    method_scores: Sequence[float] | np.ndarray,
    oracle_utilities: Sequence[float] | np.ndarray,
    *,
    alternative_ids: Sequence[str] = ALTERNATIVE_IDS,
) -> ContextDecisionFidelity:
    """Evaluate all frozen decision metrics for one TEST context."""
    canonical_scores = _canonical_values(
        method_scores, alternative_ids, label="Method scores"
    )
    canonical_utility = _canonical_values(
        oracle_utilities, alternative_ids, label="Oracle U_star"
    )
    if np.any(canonical_utility < -EPSILON) or np.any(canonical_utility > 1.0 + EPSILON):
        raise ValueError("Oracle U_star escaped the theoretical [0,1] range.")

    method_ranking = rank_scores_anchor_ties(canonical_scores, ALTERNATIVE_IDS)
    oracle_ranking = rank_scores_anchor_ties(canonical_utility, ALTERNATIVE_IDS)
    method_ranks = np.asarray(
        [method_ranking.ranks_by_alternative[item] for item in ALTERNATIVE_IDS],
        dtype=float,
    )
    oracle_ranks = np.asarray(
        [oracle_ranking.ranks_by_alternative[item] for item in ALTERNATIVE_IDS],
        dtype=float,
    )
    kendall = kendall_tau_b_from_ranks(method_ranks, oracle_ranks)
    top1_correct = method_ranking.selected_top1 == oracle_ranking.selected_top1

    maximum = float(np.max(canonical_utility))
    minimum = float(np.min(canonical_utility))
    utility_range = maximum - minimum
    denominator = utility_range + EPSILON
    selected_index = ALTERNATIVE_IDS.index(method_ranking.selected_top1)
    regret = float((maximum - canonical_utility[selected_index]) / denominator)
    if regret < -EPSILON or regret > 1.0 + EPSILON:
        raise FloatingPointError("Normalized oracle regret escaped [0,1].")
    regret = float(np.clip(regret, 0.0, 1.0))
    sorted_utility = np.sort(canonical_utility)[::-1]
    margin = float((sorted_utility[0] - sorted_utility[1]) / denominator)
    if margin < -EPSILON or margin > 1.0 + EPSILON:
        raise FloatingPointError("Oracle decision margin escaped [0,1].")
    margin = float(np.clip(margin, 0.0, 1.0))

    diagnostics = {
        "kendall_variant": "tau_b",
        "kendall_tau_b_defined": kendall is not None,
        "score_tie_absolute_tolerance": SCORE_TIE_ABSOLUTE_TOLERANCE,
        "rank_ties": "anchor_based_average_ranks_no_chaining",
        "top1_rule": "deterministic_selected_alternative_match",
        "top1_tie_break": "alternative_id_ascending",
        "normalized_oracle_regret_epsilon": EPSILON,
        "oracle_decision_margin_epsilon": EPSILON,
    }
    return ContextDecisionFidelity(
        method_ranking=method_ranking,
        oracle_ranking=oracle_ranking,
        kendall_tau_b=kendall,
        kendall_tau_b_defined=kendall is not None,
        top1_correct=bool(top1_correct),
        normalized_oracle_regret=regret,
        oracle_decision_margin=margin,
        oracle_utility_range=utility_range,
        regret_denominator=denominator,
        diagnostics=diagnostics,
    )


def _prepare_oracle_test_rows(rows: pd.DataFrame) -> pd.DataFrame:
    required = {"context_id", "context_number", "alternative_id", "U_star"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Oracle TEST rows are missing columns: {missing}.")
    selected = rows.loc[rows["partition"].eq("test")].copy() if "partition" in rows else rows.copy()
    if selected.empty:
        raise ValueError("No oracle TEST rows found.")
    selected.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate oracle TEST context-alternative identity.")
    return selected


def _summary(context_metrics: pd.DataFrame, *, include_kendall: bool) -> dict[str, Any]:
    regret = context_metrics["normalized_oracle_regret"].to_numpy(dtype=float)
    margin = context_metrics["oracle_decision_margin"].to_numpy(dtype=float)
    result: dict[str, Any] = {
        "contexts": int(len(context_metrics)),
        "top1_accuracy": float(context_metrics["top1_correct"].mean()),
        "mean_normalized_oracle_regret": float(np.mean(regret)),
        "median_normalized_oracle_regret": float(np.median(regret)),
        "p95_normalized_oracle_regret": float(
            np.quantile(regret, 0.95, method=REGRET_QUANTILE_METHOD)
        ),
        "mean_oracle_decision_margin": float(np.mean(margin)),
        "regret_quantile_method": REGRET_QUANTILE_METHOD,
    }
    if include_kendall:
        defined = context_metrics["kendall_tau_b_defined"].to_numpy(dtype=bool)
        values = context_metrics.loc[defined, "kendall_tau_b"].to_numpy(dtype=float)
        result["kendall_tau_b_defined_contexts"] = int(np.count_nonzero(defined))
        result["kendall_tau_b_undefined_contexts"] = int(np.count_nonzero(~defined))
        result["mean_kendall_tau_b_defined_contexts"] = (
            float(np.mean(values)) if len(values) else None
        )
    return result


def evaluate_decision_fidelity_batch(
    method_scored_rows: pd.DataFrame,
    oracle_rows: pd.DataFrame,
    *,
    method: str,
) -> DecisionFidelityBatchResult:
    """Evaluate six-score method rankings against oracle TEST utility."""
    required = {"context_id", "context_number", "alternative_id", "score"}
    missing = sorted(required - set(method_scored_rows.columns))
    if missing:
        raise ValueError(f"Method scored rows are missing columns: {missing}.")
    scored = method_scored_rows.copy()
    if "method" in scored and not scored["method"].astype(str).eq(str(method)).all():
        raise ValueError("Method label does not match scored rows.")
    scored.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    if scored.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate method context-alternative identity.")
    oracle = _prepare_oracle_test_rows(oracle_rows)
    if set(scored["context_number"]) != set(oracle["context_number"]):
        raise ValueError("Method and oracle TEST context sets differ.")

    records: list[dict[str, Any]] = []
    for context_number, oracle_group in oracle.groupby("context_number", sort=False):
        method_group = scored.loc[scored["context_number"].eq(context_number)]
        if len(method_group) != N_ALTERNATIVES or len(oracle_group) != N_ALTERNATIVES:
            raise ValueError("Every decision context must contain six alternatives.")
        if method_group["context_id"].nunique() != 1 or oracle_group["context_id"].nunique() != 1:
            raise ValueError("A context number maps to multiple context IDs.")
        if str(method_group["context_id"].iloc[0]) != str(oracle_group["context_id"].iloc[0]):
            raise ValueError("Method and oracle context IDs differ.")
        ids = tuple(oracle_group["alternative_id"].astype(str).tolist())
        if set(method_group["alternative_id"].astype(str)) != set(ids):
            raise ValueError("Method and oracle alternative sets differ.")
        method_by_id = method_group.set_index("alternative_id")["score"]
        scores = np.asarray([method_by_id.loc[item] for item in ids], dtype=float)
        utility = oracle_group["U_star"].to_numpy(dtype=float)
        value = evaluate_context_decision_fidelity(scores, utility, alternative_ids=ids)
        records.append({
            "context_id": str(oracle_group["context_id"].iloc[0]),
            "context_number": int(context_number),
            "method": str(method),
            "method_selected_top1": value.method_ranking.selected_top1,
            "oracle_selected_top1": value.oracle_ranking.selected_top1,
            "kendall_tau_b": np.nan if value.kendall_tau_b is None else value.kendall_tau_b,
            "kendall_tau_b_defined": value.kendall_tau_b_defined,
            "top1_correct": value.top1_correct,
            "normalized_oracle_regret": value.normalized_oracle_regret,
            "oracle_decision_margin": value.oracle_decision_margin,
            "oracle_utility_range": value.oracle_utility_range,
        })
    metrics = pd.DataFrame.from_records(records)
    diagnostics = {
        "evaluation_partition": "test",
        "method_scores_used": True,
        "oracle_U_star_used_for_evaluation": True,
        "target_Y_used": False,
        "model_fit_executed": False,
        "weight_estimation_executed": False,
        "mcdm_executed": False,
        "method_tuning_executed": False,
        "bootstrap_executed": False,
        "results_written": False,
    }
    return DecisionFidelityBatchResult(
        method=str(method),
        context_metrics=metrics,
        summary=_summary(metrics, include_kendall=True),
        diagnostics=diagnostics,
    )


def evaluate_top1_reference_batch(
    predicted_contexts: pd.DataFrame,
    oracle_rows: pd.DataFrame,
    *,
    reference: str,
) -> Top1ReferenceBatchResult:
    """Evaluate an identity-only Top-1 reference without inventing ranks."""
    required = {"context_id", "context_number", "predicted_alternative_id"}
    missing = sorted(required - set(predicted_contexts.columns))
    if missing:
        raise ValueError(f"Top-1 reference rows are missing columns: {missing}.")
    predictions = predicted_contexts.copy()
    if predictions["context_number"].duplicated().any():
        raise ValueError("Top-1 reference must have one prediction per context.")
    oracle = _prepare_oracle_test_rows(oracle_rows)
    if set(predictions["context_number"]) != set(oracle["context_number"]):
        raise ValueError("Top-1 reference and oracle TEST context sets differ.")
    records: list[dict[str, Any]] = []
    for context_number, oracle_group in oracle.groupby("context_number", sort=False):
        prediction = predictions.loc[predictions["context_number"].eq(context_number)].iloc[0]
        if str(prediction["context_id"]) != str(oracle_group["context_id"].iloc[0]):
            raise ValueError("Top-1 reference and oracle context IDs differ.")
        predicted = str(prediction["predicted_alternative_id"])
        if predicted not in ALTERNATIVE_IDS:
            raise ValueError("Predicted alternative is outside A1..A6.")
        ids = tuple(oracle_group["alternative_id"].astype(str).tolist())
        utility = _canonical_values(
            oracle_group["U_star"].to_numpy(dtype=float), ids, label="Oracle U_star"
        )
        if np.any(utility < -EPSILON) or np.any(utility > 1.0 + EPSILON):
            raise ValueError("Oracle U_star escaped the theoretical [0,1] range.")
        oracle_ranking = rank_scores_anchor_ties(utility, ALTERNATIVE_IDS)
        maximum = float(np.max(utility))
        minimum = float(np.min(utility))
        denominator = maximum - minimum + EPSILON
        regret = float((maximum - utility[ALTERNATIVE_IDS.index(predicted)]) / denominator)
        sorted_utility = np.sort(utility)[::-1]
        margin = float((sorted_utility[0] - sorted_utility[1]) / denominator)
        records.append({
            "context_id": str(oracle_group["context_id"].iloc[0]),
            "context_number": int(context_number),
            "reference": str(reference),
            "predicted_top1": predicted,
            "oracle_selected_top1": oracle_ranking.selected_top1,
            "top1_correct": predicted == oracle_ranking.selected_top1,
            "normalized_oracle_regret": float(np.clip(regret, 0.0, 1.0)),
            "oracle_decision_margin": float(np.clip(margin, 0.0, 1.0)),
        })
    metrics = pd.DataFrame.from_records(records)
    diagnostics = {
        "evaluation_partition": "test",
        "identity_only_reference": True,
        "kendall_tau_b_not_computed_without_scores": True,
        "oracle_U_star_used_for_evaluation": True,
        "target_Y_used": False,
        "model_fit_executed": False,
        "weight_estimation_executed": False,
        "mcdm_executed": False,
        "bootstrap_executed": False,
        "results_written": False,
    }
    return Top1ReferenceBatchResult(
        reference=str(reference),
        context_metrics=metrics,
        summary=_summary(metrics, include_kendall=False),
        diagnostics=diagnostics,
    )
