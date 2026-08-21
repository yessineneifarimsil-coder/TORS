from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "d29_hard_gate_validity_audit_v1.json"

def _p():
    return json.loads(P.read_text(encoding="utf-8"))

def test_gate_validity_audit_uses_consumed_data_only():
    p = _p()
    assert p["new_seed_use"] is False
    assert p["analysis_A_matched_profile_ensemble"]["seeds"] == [29001,29002,29003,29004,29005]
    assert p["analysis_B_gate_calibration"]["d2_9_calibration_seeds"] == [25001,25002,25003,25004,25005]
    assert p["analysis_B_gate_calibration"]["new_simulation"] is False
    assert p["reserve_30001_30005_blocked"] is True
    assert p["primary_blocked"] is True
    assert p["external_test_blocked"] is True

def test_d3_sync_is_preserved_but_execution_paused():
    p = _p()
    assert p["d3_protocol_sync_preserved"] is True
    assert p["d3_execution_paused_pending_audit"] is True
    assert p["d3_worlds_observed_before_audit"] is False
    assert p["firewalls"]["no_D3_worlds"] is True

def test_matched_audit_interpretation_is_frozen():
    p = _p()
    a = p["analysis_A_matched_profile_ensemble"]
    assert a["support_equivalent_criteria"] == ["C1","C2","C4","C6","C7"]
    assert a["support_mismatch_criteria"] == ["C3","C5"]
    assert p["predeclared_interpretation"]["no_arbitrary_5pct_or_30pct_cutoff"] is True

def test_audit_firewalls_prevent_result_driven_rescue():
    p = _p()
    f = p["firewalls"]
    assert f["no_D3_worlds"] is True
    assert f["no_30001_30005"] is True
    assert f["no_primary_11001_11030"] is True
    assert f["no_external_TEST"] is True
    assert f["no_new_response_family"] is True
    assert f["no_delta_change"] is True
    assert f["no_threshold_change_during_audit"] is True
    assert f["no_alpha_change"] is True
    assert f["no_SHAP_or_MCDM_or_winner_outcomes"] is True
