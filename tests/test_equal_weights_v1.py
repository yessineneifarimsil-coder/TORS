from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "equal_weights_v1.py"

spec = importlib.util.spec_from_file_location(
    "equal_weights_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load equal_weights_v1.py for tests.")

equal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = equal
spec.loader.exec_module(equal)


def test_frozen_feature_order_is_g_c1_through_g_c10():
    assert equal.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))


def test_frozen_equal_weight_is_point_one():
    assert equal.N_CRITERIA == 10
    assert equal.EQUAL_WEIGHT == 0.1


def test_compute_equal_weights_returns_exact_ten_feature_mapping():
    result = equal.compute_equal_weights()
    assert result.weights_by_feature == {
        f"g_C{i}": 0.1 for i in range(1, 11)
    }


def test_equal_weights_sum_to_one():
    result = equal.compute_equal_weights()
    assert abs(sum(result.weights_by_feature.values()) - 1.0) <= 1.0e-12


def test_equal_weights_are_deterministic_across_calls():
    first = equal.compute_equal_weights()
    second = equal.compute_equal_weights()
    assert first == second


def test_equal_baseline_uses_no_scientific_data_or_seed():
    result = equal.compute_equal_weights()
    diagnostics = result.diagnostics

    assert diagnostics["data_used"] is False
    assert diagnostics["partition_used"] is None
    assert diagnostics["replication_seed_used"] is False
    assert diagnostics["target_Y_used"] is False
    assert diagnostics["oracle_utility_used"] is False
    assert diagnostics["shap_used"] is False
    assert diagnostics["mcdm_executed"] is False
    assert diagnostics["winner_inspected"] is False


def test_equal_baseline_is_not_a_fallback_event():
    result = equal.compute_equal_weights()
    assert result.diagnostics["method"] == "Equal"
    assert result.diagnostics["fallback"] is False
