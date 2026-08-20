from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "d2_9_admissible_positive_control"
EXPECTED_COMMIT = '3463d5d294798e8d2770d6c95ee63ecf01230dca'
EXPECTED_LAYER_A = {'C1': (0.0823367060180439, 0.04150944500477258), 'C2': (0.05135703082499147, 0.030180789560001246), 'C3': (0.06320131683925327, 0.032871176397166704), 'C4': (0.0584394716346404, 0.033274732045588784), 'C5': (0.06114512257795974, 0.03893229936662514), 'C6': (0.10669498984969662, 0.06203584559273667), 'C7': (0.06752862595487336, 0.0421069255807601)}
EXPECTED_REACH = {'h_D->C1': 0.6252491501173607, 'h_D->C2': 0.3049148696475096, 'h_D->C3': 0.4220320343087468, 'h_D->C4': 0.32269510335210616, 'h_D->C6': 0.4123214319717975, 'h_D->C7': 0.27257109898658916, 'h_E->C6': 0.27555688651992993, 'h_I->C2': 0.20048975060267737, 'h_I->C4': 0.3327413283163435, 'h_I->C5': 0.5701057397882139, 'h_T->C3': 0.29261826954559067, 'h_T->C7': 0.41859298239010767}


def _b(value: str) -> bool:
    return value.strip().lower() == "true"


def test_frozen_d29_provenance_firewalls_and_references():
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )
    refs = json.loads(
        (RESULTS / "references.json").read_text(encoding="utf-8")
    )

    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["calibration_seeds"] == [25001, 25002, 25003, 25004, 25005]
    assert metadata["reserved_seeds"] == [26001, 26002, 26003, 26004, 26005]
    assert metadata["rho"] == 0.4
    assert metadata["lambda"] == 0.5
    assert metadata["sigma_x"] == 0.0
    assert metadata["delta"] == 0.05
    assert metadata["max_abs_response_departure"] == 0.0125

    for key in (
        "external_test_used",
        "structural_validation_seeds_used",
        "primary_seeds_used",
        "old_d2_7_design_seeds_used",
        "v3_development_seeds_used",
        "reserved_seeds_used",
        "old_d2_7_thresholds_used",
        "d2_8_numerical_thresholds_modified",
        "layer_b_used_for_scientific_threshold",
    ):
        assert metadata[key] is False

    assert refs["layer_b"]["activated"] is False
    assert refs["layer_b"]["T_R_sci"] is None

    for criterion, (lrv, nsv) in EXPECTED_LAYER_A.items():
        assert refs["layer_a"][criterion]["T_sci_LRV"] == lrv
        assert refs["layer_a"][criterion]["T_sci_NSV_vector"] == nsv

    for pathway, sre in EXPECTED_REACH.items():
        assert refs["reachability"][pathway]["T_sci_SRE"] == sre


def test_frozen_d29_admissibility():
    with (RESULTS / "admissibility_diagnostics.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1260
    active = [row for row in rows if str(row["class"]) != "0"]
    assert len(active) == 1200

    for row in rows:
        assert _b(row["lower_bound_ok"])
        assert _b(row["semantic_ceiling_ok"])
        assert _b(row["monotonicity_ok"])
        assert _b(row["structural_zero_ok"])

    assert min(float(row["min_derivative"]) for row in rows) >= 0.0
    assert max(float(row["max_abs_departure"]) for row in rows) == 0.0125
