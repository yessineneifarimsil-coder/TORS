from __future__ import annotations

import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "weighting_mcdm_protocol_v1.json"


def load_protocol():
    return json.loads(P.read_text(encoding="utf-8"))


def test_protocol_status_and_parent():
    p = load_protocol()
    assert p["status"] == "FROZEN_BEFORE_WEIGHTING_MCDM_IMPLEMENTATION_AND_PILOT_B"
    assert p["parent_commit"] == "d168988b3e514f5ab8cb920caedd1f9556a053e1"


def test_common_tie_and_epsilon_contract():
    p = load_protocol()
    c = p["common"]
    assert c["features"] == [f"g_C{i}" for i in range(1, 11)]
    assert c["epsilon"] == 1e-12
    assert c["score_tie_absolute_tolerance"] == 1e-12
    assert c["score_tie_relative_tolerance"] == 0.0
    assert c["rank_ties"] == "average_ranks"
    assert "tie-group anchor" in c["tie_grouping_rule"]
    assert "Do not chain" in c["tie_grouping_rule"]
    assert c["top1_tie_set_rule"].startswith("Form the top tie set")
    assert c["top1_tie_break"] == "alternative_id_ascending"


def test_oracle_zero_sum_is_undefined_without_equal_fallback():
    o = load_protocol()["oracle_attribution"]
    assert o["zero_or_near_zero_total_rule"] == "undefined_oracle_attribution_weight_vector"
    assert o["equal_weight_fallback"] is False
    assert o["continue_other_methods_when_undefined"] is True
    assert o["oracle_weight_mcdm_when_undefined"] is False


def test_pi_has_dedicated_seed_and_common_derangements():
    p = load_protocol()["permutation_importance"]
    assert p["master_seed"] == 84001
    assert p["repeats"] == 20
    assert p["scheme"] == "derangement"
    assert p["same_20_derangements_reused_across_all_criteria"] is True
    assert p["reuse_across_rho"] is True
    assert p["reuse_across_c"] is True
    assert p["reuse_across_lambda"] is True
    assert p["separate_deterministic_derangement_set_per_N"] is True
    d = p["derangement_generation"]
    assert d["context_order"] == "context_number_ascending"
    assert d["candidate_draw"] == "perm = rng.permutation(m)"
    assert "perm[d] != d" in d["acceptance_rule"]
    assert "destination context position d" in d["mapping_direction"]
    assert d["accepted_derangements_required"] == 20
    assert d["max_candidate_draws"] == 100000
    assert d["on_failure"] == "raise_RuntimeError_no_fallback_no_result"
    assert p["all_nonpositive_fallback"] == "equal_weights"
    assert p["sd_ddof"] == 1


def test_ridge_contract_closes_standardization_solver_and_ties():
    r = load_protocol()["ridge_plus"]
    assert r["intercept"] == "none_in_standardized_space"
    assert r["solver"] == "scipy.optimize.nnls_on_L2_augmented_design"
    assert r["standardization"]["ddof"] == 0
    assert r["standardization"]["statistics_fit_within_each_cv_training_fold"] is True
    assert r["cv"]["shuffle"] is False
    assert r["cv"]["metric"] == "RMSE_on_original_Y_scale"
    assert r["cv"]["tie_break"] == "smallest_tau"
    assert r["candidate_tau"] == [0.0001,0.001,0.01,0.1,1.0,10.0,100.0]


def test_critic_entropy_contract_closes_numerics():
    p = load_protocol()
    c = p["critic"]
    e = p["entropy"]
    assert c["standard_deviation_ddof"] == 0
    assert c["constant_columns_in_conflict_sum"] == "excluded"
    assert c["all_zero_information_fallback"] == "equal_weights"
    assert e["n_definition"] == "number_of_alternative_context_rows_in_weight_partition"
    assert e["zero_log_zero"] is True
    assert e["all_zero_diversification_fallback"] == "equal_weights"


def test_random_reference_seed_rule():
    r = load_protocol()["random_dirichlet"]
    assert r["master_seed"] == 81001
    assert r["draws_per_replication"] == 200
    assert r["reuse_same_200_vectors_across_N_rho_c_lambda_for_seed"] is True


