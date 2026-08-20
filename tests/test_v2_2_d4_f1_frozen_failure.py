from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_2_d4_f1_candidates"
EXPECTED_COMMIT = "575358303293ae102a3d64721aab71ba4df67b9b"


def _load():
    selection = json.loads(
        (RESULTS / "selection.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )
    return selection, metadata


def test_frozen_d4_f1_failure_and_provenance():
    selection, metadata = _load()
    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["external_test_used"] is False
    assert metadata["structural_validation_seeds_used"] is False
    assert metadata["primary_seeds_used"] is False
    assert metadata["layer_b_used_for_selection"] is False
    assert selection["family_failed"] is True
    assert selection["selected_kappa"] is None


def test_frozen_d4_f1_gate_pattern():
    with (RESULTS / "candidate_gate_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 10
    by_kappa = {float(r["kappa"]): r for r in rows}

    for row in rows:
        assert row["pass_numerical"].lower() == "true"
        assert row["pass_reachability"].lower() == "false"
        assert row["all_frozen_gates"].lower() == "false"

    assert by_kappa[0.9]["pass_scientific_layer_a"].lower() == "true"
    assert by_kappa[1.0]["pass_scientific_layer_a"].lower() == "true"
    assert by_kappa[0.9]["failed_layer_a_criteria"] == ""
    assert by_kappa[1.0]["failed_layer_a_criteria"] == ""
