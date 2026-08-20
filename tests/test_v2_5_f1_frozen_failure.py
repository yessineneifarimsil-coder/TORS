from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_5_f1_candidates"
EXPECTED_COMMIT = "869c749c0160fc454f267b4a5b073edfa18e07df"


def _b(v: str) -> bool:
    return v.strip().lower() == "true"


def test_frozen_v25_f1_failure_and_provenance():
    selection = json.loads(
        (RESULTS / "selection.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["signed_profile_namespace"] == 2007
    assert metadata["external_test_used"] is False
    assert metadata["structural_validation_seeds_used"] is False
    assert metadata["primary_seeds_used"] is False
    assert metadata["production_generator_modified"] is False
    assert metadata["layer_b_used_for_selection"] is False

    assert selection["family_failed"] is True
    assert selection["selected_eta"] is None
    assert selection["layer_b_used_for_selection"] is False


def test_frozen_v25_f1_gate_tradeoff():
    with (RESULTS / "candidate_gate_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 10

    for row in rows:
        eta = float(row["eta"])

        assert _b(row["pass_numerical"])
        assert _b(row["pass_invariants"])
        assert not _b(row["all_frozen_gates"])

        if eta <= 0.6:
            assert _b(row["pass_reachability"])
        else:
            assert not _b(row["pass_reachability"])
            assert row["failed_reachability_pathways"] == (
                "h_D->C6,h_E->C6"
            )

        if eta >= 0.9:
            assert _b(row["pass_scientific_layer_a"])
            assert row["failed_layer_a_criteria"] == ""
        else:
            assert not _b(row["pass_scientific_layer_a"])
