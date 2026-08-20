from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_3_f1_candidates"
EXPECTED_COMMIT = "64f5a6f5c8f429af3b80b62aea2374c29db7d56b"


def _b(v: str) -> bool:
    return v.strip().lower() == "true"


def test_frozen_v23_f1_failure_and_provenance():
    selection = json.loads(
        (RESULTS / "selection.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["headroom_namespace"] == 2005
    assert metadata["tau"] == 0.5
    assert metadata["external_test_used"] is False
    assert metadata["structural_validation_seeds_used"] is False
    assert metadata["primary_seeds_used"] is False
    assert metadata["production_generator_modified"] is False
    assert metadata["layer_b_used_for_selection"] is False

    assert selection["family_failed"] is True
    assert selection["selected_eta"] is None
    assert selection["layer_b_used_for_selection"] is False


def test_frozen_v23_f1_gate_pattern():
    with (RESULTS / "candidate_gate_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 10

    for row in rows:
        assert _b(row["pass_numerical"])
        assert not _b(row["pass_scientific_layer_a"])
        assert _b(row["pass_reachability"])
        assert _b(row["pass_invariants"])
        assert not _b(row["all_frozen_gates"])
        assert row["failed_layer_a_criteria"] == (
            "C1,C2,C3,C4,C5,C6,C7"
        )
        assert row["failed_reachability_pathways"] == ""
