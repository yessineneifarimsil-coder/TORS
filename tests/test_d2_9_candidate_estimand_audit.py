from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "results" / "d2_9_candidate_estimand_audit" / "audit_summary.json"

def test_estimand_mismatch_is_frozen():
    a = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert a["status"] == "CONFIRMED_METHOD_COMPARABILITY_LIMITATION"
    assert a["historical_results_modified"] is False
    assert a["historical_candidate_adjudications_preserved"] is True
    assert a["profile_ensemble_estimand_match"] is False
    assert a["hard_threshold_direct_comparability"] is False
    assert a["support_mismatch_criteria"] == ["C3", "C5"]

def test_full6_support_and_c3_c5_mismatch_are_distinguished():
    a = json.loads(AUDIT.read_text(encoding="utf-8"))
    s = a["support_by_criterion"]

    for c in ("C1","C2","C4","C6","C7"):
        assert s[c]["active_count"] == 6
        assert s[c]["same_support"] is True
        assert s[c]["v4_possible_permutations"] == 720

    for c in ("C3","C5"):
        assert s[c]["active_count"] == 5
        assert s[c]["same_support"] is False
        assert s[c]["v4_possible_permutations"] == 120
        assert s[c]["v4_support"] == [-1.0,-0.5,0.0,0.5,1.0]
