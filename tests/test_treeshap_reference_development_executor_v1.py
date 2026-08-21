from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "treeshap_reference_development_executor_v1.py"


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
    return _load("treeshap_reference_executor_v1_tested", MODULE_PATH)


def test_reference_condition_and_seed_are_hard_frozen(mod):
    configs = mod.load_configs()
    assert mod.REFERENCE_DEVELOPMENT_SEED == 21001
    assert mod.EXPECTED_REFERENCE_CONDITION == {
        "N": 250,
        "c": 0.30,
        "rho": 0.4,
        "lambda": 0.5,
        "alpha_structure": "heterogeneous_fixed",
    }
    assert configs["experiment"]["reference_condition"] == mod.EXPECTED_REFERENCE_CONDITION
    assert configs["seeds"]["development"] == [21001, 21002, 21003, 21004, 21005]


def _contexts(seed=21001):
    rows = []
    for c in range(1, 1201):
        partition = "test" if c > 1000 else ("weight" if c % 5 == 0 else "fit")
        rows.append(
            {
                "context_id": f"S{seed}_C{c:04d}",
                "context_number": c,
                "replication_seed": seed,
                "rho": 0.4,
                "partition": partition,
                "h_R": 0.5,
            }
        )
    return pd.DataFrame(rows)


def _response_master(contexts):
    rows = contexts.loc[contexts.index.repeat(6)].copy().reset_index(drop=True)
    rows["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts)
    rows["alternative_key"] = rows["alternative_id"]
    rows["alternative_name"] = rows["alternative_id"]
    for j in range(1, 11):
        rows[f"g_C{j}"] = 0.1 + 0.01 * j
        rows[f"x_C{j}"] = rows[f"g_C{j}"]
    return rows


class FakeStep1:
    @staticmethod
    def generate_master_contexts(replication_seed, rho, benchmark, experiment, seeds):
        contexts = _contexts(replication_seed)
        return contexts, contexts[["context_id", "context_number"]].copy()


class FakeStep2:
    @staticmethod
    def generate_master_technology_responses(contexts, replication_seed, benchmark):
        baseline = _response_master(contexts)
        caps = pd.DataFrame([{"alternative_key": "A1", "criterion": "C1", "amplitude": 0.5}])
        deps = pd.DataFrame([{"alternative_key": "A1"}])
        audit = baseline[["context_id", "context_number", "alternative_id"]].copy()
        return baseline, caps, deps, audit

    @staticmethod
    def compute_opportunities(contexts, benchmark):
        return contexts[["context_id", "context_number"]].copy()


class FakeD29:
    @staticmethod
    def build_candidate_responses(
        baseline, opportunities, capability_parameters, benchmark, replication_seed
    ):
        return baseline.copy()


class FakeStep3:
    @staticmethod
    def load_oracle_spec(benchmark):
        return object()

    @staticmethod
    def compute_oracle_utility(responses, *, oracle_spec, lambda_value):
        out = responses.copy()
        out["lambda"] = float(lambda_value)
        out["U_star"] = np.linspace(0.1, 0.9, len(out))
        return out


class FakeStep4:
    @staticmethod
    def validate_target_noise_protocol(experiment, seeds):
        return None

    @staticmethod
    def compute_signal_sd(oracle_master):
        return 0.2

    @staticmethod
    def master_noise_table(identities, *, replication_seed, namespace):
        out = identities.copy()
        out["target_noise_e"] = 0.0
        return out

    @staticmethod
    def add_relative_noise(oracle_master, *, c, signal_sd, noise_table):
        out = oracle_master.copy()
        out["c"] = float(c)
        out["signal_sd"] = float(signal_sd)
        out["imposed_noise_sd"] = float(c * signal_sd)
        out["target_noise_e"] = 0.0
        out["target_noise"] = 0.0
        out["Y"] = out["U_star"]
        return out


def _fake_configs(mod):
    return {
        "benchmark": {},
        "experiment": {"reference_condition": dict(mod.EXPECTED_REFERENCE_CONDITION)},
        "seeds": {
            "development": [21001, 21002, 21003, 21004, 21005],
            "target_noise": {"stream_namespace": 3001},
        },
    }


def _fake_modules():
    return {
        "step1": FakeStep1,
        "step2": FakeStep2,
        "step3": FakeStep3,
        "step4": FakeStep4,
        "d29": FakeD29,
    }


def test_build_reference_master_reconstructs_exact_partition_geometry(mod):
    master, audit = mod.build_reference_master(
        replication_seed=21001,
        configs=_fake_configs(mod),
        modules=_fake_modules(),
    )
    assert len(master) == 7200
    assert master["context_id"].nunique() == 1200
    assert int(master["partition"].isin(["fit", "weight"]).sum()) == 6000
    assert int(master["partition"].eq("test").sum()) == 1200
    assert audit["reference_fit_rows"] == 1200
    assert audit["reference_weight_rows"] == 300
    assert audit["production_generator"] == "d29_kernel"
    assert audit["external_test_used_for_signal_sd"] is False
    assert audit["external_test_used_for_model_fit"] is False
    assert audit["external_test_used_for_background"] is False
    assert audit["external_test_used_for_global_shap_weights"] is False
    assert audit["mcdm_executed"] is False


def test_executor_rejects_any_seed_other_than_21001(mod):
    with pytest.raises(ValueError, match="locked to development seed 21001"):
        mod.build_reference_master(
            replication_seed=21002,
            configs=_fake_configs(mod),
            modules=_fake_modules(),
        )


def test_execute_reference_once_is_guarded_and_serializes_only_result_contract(
    tmp_path, mod
):
    master, pipeline_audit = mod.build_reference_master(
        replication_seed=21001,
        configs=_fake_configs(mod),
        modules=_fake_modules(),
    )

    fake_result = SimpleNamespace(
        weights_defined=True,
        importance_by_feature={f"g_C{i}": 0.1 for i in range(1, 11)},
        weights_by_feature={f"g_C{i}": 0.1 for i in range(1, 11)},
        diagnostics={
            "total_importance": 1.0,
            "local_accuracy_max_absolute_error": 0.0,
            "local_accuracy_max_scaled_error": 0.0,
            "background_identity_sha256": "a" * 64,
        },
    )

    class FakeTreeSHAP:
        calls = 0

        @classmethod
        def compute_scientific_treeshap_weights(
            cls, frame, *, replication_seed, n_contexts
        ):
            cls.calls += 1
            assert len(frame) == 7200
            assert replication_seed == 21001
            assert n_contexts == 250
            return fake_result

    modules = _fake_modules()
    modules["treeshap"] = FakeTreeSHAP

    output = tmp_path / "reference.json"
    payload = mod.execute_reference_once(
        output_path=output,
        configs=_fake_configs(mod),
        modules=modules,
    )

    assert FakeTreeSHAP.calls == 1
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == payload
    assert payload["scientific_role"] == "development_reference_only_not_primary_evidence"
    assert payload["external_test_evaluated"] is False
    assert payload["mcdm_executed"] is False
    assert payload["primary_or_reserve_seed_used"] is False
    assert payload["pipeline_audit"] == pipeline_audit

    with pytest.raises(FileExistsError, match="refusing rerun"):
        mod.execute_reference_once(
            output_path=output,
            configs=_fake_configs(mod),
            modules=modules,
        )
    assert FakeTreeSHAP.calls == 1


def test_cli_requires_explicit_execute_flag(mod):
    with pytest.raises(SystemExit, match="Refusing to execute without explicit --execute"):
        mod.main([])


def test_executor_source_has_no_primary_reserve_mcdm_or_legacy_csv_logic():
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "11001" not in text
    assert "30001" not in text
    assert "MOORA(" not in text
    assert "TOPSIS(" not in text
    assert "read_csv(" not in text
    assert ".csv" not in text.lower()


def test_default_output_is_reference_development_only(mod):
    rel = mod.DEFAULT_OUTPUT.relative_to(ROOT).as_posix()
    assert rel == (
        "results/treeshap_reference_development_v1/"
        "seed21001_N250_c0p30_rho0p4_lambda0p5.json"
    )
