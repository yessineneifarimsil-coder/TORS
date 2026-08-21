from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "d29_hard_gate_validity_audit_v1"
AUDIT = RES / "audit_summary.json"


def _audit():
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def test_frozen_gate_validity_audit_core_results():
    a = _audit()
    assert a["status"] == "FROZEN_POST_V4_D29_HARD_GATE_VALIDITY_AUDIT"
    assert a["analysis_A"]["profile_ensemble_mismatch_fully_explains_old_v4_failure"] is False
    assert a["analysis_A"]["profile_ensemble_mismatch_does_not_fully_explain_old_v4_failure"] is True
    assert a["analysis_A"]["unresolved_support_equivalent_layerA_criteria"] == ["C1","C4","C6","C7"]
    assert a["analysis_A"]["unresolved_support_equivalent_reachability_pathways"] == ["h_D->C1","h_D->C4","h_I->C4"]

    b = a["analysis_B"]
    assert b["pseudo_candidate_count"] == 7776
    assert b["layerA_joint_pass_count"] == 0
    assert b["reachability_joint_pass_count"] == 0
    assert b["overall_joint_pass_count"] == 0
    assert b["conditional_acceptance_region_empty_in_7776"] is True
    assert b["maximum_minimum_normalized_ratio"] < 1.0


def test_frozen_audit_firewalls_and_interpretation():
    a = _audit()
    f = a["firewalls"]
    assert f["new_seeds_used"] is False
    assert f["D3_worlds_used"] is False
    assert f["reserve_30001_30005_used"] is False
    assert f["primary_11001_11030_used"] is False
    assert f["external_TEST_used"] is False
    assert f["thresholds_changed"] is False
    assert f["response_formula_changed"] is False

    assert a["interpretation"]["profile_ensemble_mismatch_alone_is_sufficient_explanation"] is False
    assert a["interpretation"]["old_simultaneous_joint_gate_supported_as_binary_eligibility_rule"] is False
    assert a["interpretation"]["D29_references_retained_as_continuous_diagnostics"] is True
    assert a["next_step"]["historical_family_corrected_eligibility_readjudication_required"] is True
    assert a["next_step"]["D3_execution_paused"] is True


def test_result_files_reproduce_zero_joint_pass():
    pseudo = pd.read_csv(RES / "analysis_B_pseudo_candidate_joint_results.csv")
    assert len(pseudo) == 7776
    assert int(pseudo["layerA_joint_pass"].astype(bool).sum()) == 0
    assert int(pseudo["reachability_joint_pass"].astype(bool).sum()) == 0
    assert int(pseudo["overall_joint_pass"].astype(bool).sum()) == 0
    assert float(pseudo["min_normalized_ratio"].max()) < 1.0
