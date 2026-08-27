from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "pilot_b_fixed_weight_selection_diagnostic_v1.json"
DOC_PATH = ROOT / "docs" / "pilot_b_fixed_weight_selection_diagnostic_v1.md"
FROZEN_RESULT_PATH = (
    ROOT
    / "results"
    / "pilot_b_reference_v1"
    / "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
)
EXPECTED_RESULT_SHA256 = (
    "0507285715b0f21d32744da543cd769fc269e12084b6c6819a863fca9f787a88"
)


def load_protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_is_prospective_relative_to_closed_v1():
    p = load_protocol()
    assert p["schema"] == "pilot_b_fixed_weight_selection_diagnostic_protocol_v1"
    assert p["status"] == (
        "FROZEN_PROSPECTIVELY_BEFORE_ANY_FIXED_WEIGHT_SELECTION_DIAGNOSTIC_RESULT"
    )
    assert p["parent_commit"] == "f2f573aad96e1813cfc55938a101fdee18aa7395"
    assert p["closure_tag"] == "pilot-b-v1-hard-stop-f2f573a"


def test_frozen_pilot_b_result_identity_is_guarded():
    p = load_protocol()["frozen_inputs"]
    assert p["result_commit"] == "f2f573aad96e1813cfc55938a101fdee18aa7395"
    assert p["result_path"] == (
        "results/pilot_b_reference_v1/"
        "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
    )
    assert p["result_sha256"] == EXPECTED_RESULT_SHA256
    assert hashlib.sha256(FROZEN_RESULT_PATH.read_bytes()).hexdigest() == EXPECTED_RESULT_SHA256


def test_scope_is_development_only_and_exact():
    s = load_protocol()["scope"]
    assert s["development_worlds"] == [21001, 21002, 21003, 21004, 21005]
    assert s["primary_seeds_used"] is False
    assert s["reserve_seeds_used"] is False
    assert s["reference_condition"] == {"N": 250, "c": 0.3, "rho": 0.4, "lambda": 0.5}
    assert s["evaluation_partition"] == "fixed_external_TEST_only"
    assert s["test_contexts_per_world"] == 200
    assert s["alternatives_per_context"] == 6
    assert s["criteria"] == 10


def test_only_observed_fixed_vectors_are_in_scope():
    s = load_protocol()["scope"]
    assert s["observed_fixed_weight_methods"] == [
        "OracleAttribution", "SHAP", "PermutationImportance", "RidgePlus",
        "CRITIC", "Entropy", "Equal",
    ]
    assert s["constant_reference"] == "MajorityWinner"
    assert s["unobserved_weight_vectors_evaluated"] is False
    assert s["random_weight_draws_evaluated"] is False
    assert load_protocol()["frozen_inputs"]["equal_weight_vector"] == [0.1] * 10


def test_no_learning_or_weight_reestimation_is_allowed():
    r = load_protocol()["reconstruction"]
    assert r["use_archived_method_weights_without_reestimation"] is True
    assert r["target_y_generated"] is False
    assert r["model_fit_executed"] is False
    assert r["model_prediction_executed"] is False
    assert r["oracle_weights_reestimated"] is False
    assert r["shap_executed"] is False
    assert r["permutation_importance_executed"] is False
    assert r["ridge_plus_executed"] is False
    assert r["critic_weights_reestimated"] is False
    assert r["entropy_weights_reestimated"] is False


def test_frozen_moora_and_tie_semantics_are_exact():
    r = load_protocol()["reconstruction"]
    assert r["apply_benefit_oriented_G"] is True
    assert r["apply_common_MOORA_vector_normalization"] is True
    assert r["epsilon"] == 1e-12
    assert r["top1_tie_break"] == "alternative_id_ascending"
    assert r["rank_ties"] == "anchor_based_average_no_chaining"


