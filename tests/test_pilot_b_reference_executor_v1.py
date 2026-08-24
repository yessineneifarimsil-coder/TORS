from __future__ import annotations

import inspect
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src import pilot_b_reference_executor_v1 as executor


def test_executor_is_locked_to_frozen_scope_and_commit():
    assert executor.BRANCH == "implement-weighting-mcdm-v1"
    assert executor.THRESHOLD_COMMIT == "90079c4b9917b0859878a855ed5fbeeac3d69282"
    assert executor.DEVELOPMENT_SEEDS == (21001, 21002, 21003, 21004, 21005)
    assert executor.REFERENCE_CONDITION == {"N": 250, "c": 0.30, "rho": 0.4, "lambda": 0.5}
    assert not set(executor.DEVELOPMENT_SEEDS) & set(executor.PRIMARY_SEEDS)
    assert not set(executor.DEVELOPMENT_SEEDS) & set(executor.RESERVE_SEEDS)


def test_default_result_path_is_single_reference_json():
    assert executor.DEFAULT_OUTPUT.name == "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
    assert executor.DEFAULT_OUTPUT.parent.name == "pilot_b_reference_v1"


def test_direct_cli_repository_bootstrap_precedes_src_imports():
    source = Path(executor.__file__).read_text(encoding="utf-8")
    bootstrap = source.index("if str(ROOT) not in sys.path:")
    first_src_import = source.index("from src import critic_weights_v1 as critic")
    assert bootstrap < first_src_import
    assert "sys.path.insert(0, str(ROOT))" in source[bootstrap:first_src_import]


def _mock_git(monkeypatch, *, branch=None, head=None, status="", ancestor_code=0):
    branch = executor.BRANCH if branch is None else branch
    head = "a" * 40 if head is None else head

    def fake_run_git(*args):
        if args == ("branch", "--show-current"):
            return branch
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return status
        raise AssertionError(args)

    monkeypatch.setattr(executor, "_run_git", fake_run_git)
    monkeypatch.setattr(
        executor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=ancestor_code, stdout="", stderr=""),
    )


def test_environment_guard_accepts_clean_post_threshold_commit(tmp_path, monkeypatch):
    _mock_git(monkeypatch)
    assert executor.assert_execution_environment(tmp_path / "absent.json") == "a" * 40


def test_environment_guard_rejects_wrong_branch(tmp_path, monkeypatch):
    _mock_git(monkeypatch, branch="main")
    with pytest.raises(RuntimeError, match="requires branch"):
        executor.assert_execution_environment(tmp_path / "absent.json")


def test_environment_guard_rejects_uncommitted_implementation(tmp_path, monkeypatch):
    _mock_git(monkeypatch, head=executor.THRESHOLD_COMMIT)
    with pytest.raises(RuntimeError, match="committed after"):
        executor.assert_execution_environment(tmp_path / "absent.json")


def test_environment_guard_rejects_missing_threshold_ancestor(tmp_path, monkeypatch):
    _mock_git(monkeypatch, ancestor_code=1)
    with pytest.raises(RuntimeError, match="not an ancestor"):
        executor.assert_execution_environment(tmp_path / "absent.json")


def test_environment_guard_rejects_dirty_worktree(tmp_path, monkeypatch):
    _mock_git(monkeypatch, status="?? stray.txt")
    with pytest.raises(RuntimeError, match="clean committed worktree"):
        executor.assert_execution_environment(tmp_path / "absent.json")


def test_environment_guard_refuses_result_overwrite(tmp_path, monkeypatch):
    _mock_git(monkeypatch)
    output = tmp_path / "result.json"
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing overwrite"):
        executor.assert_execution_environment(output)


def _contexts(seed):
    records = []
    for context_number in range(1, 1201):
        partition = "test" if context_number > 1000 else ("weight" if context_number % 5 == 0 else "fit")
        records.append({
            "context_id": f"S{seed}_C{context_number:04d}",
            "context_number": context_number,
            "replication_seed": seed,
            "partition": partition,
        })
    return pd.DataFrame(records)


