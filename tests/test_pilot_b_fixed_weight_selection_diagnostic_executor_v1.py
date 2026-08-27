from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import pilot_b_fixed_weight_selection_diagnostic_executor_v1 as executor


EXECUTOR_PATH = ROOT / "src" / "pilot_b_fixed_weight_selection_diagnostic_executor_v1.py"
CORE_PATH = ROOT / "src" / "pilot_b_fixed_weight_selection_diagnostic_v1.py"
PROTOCOL_PATH = ROOT / "config" / "pilot_b_fixed_weight_selection_diagnostic_v1.json"


def test_protocol_commit_and_frozen_result_identity_are_exact():
    assert executor.PROTOCOL_COMMIT == "33bd9dab4e0f1c32eed43163ded28d15f8e03883"
    assert executor.FROZEN_RESULT_COMMIT == "f2f573aad96e1813cfc55938a101fdee18aa7395"
    assert executor.FROZEN_RESULT_SHA256 == (
        "0507285715b0f21d32744da543cd769fc269e12084b6c6819a863fca9f787a88"
    )


def test_protocol_and_executor_output_path_match():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert executor.DEFAULT_OUTPUT.relative_to(ROOT).as_posix() == (
        protocol["execution_policy"]["output_path"]
    )


def test_direct_cli_requires_explicit_execute_flag():
    result = subprocess.run(
        [sys.executable, "-B", str(EXECUTOR_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "explicit --execute" in (result.stdout + result.stderr)


def test_direct_cli_loader_bootstraps_root_before_src_imports():
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    root_assignment = source.index("ROOT = Path(__file__).resolve().parents[1]")
    path_insert = source.index("sys.path.insert(0, str(ROOT))")
    src_import = source.index("from src import")
    assert root_assignment < path_insert < src_import


def test_executor_does_not_load_target_y_step_or_learning_modules():
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "src.treeshap_scientific_computation_v1" not in imported
    assert "src.permutation_importance_weights_v1" not in imported
    assert "src.ridge_plus_weights_v1" not in imported
    assert "src.critic_weights_v1" not in imported
    assert "src.entropy_weights_v1" not in imported
    assert "04_generate_noisy_target.py" not in source
    assert "step4" not in source


def test_core_has_no_file_write_or_generator_execution():
    source = CORE_PATH.read_text(encoding="utf-8")
    assert ".write_text(" not in source
    assert ".open(" not in source
    assert "generate_master_contexts" not in source
    assert "build_candidate_responses" not in source
    assert "model.fit" not in source
    assert "bootstrap" in source.lower()


def test_build_decision_master_rejects_protected_seed_before_modules_are_used():
    with pytest.raises(ValueError, match="development worlds"):
        executor.build_decision_master(
            development_world=11001,
            configs={"benchmark": {}, "experiment": {}, "seeds": {}},
            modules={},
        )


def test_execution_environment_refuses_existing_output(monkeypatch, tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(executor, "_run_git", lambda *args: (
        executor.BRANCH if args == ("branch", "--show-current")
        else "a" * 40 if args == ("rev-parse", "HEAD")
        else ""
    ))
    monkeypatch.setattr(executor, "_require_ancestor", lambda *args: None)
    with pytest.raises(FileExistsError, match="overwrite"):
        executor.assert_execution_environment(output)


def test_json_ready_preserves_plain_values_and_converts_numpy():
    import numpy as np

    value = executor._json_ready({
        "integer": np.int64(2),
        "floating": np.float64(0.5),
        "boolean": np.bool_(True),
        "array": np.asarray([1.0, 2.0]),
    })
    assert value == {
        "integer": 2, "floating": 0.5, "boolean": True, "array": [1.0, 2.0]
    }
