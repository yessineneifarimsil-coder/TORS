from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oracle_b100_background_diagnostic_v1.py"


def _load(name: str, path: Path):
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load("oracle_b100_background_diagnostic_v1_tested", MODULE_PATH)


@pytest.fixture(scope="module")
def oracle_spec():
    alphas = {
        "C1": 0.11,
        "C2": 0.04,
        "C3": 0.05,
        "C4": 0.07,
        "C5": 0.10,
        "C6": 0.14,
        "C7": 0.12,
        "C8": 0.16,
        "C9": 0.08,
        "C10": 0.13,
    }
    interactions = tuple(
        SimpleNamespace(left=left, right=right, beta=0.2)
        for left, right in (
            ("C1", "C2"),
            ("C3", "C7"),
            ("C4", "C5"),
            ("C6", "C10"),
            ("C8", "C9"),
        )
    )
    return SimpleNamespace(alphas=alphas, interactions=interactions)


@pytest.fixture(scope="module")
def synthetic_inputs():
    seed = 21001
    contexts = pd.DataFrame(
        {
            "replication_seed": seed,
            "context_id": [f"{seed}:{number:04d}" for number in range(1, 1201)],
            "context_number": np.arange(1, 1201, dtype=int),
        }
    )
    contexts["partition"] = np.where(
        contexts["context_number"].gt(1000),
        "test",
        np.where(contexts["context_number"].mod(5).eq(0), "weight", "fit"),
    )
    selection_master = contexts.loc[contexts.index.repeat(6)].copy().reset_index(drop=True)
    selection_master["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts)

    oracle_rows = selection_master.loc[
        selection_master["partition"].isin(["fit", "weight"])
    ].copy()
    context = oracle_rows["context_number"].to_numpy(dtype=float)
    alternative = oracle_rows["alternative_id"].str[1:].astype(int).to_numpy(dtype=float)
    for criterion_index in range(1, 11):
        values = (
            context * (criterion_index + 7)
            + alternative * (criterion_index * 3 + 1)
            + criterion_index**2
        ) % 991
        oracle_rows[f"q_C{criterion_index}"] = values / 991.0

    return oracle_rows.reset_index(drop=True), selection_master.reset_index(drop=True)


@pytest.fixture(scope="module")
def result(mod, oracle_spec, synthetic_inputs):
    oracle_rows, selection_master = synthetic_inputs
    return mod.compute_oracle_b100_background_diagnostic(
        oracle_rows,
        selection_master_rows=selection_master,
        replication_seed=21001,
        n_contexts=250,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )


def test_frozen_protocol_validates(mod):
    protocol = mod.validate_frozen_protocol()
    assert protocol["primary_oracle"]["remains_primary"] is True
    assert protocol["b100_diagnostic_oracle"]["background_size"] == 100
    assert protocol["b100_diagnostic_oracle"]["row_priority_namespace"] == 83001


def test_exact_background_and_weight_geometry(result):
    diagnostics = result.diagnostics
    assert diagnostics["full_fit_background_rows"] == 1200
    assert diagnostics["b100_background_rows"] == 100
    assert diagnostics["weight_evaluation_rows"] == 300
    assert diagnostics["same_weight_evaluation_rows"] is True
    assert diagnostics["only_background_moments_changed"] is True
    assert len(diagnostics["background_identity_sha256"]) == 64


def test_primary_full_fit_result_is_exact_existing_oracle(
    mod, oracle_spec, synthetic_inputs, result
):
    oracle_rows, _ = synthetic_inputs
    expected = mod.oracle_v1.compute_oracle_attribution_weights(
        oracle_rows,
        replication_seed=21001,
        n_contexts=250,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )
    assert result.full_fit_oracle == expected


def test_b100_membership_is_exact_frozen_treeshap_selection(
    mod, oracle_spec, synthetic_inputs, result
):
    oracle_rows, selection_master = synthetic_inputs
    fit, weight = mod.oracle_v1.prepare_oracle_attribution_rows(
        oracle_rows,
        replication_seed=21001,
        n_contexts=250,
    )
    selected, _ = mod.background_v1.select_background_rows(
        selection_master,
        replication_seed=21001,
        n_contexts=250,
    )
    mapped = mod._materialize_selected_fit_rows(fit, selected)
    expected_moments = mod.oracle_v1.compute_fit_background_moments(
        mapped,
        oracle_spec=oracle_spec,
    )
    expected = mod._weights_from_moments(
        weight,
        replication_seed=21001,
        n_contexts=250,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
        moments=expected_moments,
    )
    assert result.b100_oracle == expected
    assert result.diagnostics["background_identity_sha256"] == mod._background_identity_hash(mapped)


def test_only_background_moments_change(mod, oracle_spec, synthetic_inputs, result):
    oracle_rows, _ = synthetic_inputs
    _, weight = mod.oracle_v1.prepare_oracle_attribution_rows(
        oracle_rows,
        replication_seed=21001,
        n_contexts=250,
    )
    full_phi = mod.oracle_v1.closed_form_oracle_shapley(
        weight,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
        background_moments=result.full_fit_oracle.background_moments,
    )
    b100_phi = mod.oracle_v1.closed_form_oracle_shapley(
        weight,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
        background_moments=result.b100_oracle.background_moments,
    )
    assert full_phi.shape == b100_phi.shape == (300, 10)
    assert not np.array_equal(full_phi, b100_phi)


def test_vector_metrics_are_exact(result):
    full = np.array(
        [result.full_fit_oracle.weights_by_feature[f"g_C{i}"] for i in range(1, 11)]
    )
    b100 = np.array(
        [result.b100_oracle.weights_by_feature[f"g_C{i}"] for i in range(1, 11)]
    )
    difference = np.abs(b100 - full)
    metrics = result.vector_metrics
    assert metrics["MAE_w"] == pytest.approx(float(np.mean(difference)))
    assert metrics["TV_w"] == pytest.approx(float(0.5 * np.sum(difference)))
    assert metrics["max_absolute_weight_difference"] == pytest.approx(float(np.max(difference)))
    assert -1.0 <= metrics["Spearman_rho_w"] <= 1.0
    assert metrics["Spearman_rho_w_defined"] is True
    assert metrics["top3_overlap"] in {0.0, 1 / 3, 2 / 3, 1.0}
    assert metrics["top5_overlap"] in {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}


def test_per_feature_metrics_are_exact(result):
    for feature, row in result.per_feature.items():
        full = result.full_fit_oracle.weights_by_feature[feature]
        b100 = result.b100_oracle.weights_by_feature[feature]
        assert row["full_fit_oracle_weight"] == full
        assert row["b100_oracle_weight"] == b100
        assert row["absolute_weight_difference"] == abs(b100 - full)


def test_moment_metrics_are_exact(result):
    full = result.full_fit_oracle.background_moments
    b100 = result.b100_oracle.background_moments
    marginal = max(
        abs(b100.marginal_by_criterion[key] - full.marginal_by_criterion[key])
        for key in full.marginal_by_criterion
    )
    joint = max(
        abs(b100.joint_by_pair[key] - full.joint_by_pair[key])
        for key in full.joint_by_pair
    )
    assert result.moment_metrics == {
        "max_absolute_marginal_moment_difference": marginal,
        "max_absolute_joint_moment_difference": joint,
    }


def test_defined_coverage_and_no_equal_fallback(result):
    assert result.coverage == {
        "full_fit_weights_defined": True,
        "b100_weights_defined": True,
        "jointly_defined": True,
    }
    assert result.full_fit_oracle.diagnostics["equal_weight_fallback_used"] is False
    assert result.b100_oracle.diagnostics["equal_weight_fallback_used"] is False


def test_constant_q_is_undefined_without_equal_fallback(
    mod, oracle_spec, synthetic_inputs
):
    oracle_rows, selection_master = synthetic_inputs
    constant = oracle_rows.copy()
    for column in mod.Q_COLUMNS:
        constant[column] = 0.5
    result = mod.compute_oracle_b100_background_diagnostic(
        constant,
        selection_master_rows=selection_master,
        replication_seed=21001,
        n_contexts=25,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )
    assert result.coverage == {
        "full_fit_weights_defined": False,
        "b100_weights_defined": False,
        "jointly_defined": False,
    }
    assert result.full_fit_oracle.weights_by_feature is None
    assert result.b100_oracle.weights_by_feature is None
    assert all(value is None for row in result.per_feature.values() for value in row.values())
    assert result.vector_metrics == {
        "MAE_w": None,
        "TV_w": None,
        "max_absolute_weight_difference": None,
        "Spearman_rho_w": None,
        "Spearman_rho_w_defined": False,
        "top3_overlap": None,
        "top5_overlap": None,
    }


def test_input_order_invariance(mod, oracle_spec, synthetic_inputs, result):
    oracle_rows, selection_master = synthetic_inputs
    shuffled_oracle = oracle_rows.sample(frac=1.0, random_state=77101).reset_index(drop=True)
    shuffled_master = selection_master.sample(frac=1.0, random_state=77102).reset_index(drop=True)
    shuffled = mod.compute_oracle_b100_background_diagnostic(
        shuffled_oracle,
        selection_master_rows=shuffled_master,
        replication_seed=21001,
        n_contexts=250,
        oracle_spec=oracle_spec,
        lambda_value=0.5,
    )
    assert shuffled.full_fit_oracle == result.full_fit_oracle
    assert shuffled.b100_oracle == result.b100_oracle
    assert shuffled.per_feature == result.per_feature
    assert shuffled.vector_metrics == result.vector_metrics
    assert shuffled.moment_metrics == result.moment_metrics
    assert shuffled.diagnostics["background_identity_sha256"] == result.diagnostics["background_identity_sha256"]


def test_topk_ties_break_by_ascending_criterion_index(mod):
    weights = np.array([0.1, 0.2, 0.2, 0.2, 0.1, 0.05, 0.05, 0.04, 0.03, 0.03])
    assert mod._top_k_features(weights, 3) == ("g_C2", "g_C3", "g_C4")
    assert mod._top_k_features(weights, 5) == ("g_C2", "g_C3", "g_C4", "g_C1", "g_C5")


def test_spearman_constant_rank_vector_is_explicitly_undefined(mod):
    constant = np.full(10, 0.1)
    varying = np.arange(10, dtype=float)
    assert mod._spearman_rho(constant, varying) is None


def test_firewall_diagnostics_are_false(result):
    diagnostics = result.diagnostics
    assert diagnostics["external_test_rows_used_for_moments"] == 0
    assert diagnostics["external_test_rows_used_for_weight_evaluation"] == 0
    assert diagnostics["target_Y_used"] is False
    assert diagnostics["predictive_model_fit"] is False
    assert diagnostics["shap_package_used"] is False
    assert diagnostics["mcdm_executed"] is False
    assert diagnostics["winner_identity_used"] is False


def test_invalid_sample_size_fails_closed(mod, oracle_spec, synthetic_inputs):
    oracle_rows, selection_master = synthetic_inputs
    with pytest.raises(ValueError, match="not a frozen sample-size"):
        mod.compute_oracle_b100_background_diagnostic(
            oracle_rows,
            selection_master_rows=selection_master,
            replication_seed=21001,
            n_contexts=26,
            oracle_spec=oracle_spec,
            lambda_value=0.5,
        )


def test_module_has_no_writes_models_shap_or_mcdm_calls():
    text = MODULE_PATH.read_text(encoding="utf-8")
    for token in (
        ".to_csv(",
        ".to_json(",
        ".to_excel(",
        "open(",
        "XGBRegressor",
        "shap.TreeExplainer",
        "MOORA(",
        "TOPSIS(",
    ):
        assert token not in text
