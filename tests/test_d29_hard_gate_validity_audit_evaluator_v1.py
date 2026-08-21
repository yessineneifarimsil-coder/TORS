from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "d29_hard_gate_validity_audit_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_validity_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_constants_and_frozen_formula_sources():
    m = _load()
    assert m.AUDIT_SEEDS == (29001,29002,29003,29004,29005)
    assert m.D29_SEEDS == (25001,25002,25003,25004,25005)
    assert m.ROTATIONS == (0,1,2,3,4,5)
    assert m.DELTA == 0.05
    assert m.SUPPORT_EQUIVALENT == ("C1","C2","C4","C6","C7")
    assert m.SUPPORT_MISMATCH == ("C3","C5")
    assert m.d29.DELTA == m.v40.DELTA == 0.05


def test_six_rotation_layer_aggregation_is_median_within_seed_then_across():
    m = _load()
    rows = []
    for seed_offset, seed in enumerate(m.AUDIT_SEEDS):
        for rotation in m.ROTATIONS:
            for cidx, criterion in enumerate(m.C1_C7):
                rows.append(
                    {
                        "seed": seed,
                        "rotation": rotation,
                        "criterion": criterion,
                        "lrv50": seed_offset + rotation + cidx,
                        "nsv_vector": 10 + seed_offset + 2 * rotation + cidx,
                    }
                )
    out = m.aggregate_six_rotation_layer(pd.DataFrame(rows))
    c1 = out.loc[out["criterion"] == "C1"].iloc[0]

    # Per seed LRV medians: 2.5,3.5,4.5,5.5,6.5 -> across-seed median 4.5.
    assert c1["six_rotation_median_LRV50"] == 4.5
    # Per seed NSV medians: 15,16,17,18,19 -> across-seed median 17.
    assert c1["six_rotation_median_NSV_vector"] == 17.0


def test_shortfall_fraction_closed_has_no_posthoc_cutoff():
    m = _load()
    assert np.isclose(m.shortfall_fraction_closed(0.70, 0.85), 0.5)
    assert np.isclose(m.shortfall_fraction_closed(0.70, 1.00), 1.0)
    assert np.isnan(m.shortfall_fraction_closed(1.01, 1.02))


def test_exact_rotation_combination_count_is_7776():
    m = _load()
    assert sum(1 for _ in itertools.product(m.ROTATIONS, repeat=5)) == 7776
