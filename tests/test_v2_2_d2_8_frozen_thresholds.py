from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_2_d2_8_numerical_null"
EXPECTED_COMMIT = "a1f2e54ff8965654cbf2e0773a1e249cd22170f7"


def _load():
    thresholds = json.loads(
        (RESULTS / "thresholds.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (RESULTS / "run_metadata.json").read_text(encoding="utf-8")
    )
    return thresholds, metadata


def test_frozen_d28_thresholds():
    thresholds, _ = _load()
    assert thresholds["T_num_NS"] == pytest.approx(1e-12, abs=0.0)
    assert thresholds["T_num_LRV"] == pytest.approx(1e-10, abs=0.0)
    assert thresholds["T_num_NSV_vector"] == pytest.approx(
        3.2506084454037334e-08,
        abs=1e-20,
    )
    assert thresholds["Q999_NS_null"] == 0.0


def test_frozen_d28_provenance():
    _, metadata = _load()
    assert metadata["git_commit"] == EXPECTED_COMMIT
    assert metadata["candidate_responses_used"] is False
    assert metadata["external_test_used"] is False
    assert metadata["primary_seeds_used"] is False
    assert metadata["historical_all_below_T_num"] is True


def test_frozen_d28_historical_collapse_check():
    with (RESULTS / "historical_v2_1_check.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 35

    for row in rows:
        assert row["below_T_num_NS"].lower() == "true"
        assert row["below_T_num_LRV"].lower() == "true"
        assert row["below_T_num_NSV"].lower() == "true"
