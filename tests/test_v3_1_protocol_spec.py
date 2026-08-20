from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "v3_1_interpolated_monotone_shape_protocol.json"

def _cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))

def test_v31_prospective_cohorts_and_grid_are_frozen():
    c = _cfg()
    assert c["development_seeds"] == [27001,27002,27003,27004,27005]
    assert c["reserve_seeds"] == [28001,28002,28003,28004,28005]
    assert c["structural_validation_seeds"] == [22001,22002,22003,22004,22005]
    assert c["rng_namespace"] == 2009
    assert c["candidate_tau_grid"] == [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
    assert c["descriptive_anchor_tau"] == [0.0,1.0]
    assert c["anchors_selectable"] is False

def test_v31_selection_firewalls_and_stop_rules():
    c = _cfg()
    assert c["external_test_used_in_development"] is False
    assert c["scientific_gates"]["layer_b_used_for_selection"] is False
    assert c["scientific_gates"]["winner_identity_used_for_selection"] is False
    assert c["scientific_gates"]["mcdm_outcomes_used_for_selection"] is False
    assert "minimum tau" in c["selection_rule"]
    assert "do not refine" in c["failure_rule"]
    assert "22001-22005" in c["post_selection_validation"]
    assert "do not fall back" in c["validation_failure_rule"]
    assert "not backup validation seeds" in c["reserve_policy"]
