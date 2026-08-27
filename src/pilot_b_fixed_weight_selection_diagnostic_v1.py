from __future__ import annotations

"""Pure fixed-weight selection-map reconstruction for the Pilot-B diagnostic.

This module consumes already reconstructed D29 TEST decision matrices and
already archived fixed weight vectors.  It reuses frozen MOORA and decision
metrics, records context-level selections/scores/ranks, reconstructs archived
aggregates, and produces descriptive summaries.  It does not generate data,
fit or query a model, estimate weights, run SHAP/PI, bootstrap, or write files.
"""

from itertools import combinations
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from src import decision_fidelity_metrics_v1 as metrics
from src import moora_topsis_v1 as mcdm


DEVELOPMENT_WORLDS = (21001, 21002, 21003, 21004, 21005)
PRIMARY_SEEDS = tuple(range(11001, 11031))
RESERVE_SEEDS = tuple(range(30001, 30006))
METHODS = (
    "OracleAttribution",
    "SHAP",
    "PermutationImportance",
    "RidgePlus",
    "CRITIC",
    "Entropy",
    "Equal",
)
STRUCTURED_METHODS = METHODS[:-1]
FEATURES = mcdm.FEATURES
ALTERNATIVE_IDS = mcdm.ALTERNATIVE_IDS
EXPECTED_TEST_CONTEXTS = 200
EXPECTED_RECORDS_PER_WORLD = EXPECTED_TEST_CONTEXTS * len(METHODS)
EXPECTED_TOTAL_RECORDS = len(DEVELOPMENT_WORLDS) * EXPECTED_RECORDS_PER_WORLD
AGGREGATE_ATOL = 1.0e-12

CONTEXT_RECORD_FIELDS = (
    "development_world",
    "test_context_id",
    "method",
    "selected_alternative_id",
    "moora_scores_A1_to_A6",
    "moora_ranks_A1_to_A6",
    "oracle_selected_alternative_id",
    "oracle_utilities_A1_to_A6",
    "oracle_ranks_A1_to_A6",
    "top1_match",
    "normalized_oracle_regret_contribution",
    "majority_winner_alternative_id",
    "agrees_with_majority_winner",
)


def _require_development_world(value: int) -> int:
    world = int(value)
    if world not in DEVELOPMENT_WORLDS:
        raise ValueError("Only development worlds 21001--21005 are permitted.")
    if world in PRIMARY_SEEDS or world in RESERVE_SEEDS:
        raise AssertionError("Protected primary/reserve seed reached the diagnostic.")
    return world


