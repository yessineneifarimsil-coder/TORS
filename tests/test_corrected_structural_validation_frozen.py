from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "corrected_structural_validation_v1"
FREEZE = ROOT / "config" / "production_response_generator_v1.json"

def test_corrected_validation_success_is_frozen():
    decision = json.loads((RES / "decision.json").read_text(encoding="utf-8"))
    meta = json.loads((RES / "run_metadata.json").read_text(encoding="utf-8"))
    gate = pd.read_csv(RES / "corrected_gate_summary.csv")

    assert decision["candidate_id"] == "d29_kernel"
    assert decision["validation_passed"] is True
    assert decision["production_generator_eligible_for_freeze"] is True
    assert decision["parameter_tuning"] is False
    assert decision["fallback_candidate_selection"] is False
    assert decision["D29_LRV_NSV_SRE_used_for_pass_fail"] is False

    assert meta["structural_validation_seeds"] == [22001,22002,22003,22004,22005]
    assert meta["one_shot"] is True
    assert meta["parameter_tuning_allowed"] is False
    assert meta["D29_ratios_used_for_pass_fail"] is False
    assert meta["external_test_used"] is False
    assert meta["reserve_seeds_used"] is False
    assert meta["primary_seeds_used"] is False

    assert len(gate) == 1
    row = gate.iloc[0]
    assert bool(row["pass_D2_8_numerical_non_degeneracy"]) is True
    assert bool(row["pass_analytic_response_invariants"]) is True
    assert bool(row["pass_C8_C10_invariance"]) is True
    assert bool(row["pass_all_corrected_invariants"]) is True
    assert bool(row["D29_LRV_NSV_SRE_used_for_pass_fail"]) is False
    assert bool(row["validation_passed"]) is True

def test_production_response_generator_freeze():
    f = json.loads(FREEZE.read_text(encoding="utf-8"))

    assert f["status"] == "FROZEN_PRODUCTION_RESPONSE_GENERATOR"
    assert f["candidate_id"] == "d29_kernel"
    assert f["response_formula"] == "theta*o + 0.05*v*o*(1-o)"
    assert f["delta"] == 0.05
    assert f["signed_profile_namespace"] == 2010
    assert f["development_history_preserved"] is True
    assert f["corrected_structural_validation_passed"] is True
    assert f["response_generator_development_closed"] is True
    assert f["d3_unblocked"] is True
    assert f["primary_still_blocked_pending_d3"] is True
    assert f["external_test_still_blocked"] is True
