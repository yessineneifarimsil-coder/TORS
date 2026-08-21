from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "historical_family_corrected_eligibility_readjudication_v1.json"

def _p():
    return json.loads(P.read_text(encoding="utf-8"))

def test_readjudication_excludes_old_structural_gate_and_selection():
    p = _p()
    assert p["D29_LRV_NSV_SRE_binary_gate"] is False
    assert p["selection_during_readjudication"] is False
    assert p["ranking_during_readjudication"] is False
    assert p["downstream_outcomes_used"] is False
    assert p["no_parameter_selection"] is True

def test_readjudication_preserves_history_and_handles_v22_conservatively():
    p = _p()
    assert p["historical_status_preserved"] is True
    assert p["no_family_relabeling"] is True
    assert "INSUFFICIENT_FROZEN_EVIDENCE" in p["allowed_statuses"]
    assert "C8-C10" in p["family_specific_rules"]["v2.2"]

def test_readjudication_firewalls():
    p = _p()
    assert p["new_simulation"] is False
    assert p["new_seed_use"] is False
    assert p["D3_execution_paused"] is True
    assert p["reserve_30001_30005_blocked"] is True
    assert p["primary_11001_11030_blocked"] is True
    assert p["external_TEST_blocked"] is True
