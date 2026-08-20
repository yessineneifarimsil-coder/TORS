from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = (
    ROOT
    / "src"
    / "v2_3_f1_candidate_evaluator.py"
)


def load():
    spec = importlib.util.spec_from_file_location(
        "v23_f1_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[
        "v23_f1_under_test"
    ] = module
    spec.loader.exec_module(module)
    return module


v23 = load()


def test_frozen_v23_constants():
    assert v23.HEADROOM_NAMESPACE == 2005
    assert v23.TAU == 0.5
    assert v23.ETA_REFERENCE == 0.0
    assert v23.ETA_LADDER == (
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
    )
    assert v23.DESIGN_SEEDS == (
        21001,
        21002,
        21003,
        21004,
        21005,
    )


def test_headroom_grid_matches_frozen_definition():
    for m in (5, 6):
        grid = v23.headroom_grid(m)
        assert len(grid) == m
        assert grid[0] == 0.0
        assert grid[-1] == 1.0
        assert np.allclose(
            grid,
            np.linspace(0.0, 1.0, m),
            atol=0.0,
            rtol=0.0,
        )


def test_class_ceilings_are_frozen():
    assert v23.class_ceiling("I") == 0.20
    assert v23.class_ceiling("D") == 0.40
    assert v23.class_ceiling("0") == 0.0


def test_eta_zero_reproduces_historical_multiplicative_response():
    theta = 0.23
    headroom = 0.17
    o = np.linspace(
        0.0,
        1.0,
        101,
    )

    for c in np.linspace(0.0, 1.0, 6):
        got = v23.candidate_response(
            theta=theta,
            opportunity=o,
            eta=0.0,
            headroom=headroom,
            c=c,
        )
        expected = theta * o
        assert np.allclose(
            got,
            expected,
            atol=0.0,
            rtol=0.0,
        )


def test_response_respects_zero_ceiling_and_derivative_floor():
    cases = [
        (0.05, 0.20),
        (0.12, 0.20),
        (0.199, 0.20),
        (0.20, 0.40),
        (0.31, 0.40),
        (0.399, 0.40),
    ]
    o = np.linspace(
        0.0,
        1.0,
        10001,
    )

    for theta, ceiling in cases:
        h = ceiling - theta
        for eta in v23.ETA_LADDER:
            for c in np.linspace(
                0.0,
                1.0,
                11,
            ):
                g = v23.candidate_response(
                    theta=theta,
                    opportunity=o,
                    eta=eta,
                    headroom=h,
                    c=c,
                )
                assert np.isclose(
                    g[0],
                    0.0,
                    atol=1e-15,
                )
                assert g.min() >= -1e-15
                assert g.max() <= ceiling + 1e-15
                assert np.min(
                    np.diff(g)
                ) >= -1e-12

                derivative = (
                    theta
                    + eta
                    * h
                    * (
                        v23.TAU
                        + 2.0
                        * (1.0 - v23.TAU)
                        * c
                        * o
                    )
                )
                assert derivative.min() >= theta - 1e-15


def test_full_opportunity_never_exceeds_semantic_ceiling():
    for capability_class, theta in (
        ("I", 0.05),
        ("I", 0.19),
        ("D", 0.20),
        ("D", 0.39),
    ):
        ceiling = v23.class_ceiling(
            capability_class
        )
        h = ceiling - theta

        for eta in v23.ETA_LADDER:
            for c in np.linspace(
                0.0,
                1.0,
                11,
            ):
                g1 = float(
                    v23.candidate_response(
                        theta=theta,
                        opportunity=1.0,
                        eta=eta,
                        headroom=h,
                        c=c,
                    )
                )
                assert g1 <= ceiling + 1e-15


def test_selection_rule_chooses_smallest_passing_eta_only():
    frame = pd.DataFrame(
        {
            "eta": [
                0.1,
                0.2,
                0.3,
                0.4,
            ],
            "all_frozen_gates": [
                False,
                False,
                True,
                True,
            ],
        }
    )

    assert v23.select_eta(
        frame
    ) == 0.3

    frame[
        "all_frozen_gates"
    ] = False

    assert v23.select_eta(
        frame
    ) is None


def test_frozen_d27_d28_references_and_layer_b_status():
    d27_refs, d28_thresholds = (
        v23.load_frozen_thresholds()
    )

    assert d27_refs[
        "layer_b"
    ][
        "activated"
    ] is False
    assert d27_refs[
        "layer_b"
    ][
        "T_R_sci"
    ] is None

    assert d28_thresholds[
        "T_num_NS"
    ] == 1e-12
    assert d28_thresholds[
        "T_num_LRV"
    ] == 1e-10
    assert d28_thresholds[
        "T_num_NSV_vector"
    ] > 0.0
