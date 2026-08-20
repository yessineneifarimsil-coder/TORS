from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "d2_9_historical_readjudication"


def test_no_historical_family_feasible():
    s = pd.read_csv(OUT / "family_summary.csv")
    assert len(s) == 5
    assert set(s["status"]) == {"NO_FEASIBLE_CANDIDATE"}


def test_expected_closest_points_and_firewalls():
    s = pd.read_csv(OUT / "family_summary.csv")
    m = json.loads((OUT / "run_metadata.json").read_text(encoding="utf-8"))

    expected = {
        "v2.2-D4-F1": (0.4, 0.600554),
        "v2.3-F1": (1.0, 0.200529),
        "v2.4-F1": (0.6, 0.841863),
        "v2.5-F1": (0.7, 0.947419),
        "v3.0-F1": (2.0, 0.956089),
    }

    for family, (value, ratio) in expected.items():
        row = s.loc[s["family"] == family].iloc[0]
        assert abs(float(row["best_descriptive_value"]) - value) < 1e-12
        assert abs(float(row["best_joint_min_ratio"]) - ratio) < 5e-7

    assert m["candidate_generators_rerun"] is False
    assert m["validation_seeds_used"] is False
    assert m["primary_seeds_used"] is False
    assert m["external_test_used"] is False
    assert m["layer_b_used_for_selection"] is False
