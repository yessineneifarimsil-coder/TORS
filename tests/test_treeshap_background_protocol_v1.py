from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
XGB = ROOT / "config" / "xgboost.yaml"
SEEDS = ROOT / "config" / "seeds.yaml"
PROTOCOL = ROOT / "config" / "treeshap_background_protocol_v1.json"


def _yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_primary_background_is_frozen_at_100_before_results():
    bg = _yaml(XGB)["tree_shap"]["background"]
    assert bg["calibrated"] is True
    assert bg["calibration_mode"] == "prospective_fixed_choice_without_outcome_tuning"
    assert bg["frozen_target_size"] == 100
    assert bg["candidate_sizes"] == [25, 50, 75, 100]
    assert bg["sensitivity_sizes_are_non_decision"] is True


def test_binding_smallest_N_feasibility_is_explicit():
    bg = _yaml(XGB)["tree_shap"]["background"]
    f = bg["feasibility"]
    assert f["fit_contexts_at_smallest_primary_sample"] == 20
    assert f["alternatives_per_context"] == 6
    assert f["available_fit_rows_at_smallest_primary_sample"] == 120
    assert bg["frozen_target_size"] <= f["available_fit_rows_at_smallest_primary_sample"]
    assert bg["if_target_exceeds_available_rows"]["rule"] == "raise_error"


def test_treeshap_semantics_and_partition_firewall():
    x = _yaml(XGB)
    assert x["tree_shap"]["feature_perturbation"] == "interventional"
    assert x["tree_shap"]["model_output"] == "raw"
    assert x["tree_shap"]["background"]["source_partition"] == "fit"
    assert x["tree_shap"]["background"]["selection"] == "random_without_replacement"
    assert x["tree_shap"]["explanation_partition"] == "weight"


def test_dedicated_background_seed_namespace_is_frozen():
    s = _yaml(SEEDS)
    assert s["treeshap_background"]["row_priority_namespace"] == 83001


def test_background_membership_is_outcome_independent():
    rp = _yaml(XGB)["tree_shap"]["background"]["row_priority"]
    assert rp["reuse_priority_across_rho"] is True
    assert rp["reuse_priority_across_c"] is True
    assert rp["reuse_priority_across_lambda"] is True
    assert rp["depends_on_feature_values"] is False
    assert rp["depends_on_target_values"] is False
    assert rp["depends_on_oracle_values"] is False
    assert rp["depends_on_method_outcomes"] is False


def test_protocol_records_historical_gap_and_firewalls():
    p = _protocol()
    assert p["status"] == "FROZEN_BEFORE_ANY_TREESHAP_BACKGROUND_SIZE_RESULT"
    assert p["historical_audit"]["historical_selection_metric_found"] is False
    assert p["historical_audit"]["historical_background_rng_rule_found"] is False
    assert p["resolution"]["frozen_background_size"] == 100
    assert p["resolution"]["sensitivity_sizes_can_change_primary_background_size"] is False
    assert all(v is False for v in p["firewalls"].values())
