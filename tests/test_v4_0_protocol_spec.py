from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "v4_0_terminal_d29_kernel_protocol.json"

def _cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))

def test_v40_single_candidate_and_fresh_cohorts_are_frozen():
    c = _cfg()
    assert c["development_seeds"] == [29001,29002,29003,29004,29005]
    assert c["reserve_seeds"] == [30001,30002,30003,30004,30005]
    assert c["structural_validation_seeds"] == [22001,22002,22003,22004,22005]
    assert c["rng_namespace"] == 2010
    assert c["candidate_count"] == 1
    assert c["parameter_search"] is False
    assert c["delta"] == 0.05

def test_v40_firewalls_and_terminal_stop_rule_are_frozen():
    c = _cfg()
    assert c["external_test_used_in_development"] is False
    assert c["scientific_gates"]["layer_b_used_for_selection"] is False
    assert c["scientific_gates"]["winner_identity_used_for_selection"] is False
    assert c["scientific_gates"]["shap_used_for_selection"] is False
    assert c["scientific_gates"]["mcdm_outcomes_used_for_selection"] is False
    assert c["scientific_gates"]["oracle_outcomes_used_for_selection"] is False
    assert "do not tune delta" in c["development_failure_rule"]
    assert "22001-22005" in c["post_development_validation"]
    assert "development stops" in c["validation_failure_rule"]
    assert "not backup validation seeds" in c["reserve_policy"]
