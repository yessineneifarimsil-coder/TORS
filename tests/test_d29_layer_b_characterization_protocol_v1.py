from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "d29_layer_b_characterization_v1.json"


def load_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_identity_and_status():
    p = load_protocol()
    assert p["protocol_name"] == "d29_layer_b_characterization_v1"
    assert p["status"] == "freeze_before_characterization_execution"


def test_characterization_is_descriptive_only():
    p = load_protocol()
    assert p["retention_effect"] == "none"
    assert p["can_change_d29_retention"] is False
    assert p["can_change_corrected_eligible_set"] is False
    assert p["can_create_new_generator_gate"] is False
    assert p["pass_fail_thresholds"] is None


def test_exact_development_seed_set():
    p = load_protocol()
    assert p["seeds"]["development"] == [21001, 21002, 21003, 21004, 21005]
    assert p["seeds"]["primary_allowed"] is False
    assert p["seeds"]["reserve_allowed"] is False
    assert p["seeds"]["structural_validation_allowed"] is False


def test_exact_context_and_condition():
    p = load_protocol()
    assert p["contexts"]["pool"] == "estimation_master_fit_plus_weight"
    assert p["contexts"]["n_contexts_per_seed"] == 1000
    assert p["contexts"]["external_test_used"] is False

    c = p["condition"]
    assert c["rho"] == 0.4
    assert c["sigma_x"] == 0.0
    assert c["lambda"] == 0.5
    assert c["target_noise_used"] is False
    assert c["c"] is None
    assert c["N"] == 1000


def test_noise_free_primary_oracle_is_frozen():
    p = load_protocol()["oracle"]
    assert p["utility"] == "noise_free_U_star"
    assert p["alpha_mapping"] == "primary_heterogeneous_fixed"
    assert p["q_transform"] == "normalized_log1p_zeta_2"
    assert p["interaction_graph"] == "frozen_primary_pairwise_graph"


def test_tie_semantics_are_frozen():
    p = load_protocol()["oracle"]
    assert p["winner_tolerance"] == 1e-12
    assert p["ranking_tolerance"] == 1e-12
    assert p["tie_rtol"] == 0.0
    assert (
        p["tie_semantics"]
        == "decision_semantics_v1_anchor_average_ranks_and_true_max_top1"
    )


def test_exact_metric_set():
    p = load_protocol()
    assert p["metrics_per_seed"] == [
        "distinct_complete_oracle_orderings",
        "distinct_deterministic_oracle_winners",
        "modal_oracle_winner_id",
        "modal_oracle_winner_share",
        "modal_baseline_mean_normalized_oracle_regret",
        "modal_baseline_median_normalized_oracle_regret",
        "modal_baseline_p95_normalized_oracle_regret",
        "undefined_normalized_regret_context_count",
    ]
    assert (
        p["ordering_representation"]
        == "tuple_of_anchor_average_ranks_in_A1_to_A6_order"
    )
    assert p["modal_tie_rule"] == "ascending_alternative_id"


def test_regret_semantics_have_no_epsilon_regularization():
    r = load_protocol()["normalized_regret"]
    assert r["denominator"] == "max_a(U_star)-min_a(U_star)"
    assert r["undefined_if_denominator_le"] == 1e-12
    assert r["epsilon_regularization"] is False


def test_cross_seed_summary_cannot_optimize_winner():
    s = load_protocol()["cross_seed_summary"]
    assert s["retain_all_seed_level_results"] is True
    assert s["summary_statistics"] == ["median", "min", "max"]
    assert s["winner_identity_is_not_an_optimization_target"] is True


def test_execution_is_one_shot_and_audited():
    e = load_protocol()["execution"]
    assert e["one_shot"] is True
    assert e["result_overwrite_forbidden"] is True
    assert e["independent_read_only_audit_required_after_execution"] is True


def test_all_firewalls_are_enabled():
    f = load_protocol()["firewalls"]
    assert all(value is True for value in f.values())
