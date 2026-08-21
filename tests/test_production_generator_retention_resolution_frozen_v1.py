from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "production_generator_retention_resolution_v1"
FREEZE = RES / "freeze_summary.json"


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_retention_freeze_core_result():
    a = _freeze()
    assert a["status"] == "FROZEN_PRODUCTION_GENERATOR_RETENTION_RESOLUTION"
    assert a["eligible_universe_count"] == 54
    assert a["resolution"] == "RETAIN_D29_KERNEL_UNDER_MINIMAL_INTERVENTION"
    assert a["retained_primary_candidate"] == "d29_kernel"
    assert a["all_retention_preconditions_pass"] is True


def test_retention_freeze_is_not_superiority_or_reoptimization():
    a = _freeze()
    assert a["retention_is_superiority_claim"] is False
    assert a["retention_is_uniqueness_claim"] is False
    assert a["retention_is_statistical_selection"] is False
    assert a["ranking_or_reoptimization_performed"] is False
    assert a["D29_LRV_NSV_SRE_used_for_selection"] is False
    assert a["SHAP_used_for_selection"] is False
    assert a["MCDM_used_for_selection"] is False
    assert a["winner_identity_used_for_selection"] is False


def test_retention_freeze_firewalls_and_semantic_clarification():
    a = _freeze()
    assert a["new_simulation"] is False
    assert a["new_seeds_used"] is False
    assert a["D3_worlds_used"] is False
    assert a["reserve_30001_30005_used"] is False
    assert a["primary_11001_11030_used"] is False
    assert a["external_TEST_used"] is False
    assert a["firewall_check_true_means_negative_usage_condition_verified"] is True


def test_retention_preconditions_frozen_all_true():
    table = pd.read_csv(RES / "retention_precondition_table.csv")
    assert len(table) == 5
    vals = table["pass"].map(
        lambda x: x if isinstance(x, bool)
        else str(x).strip().lower() == "true"
    )
    assert bool(vals.all())
