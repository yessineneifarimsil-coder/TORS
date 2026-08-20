from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "v3_0_f1_candidate_evaluator.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "v30_f1_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["v30_f1_under_test"] = module
    spec.loader.exec_module(module)
    return module


v30 = load()


def test_frozen_v30_constants_and_cohorts():
    assert v30.SIGNED_PROFILE_NAMESPACE == 2008
    assert v30.P_REFERENCE == 1
    assert v30.P_LADDER == (2, 3, 4, 5)
    assert v30.DEVELOPMENT_SEEDS == (
        23001, 23002, 23003, 23004, 23005,
    )
    assert v30.RESERVED_SEEDS == (
        24001, 24002, 24003, 24004, 24005,
    )
    assert v30.OLD_DEVELOPMENT_SEEDS == (
        21001, 21002, 21003, 21004, 21005,
    )


def test_signed_grid_is_symmetric_zero_mean():
    for m in (5, 6):
        grid = v30.signed_grid(m)
        assert len(grid) == m
        assert grid[0] == -1.0
        assert grid[-1] == 1.0
        assert np.isclose(grid.mean(), 0.0, atol=1e-15)
        assert np.allclose(
            grid,
            -grid[::-1],
            atol=1e-15,
            rtol=0.0,
        )


def test_shape_endpoints_and_bounds():
    o = np.linspace(0.0, 1.0, 1001)
    for p in (1, 2, 3, 4, 5):
        for v in np.linspace(-1.0, 1.0, 11):
            f = v30.headroom_shape(
                opportunity=o,
                p=p,
                v=v,
            )
            assert np.isclose(f[0], 0.0, atol=1e-15)
            assert np.isclose(f[-1], 1.0, atol=1e-15)
            assert f.min() >= -1e-15
            assert f.max() <= 1.0 + 1e-15


def test_shape_derivative_nonnegative():
    o = np.linspace(0.0, 1.0, 1001)
    for p in (1, 2, 3, 4, 5):
        for v in np.linspace(-1.0, 1.0, 11):
            fp = v30.headroom_shape_derivative(
                opportunity=o,
                p=p,
                v=v,
            )
            assert fp.min() >= -1e-15


def test_shape_reflection_symmetry():
    o = np.linspace(0.0, 1.0, 1001)
    for p in (2, 3, 4, 5):
        for a in (0.2, 0.6, 1.0):
            positive = v30.headroom_shape(
                opportunity=o,
                p=p,
                v=a,
            )
            reflected_negative = (
                1.0
                - v30.headroom_shape(
                    opportunity=1.0 - o,
                    p=p,
                    v=-a,
                )
            )
            assert np.allclose(
                positive,
                reflected_negative,
                atol=1e-15,
                rtol=0.0,
            )


def test_p_one_is_linear_full_headroom_reference():
    o = np.linspace(0.0, 1.0, 101)
    for v in np.linspace(-1.0, 1.0, 11):
        f = v30.headroom_shape(
            opportunity=o,
            p=1,
            v=v,
        )
        assert np.allclose(
            f,
            o,
            atol=1e-15,
            rtol=0.0,
        )


def test_quadratic_special_case():
    o = np.linspace(0.0, 1.0, 101)
    for v in np.linspace(-1.0, 1.0, 11):
        got = v30.headroom_shape(
            opportunity=o,
            p=2,
            v=v,
        )
        expected = o + v * o * (1.0 - o)
        assert np.allclose(
            got,
            expected,
            atol=1e-15,
            rtol=0.0,
        )


def test_response_bounds_endpoints_and_derivative_floor():
    o = np.linspace(0.0, 1.0, 10001)

    for theta, ceiling in (
        (0.05, 0.20),
        (0.12, 0.20),
        (0.199, 0.20),
        (0.20, 0.40),
        (0.31, 0.40),
        (0.399, 0.40),
    ):
        h = ceiling - theta

        for p in (1, 2, 3, 4, 5):
            for v in np.linspace(-1.0, 1.0, 11):
                g = v30.candidate_response(
                    theta=theta,
                    opportunity=o,
                    p=p,
                    ceiling=ceiling,
                    v=v,
                )
                fp = v30.headroom_shape_derivative(
                    opportunity=o,
                    p=p,
                    v=v,
                )
                derivative = theta + h * fp

                assert np.isclose(g[0], 0.0, atol=1e-15)
                assert np.isclose(g[-1], ceiling, atol=1e-15)
                assert g.min() >= -1e-15
                assert g.max() <= ceiling + 1e-12
                assert np.min(np.diff(g)) >= -1e-12
                assert derivative.min() >= theta - 1e-12


def test_class_ceiling_helper_unchanged():
    assert v30.class_ceiling("I") == 0.20
    assert v30.class_ceiling("D") == 0.40
    assert v30.class_ceiling("0") == 0.0


def test_selection_rule_chooses_smallest_p_only():
    frame = pd.DataFrame(
        {
            "p": [2, 3, 4, 5],
            "all_frozen_gates": [
                False, False, True, True,
            ],
        }
    )
    assert v30.select_p(frame) == 4

    frame["all_frozen_gates"] = False
    assert v30.select_p(frame) is None


def test_frozen_d27_d28_references_and_layer_b_status():
    d27_refs, d28_thresholds = (
        v30.load_frozen_thresholds()
    )

    assert d27_refs["layer_b"]["activated"] is False
    assert d27_refs["layer_b"]["T_R_sci"] is None
    assert d28_thresholds["T_num_NS"] == 1e-12
    assert d28_thresholds["T_num_LRV"] == 1e-10
    assert d28_thresholds["T_num_NSV_vector"] > 0.0
