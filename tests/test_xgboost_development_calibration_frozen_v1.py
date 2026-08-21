from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
XGB = ROOT / "config" / "xgboost.yaml"
RESULT = ROOT / "results" / "xgboost_development_calibration_v1"
FREEZE = RESULT / "freeze_summary.json"

EXPECTED = {
    "n_estimators": 600,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
}


def _xgb():
    return yaml.safe_load(XGB.read_text(encoding="utf-8"))


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_xgboost_frozen_parameters_match_audited_selection():
    cfg = _xgb()
    fp = cfg["frozen_parameters"]
    assert fp["calibrated"] is True
    for key, value in EXPECTED.items():
        assert fp[key] == value


def test_freeze_summary_records_independent_audit_and_candidate_hash():
    f = _freeze()
    assert f["status"] == "FROZEN_XGBOOST_DEVELOPMENT_CALIBRATION"
    assert f["independent_result_audit_status"] == "PASS"
    assert f["candidate_set_sha256"] == "b1c76b23873d6001a60cc78060d5fc4c10686531770558bbd99e125e86e201a9"
    assert f["selected_candidate_id"] == 45
    assert f["selected_parameters"] == EXPECTED


def test_freeze_firewalls_remain_closed():
    f = _freeze()
    for key in [
        "primary_11001_11030_used",
        "reserve_30001_30005_used",
        "weight_rows_used_for_selection",
        "external_test_used_for_signal_sd",
        "external_test_used_for_fit_or_cv",
        "external_test_metrics_computed_or_inspected",
        "SHAP_used_for_selection",
        "MCDM_used_for_selection",
        "winner_identity_used_for_selection",
        "treeSHAP_background_selected",
        "legacy_cached_csvs_used",
    ]:
        assert f[key] is False
    assert f["calibration_executor_must_not_be_rerun"] is True


def test_raw_execution_artifacts_are_preserved():
    expected_files = {
        "candidate_results.csv",
        "selected_candidate_per_seed_oof_rmse.csv",
        "selected_candidate_oof_folds.csv",
        "development_seed_audit.csv",
        "selected_parameters.json",
        "execution_summary.json",
        "summary.txt",
        "freeze_summary.json",
    }
    assert expected_files.issubset({p.name for p in RESULT.iterdir() if p.is_file()})


def test_treeshap_remains_unfrozen_for_next_stage():
    cfg = _xgb()
    bg = cfg["tree_shap"]["background"]
    assert bg["calibrated"] is False
    assert bg["frozen_target_size"] is None
    assert bg["candidate_set_status"] == "reopened_pending_v2_1_reassessment"
    assert bg["candidate_100_now_feasible"] is True
