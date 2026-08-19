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
    / "v2_2_d4_f1_candidate_evaluator.py"
)


def load():
    spec = importlib.util.spec_from_file_location(
        "d4_f1_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[
        "d4_f1_under_test"
    ] = module
    spec.loader.exec_module(module)
    return module


d4 = load()


def test_frozen_candidate_ladder_and_namespace():
    assert d4.CURVATURE_NAMESPACE == 2004
    assert d4.KAPPA_REFERENCE == 0.0
    assert d4.KAPPA_LADDER == (
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
    assert d4.DESIGN_SEEDS == (
        21001,
        21002,
        21003,
        21004,
        21005,
    )


def test_symmetric_grid_is_zero_mean_and_spans_full_range():
    for m in (5, 6):
        grid = d4.symmetric_grid(m)
        assert len(grid) == m
        assert np.isclose(
            grid.mean(),
            0.0,
            atol=1e-15,
        )
        assert grid[0] == -1.0
        assert grid[-1] == 1.0


def test_candidate_response_endpoints_bounds_and_monotonicity():
    theta = 0.4
    o = np.linspace(
        0.0,
        1.0,
        10001,
    )

    for kappa in d4.KAPPA_LADDER:
        for v in np.linspace(
            -1.0,
            1.0,
            11,
        ):
            g = d4.candidate_response(
                theta=theta,
                opportunity=o,
                kappa=kappa,
                v=v,
            )

            assert np.isclose(
                g[0],
                0.0,
                atol=1e-15,
            )
            assert np.isclose(
                g[-1],
                theta,
                atol=1e-15,
            )
            assert g.min() >= -1e-15
            assert g.max() <= theta + 1e-15
            assert np.min(
                np.diff(g)
            ) >= -1e-12


def test_kappa_zero_reproduces_historical_multiplicative_response():
    theta = 0.23
    o = np.linspace(
        0.0,
        1.0,
        100,
    )
    for v in (-1.0, -0.4, 0.0, 0.7, 1.0):
        got = d4.candidate_response(
            theta=theta,
            opportunity=o,
            kappa=0.0,
            v=v,
        )
        expected = theta * o
        assert np.allclose(
            got,
            expected,
            atol=0.0,
            rtol=0.0,
        )


def test_selection_rule_chooses_smallest_passing_kappa_only():
    frame = pd.DataFrame(
        {
            "kappa": [
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

    assert d4.select_kappa(
        frame
    ) == 0.3

    frame[
        "all_frozen_gates"
    ] = False

    assert d4.select_kappa(
        frame
    ) is None


def test_frozen_reference_files_exist_and_layer_b_is_not_gating():
    d27_refs, d28_thresholds = (
        d4.load_frozen_thresholds()
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