def _master(contexts):
    rows = contexts.loc[contexts.index.repeat(6)].reset_index(drop=True)
    rows["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts)
    for criterion in range(1, 11):
        rows[f"g_C{criterion}"] = 0.02 * criterion
        rows[f"x_C{criterion}"] = rows[f"g_C{criterion}"]
    return rows


class FakeStep1:
    @staticmethod
    def generate_master_contexts(replication_seed, rho, benchmark, experiment, seeds):
        value = _contexts(replication_seed)
        return value, value[["context_id", "context_number"]].copy()


class FakeStep2:
    @staticmethod
    def generate_master_technology_responses(contexts, replication_seed, benchmark):
        rows = _master(contexts)
        return rows, pd.DataFrame([{"x": 1}]), pd.DataFrame([{"x": 1}]), rows[["context_id"]].copy()

    @staticmethod
    def compute_opportunities(contexts, benchmark):
        return contexts.copy()


class FakeD29:
    @staticmethod
    def build_candidate_responses(baseline, opportunities, capability_parameters, benchmark, replication_seed):
        return baseline.copy()


class FakeStep3:
    @staticmethod
    def load_oracle_spec(benchmark):
        return object()

    @staticmethod
    def compute_oracle_utility(responses, *, oracle_spec, lambda_value):
        rows = responses.copy()
        for criterion in range(1, 11):
            rows[f"q_C{criterion}"] = rows[f"g_C{criterion}"]
        rows["U_star"] = 0.5
        return rows


class FakeStep4:
    @staticmethod
    def validate_target_noise_protocol(experiment, seeds):
        return None

    @staticmethod
    def compute_signal_sd(oracle_master):
        return 0.1

    @staticmethod
    def master_noise_table(identities, *, replication_seed, namespace):
        out = identities.copy()
        out["target_noise_e"] = 0.0
        return out

    @staticmethod
    def add_relative_noise(oracle_master, *, c, signal_sd, noise_table):
        rows = oracle_master.copy()
        rows["Y"] = rows["U_star"]
        return rows


def fake_configs():
    return {
        "benchmark": {},
        "experiment": {"reference_condition": dict(executor.EXPECTED_EXPERIMENT_REFERENCE)},
        "seeds": {
            "development": list(executor.DEVELOPMENT_SEEDS),
            "target_noise": {"stream_namespace": 3001},
        },
    }


def fake_modules():
    return {"step1": FakeStep1, "step2": FakeStep2, "step3": FakeStep3, "step4": FakeStep4, "d29": FakeD29}


def test_master_reconstruction_preserves_full_test_for_evaluation():
    master, oracle_spec, audit = executor.build_reference_master(
        replication_seed=21002,
        configs=fake_configs(),
        modules=fake_modules(),
    )
    assert oracle_spec is not None
    assert len(master) == 7200
    assert master["partition"].eq("test").sum() == 1200
    assert master.loc[master["partition"].eq("test"), "context_id"].nunique() == 200
    assert audit["signal_sd_from_estimation_only"] == 0.1
    assert audit["primary_or_reserve_seed_used"] is False


@pytest.mark.parametrize("seed", [11001, 30001, 22001])
def test_master_reconstruction_rejects_every_nondevelopment_seed(seed):
    with pytest.raises(ValueError, match="only development seeds"):
        executor.build_reference_master(
            replication_seed=seed,
            configs=fake_configs(),
            modules=fake_modules(),
        )


def test_batch_record_preserves_coverage_and_all_frozen_metrics():
    batch = SimpleNamespace(summary={
        "contexts": 200,
        "kendall_tau_b_defined_contexts": 197,
        "mean_kendall_tau_b_defined_contexts": 0.6,
        "top1_accuracy": 0.7,
        "mean_normalized_oracle_regret": 0.08,
        "median_normalized_oracle_regret": 0.01,
        "p95_normalized_oracle_regret": 0.3,
    })
    result = executor._batch_record(batch, label_key="method", label="SHAP", seed=21001)
    assert result["method"] == "SHAP"
    assert result["test_contexts"] == 200
    assert result["kendall_defined_contexts"] == 197
    assert result["mean_kendall_tau_b"] == 0.6
    assert result["top1_accuracy"] == 0.7
    assert result["mean_normalized_oracle_regret"] == 0.08


def test_oracle_winner_records_require_exactly_200_contexts():
    rows = pd.DataFrame({
        "context_number": range(1001, 1201),
        "oracle_selected_top1": ["A1"] * 200,
    })
    result = executor._oracle_winner_records(rows, seed=21001)
    assert len(result) == 200
    with pytest.raises(AssertionError, match="requires 200"):
        executor._oracle_winner_records(rows.iloc[:-1], seed=21001)


def test_json_conversion_replaces_nan_with_null():
    assert executor._json_ready(np.nan) is None
    assert executor._json_ready({"x": np.float64(0.5), "y": np.array([1, 2])}) == {"x": 0.5, "y": [1, 2]}


def test_executor_source_requires_explicit_flag_clean_state_and_exclusive_write():
    source = inspect.getsource(executor)
    assert 'parser.add_argument("--execute", action="store_true"' in source
    assert '"status", "--porcelain"' in source
    assert 'output_path.open("x"' in source
    assert "merge-base" in source and "--is-ancestor" in source


def test_executor_source_calls_every_frozen_pilot_method_and_reference():
    source = inspect.getsource(executor.execute_seed)
    for token in [
        "compute_oracle_attribution_weights",
        "compute_scientific_treeshap_weights",
        "compute_permutation_importance_weights",
        "compute_ridge_plus_weights",
        "compute_critic_weights",
        "compute_entropy_weights",
        "compute_equal_weights",
        "generate_random_weight_reference",
        "estimate_majority_winner",
        "score_direct_xgboost_test_rows",
        "score_weights",
    ]:
        assert token in source


def test_executor_source_uses_moora_and_common_decision_metrics():
    scoring = inspect.getsource(executor._score_weights)
    assert 'method="MOORA"' in scoring
    assert "evaluate_decision_fidelity_batch" in scoring
    source = inspect.getsource(executor.execute_pilot_b_once)
    assert "evaluate_pilot_b_hard_stops" in source


def test_no_execute_flag_exits_before_scientific_work(monkeypatch):
    monkeypatch.setattr(executor, "execute_pilot_b_once", lambda **kwargs: pytest.fail("must not execute"))
    with pytest.raises(SystemExit, match="without explicit --execute"):
        executor.main([])


def test_main_reports_persisted_gate_decision(monkeypatch, capsys):
    fake = {
        "hard_stop_evaluation": {
            "gates": {"coverage_hard_stop": False},
            "hard_stop": False,
            "pilot_b_pass": True,
        }
    }
    monkeypatch.setattr(executor, "execute_pilot_b_once", lambda **kwargs: fake)
    assert executor.main(["--execute"]) == 0
    output = capsys.readouterr().out
    assert "PILOT_B_REFERENCE_EXECUTION_COMPLETE: True" in output
    assert "PILOT_B_PASS: True" in output


def test_execute_function_guards_before_loading_or_computing(tmp_path, monkeypatch):
    calls = []

    def guard(path):
        calls.append("guard")
        raise RuntimeError("blocked")

    monkeypatch.setattr(executor, "assert_execution_environment", guard)
    monkeypatch.setattr(executor, "load_configs", lambda: calls.append("configs"))
    with pytest.raises(RuntimeError, match="blocked"):
        executor.execute_pilot_b_once(output_path=tmp_path / "result.json")
    assert calls == ["guard"]
