from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import pilot_b_fixed_weight_selection_diagnostic_v1 as diagnostic


def synthetic_master(contexts: int = 2) -> pd.DataFrame:
    records = []
    for context_number in range(1, contexts + 1):
        for alternative_index, alternative in enumerate(diagnostic.ALTERNATIVE_IDS):
            row = {
                "context_id": f"S21001_C{context_number:04d}",
                "context_number": context_number,
                "partition": "test",
                "alternative_id": alternative,
                "U_star": (alternative_index + context_number) / 10.0,
            }
            for criterion_index, feature in enumerate(diagnostic.FEATURES):
                row[feature] = (
                    0.05
                    + 0.01 * criterion_index
                    + 0.02 * alternative_index
                    + 0.005 * context_number
                )
            records.append(row)
    return pd.DataFrame.from_records(records)


def synthetic_weights():
    return {
        method: {feature: 0.1 for feature in diagnostic.FEATURES}
        for method in diagnostic.METHODS
    }


def fake_seed_result(summaries):
    structured = []
    references = []
    for row in summaries:
        record = {
            "replication_seed": 21001,
            "test_contexts": row["test_contexts"],
            "kendall_defined_contexts": row["defined_kendall_context_count"],
            "mean_kendall_tau_b": row["mean_kendall_tau_b"],
            "top1_accuracy": row["top1_accuracy"],
            "mean_normalized_oracle_regret": row["mean_normalized_oracle_regret"],
        }
        if row["method"] == "Equal":
            record["reference"] = "Equal"
            references.append(record)
        else:
            record["method"] = row["method"]
            record["weights_defined"] = True
            record["equal_fallback_used"] = False
            structured.append(record)
    return {
        "replication_seed": 21001,
        "structured_seed_metrics": structured,
        "reference_seed_metrics": references,
    }


def test_constants_are_exact_and_protected_namespaces_are_disjoint():
    assert diagnostic.DEVELOPMENT_WORLDS == (21001, 21002, 21003, 21004, 21005)
    assert diagnostic.METHODS == (
        "OracleAttribution", "SHAP", "PermutationImportance", "RidgePlus",
        "CRITIC", "Entropy", "Equal",
    )
    assert diagnostic.EXPECTED_TOTAL_RECORDS == 7000
    assert not set(diagnostic.DEVELOPMENT_WORLDS) & (
        set(diagnostic.PRIMARY_SEEDS) | set(diagnostic.RESERVE_SEEDS)
    )


def test_context_record_schema_matches_protocol():
    assert diagnostic.CONTEXT_RECORD_FIELDS == (
        "development_world", "test_context_id", "method",
        "selected_alternative_id", "moora_scores_A1_to_A6",
        "moora_ranks_A1_to_A6", "oracle_selected_alternative_id",
        "oracle_utilities_A1_to_A6", "oracle_ranks_A1_to_A6",
        "top1_match", "normalized_oracle_regret_contribution",
        "majority_winner_alternative_id", "agrees_with_majority_winner",
    )


def test_build_context_records_uses_all_observed_vectors_and_no_target_y():
    records = diagnostic.build_context_records(
        synthetic_master(), synthetic_weights(), development_world=21001,
        majority_winner_alternative_id="A6", expected_contexts=2,
    )
    assert len(records) == 14
    assert [row["method"] for row in records[::2]] == list(diagnostic.METHODS)
    assert all(tuple(row) == diagnostic.CONTEXT_RECORD_FIELDS for row in records)
    assert all(len(row["moora_scores_A1_to_A6"]) == 6 for row in records)
    assert all(len(row["moora_ranks_A1_to_A6"]) == 6 for row in records)
    assert all(len(row["oracle_utilities_A1_to_A6"]) == 6 for row in records)


def test_target_y_is_rejected_even_if_present():
    master = synthetic_master()
    master["Y"] = 0.0
    with pytest.raises(ValueError, match="target Y"):
        diagnostic.build_context_records(
            master, synthetic_weights(), development_world=21001,
            majority_winner_alternative_id="A6", expected_contexts=2,
        )


