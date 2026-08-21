from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "v4_0_f1_terminal_d29_kernel"

def test_v40_terminal_failure_and_firewalls():
    sel = json.loads((RES / "selection.json").read_text(encoding="utf-8"))
    meta = json.loads((RES / "run_metadata.json").read_text(encoding="utf-8"))
    gate = pd.read_csv(RES / "candidate_gate_summary.csv")

    assert sel["candidate_id"] == "d29_kernel"
    assert sel["candidate_passed"] is False
    assert sel["family_failed"] is True
    assert sel["candidate_count"] == 1
    assert sel["parameter_search"] is False
    assert sel["delta"] == 0.05

    assert len(gate) == 1
    row = gate.iloc[0]
    assert bool(row["pass_numerical"]) is True
    assert bool(row["pass_invariants"]) is True
    assert bool(row["pass_scientific_layer_a"]) is False
    assert bool(row["pass_reachability"]) is False
    assert bool(row["all_frozen_gates"]) is False

    assert meta["development_seeds"] == [29001,29002,29003,29004,29005]
    assert meta["signed_profile_namespace"] == 2010
    assert meta["structural_validation_seeds_used"] is False
    assert meta["reserved_seeds_used"] is False
    assert meta["primary_seeds_used"] is False
    assert meta["external_test_used"] is False
    assert meta["layer_b_used_for_selection"] is False

def test_v40_terminal_failure_audit_summary():
    audit = json.loads((RES / "audit_summary.json").read_text(encoding="utf-8"))

    assert audit["status"] == "FAILED_TERMINAL"
    assert audit["candidate_id"] == "d29_kernel"
    assert audit["candidate_passed"] is False
    assert audit["terminal_stop_rule_triggered"] is True
    assert audit["all_numerical_gates_passed"] is True
    assert audit["all_invariant_gates_passed"] is True
    assert audit["structural_validation_seeds_used"] is False

    assert abs(audit["min_layerA_ratio"] - 0.669258332) < 5e-10
    assert audit["layerA_bottleneck"] == "C6"
    assert abs(audit["min_SRE_ratio"] - 0.805299227) < 5e-10
    assert audit["SRE_bottleneck"] == "h_T->C3"
    assert abs(audit["joint_min_ratio"] - 0.669258332) < 5e-10
