from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "oracle_b100_background_diagnostic_reference_executor_v1.py"


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
    return _load("oracle_b100_reference_executor_v1_tested", MODULE_PATH)


def _contexts(seed: int = 21001) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "replication_seed": seed,
            "context_id": [f"{seed}:{number:04d}" for number in range(1, 1201)],
            "context_number": np.arange(1, 1201, dtype=int),
        }
    )
    frame["partition"] = np.where(
        frame["context_number"].gt(1000),
        "test",
        np.where(frame["context_number"].mod(5).eq(0), "weight", "fit"),
    )
    return frame


class FakeStep1:
    @staticmethod
    def generate_master_contexts(**kwargs):
        contexts = _contexts(int(kwargs["replication_seed"]))
        return contexts, pd.DataFrame({"context_number": np.arange(1, 1201)})


class FakeStep2:
    @staticmethod
    def generate_master_technology_responses(*, contexts, replication_seed, benchmark):
        rows = contexts.loc[contexts.index.repeat(6)].copy().reset_index(drop=True)
        rows["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts)
        context = rows["context_number"].to_numpy(dtype=float)
        alternative = rows["alternative_id"].str[1:].astype(int).to_numpy(dtype=float)
        for index in range(1, 11):
            rows[f"g_C{index}"] = ((context * (index + 1) + alternative) % 997) / 997.0
        capability = pd.DataFrame({"row": np.arange(42)})
        deployment = pd.DataFrame({"row": np.arange(6)})
        audit = pd.DataFrame({"row": np.arange(7200)})
        return rows, capability, deployment, audit

    @staticmethod
    def compute_opportunities(*, contexts, benchmark):
        return contexts[["context_id", "context_number"]].copy()


class FakeD29:
    @staticmethod
    def build_candidate_responses(**kwargs):
        return kwargs["baseline"].copy()


class FakeStep3:
    partitions_seen = None

    @classmethod
    def load_oracle_spec(cls, benchmark):
        return SimpleNamespace(name="fake_oracle_spec")

    @classmethod
    def compute_oracle_utility(cls, responses, *, oracle_spec, lambda_value):
        cls.partitions_seen = set(responses["partition"].unique())
        rows = responses.copy()
        for index in range(1, 11):
            rows[f"q_C{index}"] = rows[f"g_C{index}"]
        rows["U_star"] = rows[[f"q_C{i}" for i in range(1, 11)]].mean(axis=1)
        return rows


def _configs():
    return {
        "benchmark": {},
        "experiment": {},
        "seeds": {"development": [21001, 21002, 21003, 21004, 21005]},
        "protocol": {},
    }


def _modules(diagnostic=None):
    return {
        "step1": FakeStep1,
        "step2": FakeStep2,
        "step3": FakeStep3,
        "d29": FakeD29,
        "diagnostic": diagnostic,
    }


def test_executor_is_locked_to_frozen_reference(mod):
    assert mod.REFERENCE_DEVELOPMENT_SEED == 21001
    assert mod.REFERENCE_CONDITION == {"N": 250, "rho": 0.4, "lambda": 0.5}
    assert mod.PROTOCOL_COMMIT == "f98c23f"
    assert mod.FROZEN_TREESHAP_REFERENCE_BACKGROUND_IDENTITY_SHA256 == (
        "3184c675397c8caf547a8da7f68d04a589b949ce39a1953bbf55d4461646eda1"
    )


def test_build_reference_uses_test_identities_but_not_test_oracle_values(mod):
    oracle_rows, selection_master, oracle_spec, audit = mod.build_reference_oracle_inputs(
        replication_seed=21001,
        configs=_configs(),
        modules=_modules(),
    )
    assert len(selection_master) == 7200
    assert selection_master["partition"].eq("test").sum() == 1200
    assert len(oracle_rows) == 6000
    assert set(oracle_rows["partition"]) == {"fit", "weight"}
    assert FakeStep3.partitions_seen == {"fit", "weight"}
    assert audit["external_test_rows_used_for_oracle_utility"] == 0
    assert audit["external_test_rows_used_for_background_moments"] == 0
    assert audit["external_test_rows_used_for_weight_evaluation"] == 0
    assert audit["target_Y_generated"] is False
    assert oracle_spec.name == "fake_oracle_spec"


def test_build_reference_rejects_nondevelopment_seed(mod):
    with pytest.raises(ValueError, match="locked to development seed 21001"):
        mod.build_reference_oracle_inputs(
            replication_seed=11001,
            configs=_configs(),
            modules=_modules(),
        )


def test_no_execute_flag_refuses_without_result(mod, tmp_path):
    with pytest.raises(SystemExit, match="Refusing to execute without explicit --execute"):
        mod.main([])
    assert list(tmp_path.iterdir()) == []


def test_existing_output_refuses_before_git_or_science(monkeypatch, mod, tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("already frozen\n", encoding="utf-8")
    called = {"git": False}

    def forbidden_git():
        called["git"] = True
        raise AssertionError("Git/science must not run after overwrite refusal.")

    monkeypatch.setattr(mod, "require_clean_committed_state", forbidden_git)
    with pytest.raises(FileExistsError, match="refusing rerun"):
        mod.execute_reference_once(output_path=output)
    assert called["git"] is False
    assert output.read_text(encoding="utf-8") == "already frozen\n"


def test_execute_persists_one_guarded_payload(monkeypatch, mod, tmp_path):
    output = tmp_path / "reference.json"
    monkeypatch.setattr(
        mod,
        "require_clean_committed_state",
        lambda: ("a" * 40, "implement-weighting-mcdm-v1"),
    )
    oracle_rows = pd.DataFrame({"placeholder": [1]})
    selector = pd.DataFrame({"placeholder": [2]})
    spec = SimpleNamespace(name="spec")
    pipeline_audit = {
        "target_Y_generated": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
    }
    monkeypatch.setattr(
        mod,
        "build_reference_oracle_inputs",
        lambda **kwargs: (oracle_rows, selector, spec, pipeline_audit),
    )

    full = SimpleNamespace(
        replication_seed=21001,
        n_contexts=250,
        lambda_value=0.5,
        weights_defined=True,
        importance_by_feature={"g_C1": 1.0},
        weights_by_feature={"g_C1": 1.0},
        background_moments=SimpleNamespace(
            marginal_by_criterion={"C1": 0.5},
            joint_by_pair={"C1|C2": 0.25},
        ),
        diagnostics={"total_importance": 1.0, "equal_weight_fallback_used": False},
    )
    fake_result = SimpleNamespace(
        replication_seed=21001,
        n_contexts=250,
        lambda_value=0.5,
        full_fit_oracle=full,
        b100_oracle=full,
        per_feature={
            "g_C1": {
                "full_fit_oracle_weight": 1.0,
                "b100_oracle_weight": 1.0,
                "absolute_weight_difference": 0.0,
            }
        },
        vector_metrics={
            "MAE_w": 0.0,
            "TV_w": 0.0,
            "max_absolute_weight_difference": 0.0,
            "Spearman_rho_w": None,
            "Spearman_rho_w_defined": False,
            "top3_overlap": 1.0,
            "top5_overlap": 1.0,
        },
        moment_metrics={
            "max_absolute_marginal_moment_difference": 0.0,
            "max_absolute_joint_moment_difference": 0.0,
        },
        coverage={
            "full_fit_weights_defined": True,
            "b100_weights_defined": True,
            "jointly_defined": True,
        },
        diagnostics={
            "background_identity_sha256": (
                mod.FROZEN_TREESHAP_REFERENCE_BACKGROUND_IDENTITY_SHA256
            )
        },
    )
    monkeypatch.setattr(
        mod,
        "asdict",
        lambda value: {
            "replication_seed": value.replication_seed,
            "n_contexts": value.n_contexts,
            "lambda_value": value.lambda_value,
            "per_feature": value.per_feature,
            "vector_metrics": value.vector_metrics,
            "moment_metrics": value.moment_metrics,
            "coverage": value.coverage,
            "diagnostics": value.diagnostics,
        },
    )

    class FakeDiagnostic:
        @staticmethod
        def compute_oracle_b100_background_diagnostic(*args, **kwargs):
            return fake_result

    payload = mod.execute_reference_once(
        output_path=output,
        configs=_configs(),
        modules={"diagnostic": FakeDiagnostic},
    )
    assert output.is_file()
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == payload
    assert payload["background_identity_matches_frozen_treeshap_reference"] is True
    assert payload["primary_oracle_replaced"] is False
    assert payload["new_weighting_method_created"] is False
    assert payload["equal_fallback_used"] is False
    assert payload["external_test_evaluated"] is False
    assert payload["target_Y_used"] is False
    assert payload["predictive_model_fit"] is False
    assert payload["shap_package_used"] is False
    assert payload["mcdm_executed"] is False
    assert payload["primary_or_reserve_seed_used"] is False


def test_hash_mismatch_emits_no_result(monkeypatch, mod, tmp_path):
    output = tmp_path / "must_not_exist.json"
    monkeypatch.setattr(
        mod,
        "require_clean_committed_state",
        lambda: ("b" * 40, "implement-weighting-mcdm-v1"),
    )
    monkeypatch.setattr(
        mod,
        "build_reference_oracle_inputs",
        lambda **kwargs: (
            pd.DataFrame({"x": [1]}),
            pd.DataFrame({"x": [1]}),
            SimpleNamespace(),
            {},
        ),
    )

    class WrongHashDiagnostic:
        @staticmethod
        def compute_oracle_b100_background_diagnostic(*args, **kwargs):
            return SimpleNamespace(diagnostics={"background_identity_sha256": "wrong"})

    with pytest.raises(RuntimeError, match="does not match"):
        mod.execute_reference_once(
            output_path=output,
            configs=_configs(),
            modules={"diagnostic": WrongHashDiagnostic},
        )
    assert not output.exists()


def test_executor_imports_no_target_noise_model_or_shap_package():
    text = MODULE_PATH.read_text(encoding="utf-8")
    for token in (
        "04_generate_noisy_target.py",
        "XGBRegressor",
        "shap.TreeExplainer",
        "compute_scientific_treeshap_weights",
        "MOORA(",
        "TOPSIS(",
    ):
        assert token not in text
