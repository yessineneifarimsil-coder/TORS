from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "config" / "production_generator_retention_resolution_v1.json"

def _p():
    return json.loads(P.read_text(encoding="utf-8"))

def test_retention_rule_is_nonoptimizing():
    p = _p()
    assert p["eligible_universe_count"] == 54
    assert p["retention_rule_name"] == "minimal_intervention_and_provenance_stability"
    assert p["retention_is_not_superiority_claim"] is True
    assert p["retention_is_not_uniqueness_claim"] is True
    assert p["retention_is_not_statistical_selection"] is True
    assert p["D29_LRV_NSV_SRE_used_for_selection"] is False
    assert p["development_metric_ranking_used_for_selection"] is False

def test_retention_rule_targets_preexisting_frozen_candidate():
    p = _p()
    assert p["preexisting_production_candidate"] == "d29_kernel"
    assert p["preexisting_production_freeze_commit"] == "bd56c2d"
    assert p["corrected_eligibility_nonunique"] is True
    assert p["historical_failures_preserved"] is True

def test_retention_resolution_firewalls():
    p = _p()
    assert p["new_simulation"] is False
    assert p["new_seed_use"] is False
    assert p["D3_execution_paused_during_resolution"] is True
    assert p["reserve_30001_30005_blocked"] is True
    assert p["primary_11001_11030_blocked"] is True
    assert p["external_TEST_blocked"] is True

def test_secondary_robustness_is_mandatory_but_not_selected_here():
    p = _p()
    assert p["mandatory_secondary_robustness_protocol"] is True
    assert "v2.2" in p["secondary_robustness_scope"]
    assert p["secondary_robustness_may_not_change_primary_by_default"] is True
