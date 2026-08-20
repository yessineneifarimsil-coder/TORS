from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v3_0_f1_candidates"
EXPECTED_COMMIT = "80b9b52e825ce15e9e60b816acae55d4d70e4964"


def _b(value: str) -> bool:
    return value.strip().lower() == "true"


def test_frozen_v30_f1_failure_and_firewalls():
    selection = json.loads(
        (RESULTS / "selection.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["signed_profile_namespace"] == 2008
    assert metadata["development_seeds"] == [
        23001, 23002, 23003, 23004, 23005
    ]
    assert metadata["reserved_seeds"] == [
        24001, 24002, 24003, 24004, 24005
    ]

    for key in (
        "external_test_used",
        "structural_validation_seeds_used",
        "primary_seeds_used",
        "old_development_seeds_used",
        "reserved_seeds_used",
        "production_generator_modified",
        "layer_b_used_for_selection",
    ):
        assert metadata[key] is False

    assert selection["family_failed"] is True
    assert selection["selected_p"] is None
    assert selection["p_reference"] == 1
    assert selection["p_ladder"] == [2, 3, 4, 5]
    assert selection["layer_b_used_for_selection"] is False


def test_frozen_v30_f1_gate_pattern_and_invariants():
    with (RESULTS / "candidate_gate_summary.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 4

    expected_layer = {
        2: "C1,C2,C3,C4,C5,C6,C7",
        3: "C1,C2,C4,C5,C6,C7",
        4: "C1,C6",
        5: "C1,C6",
    }
    expected_reach = {
        2: "",
        3: "h_E->C6",
        4: "h_D->C6,h_E->C6",
        5: "h_D->C6,h_E->C6",
    }

    for row in rows:
        p = int(float(row["p"]))

        assert _b(row["pass_numerical"])
        assert _b(row["pass_invariants"])
        assert not _b(row["pass_scientific_layer_a"])
        assert not _b(row["all_frozen_gates"])
        assert row["failed_layer_a_criteria"] == expected_layer[p]
        assert row["failed_reachability_pathways"] == expected_reach[p]

        if p == 2:
            assert _b(row["pass_reachability"])
        else:
            assert not _b(row["pass_reachability"])

    with (RESULTS / "boundary_diagnostics.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        boundary = list(csv.DictReader(handle))

    assert boundary

    for row in boundary:
        for key in (
            "lower_bound_ok",
            "class_ceiling_ok",
            "headroom_nonnegative_ok",
            "shape_bounds_ok",
            "monotonicity_ok",
            "derivative_floor_ok",
            "structural_zero_ok",
        ):
            assert _b(row[key])
