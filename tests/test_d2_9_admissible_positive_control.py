from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "d2_9_admissible_positive_control.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "d29_under_test",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["d29_under_test"] = module
    spec.loader.exec_module(module)
    return module


d29 = load()


def test_frozen_d29_constants_and_fresh_cohorts():
    assert d29.CALIBRATION_SEEDS == (
        25001, 25002, 25003, 25004, 25005,
    )
    assert d29.RESERVED_SEEDS == (
        26001, 26002, 26003, 26004, 26005,
    )
    assert d29.RHO == 0.4
    assert d29.DELTA == 0.05
    assert np.allclose(
        d29.CONTRAST,
        [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0],
    )


def test_rotation_coefficients_cycle_complete_grid():
    alternatives = [
        "A1", "A2", "A3", "A4", "A5", "A6"
    ]

    seen = {
        alternative: []
        for alternative in alternatives
    }

    for rotation in range(6):
        coeff = d29.rotation_coefficients(
            alternatives,
            rotation,
        )
        for alternative in alternatives:
            seen[alternative].append(
                coeff[alternative]
            )

    expected = sorted(
        d29.CONTRAST.tolist()
    )

    for values in seen.values():
        assert sorted(values) == expected


def test_corrected_quadratic_pc_global_admissibility():
    o = np.linspace(0.0, 1.0, 10001)

    for theta, ceiling in (
        (0.05, 0.20),
        (0.10, 0.20),
        (0.15, 0.20),
        (0.199, 0.20),
        (0.20, 0.40),
        (0.30, 0.40),
        (0.399, 0.40),
    ):
        for c in d29.CONTRAST:
            g = (
                theta * o
                + d29.DELTA
                * c
                * o
                * (1.0 - o)
            )
            derivative = (
                theta
                + d29.DELTA
                * c
                * (1.0 - 2.0 * o)
            )

            assert np.isclose(g[0], 0.0)
            assert np.isclose(g[-1], theta)
            assert g.min() >= -1e-12
            assert g.max() <= ceiling + 1e-12
            assert derivative.min() >= -1e-12


def test_actual_max_departure_is_delta_over_four():
    o = np.linspace(0.0, 1.0, 100001)

    departure = (
        d29.DELTA
        * o
        * (1.0 - o)
    )

    assert np.isclose(
        departure.max(),
        d29.DELTA / 4.0,
        atol=1e-12,
    )
    assert np.isclose(
        d29.DELTA / 4.0,
        0.0125,
    )


def test_build_references_preserves_double_median_semantics():
    seeds = [25001, 25002, 25003, 25004, 25005]
    rotations = list(range(6))

    layer_a_rows = []
    reachability_rows = []
    layer_b_rows = []
    baseline_rows = []

    for seed_index, seed in enumerate(seeds):
        for rotation in rotations:
            for criterion_index in range(1, 8):
                criterion = f"C{criterion_index}"

                layer_a_rows.append(
                    {
                        "seed": seed,
                        "rotation": rotation,
                        "criterion": criterion,
                        "lrv50":
                            100.0 * seed_index
                            + 10.0 * criterion_index
                            + rotation,
                        "nsv_vector":
                            1000.0 * seed_index
                            + 10.0 * criterion_index
                            + rotation,
                    }
                )

            reachability_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    "factor": "h_D",
                    "criterion": "C1",
                    "sre":
                        50.0 * seed_index
                        + rotation,
                }
            )

            layer_b_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    "regret_mean":
                        20.0 * seed_index
                        + rotation,
                }
            )

        baseline_rows.append(
            {
                "seed": seed,
                "regret_mean": 0.0,
            }
        )

    refs = d29.build_references(
        layer_a=pd.DataFrame(layer_a_rows),
        reachability=pd.DataFrame(reachability_rows),
        layer_b=pd.DataFrame(layer_b_rows),
        baseline_b=pd.DataFrame(baseline_rows),
    )

    assert np.isclose(
        refs["layer_a"]["C1"]["T_sci_LRV"],
        100.0 * 2 + 10.0 + 2.5,
    )
    assert np.isclose(
        refs["layer_a"]["C1"]["T_sci_NSV_vector"],
        1000.0 * 2 + 10.0 + 2.5,
    )
    assert np.isclose(
        refs["reachability"]["h_D->C1"]["T_sci_SRE"],
        50.0 * 2 + 2.5,
    )


def test_layer_b_forced_descriptive_only():
    seeds = [25001, 25002, 25003, 25004, 25005]

    layer_a_rows = []
    reachability_rows = []
    layer_b_rows = []
    baseline_rows = []

    for seed in seeds:
        for rotation in range(6):
            for criterion_index in range(1, 8):
                layer_a_rows.append(
                    {
                        "seed": seed,
                        "rotation": rotation,
                        "criterion": f"C{criterion_index}",
                        "lrv50": 1.0,
                        "nsv_vector": 1.0,
                    }
                )

            reachability_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    "factor": "h_D",
                    "criterion": "C1",
                    "sre": 1.0,
                }
            )

            layer_b_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    "regret_mean": 10.0,
                }
            )

        baseline_rows.append(
            {
                "seed": seed,
                "regret_mean": 0.0,
            }
        )

    refs = d29.build_references(
        layer_a=pd.DataFrame(layer_a_rows),
        reachability=pd.DataFrame(reachability_rows),
        layer_b=pd.DataFrame(layer_b_rows),
        baseline_b=pd.DataFrame(baseline_rows),
    )

    assert refs["layer_b"]["activated"] is False
    assert refs["layer_b"]["T_R_sci"] is None
    assert refs["layer_b"]["paired_uplift_by_seed"]


def test_d29_does_not_use_old_or_reserved_seed_blocks_as_calibration():
    source = MODULE.read_text(
        encoding="utf-8"
    )

    assert "CALIBRATION_SEEDS = (25001, 25002, 25003, 25004, 25005)" in source
    assert "RESERVED_SEEDS = (26001, 26002, 26003, 26004, 26005)" in source
    assert "CALIBRATION_SEEDS = (21001" not in source
    assert "CALIBRATION_SEEDS = (22001" not in source
    assert "CALIBRATION_SEEDS = (23001" not in source
    assert "CALIBRATION_SEEDS = (24001" not in source
    assert "CALIBRATION_SEEDS = (26001" not in source