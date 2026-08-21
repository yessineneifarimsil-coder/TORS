from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "d3_alpha_dispersion_execution_v1"
FREEZE = RES / "freeze_summary.json"


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_d3_freeze_core_convergence():
    a = _freeze()
    assert a["status"] == "FROZEN_D3_CONVERGED_MAPPING"
    assert a["worlds_observed"] == 200
    assert a["expanded_beyond_200"] is False
    assert a["order_150_equals_200"] is True
    assert a["precision_pass_W200"] is True
    assert a["max_relative_95pct_half_width_W200"] <= 0.05


def test_d3_freeze_order_and_mappings():
    a = _freeze()
    order = ["C8","C10","C5","C2","C3","C4","C1","C7","C6","C9"]
    assert a["final_order_descending_q_mad"] == order
    aligned = a["dispersion_aligned"]
    anti = a["dispersion_anti_aligned"]
    assert aligned["C8"] == 0.16
    assert aligned["C9"] == 0.04
    assert anti["C9"] == 0.16
    assert anti["C8"] == 0.04
    assert np.isclose(sum(aligned.values()), 1.0)
    assert np.isclose(sum(anti.values()), 1.0)


def test_d3_freeze_world_artifacts_are_complete():
    world = pd.read_csv(RES / "world_q_mad.csv")
    audit = pd.read_csv(RES / "world_audit.csv")
    assert len(world) == 2000
    assert world["world_index"].nunique() == 200
    assert set(world["criterion"]) == {f"C{i}" for i in range(1,11)}
    assert bool((world["n_observations"] == 6000).all())
    assert len(audit) == 200
    assert bool((audit["contexts"] == 1000).all())
    assert bool((audit["rows"] == 6000).all())


def test_d3_freeze_firewalls():
    a = _freeze()
    assert a["primary_11001_11030_used"] is False
    assert a["reserve_30001_30005_used"] is False
    assert a["external_TEST_used"] is False
    assert a["FIT_WEIGHT_partition_roles_used"] is False
    assert a["SHAP_used"] is False
    assert a["MCDM_used"] is False
    assert a["winner_identity_used"] is False
    assert a["v2_2_robustness_executed"] is False
    assert a["primary_alpha_changed"] is False


def test_d3_freeze_documents_legacy_diagnostic_deviation():
    a = _freeze()
    assert a["minmax_population_sd_used_for_mapping"] is False
    assert a["legacy_minmax_population_sd_status"] == (
        "NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC"
    )
    assert a["legacy_historical_single_pool_formula_recovered"] is True
    assert a["legacy_multiworld_aggregation_prespecified"] is False
    assert a["legacy_diagnostic_deviation_affects_mapping"] is False
