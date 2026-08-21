from pathlib import Path
import json
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "xgboost_development_calibration_v1.json"
XGB = ROOT / "config" / "xgboost.yaml"
SEEDS = ROOT / "config" / "seeds.yaml"


def _p():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_inherits_frozen_xgboost_search_contract():
    p = _p()
    x = yaml.safe_load(XGB.read_text(encoding="utf-8"))
    assert x["development"]["search"]["method"] == "RandomizedSearchCV"
    assert x["development"]["search"]["number_of_candidates"] == 60
    assert x["development"]["cross_validation"]["method"] == "GroupKFold"
    assert x["development"]["cross_validation"]["folds"] == 5
    assert x["development"]["optimization_metric"] == "RMSE"
    assert p["selection"]["scikit_learn_scoring"] == "neg_root_mean_squared_error"


def test_protocol_uses_only_five_development_seeds_and_reference_condition():
    p = _p()
    assert p["development_data"]["replication_seeds"] == [21001,21002,21003,21004,21005]
    assert p["development_data"]["reference_condition"] == {
        "N": 250,
        "c": 0.3,
        "rho": 0.4,
        "lambda": 0.5,
        "alpha_structure": "heterogeneous_fixed",
    }
    assert p["development_data"]["pooled_fit_contexts"] == 1000
    assert p["development_data"]["pooled_fit_rows"] == 6000
    assert p["development_data"]["cached_legacy_csvs_allowed_as_calibration_input"] is False


def test_grouping_and_deterministic_randomness_are_frozen():
    p = _p()
    assert p["pooling_and_cv"]["pool_all_five_development_seeds"] is True
    assert p["pooling_and_cv"]["group_identifier"] == "(replication_seed, context_id)"
    assert p["randomness"]["candidate_sampling_random_state"] == 82001
    assert p["randomness"]["xgboost_estimator_random_state"] == 82002
    text = SEEDS.read_text(encoding="utf-8")
    assert re.search(r"xgboost_calibration:\s*\n\s*search_random_state:\s*82001", text)
    assert re.search(r"estimator_random_state:\s*82002", text)


def test_selection_rule_is_one_shot_and_outcome_independent():
    p = _p()
    s = p["selection"]
    assert s["direction"] == "minimize"
    assert s["primary_statistic"] == "mean_five_fold_grouped_CV_RMSE"
    assert s["second_search_allowed_after_results"] is False
    assert s["performance_gate_for_reopening_search"] is False
    assert s["per_seed_diagnostics_used_for_selection"] is False
    assert s["refit_during_search"] is False


def test_firewalls_exclude_protected_and_downstream_information():
    f = _p()["firewalls"]
    assert f["primary_seeds_11001_11030_used"] is False
    assert f["reserve_seeds_30001_30005_used"] is False
    assert f["external_TEST_used"] is False
    assert f["SHAP_used_for_selection"] is False
    assert f["MCDM_used_for_selection"] is False
    assert f["winner_identity_used_for_selection"] is False
    assert f["preferred_ITS_used_for_selection"] is False
    assert f["treeSHAP_background_selected_here"] is False

def test_full_master_generation_does_not_use_external_test_for_calibration():
    p = _p()
    d = p["development_data"]
    assert d["full_master_contexts_generated_per_seed"] == 1200
    assert d["full_master_rows_generated_per_seed"] == 7200
    assert d["external_TEST_contexts_generated_per_seed"] == 200
    assert d["external_TEST_generated_only_to_preserve_frozen_master_architecture"] is True
    assert d["external_TEST_used_for_signal_sd"] is False
    assert d["external_TEST_used_for_hyperparameter_selection"] is False
    assert d["external_TEST_metrics_computed_during_calibration"] is False
    assert d["external_TEST_inspected_for_calibration_decisions"] is False
    assert p["protocol_synchronization"]["performed_before_any_xgboost_calibration_result"] is True
    assert p["protocol_synchronization"]["scientific_selection_rule_changed"] is False