def extract_archived_weights(seed_result: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """Extract the six stored vectors plus exact Equal weights without estimation."""
    world = _require_development_world(int(seed_result["replication_seed"]))
    details = seed_result.get("method_details")
    if not isinstance(details, Mapping) or set(details) != set(STRUCTURED_METHODS):
        raise ValueError(f"Archived method details changed for development world {world}.")
    output: dict[str, dict[str, float]] = {}
    for method in STRUCTURED_METHODS:
        detail = details[method]
        if detail.get("weights_defined") is not True:
            raise ValueError(f"Archived {method} weights are undefined in world {world}.")
        if detail.get("equal_fallback_used") is not False:
            raise ValueError(f"Archived {method} used Equal fallback in world {world}.")
        raw = detail.get("weights_by_feature")
        if not isinstance(raw, Mapping):
            raise ValueError(f"Archived {method} weights are missing in world {world}.")
        values = mcdm.coerce_weights(raw)
        output[method] = {
            feature: float(value)
            for feature, value in zip(FEATURES, values, strict=True)
        }
    output["Equal"] = {feature: 0.1 for feature in FEATURES}
    return output


def extract_majority_winner(seed_result: Mapping[str, Any]) -> str:
    """Read the frozen MajorityWinner identity; do not estimate it again."""
    world = _require_development_world(int(seed_result["replication_seed"]))
    references = seed_result.get("reference_details")
    if not isinstance(references, Mapping) or "MajorityWinner" not in references:
        raise ValueError(f"MajorityWinner metadata is missing in world {world}.")
    identity = str(references["MajorityWinner"].get("modal_winner_id"))
    if identity not in ALTERNATIVE_IDS:
        raise ValueError(f"Invalid archived MajorityWinner identity in world {world}.")
    return identity


def _canonical_test(master: pd.DataFrame, *, expected_contexts: int) -> pd.DataFrame:
    required = {
        "context_id", "context_number", "partition", "alternative_id", "U_star", *FEATURES,
    }
    missing = sorted(required - set(master.columns))
    if missing:
        raise ValueError(f"Diagnostic master is missing columns: {missing}.")
    if "Y" in master.columns:
        raise ValueError("Diagnostic master must not contain or generate target Y.")
    test = master.loc[master["partition"].eq("test")].copy()
    test.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    if len(test) != expected_contexts * len(ALTERNATIVE_IDS):
        raise ValueError("Diagnostic TEST row count changed.")
    if test["context_id"].nunique() != expected_contexts:
        raise ValueError("Diagnostic TEST context count changed.")
    counts = test.groupby("context_number", sort=False)["alternative_id"].nunique()
    if not counts.eq(len(ALTERNATIVE_IDS)).all():
        raise ValueError("Each TEST context must contain A1--A6 exactly once.")
    return test


def build_context_records(
    master: pd.DataFrame,
    method_weights: Mapping[str, Mapping[str, float] | Sequence[float] | np.ndarray],
    *,
    development_world: int,
    majority_winner_alternative_id: str,
    expected_contexts: int = EXPECTED_TEST_CONTEXTS,
) -> list[dict[str, Any]]:
    """Reconstruct context-level fixed-vector MOORA decisions and oracle metrics."""
    world = _require_development_world(development_world)
    if tuple(method_weights) != METHODS:
        raise ValueError("Fixed-weight methods or method order changed.")
    majority = str(majority_winner_alternative_id)
    if majority not in ALTERNATIVE_IDS:
        raise ValueError("MajorityWinner identity must be A1--A6.")
    test = _canonical_test(master, expected_contexts=expected_contexts)
    records: list[dict[str, Any]] = []
    for method in METHODS:
        weights = mcdm.coerce_weights(method_weights[method])
        scored = mcdm.score_test_contexts(test, weights, method="MOORA")
        batch = metrics.evaluate_decision_fidelity_batch(
            scored.scored_rows, test, method="MOORA"
        )
        metric_by_number = batch.context_metrics.set_index("context_number", drop=False)
        for context_number, oracle_group in test.groupby("context_number", sort=False):
            score_group = scored.scored_rows.loc[
                scored.scored_rows["context_number"].eq(context_number)
            ].sort_values("alternative_id", kind="stable")
            oracle_group = oracle_group.sort_values("alternative_id", kind="stable")
            if tuple(score_group["alternative_id"].astype(str)) != ALTERNATIVE_IDS:
                raise AssertionError("MOORA alternative order changed.")
            if tuple(oracle_group["alternative_id"].astype(str)) != ALTERNATIVE_IDS:
                raise AssertionError("Oracle alternative order changed.")
            metric = metric_by_number.loc[int(context_number)]
            oracle_utilities = oracle_group["U_star"].to_numpy(dtype=float)
            oracle_ranking = metrics.rank_scores_anchor_ties(
                oracle_utilities, ALTERNATIVE_IDS
            )
            selected = str(metric["method_selected_top1"])
            record = {
                "development_world": world,
                "test_context_id": str(oracle_group["context_id"].iloc[0]),
                "method": method,
                "selected_alternative_id": selected,
                "moora_scores_A1_to_A6": score_group["score"].astype(float).tolist(),
                "moora_ranks_A1_to_A6": score_group["rank"].astype(float).tolist(),
                "oracle_selected_alternative_id": str(metric["oracle_selected_top1"]),
                "oracle_utilities_A1_to_A6": oracle_utilities.astype(float).tolist(),
                "oracle_ranks_A1_to_A6": [
                    float(oracle_ranking.ranks_by_alternative[item])
                    for item in ALTERNATIVE_IDS
                ],
                "top1_match": bool(metric["top1_correct"]),
                "normalized_oracle_regret_contribution": float(
                    metric["normalized_oracle_regret"]
                ),
                "majority_winner_alternative_id": majority,
                "agrees_with_majority_winner": selected == majority,
            }
            if tuple(record) != CONTEXT_RECORD_FIELDS:
                raise AssertionError("Context-record schema or field order changed.")
            records.append(record)
    if len(records) != expected_contexts * len(METHODS):
        raise AssertionError("Context-level diagnostic record count is incomplete.")
    return records


def summarize_context_records(
    records: Sequence[Mapping[str, Any]],
    *,
    development_world: int,
    expected_contexts: int = EXPECTED_TEST_CONTEXTS,
) -> list[dict[str, Any]]:
    """Produce protocol-frozen per-world/method descriptive summaries."""
    world = _require_development_world(development_world)
    output: list[dict[str, Any]] = []
    for method in METHODS:
        selected = [
            row for row in records
            if int(row["development_world"]) == world and row["method"] == method
        ]
        if len(selected) != expected_contexts:
            raise ValueError(f"Expected {expected_contexts} records for {method}.")
        context_ids = [str(row["test_context_id"]) for row in selected]
        if len(set(context_ids)) != expected_contexts:
            raise ValueError(f"Duplicate or missing TEST context for {method}.")
        counts = {
            alternative: sum(
                str(row["selected_alternative_id"]) == alternative for row in selected
            )
            for alternative in ALTERNATIVE_IDS
        }
        maximum = max(counts.values())
        modal = min(item for item, count in counts.items() if count == maximum)
        kendall_values: list[float] = []
        for row in selected:
            value = metrics.kendall_tau_b_from_ranks(
                row["moora_ranks_A1_to_A6"], row["oracle_ranks_A1_to_A6"]
            )
            if value is not None:
                kendall_values.append(float(value))
        output.append({
            "development_world": world,
            "method": method,
            "test_contexts": expected_contexts,
            "selected_alternative_counts_A1_to_A6": counts,
            "number_of_unique_selected_alternatives": sum(count > 0 for count in counts.values()),
            "modal_selected_alternative_id": modal,
            "modal_selected_share": float(maximum / expected_contexts),
            "selection_constant_across_200_contexts": len({
                str(row["selected_alternative_id"]) for row in selected
            }) == 1,
            "agreement_rate_with_majority_winner": float(np.mean([
                bool(row["agrees_with_majority_winner"]) for row in selected
            ])),
            "agreement_with_majority_winner_all_200_contexts": all(
                bool(row["agrees_with_majority_winner"]) for row in selected
            ),
            "mean_kendall_tau_b": (
                float(np.mean(kendall_values)) if kendall_values else None
            ),
            "defined_kendall_context_count": len(kendall_values),
            "top1_accuracy": float(np.mean([
                bool(row["top1_match"]) for row in selected
            ])),
            "mean_normalized_oracle_regret": float(np.mean([
                float(row["normalized_oracle_regret_contribution"]) for row in selected
            ])),
        })
    return output


def pairwise_selection_agreement(
    records: Sequence[Mapping[str, Any]],
    *,
    development_world: int,
    expected_contexts: int = EXPECTED_TEST_CONTEXTS,
) -> list[dict[str, Any]]:
    """Compare argmax selections for every pair of observed archived vectors."""
    world = _require_development_world(development_world)
    maps: dict[str, dict[str, str]] = {}
    for method in METHODS:
        maps[method] = {
            str(row["test_context_id"]): str(row["selected_alternative_id"])
            for row in records
            if int(row["development_world"]) == world and row["method"] == method
        }
        if len(maps[method]) != expected_contexts:
            raise ValueError(f"Incomplete pairwise selection map for {method}.")
    common_ids = set(next(iter(maps.values())))
    if any(set(values) != common_ids for values in maps.values()):
        raise ValueError("Method TEST context identities differ.")
    output: list[dict[str, Any]] = []
    for first, second in combinations(METHODS, 2):
        agreement = [maps[first][key] == maps[second][key] for key in sorted(common_ids)]
        output.append({
            "development_world": world,
            "method_a": first,
            "method_b": second,
            "test_contexts": expected_contexts,
            "selected_alternative_agreement_rate": float(np.mean(agreement)),
            "selected_alternative_agreement_all_200_contexts": all(agreement),
        })
    return output


def _archived_metrics(seed_result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    structured = {
        str(row["method"]): row for row in seed_result["structured_seed_metrics"]
    }
    references = {
        str(row["reference"]): row for row in seed_result["reference_seed_metrics"]
    }
    if set(structured) != set(STRUCTURED_METHODS) or "Equal" not in references:
        raise ValueError("Archived aggregate method set changed.")
    return {**structured, "Equal": references["Equal"]}


def validate_reconstructed_aggregates(
    summaries: Sequence[Mapping[str, Any]],
    seed_result: Mapping[str, Any],
    *,
    absolute_tolerance: float = AGGREGATE_ATOL,
) -> list[dict[str, Any]]:
    """Require exact reconstruction of all archived method-world aggregates."""
    archived = _archived_metrics(seed_result)
    world = _require_development_world(int(seed_result["replication_seed"]))
    if {row["method"] for row in summaries} != set(METHODS):
        raise ValueError("Reconstructed summary method set changed.")
    diagnostics: list[dict[str, Any]] = []
    for summary in summaries:
        method = str(summary["method"])
        reference = archived[method]
        checks = {
            "test_contexts": int(summary["test_contexts"]) == int(reference["test_contexts"]),
            "defined_kendall_context_count": int(summary["defined_kendall_context_count"])
            == int(reference["kendall_defined_contexts"]),
            "mean_kendall_tau_b": np.isclose(
                float(summary["mean_kendall_tau_b"]),
                float(reference["mean_kendall_tau_b"]),
                atol=absolute_tolerance,
                rtol=0.0,
            ),
            "top1_accuracy": np.isclose(
                float(summary["top1_accuracy"]),
                float(reference["top1_accuracy"]),
                atol=absolute_tolerance,
                rtol=0.0,
            ),
            "mean_normalized_oracle_regret": np.isclose(
                float(summary["mean_normalized_oracle_regret"]),
                float(reference["mean_normalized_oracle_regret"]),
                atol=absolute_tolerance,
                rtol=0.0,
            ),
        }
        if not all(checks.values()):
            failed = sorted(key for key, value in checks.items() if not value)
            raise AssertionError(
                f"Archived aggregate reconstruction failed for world {world}, "
                f"method {method}: {failed}"
            )
        diagnostics.append({
            "development_world": world,
            "method": method,
            "absolute_tolerance": float(absolute_tolerance),
            "all_archived_aggregates_match": True,
            "checks": checks,
        })
    return diagnostics
