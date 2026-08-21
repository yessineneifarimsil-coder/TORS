from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "v3_1_f1_candidates"

def test_v31_frozen_failure_and_firewalls():
    sel = json.loads((RES / "selection.json").read_text(encoding="utf-8"))
    meta = json.loads((RES / "run_metadata.json").read_text(encoding="utf-8"))
    gate = pd.read_csv(RES / "candidate_gate_summary.csv")

    assert sel["selected_tau"] is None
    assert sel["family_failed"] is True
    assert not bool(gate["all_frozen_gates"].to_numpy(dtype=bool).any())
    assert bool(gate["pass_numerical"].to_numpy(dtype=bool).all())
    assert bool(gate["pass_invariants"].to_numpy(dtype=bool).all())

    assert meta["development_seeds"] == [27001,27002,27003,27004,27005]
    assert meta["structural_validation_seeds_used"] is False
    assert meta["reserved_seeds_used"] is False
    assert meta["primary_seeds_used"] is False
    assert meta["external_test_used"] is False
    assert meta["layer_b_used_for_selection"] is False

def test_v31_frozen_audit_summary():
    a = json.loads((RES / "audit_summary.json").read_text(encoding="utf-8"))
    best = a["best_descriptive_selectable_point"]

    assert a["status"] == "FAILED"
    assert a["selected_tau"] is None
    assert a["all_selectable_points_failed"] is True
    assert a["all_numerical_gates_passed"] is True
    assert a["all_invariant_gates_passed"] is True
    assert a["anchors_excluded_from_selection"] is True

    assert abs(float(best["tau"]) - 0.9) < 1e-12
    assert abs(float(best["joint_min_ratio"]) - 0.942239058) < 5e-10
    assert abs(float(best["min_layerA_ratio"]) - 0.942239058) < 5e-10
    assert best["layerA_bottleneck"] == "C6"
    assert abs(float(best["min_SRE_ratio"]) - 0.994999294) < 5e-10
    assert best["SRE_bottleneck"] == "h_D->C1"
