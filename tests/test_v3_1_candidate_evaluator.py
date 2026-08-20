from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "v3_1_f1_candidate_evaluator.py"
V30_PATH = ROOT / "src" / "v3_0_f1_candidate_evaluator.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v31_frozen_constants_and_d29_reference_source():
    m = _load(PATH, "v31_eval_constants")

    assert m.DEVELOPMENT_SEEDS == (27001,27002,27003,27004,27005)
    assert m.RESERVED_SEEDS == (28001,28002,28003,28004,28005)
    assert m.STRUCTURAL_VALIDATION_SEEDS == (22001,22002,22003,22004,22005)
    assert m.V30_DEVELOPMENT_SEEDS == (23001,23002,23003,23004,23005)
    assert m.LEGACY_RESERVED_SEEDS == (24001,24002,24003,24004,24005)
    assert m.D29_RESERVED_SEEDS == (26001,26002,26003,26004,26005)
    assert m.SIGNED_PROFILE_NAMESPACE == 2009
    assert m.TAU_REFERENCE == 0.0
    assert m.TAU_UPPER_ANCHOR == 1.0
    assert m.TAU_GRID == (0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9)

    assert m.D29_REFERENCES == (
        ROOT / "results" / "d2_9_admissible_positive_control" / "references.json"
    )


def test_v31_interpolation_exactly_matches_frozen_v30_p2_p3_anchors():
    m = _load(PATH, "v31_eval_anchor")
    v30 = _load(V30_PATH, "v30_eval_anchor")

    o = np.linspace(0.0, 1.0, 31)
    for v in (-1.0,-0.6,-0.2,0.0,0.2,0.6,1.0):
        f2 = v30.headroom_shape(o, 2, v)
        f3 = v30.headroom_shape(o, 3, v)

        assert np.allclose(m.headroom_shape(o, 0.0, v), f2)
        assert np.allclose(m.headroom_shape(o, 1.0, v), f3)
        assert np.allclose(
            m.headroom_shape(o, 0.5, v),
            0.5 * f2 + 0.5 * f3,
        )


def test_v31_shape_and_response_invariants_on_dense_grid():
    m = _load(PATH, "v31_eval_invariants")
    o = np.linspace(0.0, 1.0, 1001)

    for tau in (0.0,0.1,0.5,0.9,1.0):
        for v in (-1.0,-0.6,-0.2,0.0,0.2,0.6,1.0):
            f = m.headroom_shape(o, tau, v)
            df = m.headroom_shape_derivative(o, tau, v)

            assert float(f.min()) >= -1e-12
            assert float(f.max()) <= 1.0 + 1e-12
            assert abs(float(f[0])) <= 1e-12
            assert abs(float(f[-1]) - 1.0) <= 1e-12
            assert float(df.min()) >= -1e-12

            theta = 0.11
            ceiling = 0.20
            g = m.candidate_response(theta, o, tau, ceiling, v)
            dg = theta + (ceiling - theta) * df

            assert float(g.min()) >= -1e-12
            assert float(g.max()) <= ceiling + 1e-12
            assert abs(float(g[0])) <= 1e-12
            assert abs(float(g[-1]) - ceiling) <= 1e-12
            assert float(dg.min()) >= theta - 1e-12


def test_v31_selection_is_minimum_feasible_selectable_tau():
    m = _load(PATH, "v31_eval_selection")
    frame = pd.DataFrame(
        {
            "tau": [0.1,0.2,0.3,0.4],
            "all_frozen_gates": [False,False,True,True],
        }
    )
    assert m.select_tau(frame) == 0.3

    frame["all_frozen_gates"] = False
    assert m.select_tau(frame) is None
