from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "d3_alpha_dispersion_executor_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("d3_exec_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_q_transform_and_qmad_exact_simple_case():
    m = _load()
    g = np.array([0.0, 0.5, 1.0], dtype=float)
    q = m.q_transform(g)
    expected = np.log1p(2.0 * g) / np.log(3.0)
    assert np.allclose(q, expected)
    assert np.isclose(
        m.q_mad(g),
        np.mean(np.abs(expected - expected.mean())),
    )


def test_criterion_order_descending_with_index_tiebreak():
    m = _load()
    means = {f"C{i}": 0.1 for i in range(1, 11)}
    means["C4"] = 0.3
    means["C2"] = 0.2
    order = m.criterion_order(means)
    assert order[:2] == ["C4", "C2"]
    assert order[2:] == ["C1", "C3", "C5", "C6", "C7", "C8", "C9", "C10"]


def test_alpha_mapping_is_deterministic_and_balanced():
    m = _load()
    order = ["C10","C9","C8","C7","C6","C5","C4","C3","C2","C1"]
    spectrum = [0.16,0.14,0.13,0.12,0.11,0.10,0.08,0.07,0.05,0.04]
    out = m.derive_alpha_mappings(order, spectrum)
    assert out["dispersion_aligned"]["C10"] == 0.16
    assert out["dispersion_aligned"]["C1"] == 0.04
    assert out["dispersion_anti_aligned"]["C1"] == 0.16
    assert out["dispersion_anti_aligned"]["C10"] == 0.04
    assert all(v == 0.10 for v in out["balanced"].values())


def test_checkpoint_summary_and_convergence_use_world_level_mcse():
    m = _load()
    rows = []
    for w in range(1, 201):
        for j in range(1, 11):
            rows.append(
                {
                    "world_index": w,
                    "world_seed": 100000 + w,
                    "criterion": f"C{j}",
                    "q_mad": 0.05 + 0.01 * j + 1e-5 * ((w % 5) - 2),
                    "n_observations": 6000,
                }
            )
    table = pd.DataFrame(rows)
    out = m.convergence_decision(
        table,
        compare_pair=(150, 200),
        final_W=200,
        epsilon=1e-12,
        target=0.05,
    )
    assert out["order_stable"] is True
    assert out["precision_pass"] is True
    assert out["all_pass"] is True
    assert out["final_order"][0] == "C10"


def test_executor_never_uses_legacy_minmax_sd_for_mapping():
    text = PATH.read_text(encoding="utf-8")
    assert '"minmax_population_sd_used_for_mapping": False' in text
    assert "NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC" in text
    assert '"primary_11001_11030_used": False' in text
    assert '"reserve_30001_30005_used": False' in text
    assert '"external_TEST_used": False' in text
    assert '"v2_2_robustness_executed": False' in text
