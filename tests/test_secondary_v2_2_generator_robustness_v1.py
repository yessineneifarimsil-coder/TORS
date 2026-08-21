from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "secondary_v2_2_generator_robustness_v1.json"

def _p():
    return json.loads(P.read_text(encoding="utf-8"))

def test_v22_robustness_has_no_kappa_selection():
    p = _p()
    assert p["kappa_grid"] == [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    assert p["kappa_selection_performed"] is False
    assert p["all_kappa_values_mandatory"] is True
    assert p["no_kappa_cherry_picking"] is True
    assert p["hard_robustness_pass_fail_gate"] is False

def test_v22_robustness_is_matched_profile():
    p = _p()
    m = p["matched_profile_design"]
    assert m["enabled"] is True
    assert m["signed_profile_namespace"] == 2010
    assert m["historical_v2_2_namespace_2004_not_used_for_primary_robustness"] is True
    assert p["common_random_numbers"] is True

def test_v22_robustness_reuses_primary_design():
    p = _p()
    assert p["primary_replication_seeds"] == list(range(11001,11031))
    assert p["N_grid"] == [25,50,100,250,1000]
    assert p["rho_grid"] == [0.0,0.4,0.8]
    assert p["reuse_primary_contexts_capability_draws_noise_and_partitions"] is True
    assert p["downstream_rule"]["reuse_frozen_primary_pipeline"] is True
    assert p["downstream_rule"]["no_new_method_tuning_per_kappa"] is True

def test_v22_robustness_cannot_change_d3_or_primary():
    p = _p()
    d3 = p["D3_rule"]
    assert d3["D3_runs_only_on_retained_primary_generator"] is True
    assert d3["v2_2_robustness_cannot_influence_D3"] is True
    assert d3["primary_D3_alpha_mappings_reused_unchanged_in_v2_2_robustness"] is True
    assert d3["no_kappa_specific_D3_recalibration"] is True
    assert p["robustness_outputs_may_replace_primary_generator"] is False
    assert p["robustness_outputs_may_reopen_kappa_selection"] is False

def test_v22_robustness_reserve_and_selection_firewalls():
    p = _p()
    assert p["reserved_seed_rule"]["reserve_30001_30005_used"] is False
    assert p["no_D29_LRV_NSV_SRE_ranking_of_kappa"] is True
    assert p["no_SHAP_or_MCDM_outcome_based_kappa_selection"] is True
    assert p["D3_execution_allowed_after_this_protocol_is_frozen"] is True
