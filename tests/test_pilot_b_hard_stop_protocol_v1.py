from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "pilot_b_hard_stop_protocol_v1.json"
DOC_PATH = ROOT / "docs" / "pilot_b_hard_stop_protocol_v1.md"


def load():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_status_is_prospective_and_parent_is_stagewise_commit():
    p = load()
    assert p["schema"] == "pilot_b_hard_stop_protocol_v1"
    assert p["status"] == "FROZEN_PROSPECTIVELY_BEFORE_ANY_PILOT_B_RESULT"
    assert p["parent_commit"] == "c2d557957f0110d7a0c1be6a9b157a8f8ca795f3"


def test_reference_scope_uses_only_five_development_seeds():
    s = load()["scope"]
    assert s["development_seeds"] == [21001, 21002, 21003, 21004, 21005]
    assert s["primary_seeds_used"] is False
    assert s["reserve_seeds_used"] is False
    assert s["reference_condition"] == {"N": 250, "c": 0.3, "rho": 0.4, "lambda": 0.5}
    assert s["evaluation_partition"] == "fixed_external_test"
    assert s["test_contexts_per_seed"] == 200
    assert s["pooled_seed_contexts"] == 1000
    assert s["primary_mcdm"] == "MOORA"
    assert s["topsis_used_for_hard_stop"] is False


def test_random_reference_is_exactly_frozen():
    s = load()["scope"]
    assert s["random_weight_draws_per_seed"] == 200
    assert s["random_weight_distribution"] == "Dirichlet(1,...,1)"
    assert s["random_weight_master_seed"] == 81001


def test_structured_gate_methods_exclude_diagnostic_references():
    roles = load()["method_roles"]
    assert roles["structured_gate_methods"] == [
        "OracleAttribution", "SHAP", "PermutationImportance",
        "RidgePlus", "CRITIC", "Entropy",
    ]
    assert roles["reported_not_allowed_to_clear_structured_gate"] == [
        "Equal", "RandomWeights", "MajorityWinner", "DirectXGBoost",
    ]
    assert set(roles["structured_gate_methods"]).isdisjoint(
        roles["reported_not_allowed_to_clear_structured_gate"]
    )


def test_cross_seed_rule_and_quantiles_are_frozen():
    a = load()["aggregation"]
    assert a["random_reference_center"] == "median_over_200_random_weight_vectors_within_seed"
    assert a["random_width"] == "p95_minus_p05_over_200_random_weight_vectors_within_seed"
    assert a["quantile_method"] == "linear"
    assert a["cross_seed_center"] == "median_over_five_development_seeds"
    assert a["positive_seed_rule"] == "strictly_greater_than_zero"
    assert a["consistent_seed_count_required"] == 4


def test_coverage_is_strict_and_undefined_is_not_substituted():
    c = load()["coverage"]
    assert c["required_development_seed_count"] == 5
    assert c["required_test_contexts_per_seed"] == 200
    assert c["required_random_draws_per_seed"] == 200
    assert c["minimum_kendall_defined_context_fraction"] == 0.95
    assert c["minimum_kendall_defined_contexts_per_200"] == 190
    assert c["minimum_eligible_random_draws_per_seed"] == 190
    assert "no_equal_fallback_used_in_any_seed" in c["structured_method_eligible_only_if"]
    assert c["incomplete_required_output_policy"] == "cannot_pass_pilot_B"


def test_advantage_orientations_all_favor_structured_method():
    d = load()["derived_advantages"]
    assert d["structured_vs_random_kendall"].startswith("structured_mean_tau_b_minus")
    assert d["structured_vs_random_regret"].startswith("within_seed_random_median_mean_regret_minus")
    assert d["structured_vs_modal_top1"].startswith("structured_top1_accuracy_minus")
    assert d["structured_vs_modal_regret"].startswith("modal_winner_mean_regret_minus")
    assert d["positive_values_favor_structured_method"] is True


def test_random_separation_gate_has_effect_sizes_and_four_of_five_consistency():
    gate = load()["gates"]["random_equivalence_hard_stop"]
    rule = gate["method_separates_random_if"]
    assert rule["logic"] == "OR"
    assert rule["kendall_clause"] == {
        "cross_seed_median_advantage_at_least": 0.05,
        "strictly_positive_advantage_seed_count_at_least": 4,
    }
    assert rule["regret_clause"] == {
        "cross_seed_median_advantage_at_least": 0.01,
        "strictly_positive_advantage_seed_count_at_least": 4,
    }
    assert gate["hard_stop_if"] == "no_structured_gate_method_separates_random"
    assert gate["failure_to_reject_null_used_as_equivalence"] is False


