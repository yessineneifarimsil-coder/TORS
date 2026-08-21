from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "treeshap_scientific_computation_v1.py"


def _load(name: str, path: Path):
    # spec_from_file_location() does not guarantee the repository root
    # is present on sys.path, while the implementation imports its
    # sibling as src.treeshap_background_v1.
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
    return _load("treeshap_scientific_computation_v1_tested", MODULE_PATH)


@pytest.fixture()
def master():
    seed = 21001
    contexts = []
    for c in range(1, 1201):
        if c <= 1000:
            partition = "weight" if c % 5 == 0 else "fit"
        else:
            partition = "test"
        contexts.append(
            {
                "context_id": f"{seed}:{c:04d}",
                "context_number": c,
                "replication_seed": seed,
                "partition": partition,
            }
        )

    cdf = pd.DataFrame(contexts)
    rows = cdf.loc[cdf.index.repeat(6)].copy().reset_index(drop=True)
    rows["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(cdf)

    alt_num = rows["alternative_id"].str[1:].astype(int).to_numpy(dtype=float)
    ctx = rows["context_number"].to_numpy(dtype=float)
    for j in range(1, 11):
        rows[f"g_C{j}"] = ((ctx * (j + 2) + alt_num * (j + 1)) % 997) / 997.0

    X = rows[[f"g_C{i}" for i in range(1, 11)]].to_numpy(dtype=float)
    rows["Y"] = X.sum(axis=1)
    return rows


class FakeExplanation:
    def __init__(self, values, base_values):
        self.values = values
        self.base_values = base_values


class FakeModel:
    last_init_kwargs = None
    last_fit_shape = None
    last_fit_target_shape = None

    def __init__(self, **kwargs):
        type(self).last_init_kwargs = dict(kwargs)

    def fit(self, X, y):
        type(self).last_fit_shape = tuple(X.shape)
        type(self).last_fit_target_shape = tuple(y.shape)
        return self

    def predict(self, X):
        return np.asarray(X, dtype=float).sum(axis=1)


class FakeExplainer:
    last_background_shape = None
    last_kwargs = None
    last_explain_shape = None

    def __init__(self, model, data, feature_perturbation, model_output):
        type(self).last_background_shape = tuple(np.asarray(data).shape)
        type(self).last_kwargs = {
            "feature_perturbation": feature_perturbation,
            "model_output": model_output,
        }
        self.model = model

    def __call__(self, X):
        X = np.asarray(X, dtype=float)
        type(self).last_explain_shape = tuple(X.shape)
        return FakeExplanation(values=X.copy(), base_values=np.zeros(len(X)))


class ZeroExplainer(FakeExplainer):
    def __call__(self, X):
        X = np.asarray(X, dtype=float)
        type(self).last_explain_shape = tuple(X.shape)
        return FakeExplanation(values=np.zeros_like(X), base_values=np.zeros(len(X)))


class ZeroPredictionModel(FakeModel):
    def predict(self, X):
        return np.zeros(len(X), dtype=float)


class BadAccuracyExplainer(FakeExplainer):
    def __call__(self, X):
        X = np.asarray(X, dtype=float)
        return FakeExplanation(values=np.zeros_like(X), base_values=np.zeros(len(X)))


def _install_fake_stack(monkeypatch, mod, model_cls=FakeModel, explainer_cls=FakeExplainer):
    monkeypatch.setattr(mod, "XGBRegressor", model_cls)
    monkeypatch.setattr(mod.shap, "TreeExplainer", explainer_cls)


def test_frozen_computation_protocol_validates(mod):
    configs = mod.validate_frozen_computation_protocol()
    assert configs["xgboost"]["frozen_parameters"]["n_estimators"] == 600
    assert configs["seeds"]["xgboost_production"]["estimator_random_state"] == 82002


@pytest.mark.parametrize(
    "n,fit_rows,weight_rows",
    [
        (25, 120, 30),
        (50, 240, 60),
        (100, 480, 120),
        (250, 1200, 300),
        (1000, 4800, 1200),
    ],
)
def test_prepare_fit_weight_rows_exact_nested_geometry(mod, master, n, fit_rows, weight_rows):
    fit, weight = mod.prepare_fit_weight_rows(
        master,
        replication_seed=21001,
        n_contexts=n,
    )
    assert len(fit) == fit_rows
    assert len(weight) == weight_rows
    assert fit["partition"].eq("fit").all()
    assert weight["partition"].eq("weight").all()
    assert fit["context_number"].max() <= n
    assert weight["context_number"].max() <= n


def test_prepare_fit_weight_rows_is_input_order_invariant(mod, master):
    fit1, weight1 = mod.prepare_fit_weight_rows(
        master,
        replication_seed=21001,
        n_contexts=250,
    )
    shuffled = master.sample(frac=1.0, random_state=77123).reset_index(drop=True)
    fit2, weight2 = mod.prepare_fit_weight_rows(
        shuffled,
        replication_seed=21001,
        n_contexts=250,
    )

    cols = ["context_number", "alternative_id"]
    assert list(fit1[cols].itertuples(index=False, name=None)) == list(
        fit2[cols].itertuples(index=False, name=None)
    )
    assert list(weight1[cols].itertuples(index=False, name=None)) == list(
        weight2[cols].itertuples(index=False, name=None)
    )


def test_scientific_compute_uses_frozen_fit_background_and_weight_contract(
    monkeypatch, mod, master
):
    _install_fake_stack(monkeypatch, mod)
    result = mod.compute_scientific_treeshap_weights(
        master,
        replication_seed=21001,
        n_contexts=25,
    )

    assert FakeModel.last_fit_shape == (120, 10)
    assert FakeModel.last_fit_target_shape == (120,)
    assert FakeExplainer.last_background_shape == (100, 10)
    assert FakeExplainer.last_explain_shape == (30, 10)
    assert FakeExplainer.last_kwargs == {
        "feature_perturbation": "interventional",
        "model_output": "raw",
    }

    kwargs = FakeModel.last_init_kwargs
    assert kwargs["n_estimators"] == 600
    assert kwargs["max_depth"] == 2
    assert kwargs["learning_rate"] == 0.05
    assert kwargs["subsample"] == 0.8
    assert kwargs["colsample_bytree"] == 0.8
    assert kwargs["min_child_weight"] == 5.0
    assert kwargs["reg_alpha"] == 0.0
    assert kwargs["reg_lambda"] == 1.0
    assert kwargs["objective"] == "reg:squarederror"
    assert kwargs["n_jobs"] == 1
    assert kwargs["verbosity"] == 0
    assert kwargs["random_state"] == 82002

    assert result.weights_defined is True
    assert result.weights_by_feature is not None
    assert np.isclose(sum(result.weights_by_feature.values()), 1.0)
    assert result.diagnostics["fit_rows"] == 120
    assert result.diagnostics["weight_rows"] == 30
    assert result.diagnostics["background_rows"] == 100
    assert result.diagnostics["external_test_rows_used_for_fit"] == 0
    assert result.diagnostics["external_test_rows_used_for_background"] == 0
    assert result.diagnostics["external_test_rows_used_for_global_shap_weights"] == 0
    assert result.diagnostics["mcdm_executed"] is False
    assert len(result.diagnostics["git_commit"]) == 40
    assert result.diagnostics["python"]
    assert set(result.diagnostics["software_versions"]) == {
        "numpy",
        "pandas",
        "scikit_learn",
        "xgboost",
        "shap",
        "pyyaml",
    }


def test_global_importance_is_mean_absolute_shap(monkeypatch, mod, master):
    _install_fake_stack(monkeypatch, mod)
    _, weight = mod.prepare_fit_weight_rows(
        master,
        replication_seed=21001,
        n_contexts=25,
    )
    expected_importance = np.mean(
        np.abs(weight.loc[:, mod.FEATURES].to_numpy(dtype=float)),
        axis=0,
    )
    expected_weights = expected_importance / expected_importance.sum()

    result = mod.compute_scientific_treeshap_weights(
        master,
        replication_seed=21001,
        n_contexts=25,
    )

    got_importance = np.array(
        [result.importance_by_feature[f] for f in mod.FEATURES],
        dtype=float,
    )
    got_weights = np.array(
        [result.weights_by_feature[f] for f in mod.FEATURES],
        dtype=float,
    )
    assert np.allclose(got_importance, expected_importance)
    assert np.allclose(got_weights, expected_weights)


def test_zero_importance_is_explicitly_undefined_without_equal_fallback(
    monkeypatch, mod, master
):
    _install_fake_stack(
        monkeypatch,
        mod,
        model_cls=ZeroPredictionModel,
        explainer_cls=ZeroExplainer,
    )
    result = mod.compute_scientific_treeshap_weights(
        master,
        replication_seed=21001,
        n_contexts=25,
    )
    assert result.weights_defined is False
    assert result.weights_by_feature is None
    assert result.diagnostics["undefined_shap_weight_vector"] is True
    assert result.diagnostics["equal_weight_fallback_used"] is False
    assert result.diagnostics["total_importance"] == 0.0


def test_local_accuracy_failure_raises_and_emits_no_result(monkeypatch, mod, master):
    _install_fake_stack(
        monkeypatch,
        mod,
        model_cls=FakeModel,
        explainer_cls=BadAccuracyExplainer,
    )
    with pytest.raises(mod.TreeSHAPNumericalError, match="local-accuracy invariant failed"):
        mod.compute_scientific_treeshap_weights(
            master,
            replication_seed=21001,
            n_contexts=25,
        )


def test_missing_feature_fails_before_model_fit(mod, master):
    damaged = master.drop(columns=["g_C10"])
    with pytest.raises(ValueError, match="missing columns"):
        mod.prepare_fit_weight_rows(
            damaged,
            replication_seed=21001,
            n_contexts=25,
        )


def test_invalid_N_fails_closed(mod, master):
    with pytest.raises(ValueError, match="not a frozen sample-size"):
        mod.prepare_fit_weight_rows(
            master,
            replication_seed=21001,
            n_contexts=26,
        )


def test_module_has_no_result_file_writes_or_mcdm_calls():
    text = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = [
        ".to_csv(",
        ".to_json(",
        ".to_excel(",
        "open(",
        "MOORA(",
        "TOPSIS(",
    ]
    for token in forbidden:
        assert token not in text


def test_background_identity_hash_uses_complete_frozen_identity(mod, master):
    fit, _ = mod.prepare_fit_weight_rows(
        master,
        replication_seed=21001,
        n_contexts=25,
    )
    background = fit.iloc[:100].copy()

    h1 = mod._background_identity_hash(background)

    changed_context_id = background.copy()
    changed_context_id.loc[0, "context_id"] = "DIFFERENT-CONTEXT-ID"
    h2 = mod._background_identity_hash(changed_context_id)

    changed_seed = background.copy()
    changed_seed.loc[0, "replication_seed"] = 21002
    h3 = mod._background_identity_hash(changed_seed)

    assert h1 != h2
    assert h1 != h3
    assert len(h1) == 64
