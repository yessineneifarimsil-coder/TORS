from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "corrected_production_eligibility_v1.json"

def _cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))

def test_corrected_hard_gates_and_d29_role_are_frozen():
    c = _cfg()

    assert c["historical_v40_status_preserved"] is True
    assert c["v40_historical_status"] == "FAILED_TERMINAL"
    assert c["retrospective_readjudication"]["eligible_for_structural_validation"] is True

    assert c["hard_gates"]["d2_8_numerical_non_degeneracy"] is True
    assert c["hard_gates"]["analytic_response_invariants"] is True
    assert c["hard_gates"]["structural_zero_preservation"] is True
    assert c["hard_gates"]["c8_c10_invariance"] is True

    assert c["d29_role"]["binary_eligibility_gate"] is False
    assert c["d29_role"]["continuous_structural_diagnostic"] is True

def test_structural_validation_firewalls_are_frozen():
    c = _cfg()

    assert c["structural_validation"]["seeds"] == [22001,22002,22003,22004,22005]
    assert c["structural_validation"]["one_shot"] is True
    assert c["structural_validation"]["parameter_tuning_allowed"] is False
    assert c["structural_validation"]["external_test_used"] is False
    assert c["structural_validation"]["reserve_used"] is False
    assert c["structural_validation"]["primary_used"] is False
    assert c["structural_validation"]["d29_ratios_used_for_pass_fail"] is False

    assert c["reserve_policy"]["seeds"] == [30001,30002,30003,30004,30005]
    assert c["reserve_policy"]["backup_validation"] is False
    assert c["d3_blocked_until_production_generator_frozen"] is True