def test_nondevelopment_and_protected_seed_are_rejected():
    with pytest.raises(ValueError, match="development worlds"):
        diagnostic.build_context_records(
            synthetic_master(), synthetic_weights(), development_world=11001,
            majority_winner_alternative_id="A6", expected_contexts=2,
        )


def test_method_order_is_strict():
    weights = synthetic_weights()
    weights = dict(reversed(list(weights.items())))
    with pytest.raises(ValueError, match="method order"):
        diagnostic.build_context_records(
            synthetic_master(), weights, development_world=21001,
            majority_winner_alternative_id="A6", expected_contexts=2,
        )


def test_summaries_reconstruct_selection_and_full_ranking_separately():
    records = diagnostic.build_context_records(
        synthetic_master(), synthetic_weights(), development_world=21001,
        majority_winner_alternative_id="A6", expected_contexts=2,
    )
    summaries = diagnostic.summarize_context_records(
        records, development_world=21001, expected_contexts=2
    )
    assert len(summaries) == 7
    assert all(row["test_contexts"] == 2 for row in summaries)
    assert all(sum(row["selected_alternative_counts_A1_to_A6"].values()) == 2 for row in summaries)
    assert all(row["defined_kendall_context_count"] == 2 for row in summaries)
    assert all(0.0 <= row["top1_accuracy"] <= 1.0 for row in summaries)


def test_pairwise_agreement_has_twenty_one_method_pairs():
    records = diagnostic.build_context_records(
        synthetic_master(), synthetic_weights(), development_world=21001,
        majority_winner_alternative_id="A6", expected_contexts=2,
    )
    pairs = diagnostic.pairwise_selection_agreement(
        records, development_world=21001, expected_contexts=2
    )
    assert len(pairs) == 21
    assert all(row["selected_alternative_agreement_rate"] == 1.0 for row in pairs)
    assert all(row["selected_alternative_agreement_all_200_contexts"] for row in pairs)


def test_aggregate_validation_matches_and_detects_change():
    records = diagnostic.build_context_records(
        synthetic_master(), synthetic_weights(), development_world=21001,
        majority_winner_alternative_id="A6", expected_contexts=2,
    )
    summaries = diagnostic.summarize_context_records(
        records, development_world=21001, expected_contexts=2
    )
    frozen = fake_seed_result(summaries)
    checks = diagnostic.validate_reconstructed_aggregates(summaries, frozen)
    assert len(checks) == 7
    assert all(row["all_archived_aggregates_match"] for row in checks)
    frozen["structured_seed_metrics"][0]["top1_accuracy"] += 0.01
    with pytest.raises(AssertionError, match="top1_accuracy"):
        diagnostic.validate_reconstructed_aggregates(summaries, frozen)


def test_extract_archived_weights_does_not_estimate_or_substitute():
    details = {}
    for method in diagnostic.STRUCTURED_METHODS:
        details[method] = {
            "weights_defined": True,
            "equal_fallback_used": False,
            "weights_by_feature": {feature: 0.1 for feature in diagnostic.FEATURES},
        }
    frozen = {
        "replication_seed": 21001,
        "method_details": details,
        "reference_details": {"MajorityWinner": {"modal_winner_id": "A2"}},
    }
    weights = diagnostic.extract_archived_weights(frozen)
    assert tuple(weights) == diagnostic.METHODS
    assert weights["Equal"] == {feature: 0.1 for feature in diagnostic.FEATURES}
    assert diagnostic.extract_majority_winner(frozen) == "A2"
    details["SHAP"]["equal_fallback_used"] = True
    with pytest.raises(ValueError, match="fallback"):
        diagnostic.extract_archived_weights(frozen)


def test_differing_full_ranks_do_not_logically_determine_argmax_difference():
    first = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    second = [1.0, 3.0, 2.0, 4.0, 5.0, 6.0]
    first_rank = diagnostic.metrics.rank_scores_anchor_ties(first)
    second_rank = diagnostic.metrics.rank_scores_anchor_ties(second)
    assert first_rank.selected_top1 == second_rank.selected_top1 == "A6"
    assert first_rank.ranks_by_alternative != second_rank.ranks_by_alternative
