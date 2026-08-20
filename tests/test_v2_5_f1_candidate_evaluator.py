from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "v2_5_f1_candidate_evaluator.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "v25_f1_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["v25_f1_under_test"] = module
    spec.loader.exec_module(module)
    return module


v25 = load()


def test_frozen_v25_constants():
    assert v25.SIGNED_PROFILE_NAMESPACE == 2007
    assert v25.ETA_REFERENCE == 0.0
    assert v25.ETA_LADDER == (
        0.1, 0.2, 0.3, 0.4, 0.5,
        0.6, 0.7, 0.8, 0.9, 1.0,
    )
    assert v25.DESIGN_SEEDS == (
        21001, 21002, 21003, 21004, 21005,
    )


def test_signed_grid_is_symmetric_zero_mean():
    for m in (5, 6):
        grid = v25.signed_grid(m)
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
    assert v25.class_ceiling("I") == 0.20
    assert v25.class_ceiling("D") == 0.40
    assert v25.class_ceiling("0") == 0.0


def test_eta_zero_recovers_historical_response():
    theta = 0.13
    ceiling = 0.20
    o = np.linspace(0.0, 1.0, 101)

    for v in np.linspace(-1.0, 1.0, 11):
        got = v25.candidate_response(
            theta=theta,
            opportunity=o,
            eta=0.0,
            ceiling=ceiling,
            v=v,
        )
        assert np.allclose(
            got,
            theta * o,
            atol=0.0,
            rtol=0.0,
        )


def test_eta_one_removes_theta_over_u_curvature_attenuation():
    o = np.linspace(0.0, 1.0, 101)
    ceiling = 0.20
    v = 0.6

    g1 = v25.candidate_response(
        theta=0.06,
        opportunity=o,
        eta=1.0,
        ceiling=ceiling,
        v=v,
    )
    g2 = v25.candidate_response(
        theta=0.19,
        opportunity=o,
        eta=1.0,
        ceiling=ceiling,
        v=v,
    )

    expected = (
        ceiling
        * o
        * (
            1.0
            + v * (1.0 - o)
        )
    )

    assert np.allclose(
        g1,
        expected,
        atol=1e-15,
        rtol=0.0,
    )
    assert np.allclose(
        g2,
        expected,
        atol=1e-15,
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
        for eta in v25.ETA_LADDER:
            for v in np.linspace(-1.0, 1.0, 11):
                g = v25.candidate_response(
                    theta=theta,
                    opportunity=o,
                    eta=eta,
                    ceiling=ceiling,
                    v=v,
                )

                assert np.isclose(g[0], 0.0, atol=1e-15)
                assert g.min() >= -1e-15
                assert g.max() <= ceiling + 1e-12
                assert np.min(np.diff(g)) >= -1e-12

                derivative = (
                    (1.0 - eta) * theta
                    + eta * ceiling
                    + eta * ceiling * v * (1.0 - 2.0 * o)
                )
                assert derivative.min() >= -1e-12


def test_full_opportunity_matches_convex_theta_ceiling_endpoint():
    for theta, ceiling in (
        (0.05, 0.20),
        (0.19, 0.20),
        (0.20, 0.40),
        (0.39, 0.40),
    ):
        for eta in v25.ETA_LADDER:
            expected = (
                (1.0 - eta) * theta
                + eta * ceiling
            )

            for v in np.linspace(-1.0, 1.0, 11):
                got = float(
                    v25.candidate_response(
                        theta=theta,
                        opportunity=1.0,
                        eta=eta,
                        ceiling=ceiling,
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
        for eta in v25.ETA_LADDER:
            for v in (-1.0, -0.6, 0.0, 0.6, 1.0):
                derivative = (
                    (1.0 - eta) * theta
                    + eta * ceiling
                    + eta * ceiling * v * (1.0 - 2.0 * o)
                )
                lower = (1.0 - eta) * theta
                assert derivative.min() >= lower - 1e-12
                assert lower >= -1e-15


def test_selection_rule_chooses_smallest_passing_eta_only():
    frame = pd.DataFrame(
        {
            "eta": [0.1, 0.2, 0.3, 0.4],
            "all_frozen_gates": [
                False, False, True, True,
            ],
        }
    )

    assert v25.select_eta(frame) == 0.3

    frame["all_frozen_gates"] = False
    assert v25.select_eta(frame) is None


def test_frozen_d27_d28_references_and_layer_b_status():
    d27_refs, d28_thresholds = (
        v25.load_frozen_thresholds()
    )

    assert d27_refs["layer_b"]["activated"] is False
    assert d27_refs["layer_b"]["T_R_sci"] is None

    assert d28_thresholds["T_num_NS"] == 1e-12
    assert d28_thresholds["T_num_LRV"] == 1e-10
    assert d28_thresholds["T_num_NSV_vector"] > 0.0
