from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "src"
    / "v2_2_d2_7_positive_control.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "d27_under_test",
        MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[
        "d27_under_test"
    ] = module
    spec.loader.exec_module(module)
    return module


d27 = load_module()


def test_rotation_schedule_is_exactly_label_balanced():
    ids = [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
    ]

    seen = {
        alt: []
        for alt in ids
    }

    for rotation in range(6):
        mapping = (
            d27.rotation_coefficients(
                ids,
                rotation,
            )
        )

        assert np.isclose(
            sum(mapping.values()),
            0.0,
            atol=1e-15,
        )

        for alt in ids:
            seen[alt].append(
                mapping[alt]
            )

    expected = sorted(
        d27.CONTRAST.tolist()
    )

    for alt in ids:
        assert sorted(
            seen[alt]
        ) == expected


def test_positive_control_departure_is_bounded_by_delta():
    theta = np.linspace(
        0.05,
        0.40,
        8,
    )
    opportunity = np.linspace(
        0.0,
        1.0,
        10001,
    )

    for t in theta:
        baseline = t * opportunity

        for c in d27.CONTRAST:
            controlled = (
                t
                + d27.DELTA
                * c
                * (
                    2.0
                    * opportunity
                    - 1.0
                )
            ) * opportunity

            departure = np.abs(
                controlled
                - baseline
            )

            assert departure.max() <= (
                d27.DELTA
                + 1e-12
            )
            assert controlled.min() >= (
                -1e-12
            )
            assert controlled.max() <= (
                0.45
                + 1e-12
            )


def test_domain_wide_departure_reaches_exact_delta():
    t = 0.20
    o = np.asarray(
        [1.0]
    )
    c = 1.0

    baseline = t * o
    controlled = (
        t
        + d27.DELTA
        * c
        * (2.0 * o - 1.0)
    ) * o

    assert np.isclose(
        np.abs(
            controlled
            - baseline
        )[0],
        d27.DELTA,
        atol=1e-15,
    )


def test_reflected_latent_formula_matches_protocol():
    rho = 0.4
    z_shared = np.asarray(
        [-1.0, 0.0, 0.5, 2.0]
    )
    z_idio = np.asarray(
        [0.7, -0.2, 1.1, -1.5]
    )

    original = (
        np.sqrt(rho)
        * z_shared
        + np.sqrt(1.0 - rho)
        * z_idio
    )

    reflected = (
        np.sqrt(rho)
        * z_shared
        - np.sqrt(1.0 - rho)
        * z_idio
    )

    shared_component = (
        original + reflected
    ) / 2.0

    assert np.allclose(
        shared_component,
        np.sqrt(rho)
        * z_shared,
        atol=1e-15,
    )


def test_frozen_numerical_constants():
    assert d27.POSITIVE_FLOOR == 1e-12
    assert d27.EPS == 1e-12
    assert (
        d27.REGRET_NUM_THRESHOLD
        == 1e-12
    )
    assert d27.DESIGN_SEEDS == (
        21001,
        21002,
        21003,
        21004,
        21005,
    )
    assert d27.RHO == 0.4
    assert d27.LAMBDA_VALUE == 0.5
    assert d27.DELTA == 0.05
