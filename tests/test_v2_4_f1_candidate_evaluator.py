from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "v2_4_f1_candidate_evaluator.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "v24_f1_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["v24_f1_under_test"] = module
    spec.loader.exec_module(module)
    return module


v24 = load()


def test_frozen_v24_constants():
    assert v24.SIGNED_PROFILE_NAMESPACE == 2006
    assert v24.ETA_REFERENCE == 0.0
    assert v24.ETA_LADDER == (
        0.1, 0.2, 0.3, 0.4, 0.5,
        0.6, 0.7, 0.8, 0.9, 1.0,
    )
    assert v24.DESIGN_SEEDS == (
        21001, 21002, 21003, 21004, 21005,
    )


def test_signed_grid_is_symmetric_zero_mean():
    for m in (5, 6):
        grid = v24.signed_grid(m)
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


def test_class_ceilings_remain_frozen():
    assert v24.class_ceiling("I") == 0.20
    assert v24.class_ceiling("D") == 0.40
    assert v24.class_ceiling("0") == 0.0


def test_eta_zero_recovers_historical_response():
    theta = 0.23
    headroom = 0.17
    o = np.linspace(0.0, 1.0, 101)

    for v in np.linspace(-1.0, 1.0, 11):
        got = v24.candidate_response(
            theta=theta,
            opportunity=o,
            eta=0.0,
            headroom=headroom,
            v=v,
        )
        assert np.allclose(
            got,
            theta * o,
            atol=0.0,
            rtol=0.0,
        )


def test_response_respects_bounds_and_monotonicity():
    cases = [
        (0.05, 0.20),
        (0.12, 0.20),
        (0.199, 0.20),
        (0.20, 0.40),
        (0.31, 0.40),
        (0.399, 0.40),
    ]
    o = np.linspace(0.0, 1.0, 10001)

    for theta, ceiling in cases:
        h = ceiling - theta
        for eta in v24.ETA_LADDER:
            for v in np.linspace(-1.0, 1.0, 11):
                g = v24.candidate_response(
                    theta=theta,
                    opportunity=o,
                    eta=eta,
                    headroom=h,
                    v=v,
                )

                assert np.isclose(g[0], 0.0, atol=1e-15)
                assert g.min() >= -1e-15
                assert g.max() <= ceiling + 1e-12
                assert np.min(np.diff(g)) >= -1e-12

                derivative = (
                    theta
                    + eta * h
                    + eta * theta * v * (1.0 - 2.0 * o)
                )
                assert derivative.min() >= -1e-12


def test_full_opportunity_equals_theta_plus_eta_headroom():
    for theta, ceiling in (
        (0.05, 0.20),
        (0.19, 0.20),
        (0.20, 0.40),
        (0.39, 0.40),
    ):
        h = ceiling - theta
        for eta in v24.ETA_LADDER:
            expected = theta + eta * h
            for v in np.linspace(-1.0, 1.0, 11):
                got = float(
                    v24.candidate_response(
                        theta=theta,
                        opportunity=1.0,
                        eta=eta,
                        headroom=h,
                        v=v,
                    )
                )
                assert np.isclose(got, expected, atol=1e-15)
                assert got <= ceiling + 1e-15


def test_analytic_monotonicity_lower_bound():
    o = np.linspace(0.0, 1.0, 1001)

    for theta, ceiling in (
        (0.05, 0.20),
        (0.199, 0.20),
        (0.20, 0.40),
        (0.399, 0.40),
    ):
        h = ceiling - theta
        for eta in v24.ETA_LADDER:
            for v in (-1.0, -0.6, 0.0, 0.6, 1.0):
                derivative = (
                    theta
                    + eta * h
                    + eta * theta * v * (1.0 - 2.0 * o)
                )
                lower = theta * (1.0 - eta) + eta * h
                assert derivative.min() >= lower - 1e-12
                assert lower >= -1e-15


def test_selection_rule_chooses_smallest_passing_eta_only():
    frame = pd.DataFrame(
        {
            "eta": [0.1, 0.2, 0.3, 0.4],
            "all_frozen_gates": [False, False, True, True],
        }
    )

    assert v24.select_eta(frame) == 0.3

    frame["all_frozen_gates"] = False
    assert v24.select_eta(frame) is None


def test_frozen_d27_d28_references_and_layer_b_status():
    d27_refs, d28_thresholds = v24.load_frozen_thresholds()

    assert d27_refs["layer_b"]["activated"] is False
    assert d27_refs["layer_b"]["T_R_sci"] is None

    assert d28_thresholds["T_num_NS"] == 1e-12
    assert d28_thresholds["T_num_LRV"] == 1e-10
    assert d28_thresholds["T_num_NSV_vector"] > 0.0
