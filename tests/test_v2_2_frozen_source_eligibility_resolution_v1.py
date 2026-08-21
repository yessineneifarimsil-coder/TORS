from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "v2_2_frozen_source_eligibility_resolution_v1.json"

def _p():
    return json.loads(P.read_text(encoding="utf-8"))

def test_v22_resolution_uses_contemporaneous_source():
    p = _p()
    assert p["scope"] == ["v2.2"]
    assert p["historical_family_freeze_commit"] == "37c8f31"
    assert p["historical_source_path"] == "src/v2_2_d4_f1_candidate_evaluator.py"
    assert p["source_must_be_read_from_historical_commit"] is True
    assert p["current_worktree_source_not_sufficient_by_itself"] is True

def test_v22_resolution_uses_corrected_eligibility_only():
    p = _p()
    assert p["D29_LRV_NSV_SRE_binary_gate"] is False
    assert p["selection_or_ranking_performed"] is False
    assert p["production_generator_selected"] is False
    assert p["historical_failure_labels_preserved"] is True

def test_v22_resolution_firewalls():
    p = _p()
    assert p["new_simulation"] is False
    assert p["new_seed_use"] is False
    assert p["D3_execution_paused"] is True
    assert p["reserve_30001_30005_blocked"] is True
    assert p["primary_11001_11030_blocked"] is True
    assert p["external_TEST_blocked"] is True
