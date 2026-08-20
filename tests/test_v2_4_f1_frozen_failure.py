from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_4_f1_candidates"
EXPECTED_COMMIT = "56ac899ccddfb9d5735cc6209a65af1e946ff0f3"


def _b(v: str) -> bool:
    return v.strip().lower() == "true"


def test_frozen_v24_f1_failure_and_provenance():
    selection = json.loads(
        (RESULTS / "selection.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["signed_profile_namespace"] == 2006
    assert metadata["external_test_used"] is False
    assert metadata["structural_validation_seeds_used"] is False
    assert metadata["primary_seeds_used"] is False
    assert metadata["production_generator_modified"] is False
    assert metadata["layer_b_used_for_selection"] is False

    assert selection["family_failed"] is True
    assert selection["selected_eta"] is None
    assert selection["layer_b_used_for_selection"] is False


def test_frozen_v24_f1_gate_pattern():
    with (RESULTS / "candidate_gate_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 10

    expected = {
        0.1: "C1,C2,C3,C4,C5,C6,C7",
        0.2: "C1,C2,C3,C4,C5,C6,C7",
        0.3: "C1,C2,C3,C4,C5,C6,C7",
        0.4: "C1,C2,C3,C4,C5,C6,C7",
        0.5: "C1,C2,C3,C4,C5,C6,C7",
        0.6: "C1,C2,C3,C4,C6,C7",
        0.7: "C1,C3,C4,C6,C7",
        0.8: "C1,C3,C6,C7",
        0.9: "C1,C6,C7",
        1.0: "C1,C6",
    }

    for row in rows:
        eta = float(row["eta"])
        assert _b(row["pass_numerical"])
        assert not _b(row["pass_scientific_layer_a"])
        assert _b(row["pass_reachability"])
        assert _b(row["pass_invariants"])
        assert not _b(row["all_frozen_gates"])
        assert row["failed_layer_a_criteria"] == expected[eta]
        assert row["failed_reachability_pathways"] == ""
