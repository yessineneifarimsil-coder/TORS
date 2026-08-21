from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "v4_0_f1_terminal_d29_kernel_evaluator.py"


def _load():
    spec = importlib.util.spec_from_file_location("v40_eval_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v40_frozen_constants_and_single_candidate_design():
    m = _load()

    assert m.DEVELOPMENT_SEEDS == (29001,29002,29003,29004,29005)
    assert m.RESERVED_SEEDS == (30001,30002,30003,30004,30005)
    assert m.STRUCTURAL_VALIDATION_SEEDS == (22001,22002,22003,22004,22005)
    assert m.SIGNED_PROFILE_NAMESPACE == 2010
    assert m.DELTA == 0.05
    assert m.CANDIDATE_ID == "d29_kernel"
    assert m.D29_REFERENCES == (
        ROOT / "results" / "d2_9_admissible_positive_control" / "references.json"
    )


def test_v40_response_matches_frozen_d29_kernel_formula():
    m = _load()

    o = np.linspace(0.0, 1.0, 101)
    theta = 0.11

    for v in (-1.0,-0.6,-0.2,0.0,0.2,0.6,1.0):
        expected = theta * o + 0.05 * v * o * (1.0 - o)
        observed = m.candidate_response(theta, o, v)
        assert np.allclose(observed, expected, rtol=0.0, atol=1e-15)


def test_v40_analytic_invariants_hold_on_dense_grid():
    m = _load()

    o = np.linspace(0.0, 1.0, 10001)

    for theta, ceiling in ((0.05,0.20),(0.11,0.20),(0.21,0.40),(0.39,0.40)):
        for v in (-1.0,-0.6,-0.2,0.0,0.2,0.6,1.0):
            g = m.candidate_response(theta, o, v)
            dg = m.candidate_response_derivative(theta, o, v)

            assert float(g.min()) >= -1e-12
            assert float(g.max()) <= ceiling + 1e-12
            assert abs(float(g[0])) <= 1e-12
            assert abs(float(g[-1]) - theta) <= 1e-12
            assert float(dg.min()) >= -1e-12


def test_v40_gate_summary_is_single_candidate_and_no_parameter_search():
    m = _load()

    layer = pd.DataFrame(
        {
            "candidate_id": [m.CANDIDATE_ID] * 7,
            "criterion": [f"C{i}" for i in range(1,8)],
            "all_seed_num_NS": [True] * 7,
            "all_seed_num_LRV": [True] * 7,
            "all_seed_num_NSV": [True] * 7,
            "pass_sci_LRV": [True] * 7,
            "pass_sci_NSV": [True] * 7,
        }
    )
    paths = [
        "h_D->C1","h_D->C2","h_D->C3","h_D->C4","h_D->C6","h_D->C7",
        "h_E->C6","h_I->C2","h_I->C4","h_I->C5","h_T->C3","h_T->C7",
    ]
    reach = pd.DataFrame(
        {
            "candidate_id": [m.CANDIDATE_ID] * 12,
            "pathway": paths,
            "pass_sci_SRE": [True] * 12,
        }
    )
    boundary = pd.DataFrame(
        {
            "candidate_id": [m.CANDIDATE_ID] * 35,
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
        {
            "candidate_id": [m.CANDIDATE_ID] * 5,
            "C8_C10_unchanged": [True] * 5,
        }
    )

    gate = m.build_gate_summary(layer, reach, boundary, inv)
    assert len(gate) == 1
    assert gate.iloc[0]["candidate_id"] == "d29_kernel"
    assert bool(gate.iloc[0]["all_frozen_gates"]) is True
