from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "corrected_structural_validation_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "corrected_validation_test",
        PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corrected_validation_constants_are_frozen():
    m = _load()

    assert m.STRUCTURAL_VALIDATION_SEEDS == (
        22001,22002,22003,22004,22005
    )
    assert m.RESERVED_SEEDS == (
        30001,30002,30003,30004,30005
    )
    assert m.SIGNED_PROFILE_NAMESPACE == 2010
    assert m.DELTA == 0.05
    assert m.CANDIDATE_ID == "d29_kernel"


def test_corrected_gate_excludes_d29_structural_ratios():
    m = _load()

    layer = pd.DataFrame(
        {
            "criterion": [f"C{i}" for i in range(1,8)],
            "all_seed_num_NS": [True] * 7,
            "all_seed_num_LRV": [True] * 7,
            "all_seed_num_NSV": [True] * 7,
            # Deliberately terrible D2.9 ratios: they must not enter pass/fail.
            "LRV_to_D29_ratio": [0.01] * 7,
            "NSV_to_D29_ratio": [0.01] * 7,
        }
    )

    boundary = pd.DataFrame(
        {
            "lower_bound_ok": [True] * 35,
            "class_ceiling_ok": [True] * 35,
            "theta_support_ok": [True] * 35,
            "monotonicity_ok": [True] * 35,
            "endpoint_zero_ok": [True] * 35,
            "endpoint_theta_ok": [True] * 35,
            "structural_zero_ok": [True] * 35,
        }
    )
    inv = pd.DataFrame(
        {"C8_C10_unchanged": [True] * 5}
    )

    gate = m.corrected_gate_summary(layer, boundary, inv)
    row = gate.iloc[0]

    assert bool(row["pass_D2_8_numerical_non_degeneracy"]) is True
    assert bool(row["pass_all_corrected_invariants"]) is True
    assert bool(row["D29_LRV_NSV_SRE_used_for_pass_fail"]) is False
    assert bool(row["validation_passed"]) is True


def test_corrected_gate_fails_on_numerical_or_invariant_failure():
    m = _load()

    layer = pd.DataFrame(
        {
            "criterion": [f"C{i}" for i in range(1,8)],
            "all_seed_num_NS": [True] * 7,
            "all_seed_num_LRV": [True] * 7,
            "all_seed_num_NSV": [True] * 7,
        }
    )
    boundary = pd.DataFrame(
        {
            "lower_bound_ok": [True] * 35,
            "class_ceiling_ok": [True] * 35,
            "theta_support_ok": [True] * 35,
            "monotonicity_ok": [True] * 35,
            "endpoint_zero_ok": [True] * 35,
            "endpoint_theta_ok": [True] * 35,
            "structural_zero_ok": [True] * 35,
        }
    )
    inv = pd.DataFrame(
        {"C8_C10_unchanged": [True] * 5}
    )

    layer.loc[0, "all_seed_num_LRV"] = False
    gate = m.corrected_gate_summary(layer, boundary, inv)
    assert bool(gate.iloc[0]["validation_passed"]) is False

    layer.loc[0, "all_seed_num_LRV"] = True
    boundary.loc[0, "monotonicity_ok"] = False
    gate = m.corrected_gate_summary(layer, boundary, inv)
    assert bool(gate.iloc[0]["validation_passed"]) is False


def test_validation_reuses_exact_v40_response_definition():
    m = _load()

    assert m.v40.DELTA == m.DELTA == 0.05
    assert m.v40.SIGNED_PROFILE_NAMESPACE == m.SIGNED_PROFILE_NAMESPACE == 2010
    assert m.v40.CANDIDATE_ID == m.CANDIDATE_ID == "d29_kernel"
