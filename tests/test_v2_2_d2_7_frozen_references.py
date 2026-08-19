from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v2_2_d2_7_positive_control"
EXPECTED_COMMIT = "2f8cd1ae1bb17321ef55ca7b2e03b4ab5ee0ff87"

def _load():
    refs = json.loads((RESULTS / "references.json").read_text(encoding="utf-8"))
    meta = json.loads((RESULTS / "run_metadata.json").read_text(encoding="utf-8"))
    return refs, meta

def test_frozen_d27_provenance():
    _, meta = _load()
    assert meta["git_commit"] == EXPECTED_COMMIT
    assert meta["design_seeds"] == [21001, 21002, 21003, 21004, 21005]
    assert meta["external_test_used"] is False
    assert meta["structural_validation_seeds_used"] is False
    assert meta["primary_seeds_used"] is False

def test_frozen_d27_key_layer_a_references():
    refs, _ = _load()
    assert refs["layer_a"]["C1"]["T_sci_LRV"] == pytest.approx(0.18560606963725407, abs=1e-14)
    assert refs["layer_a"]["C6"]["T_sci_NSV_vector"] == pytest.approx(0.12993524843563106, abs=1e-14)

def test_frozen_d27_layer_b_nonactivation():
    refs, _ = _load()
    layer_b = refs["layer_b"]
    assert layer_b["activated"] is False
    assert layer_b["T_R_sci"] is None
    assert layer_b["paired_uplift_by_seed"]["21003"] == pytest.approx(-0.01383595455383882, abs=1e-14)
