from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "historical_family_corrected_eligibility_readjudication_v1"
AUDIT = RES / "freeze_summary.json"


def _audit():
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def test_frozen_readjudication_counts_and_families():
    a = _audit()
    assert a["status"] == "FROZEN_NONSELECTIVE_CORRECTED_ELIGIBILITY_READJUDICATION"
    assert a["total_historical_points"] == 54
    assert a["verified_eligible_count"] == 44
    assert a["verified_ineligible_count"] == 0
    assert a["insufficient_frozen_evidence_count"] == 10
    assert a["verified_eligible_families"] == ["v2.3","v2.4","v2.5","v3.0","v3.1","v4.0"]
    assert a["insufficient_evidence_families"] == ["v2.2"]


def test_frozen_readjudication_preserves_history_and_has_no_selection():
    a = _audit()
    assert a["historical_statuses_modified"] is False
    assert a["production_generator_selected"] is False
    assert a["selection_or_ranking_performed"] is False
    assert a["D29_LRV_NSV_SRE_used_for_binary_eligibility"] is False
    assert a["separate_selection_protocol_required"] is True
    assert a["D3_execution_paused"] is True


def test_frozen_eligible_table_all_corrected_gates_true():
    eligible = pd.read_csv(RES / "verified_eligible_points.csv")
    assert len(eligible) == 44
    for col in [
        "corrected_numerical_pass",
        "corrected_boundary_invariants_pass",
        "corrected_structural_zero_pass",
        "corrected_C8_C10_pass",
        "frozen_evidence_complete",
        "corrected_eligible",
    ]:
        vals = eligible[col].map(
            lambda x: x if isinstance(x, bool)
            else str(x).strip().lower() == "true"
        )
        assert bool(vals.all())


def test_v22_remains_insufficient_not_reclassified():
    insufficient = pd.read_csv(RES / "insufficient_evidence_points.csv")
    assert len(insufficient) == 10
    assert set(insufficient["family"].astype(str)) == {"v2.2"}
    assert insufficient["corrected_C8_C10_pass"].isna().all()
    assert set(insufficient["readjudication_status"].astype(str)) == {
        "INSUFFICIENT_FROZEN_EVIDENCE"
    }
