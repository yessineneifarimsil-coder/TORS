from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "v2_2_d2_8_numerical_null.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "d28_test_module",
        MODULE,
    )
    if spec is None or spec.loader is None:
        raise ImportError(MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["d28_test_module"] = module
    spec.loader.exec_module(module)
    return module


d28 = load()


def test_null_matrix_is_exactly_multiplicatively_separable():
    rng = np.random.default_rng(
        np.random.SeedSequence([76001, 6])
    )
    x = d28.make_null_matrix(rng, 6)

    ratio = x[:, 0] / x[:, 1]
    assert np.std(np.log(ratio), ddof=0) < 1e-12


def test_null_structural_metrics_are_numerically_small():
    rng = np.random.default_rng(
        np.random.SeedSequence([76001, 5])
    )
    x = d28.make_null_matrix(rng, 5)

    assert abs(d28.rank_one_energy(x)) < 1e-10
    assert d28.max_pairwise_lrv(x) < 1e-10
    assert d28.d27.nsv(x, "vector") < 1e-8


def test_frozen_null_design_constants():
    assert d28.NULL_MASTER_SEED == 76001
    assert d28.ACTIVE_COUNTS == (5, 6)
    assert d28.NULL_REPLICATES_PER_COUNT == 2000
    assert d28.N_CONTEXTS == 1000
    assert d28.FLOOR_NS == 1e-12
    assert d28.FLOOR_LRV == 1e-10
    assert d28.FLOOR_NSV == 1e-10