def test_context_level_artifact_is_complete():
    o = load_protocol()["per_context_output"]
    assert o["one_record_per_world_method_context"] is True
    assert o["required_record_count"] == 7000
    assert o["retain_full_precision"] is True
    assert o["fields"] == [
        "development_world", "test_context_id", "method",
        "selected_alternative_id", "moora_scores_A1_to_A6",
        "moora_ranks_A1_to_A6", "oracle_selected_alternative_id",
        "oracle_utilities_A1_to_A6", "oracle_ranks_A1_to_A6",
        "top1_match", "normalized_oracle_regret_contribution",
        "majority_winner_alternative_id", "agrees_with_majority_winner",
    ]


def test_summary_answers_selection_question_without_a_gate():
    s = load_protocol()["summaries"]
    assert "number_of_unique_selected_alternatives" in s["per_world_method"]
    assert "selection_constant_across_200_contexts" in s["per_world_method"]
    assert "agreement_with_majority_winner_all_200_contexts" in s["per_world_method"]
    assert "selected_alternative_agreement_rate" in s["pairwise_within_world"]
    assert s["no_cross_world_pass_fail_threshold"] is True
    assert s["no_method_ranking_or_selection"] is True


def test_aggregate_reproduction_is_a_prewrite_guard():
    g = load_protocol()["validation_guards"]
    assert g["reconstructed_top1_must_match_frozen_aggregate"] is True
    assert g["reconstructed_mean_regret_must_match_frozen_aggregate"] is True
    assert g["reconstructed_mean_kendall_must_match_frozen_aggregate"] is True
    assert g["aggregate_match_absolute_tolerance"] == 1e-12
    assert g["on_any_guard_failure"] == "abort_without_writing_result"


def test_aggregate_equalities_and_kendall_do_not_identify_argmax_maps():
    i = load_protocol()["interpretation"]
    assert i["aggregate_metric_equality_implies_identical_context_decisions"] is False
    assert i["different_mean_kendall_implies_different_context_argmax"] is False
    assert i["descriptive_only"] is True


def test_claims_are_limited_to_observed_vectors_and_development_worlds():
    i = load_protocol()["interpretation"]
    assert "geometry_of_unobserved_regions_of_the_weight_simplex" in i["cannot_establish"]
    assert "causal_mechanism_for_the_closed_pilot_b_stop" in i["cannot_establish"]
    assert "universal_weight_insensitivity" in i["cannot_establish"]
    assert "performance_of_any_primary_or_reserve_seed" in i["cannot_establish"]


def test_closed_decision_and_protected_seeds_have_no_authority_path():
    a = load_protocol()["decision_authority"]
    assert set(a.values()) == {False}
    f = load_protocol()["firewalls"]
    assert f["frozen_pilot_b_result_modified"] is False
    assert f["frozen_thresholds_modified"] is False
    assert f["protected_seed_namespace_accessed"] is False


def test_bootstrap_is_explicitly_separate_and_not_executed():
    b = load_protocol()["bootstrap_policy"]
    assert b["paired_context_bootstrap_executed_in_this_layer"] is False
    assert b["fresh_TEST_contexts_generated"] is False
    assert b["existing_frozen_TEST_contexts_resampled"] is False
    assert "separate_prospectively_frozen_protocol" in b["reason"]


def test_execution_requires_commit_explicit_flag_and_no_overwrite():
    e = load_protocol()["execution_policy"]
    assert e["implementation_requires_separate_commit"] is True
    assert e["executor_requires_explicit_execute_flag"] is True
    assert e["executor_requires_clean_committed_state"] is True
    assert e["result_overwrite_forbidden"] is True
    assert e["independent_read_only_result_audit_required"] is True
    assert e["result_requires_separate_freeze_commit"] is True


def test_document_discloses_post_hoc_status_and_boundaries():
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    for token in [
        "post-hoc, development-only", "cannot alter the Pilot-B result",
        "does not prove equality of context-level choices",
        "do not prove that context-level argmax choices differ",
        "Exactly 7000 records", "No pass/fail threshold",
        "paired context bootstrap is not part of this layer",
        "unobserved regions of the weight simplex",
    ]:
        assert token in normalized_text