def test_modal_escape_gate_is_numerically_frozen():
    gate = load()["gates"]["modal_winner_effective_tie_hard_stop"]
    rule = gate["method_escapes_modal_if"]
    assert rule["logic"] == "OR"
    assert rule["top1_clause"]["cross_seed_median_advantage_at_least"] == 0.02
    assert rule["regret_clause"]["cross_seed_median_advantage_at_least"] == 0.01
    assert rule["top1_clause"]["strictly_positive_advantage_seed_count_at_least"] == 4
    assert rule["regret_clause"]["strictly_positive_advantage_seed_count_at_least"] == 4


def test_dominance_gate_is_pooled_and_ninety_percent():
    gate = load()["gates"]["oracle_winner_dominance_hard_stop"]
    assert gate["unit"] == "pooled_1000_external_test_contexts_across_five_seeds"
    assert gate["tie_break"] == "alternative_id_ascending"
    assert gate["hard_stop_if_pooled_modal_share_at_least"] == 0.90


def test_weight_insensitivity_has_context_and_width_clauses():
    gate = load()["gates"]["weight_insensitivity_hard_stop"]
    context = gate["context_invariance_clause"]
    assert context["random_draw_top1_modal_share_within_context_at_least"] == 0.95
    assert context["pooled_fraction_of_invariant_seed_contexts_at_least"] == 0.90
    width = gate["performance_width_clause"]
    assert width["within_seed_random_kendall_p95_minus_p05_at_most"] == 0.05
    assert width["within_seed_random_top1_p95_minus_p05_at_most"] == 0.02
    assert width["within_seed_random_mean_regret_p95_minus_p05_at_most"] == 0.01
    assert width["all_three_width_conditions_required_within_seed"] is True
    assert width["seed_count_at_least"] == 4
    assert gate["hard_stop_logic"] == "context_invariance_clause_OR_performance_width_clause"


def test_overall_gate_is_or_and_every_flag_must_be_false_to_pass():
    o = load()["overall_decision"]
    assert o["hard_stop_logic"] == "OR_across_all_five_hard_stop_gates"
    assert o["pass_requires_all_hard_stop_flags_false"] is True
    assert o["on_hard_stop"]["run_primary_factorial"] is False
    assert o["on_hard_stop"]["revise_using_development_data_only"] is True
    assert o["on_hard_stop"]["create_new_specification_version"] is True
    assert o["on_hard_stop"]["create_new_git_tag_before_retry"] is True


def test_firewalls_are_closed_before_pilot_B():
    f = load()["firewalls"]
    assert f == {
        "pilot_B_results_inspected_before_threshold_freeze": False,
        "primary_seed_results_used": False,
        "reserve_seed_results_used": False,
        "preferred_method_used_to_choose_thresholds": False,
        "preferred_ITS_identity_used_to_choose_thresholds": False,
        "thresholds_may_change_after_pilot_B_execution": False,
    }


def test_existing_frozen_protocol_still_requires_prospective_thresholds():
    existing = json.loads(
        (ROOT / "config" / "weighting_mcdm_protocol_v1.json").read_text(encoding="utf-8")
    )
    marker = existing["diagnostic_references"]["pilot_B_thresholds"]
    assert marker["frozen_in_this_protocol"] is False
    assert marker["must_be_frozen_before_pilot_B_execution"] is True
    assert marker["may_not_be_chosen_after_inspecting_pilot_B_results"] is True


def test_experiment_still_declares_pilot_B_prerequisites_and_hard_stop():
    experiment = yaml.safe_load(
        (ROOT / "config" / "experiment.yaml").read_text(encoding="utf-8")
    )
    pilot = experiment["development"]["pilot_B"]
    assert pilot["requires_frozen_xgboost"] is True
    assert pilot["requires_weighting_methods"] is True
    assert pilot["requires_decision_operators"] is True
    assert pilot["requires_decision_metrics"] is True
    assert pilot["on_hard_stop"]["run_primary_factorial"] is False


def test_document_states_all_numeric_boundaries_and_noncausal_purpose():
    text = DOC_PATH.read_text(encoding="utf-8")
    for token in [
        "0.05", "0.01", "0.02", "0.90", "0.95", "four of five",
        "not method selection", "Thresholds may not change",
    ]:
        assert token in text
