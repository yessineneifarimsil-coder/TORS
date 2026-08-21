from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "v2_2_frozen_source_eligibility_resolution_v1"
FREEZE = RES / "freeze_summary.json"


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_v22_frozen_resolution_counts_and_contract():
    a = _freeze()
    assert a["status"] == "FROZEN_V2_2_SOURCE_CONTRACT_ELIGIBILITY_RESOLUTION"
    assert a["historical_family_freeze_commit"] == "37c8f31"
    assert a["historical_source_contract_pass"] is True
    assert a["v2_2_historical_point_count"] == 10
    assert a["v2_2_verified_eligible_by_source_contract_count"] == 10
    assert a["v2_2_unresolved_count"] == 0
    assert a["selection_eligible_universe_count_if_used"] == 54


def test_v22_frozen_resolution_preserves_history_and_selection_firewall():
    a = _freeze()
    assert a["prior_44_10_freeze_rewritten"] is False
    assert a["historical_failure_labels_modified"] is False
    assert a["production_generator_selected"] is False
    assert a["selection_or_ranking_performed"] is False
    assert a["D29_LRV_NSV_SRE_used_for_binary_eligibility"] is False
    assert a["D3_execution_paused"] is True


def test_v22_frozen_resolution_all_points_verified():
    table = pd.read_csv(RES / "v2_2_point_resolution.csv")
    assert len(table) == 10
    assert table["kappa"].astype(float).tolist() == [
        0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0
    ]
    for col in [
        "corrected_numerical_pass",
        "corrected_lower_bound_pass",
        "corrected_upper_bound_pass",
        "corrected_structural_zero_pass",
        "historical_C8_C10_source_contract_pass",
        "corrected_eligible",
    ]:
        vals = table[col].map(
            lambda x: x if isinstance(x, bool)
            else str(x).strip().lower() == "true"
        )
        assert bool(vals.all())
    assert set(table["resolution_status"].astype(str)) == {
        "VERIFIED_ELIGIBLE_BY_FROZEN_SOURCE_CONTRACT"
    }
    assert set(table["historical_status"].astype(str)) == {"FAILED"}


def test_v22_frozen_resolution_firewalls():
    a = _freeze()
    assert a["new_simulation"] is False
    assert a["new_seeds_used"] is False
    assert a["D3_worlds_used"] is False
    assert a["reserve_30001_30005_used"] is False
    assert a["primary_11001_11030_used"] is False
    assert a["external_TEST_used"] is False
