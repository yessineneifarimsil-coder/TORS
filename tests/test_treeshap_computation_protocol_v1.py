from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
XGB = ROOT / "config" / "xgboost.yaml"
SEEDS = ROOT / "config" / "seeds.yaml"
PROTOCOL = ROOT / "config" / "treeshap_computation_protocol_v1.json"
RESEARCH = ROOT / "docs" / "research_specification.md"
V22 = ROOT / "docs" / "v2_2_design_specification.md"
EXPERIMENT = ROOT / "config" / "experiment.yaml"


def _yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_scientific_xgboost_fit_uses_frozen_model_and_fit_only():
    x = _yaml(XGB)
    c = x["treeshap_computation"]["model_fit"]
    assert c["feature_columns"] == [f"g_C{i}" for i in range(1, 11)]
    assert c["target_column"] == "Y"
    assert c["fit_partition"] == "fit"
    assert c["row_sort_order"] == ["context_number", "alternative_id"]
    assert c["frozen_parameter_source"] == "frozen_parameters"
    assert c["early_stopping"] is False
    assert c["eval_set"] is None
    assert c["weight_partition_used_for_model_fit"] is False
    assert c["external_test_used_for_model_fit"] is False


def test_production_estimator_rng_is_fixed_and_reuses_calibration_rng():
    x = _yaml(XGB)
    s = _yaml(SEEDS)
    c = x["treeshap_computation"]["model_fit"]
    assert s["xgboost_calibration"]["estimator_random_state"] == 82002
    assert s["xgboost_production"]["estimator_random_state"] == 82002
    assert s["xgboost_production"]["reuse_of"] == "xgboost_calibration.estimator_random_state"
    assert c["estimator_random_state"] == 82002
    assert c["reuse_same_estimator_random_state_across_all_fits"] is True


def test_treeshap_api_partition_and_background_contract():
    x = _yaml(XGB)
    c = x["treeshap_computation"]
    assert c["background"]["target_size"] == 100
    assert c["background"]["source_partition"] == "fit"
    assert c["explanation"]["partition"] == "weight"
    assert c["explanation"]["api"] == "shap.TreeExplainer.__call__"
    assert c["explanation"]["values_source"] == "Explanation.values"
    assert c["explanation"]["base_values_source"] == "Explanation.base_values"
    assert c["explanation"]["feature_perturbation"] == "interventional"
    assert c["explanation"]["model_output"] == "raw"
    assert c["explanation"]["external_test_used_for_shap_weight_estimation"] is False


def test_local_accuracy_is_a_hard_numerical_invariant():
    c = _yaml(XGB)["treeshap_computation"]["local_accuracy"]
    assert c["invariant"] is True
    assert c["absolute_tolerance"] == 1.0e-5
    assert c["relative_tolerance"] == 1.0e-5
    assert c["failure_action"] == "raise_numerical_error_and_emit_no_shap_weights"


def test_global_importance_and_zero_sum_policy_are_frozen():
    c = _yaml(XGB)["treeshap_computation"]
    assert c["global_importance"]["definition"] == "mean_absolute_shap"
    assert c["global_importance"]["averaging_unit"] == "WEIGHT_alternative_context_row"
    n = c["weight_normalization"]
    assert n["rule"] == "importance_divided_by_total_importance"
    assert n["epsilon"] == 1.0e-12
    assert n["valid_if_total_importance_strictly_greater_than_epsilon"] is True
    assert n["zero_or_near_zero_policy"] == "undefined_shap_weight_vector"
    assert n["equal_weight_fallback"] is False
    assert n["downstream_shap_mcdm_when_undefined"] == "not_computed"
    assert n["continue_other_methods_when_undefined"] is True


def test_computation_firewalls_are_all_false():
    f = _yaml(XGB)["treeshap_computation"]["firewalls"]
    assert all(value is False for value in f.values())


def test_machine_readable_protocol_matches_yaml_contract():
    p = _json(PROTOCOL)
    assert p["status"] == "FROZEN_BEFORE_FIRST_SCIENTIFIC_SHAP_WEIGHT_VECTOR"
    assert p["model_fit"]["random_state"] == 82002
    assert p["treeshap"]["background_size"] == 100
    assert p["treeshap"]["explanation_partition"] == "weight"
    assert p["local_accuracy"]["absolute_tolerance"] == 1.0e-5
    assert p["global_weight_compression"]["normalization_epsilon"] == 1.0e-12
    assert p["global_weight_compression"]["equal_weight_fallback"] is False
    assert all(value is False for value in p["firewalls"].values())


def test_research_and_v22_document_new_computation_resolution():
    research = RESEARCH.read_text(encoding="utf-8")
    v22 = V22.read_text(encoding="utf-8")
    assert "random_state=82002" in research
    assert "I_+^{SHAP}>10^{-12}" in research
    assert "no equal-weight fallback is allowed" in research
    assert "## 11.4 TreeSHAP scientific computation semantics — RESOLVED" in v22
    assert "**RESOLVED BEFORE FIRST SCIENTIFIC SHAP WEIGHT VECTOR.**" in v22


def test_obsolete_treeshap_calibration_language_is_removed():
    research = RESEARCH.read_text(encoding="utf-8")
    v22 = V22.read_text(encoding="utf-8")
    experiment = _yaml(EXPERIMENT)

    assert (
        "Reassess, select and freeze the TreeSHAP background candidate set/size "
        "on development seeds."
    ) not in research
    assert "- TreeSHAP background candidate set/size;" not in v22
    assert (
        "18. Resolve TreeSHAP background Conflict 3 and freeze the remaining "
        "TreeSHAP scientific computation semantics — **done**."
    ) in v22

    stages = experiment["development"]["stages"]
    assert "treeshap_background_calibration" not in stages
    assert "treeshap_background_protocol_and_computation_freeze" in stages
