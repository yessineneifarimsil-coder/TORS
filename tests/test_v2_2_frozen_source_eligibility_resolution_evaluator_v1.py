from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "v2_2_frozen_source_eligibility_resolution_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("v22_resolution_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolution_is_locked_to_historical_source_commit():
    m = _load()
    assert m.HISTORICAL_COMMIT == "37c8f31"
    assert m.HISTORICAL_SOURCE_PATH == "src/v2_2_d4_f1_candidate_evaluator.py"


def test_historical_source_contract_parser_requires_all_contract_parts():
    m = _load()
    source = """
import numpy as np
C1_C7 = ("C1",)

def candidate_response(theta, opportunity, kappa, v):
    o = opportunity
    return theta * o * (1.0 + kappa * v * (1.0 - o))

def build_candidate_responses(baseline, benchmark):
    \"""Overwrite C1-C7 systematic responses while leaving C8-C10 exactly unchanged.\"""
    result = baseline.copy()
    for criterion in C1_C7:
        capability_class = "0"
        if capability_class == "0":
            values = np.zeros(1)
        result.loc[:, f"g_{criterion}"] = values
    return result
"""
    c = m.historical_source_contract(source)
    assert c["explicit_C8_C10_unchanged_contract"] is True
    assert c["C1_C7_only_response_overwrite"] is True
    assert c["structural_zero_pathways_explicitly_zero"] is True
    assert c["no_clipping_used_to_create_admissibility"] is True
    assert c["source_contract_pass"] is True


def test_point_resolution_requires_source_contract_and_all_frozen_gates():
    m = _load()
    gate = pd.DataFrame(
        {"kappa": [x / 10 for x in range(1, 11)], "pass_numerical": [True] * 10}
    )
    boundary_rows = []
    for k in gate["kappa"]:
        boundary_rows.append(
            {
                "kappa": k,
                "lower_bound_ok": True,
                "upper_bound_ok": True,
                "structural_zero_ok": True,
                "structural_zero_max_abs": 0.0,
            }
        )
    boundary = pd.DataFrame(boundary_rows)
    contract = {"source_contract_pass": True}
    out = m.resolve_v22_points(gate, boundary, contract)
    assert len(out) == 10
    assert bool(out["corrected_eligible"].all())

    contract_bad = {"source_contract_pass": False}
    out_bad = m.resolve_v22_points(gate, boundary, contract_bad)
    assert not bool(out_bad["corrected_eligible"].any())


def test_resolution_has_no_selection_metric():
    text = PATH.read_text(encoding="utf-8")
    assert "D29_LRV_NSV_SRE_used_for_binary_eligibility" in text
    assert "production_generator_selected" in text
    assert "selection_or_ranking_performed" in text