def test_moora_and_topsis_are_fully_determined():
    p = load_protocol()
    m = p["moora"]
    t = p["topsis"]
    assert m["role"] == "primary_mcdm"
    assert m["ranking"] == "descending_score"
    assert t["role"] == "robustness_mcdm"
    assert t["positive_ideal"] == "columnwise_max_over_alternatives"
    assert t["negative_ideal"] == "columnwise_min_over_alternatives"
    assert t["distance"] == "Euclidean"
    assert t["closeness"] == "D_minus/(D_plus+D_minus)"
    assert t["zero_distance_sum_rule"] == "closeness_equals_0.5_for_all_tied_alternatives"


def test_existing_configs_are_consistent_with_protocol():
    p = load_protocol()
    xgb = yaml.safe_load((ROOT / "config" / "xgboost.yaml").read_text(encoding="utf-8"))
    benchmark = yaml.safe_load((ROOT / "config" / "benchmark.yaml").read_text(encoding="utf-8"))
    experiment = yaml.safe_load((ROOT / "config" / "experiment.yaml").read_text(encoding="utf-8"))
    seeds = yaml.safe_load((ROOT / "config" / "seeds.yaml").read_text(encoding="utf-8"))

    pi = xgb["permutation_importance"]
    assert pi["loss"] == p["permutation_importance"]["loss"]
    assert pi["repeats"] == p["permutation_importance"]["repeats"]
    assert pi["permutation_scheme"] == p["permutation_importance"]["scheme"]
    assert pi["negative_importance"]["rule"] == "truncate_to_zero"

    ridge = xgb["ridge_plus"]
    assert ridge["data_partition"] == p["ridge_plus"]["partition"]
    assert ridge["coefficient_constraint"] == p["ridge_plus"]["coefficient_constraint"]
    assert ridge["regularization_selection"]["candidate_tau"] == p["ridge_plus"]["candidate_tau"]

    assert benchmark["objective_weighting"]["CRITIC"]["preprocessing"] == "minmax"
    assert benchmark["objective_weighting"]["Entropy"]["preprocessing"] == "minmax"
    assert experiment["mcdm"]["primary"] == "MOORA"
    assert "TOPSIS" in experiment["mcdm"]["robustness"]
    assert experiment["decision_metrics"]["kendall_variant"] == "tau_b"
    assert seeds["random_weight_reference"]["master_seed"] == 81001
    assert seeds["permutation_importance"]["master_seed"] == 84001
    seed_rule = seeds["permutation_importance"]["rule"]
    assert "perm=rng.permutation(m)" in seed_rule
    assert "100000 candidate draws" in seed_rule
    assert "destination context position d" in seed_rule


def test_firewall_is_closed():
    f = load_protocol()["principle"]
    assert f["rules_may_not_be_changed_using_observed_SHAP_weights"] is True
    assert f["rules_may_not_be_changed_using_winner_identity"] is True
    assert f["primary_or_reserve_results_used_to_set_rules"] is False
    assert f["external_test_used_to_estimate_weights_or_tune_methods"] is False

def test_stagewise_ladder_is_explicit_and_matches_experiment():
    p = load_protocol()
    experiment = yaml.safe_load(
        (ROOT / "config" / "experiment.yaml").read_text(encoding="utf-8")
    )
    expected = [
        "OracleUtility",
        "OracleMainEffectReference",
        "OracleGlobalAttributionNonlinearQ",
        "SHAPGlobalAttributionNonlinearQ",
        "OracleGlobalAttributionLinearG",
        "SHAPGlobalAttributionLinearG",
        "OracleWeightMOORA",
        "SHAPWeightMOORA",
        "DirectXGBoost",
    ]
    assert p["stagewise_fidelity"]["stages"] == expected
    assert experiment["stagewise_fidelity"]["stages"] == expected
    assert p["stagewise_fidelity"]["claim_additive_error_decomposition"] is False


def test_pilot_b_diagnostic_references_are_explicit_prerequisites():
    d = load_protocol()["diagnostic_references"]
    assert d["DirectXGBoost"]["required_before_pilot_B"] is True
    assert d["RandomWeights"]["required_before_pilot_B"] is True
    assert d["MajorityWinner"]["required_before_pilot_B"] is True
    assert d["RandomWeights"]["draws"] == 200
    assert d["pilot_B_thresholds"]["frozen_in_this_protocol"] is False
    assert d["pilot_B_thresholds"]["must_be_frozen_before_pilot_B_execution"] is True
    assert d["pilot_B_thresholds"]["may_not_be_chosen_after_inspecting_pilot_B_results"] is True
