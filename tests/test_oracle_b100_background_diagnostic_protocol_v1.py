from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "oracle_b100_background_diagnostic_v1.json"


def load_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_identity_and_status():
    p = load_protocol()
    assert p["protocol_name"] == "oracle_b100_background_diagnostic_v1"
    assert p["status"] == "freeze_before_any_oracle_b100_diagnostic_result"


def test_primary_oracle_remains_primary_and_unchanged():
    p = load_protocol()["primary_oracle"]
    assert p["remains_primary"] is True
    assert p["can_be_replaced_by_b100"] is False
    assert p["weight_evaluation_partition"] == "weight"
    assert p["undefined_total_importance_threshold"] == 1e-12
    assert p["equal_fallback"] is False


def test_full_fit_row_counts_are_exact():
    counts = load_protocol()["primary_oracle"]["fit_background_rows_by_N"]
    assert counts == {
        "25": 120,
        "50": 240,
        "100": 480,
        "250": 1200,
        "1000": 4800,
    }


def test_b100_uses_exact_frozen_treeshap_membership():
    p = load_protocol()["b100_diagnostic_oracle"]
    assert p["background_size"] == 100
    assert p["background_partition"] == "fit"
    assert p["background_selection_unit"] == "alternative_context_row"
    assert p["background_selector_module"] == "src/treeshap_background_v1.py"
    assert p["selector_function"] == "select_background_rows"
    assert p["row_priority_namespace"] == 83001
    assert p["same_membership_as_treeshap"] is True


def test_only_background_moments_change():
    p = load_protocol()["b100_diagnostic_oracle"]
    assert p["weight_evaluation_partition"] == "weight"
    assert p["weight_evaluation_rows_identical_to_primary_oracle"] is True
    assert p["oracle_formula_identical_to_primary"] is True
    assert p["only_background_moments_change"] is True
    assert p["equal_fallback"] is False


def test_background_membership_reuse_is_frozen():
    p = load_protocol()["b100_diagnostic_oracle"]
    assert p["reuse_membership_across_rho"] is True
    assert p["reuse_membership_across_c"] is True
    assert p["reuse_membership_across_lambda"] is True


def test_scope_and_c_independence():
    s = load_protocol()["comparison_scope"]
    assert s["sample_sizes"] == [25, 50, 100, 250, 1000]
    assert s["rho_levels"] == [0.0, 0.4, 0.8]
    assert s["lambda_levels"] == [0.0, 0.5, 1.0]
    assert s["c_dependence"] == "none"
    assert s["reuse_result_across_c_levels"] is True
    assert s["reserve_seeds_allowed_before_primary"] is False


def test_development_reference_is_prospectively_fixed():
    s = load_protocol()["comparison_scope"]
    assert s["development_reference_allowed"] is True
    assert s["development_reference_seed"] == 21001
    assert s["development_reference_condition"] == {
        "N": 250,
        "rho": 0.4,
        "lambda": 0.5,
    }


def test_exact_vector_metrics():
    m = load_protocol()["metrics"]
    assert m["vector_level"] == [
        "MAE_w",
        "TV_w",
        "max_absolute_weight_difference",
        "Spearman_rho_w",
        "top3_overlap",
        "top5_overlap",
    ]
    assert m["coverage"] == [
        "full_fit_weights_defined",
        "b100_weights_defined",
        "jointly_defined",
    ]


def test_moment_diagnostics_are_frozen():
    m = load_protocol()["metrics"]["moment_level"]
    assert m == [
        "max_absolute_marginal_moment_difference",
        "max_absolute_joint_moment_difference",
    ]


def test_undefined_policy_forbids_equal_fallback():
    u = load_protocol()["undefined_policy"]
    assert u["equal_fallback_forbidden"] is True
    assert u["report_both_defined_flags"] is True
    assert u["do_not_drop_or_redefine_primary_oracle"] is True


def test_diagnostic_is_not_a_new_method_or_tuning_rule():
    i = load_protocol()["interpretation"]
    assert i["not_a_new_weighting_method"] is True
    assert i["not_a_primary_oracle_replacement"] is True
    assert i["not_a_tuning_rule"] is True
    assert i["cannot_change_B_bg"] is True
    assert i["cannot_change_oracle_formula"] is True
    assert i["cannot_change_D29"] is True
    assert i["cannot_change_primary_factorial_design"] is True


def test_all_firewalls_are_false():
    f = load_protocol()["firewalls"]
    assert all(value is False for value in f.values())
