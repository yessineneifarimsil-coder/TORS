from __future__ import annotations

"""Guarded executor for the frozen fixed-weight selection diagnostic v1."""

import argparse
import hashlib
from importlib import util as importlib_util
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from pathlib import Path
import platform
import subprocess
import sys
from types import ModuleType
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import yaml

from src import pilot_b_fixed_weight_selection_diagnostic_v1 as diagnostic


SRC = ROOT / "src"
CONFIG = ROOT / "config"
RESULTS = ROOT / "results"

BRANCH = "implement-weighting-mcdm-v1"
PROTOCOL_COMMIT = "33bd9dab4e0f1c32eed43163ded28d15f8e03883"
FROZEN_RESULT_COMMIT = "f2f573aad96e1813cfc55938a101fdee18aa7395"
FROZEN_RESULT_SHA256 = "0507285715b0f21d32744da543cd769fc269e12084b6c6819a863fca9f787a88"
REFERENCE_CONDITION = {"N": 250, "c": 0.30, "rho": 0.4, "lambda": 0.5}
EXPECTED_EXPERIMENT_REFERENCE = {
    "N": 250,
    "c": 0.30,
    "rho": 0.4,
    "lambda": 0.5,
    "alpha_structure": "heterogeneous_fixed",
}

PROTOCOL_PATH = CONFIG / "pilot_b_fixed_weight_selection_diagnostic_v1.json"
BENCHMARK_PATH = CONFIG / "benchmark.yaml"
EXPERIMENT_PATH = CONFIG / "experiment.yaml"
SEEDS_PATH = CONFIG / "seeds.yaml"
FROZEN_RESULT_PATH = (
    RESULTS
    / "pilot_b_reference_v1"
    / "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
)
DEFAULT_OUTPUT = (
    RESULTS
    / "pilot_b_fixed_weight_selection_diagnostic_v1"
    / "pilot_b_fixed_weight_selection_N250_c0p30_rho0p4_lambda0p5.json"
)

STEP1_PATH = SRC / "01_generate_contexts.py"
STEP2_PATH = SRC / "02_generate_technology_responses.py"
STEP3_PATH = SRC / "03_generate_oracle_utility.py"
D29_PATH = SRC / "v4_0_f1_terminal_d29_kernel_evaluator.py"


def _run_git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def _require_ancestor(commit: str, label: str) -> None:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Required {label} commit is not an ancestor: {commit}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_execution_environment(output_path: Path = DEFAULT_OUTPUT) -> str:
    """Require committed implementation, clean tree, frozen ancestry and no output."""
    if _run_git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Diagnostic requires branch {BRANCH}.")
    head = _run_git("rev-parse", "HEAD")
    if len(head) != 40 or head == PROTOCOL_COMMIT:
        raise RuntimeError("Diagnostic implementation must be committed after its protocol.")
    _require_ancestor(PROTOCOL_COMMIT, "diagnostic protocol")
    _require_ancestor(FROZEN_RESULT_COMMIT, "frozen Pilot-B result")
    if _run_git("status", "--porcelain"):
        raise RuntimeError("Diagnostic execution requires a completely clean worktree/index.")
    if Path(output_path).exists():
        raise FileExistsError(f"Refusing to overwrite diagnostic result: {output_path}")
    if not FROZEN_RESULT_PATH.is_file() or _sha256(FROZEN_RESULT_PATH) != FROZEN_RESULT_SHA256:
        raise RuntimeError("Frozen Pilot-B input result is missing or changed.")
    return head


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    return value


def load_configs_and_protocol() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    benchmark = _load_yaml(BENCHMARK_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    seeds = _load_yaml(SEEDS_PATH)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if experiment.get("reference_condition") != EXPECTED_EXPERIMENT_REFERENCE:
        raise ValueError("Frozen experiment reference condition changed.")
    if tuple(seeds.get("development", ())) != diagnostic.DEVELOPMENT_WORLDS:
        raise ValueError("Frozen development worlds changed.")
    if protocol["schema"] != "pilot_b_fixed_weight_selection_diagnostic_protocol_v1":
        raise ValueError("Fixed-weight selection diagnostic protocol schema changed.")
    if protocol["parent_commit"] != FROZEN_RESULT_COMMIT:
        raise ValueError("Diagnostic protocol closure parent changed.")
    if protocol["scope"]["development_worlds"] != list(diagnostic.DEVELOPMENT_WORLDS):
        raise ValueError("Diagnostic protocol world scope changed.")
    if protocol["scope"]["reference_condition"] != REFERENCE_CONDITION:
        raise ValueError("Diagnostic reference condition changed.")
    if protocol["scope"]["observed_fixed_weight_methods"] != list(diagnostic.METHODS):
        raise ValueError("Diagnostic observed method set changed.")
    if protocol["per_context_output"]["required_record_count"] != diagnostic.EXPECTED_TOTAL_RECORDS:
        raise ValueError("Diagnostic record-count requirement changed.")
    if protocol["bootstrap_policy"]["paired_context_bootstrap_executed_in_this_layer"] is not False:
        raise ValueError("Bootstrap firewall changed.")
    if any(protocol["decision_authority"].values()):
        raise ValueError("Closed-decision authority firewall changed.")
    return {"benchmark": benchmark, "experiment": experiment, "seeds": seeds}, protocol


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib_util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load frozen generator module {path}.")
    module = importlib_util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_generator_modules() -> dict[str, ModuleType]:
    """Load only context, response, oracle and D29 modules; never target-Y step 4."""
    return {
        "step1": _load_module("fixed_selection_step1", STEP1_PATH),
        "step2": _load_module("fixed_selection_step2", STEP2_PATH),
        "step3": _load_module("fixed_selection_step3", STEP3_PATH),
        "d29": _load_module("fixed_selection_d29", D29_PATH),
    }


def build_decision_master(
    *,
    development_world: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconstruct D29 G and oracle U_star only; target Y is never generated."""
    world = int(development_world)
    if world not in diagnostic.DEVELOPMENT_WORLDS:
        raise ValueError("Only development worlds 21001--21005 are permitted.")
    if world in diagnostic.PRIMARY_SEEDS or world in diagnostic.RESERVE_SEEDS:
        raise AssertionError("Protected primary/reserve seed reached reconstruction.")
    benchmark, experiment, seeds = (
        configs["benchmark"], configs["experiment"], configs["seeds"]
    )
    step1, step2, step3, d29 = (
        modules["step1"], modules["step2"], modules["step3"], modules["d29"]
    )
    contexts, context_audit = step1.generate_master_contexts(
        replication_seed=world,
        rho=REFERENCE_CONDITION["rho"],
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )
    baseline, capability, deployment, response_audit = (
        step2.generate_master_technology_responses(
            contexts=contexts, replication_seed=world, benchmark=benchmark
        )
    )
    opportunities = step2.compute_opportunities(contexts=contexts, benchmark=benchmark)
    responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability,
        benchmark=benchmark,
        replication_seed=world,
    )
    for criterion in ("C8", "C9", "C10"):
        column = f"g_{criterion}"
        if not np.array_equal(
            baseline[column].to_numpy(dtype=float),
            responses[column].to_numpy(dtype=float),
        ):
            raise AssertionError(f"Protected D29 column {column} changed.")
    oracle_spec = step3.load_oracle_spec(benchmark)
    master = step3.compute_oracle_utility(
        responses,
        oracle_spec=oracle_spec,
        lambda_value=REFERENCE_CONDITION["lambda"],
    )
    if "Y" in master.columns:
        raise AssertionError("Target Y unexpectedly exists in the diagnostic master.")
    test = master.loc[master["partition"].eq("test")]
    if len(master) != 7200 or len(test) != 1200 or test["context_id"].nunique() != 200:
        raise AssertionError("Frozen D29 TEST geometry changed.")
    required = {"U_star", *diagnostic.FEATURES}
    if not required <= set(master.columns):
        raise AssertionError("Diagnostic master lacks frozen G or oracle U_star.")
    return master, {
        "development_world": world,
        "master_contexts": int(contexts["context_id"].nunique()),
        "master_rows": int(len(master)),
        "test_contexts": int(test["context_id"].nunique()),
        "test_rows": int(len(test)),
        "context_audit_rows": int(len(context_audit)),
        "response_audit_rows": int(len(response_audit)),
        "capability_parameter_rows": int(len(capability)),
        "deployment_parameter_rows": int(len(deployment)),
        "target_y_generated": False,
        "model_fit_or_prediction_executed": False,
        "weight_estimation_executed": False,
        "shap_or_pi_executed": False,
        "primary_or_reserve_seed_used": False,
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _runtime_provenance(execution_commit: str) -> dict[str, Any]:
    versions: dict[str, str] = {}
    for key, distribution in {
        "numpy": "numpy", "pandas": "pandas", "scipy": "scipy", "pyyaml": "pyyaml",
    }.items():
        try:
            versions[key] = package_version(distribution)
        except PackageNotFoundError as exc:
            raise RuntimeError(f"Missing provenance distribution {distribution}.") from exc
    return {
        "execution_git_commit": execution_commit,
        "branch": BRANCH,
        "python": platform.python_version(),
        "software_versions": versions,
    }


def execute_diagnostic_once(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Execute the five-world descriptive diagnostic and persist exactly once."""
    output_path = Path(output_path)
    execution_commit = assert_execution_environment(output_path)
    configs, protocol = load_configs_and_protocol()
    modules = load_generator_modules()
    frozen_result = json.loads(FROZEN_RESULT_PATH.read_text(encoding="utf-8"))
    if frozen_result["development_seeds"] != list(diagnostic.DEVELOPMENT_WORLDS):
        raise ValueError("Frozen Pilot-B result world order changed.")
    by_world = {
        int(row["replication_seed"]): row for row in frozen_result["seed_results"]
    }
    if tuple(by_world) != diagnostic.DEVELOPMENT_WORLDS:
        raise ValueError("Frozen Pilot-B seed-result order changed.")

    all_records: list[dict[str, Any]] = []
    all_summaries: list[dict[str, Any]] = []
    all_pairwise: list[dict[str, Any]] = []
    all_validations: list[dict[str, Any]] = []
    reconstruction_audits: list[dict[str, Any]] = []
    for world in diagnostic.DEVELOPMENT_WORLDS:
        seed_result = by_world[world]
        master, reconstruction_audit = build_decision_master(
            development_world=world, configs=configs, modules=modules
        )
        weights = diagnostic.extract_archived_weights(seed_result)
        majority = diagnostic.extract_majority_winner(seed_result)
        records = diagnostic.build_context_records(
            master,
            weights,
            development_world=world,
            majority_winner_alternative_id=majority,
        )
        summaries = diagnostic.summarize_context_records(
            records, development_world=world
        )
        validations = diagnostic.validate_reconstructed_aggregates(
            summaries, seed_result
        )
        archived_oracle = {
            int(row["context_number"]): str(row["oracle_selected_top1"])
            for row in seed_result["oracle_winner_contexts"]
        }
        reconstructed_oracle = {
            int(str(row["test_context_id"]).rsplit("C", 1)[1]):
            str(row["oracle_selected_alternative_id"])
            for row in records if row["method"] == diagnostic.METHODS[0]
        }
        if reconstructed_oracle != archived_oracle:
            raise AssertionError(f"Oracle context winners changed in world {world}.")
        pairwise = diagnostic.pairwise_selection_agreement(
            records, development_world=world
        )
        all_records.extend(records)
        all_summaries.extend(summaries)
        all_pairwise.extend(pairwise)
        all_validations.extend(validations)
        reconstruction_audits.append(reconstruction_audit)
        if progress is not None:
            progress(world)

    if len(all_records) != diagnostic.EXPECTED_TOTAL_RECORDS:
        raise AssertionError("Required 7000 context records were not reconstructed.")
    payload = _json_ready({
        "schema": "pilot_b_fixed_weight_selection_diagnostic_result_v1",
        "status": "complete",
        "scientific_role": (
            "post_hoc_development_only_descriptive_observed_vector_diagnostic_"
            "cannot_change_closed_pilot_b"
        ),
        "condition": REFERENCE_CONDITION,
        "development_worlds": diagnostic.DEVELOPMENT_WORLDS,
        "protocol_commit": PROTOCOL_COMMIT,
        "frozen_pilot_b_result_commit": FROZEN_RESULT_COMMIT,
        "frozen_pilot_b_result_sha256": FROZEN_RESULT_SHA256,
        "provenance": _runtime_provenance(execution_commit),
        "context_records": all_records,
        "per_world_method_summaries": all_summaries,
        "pairwise_selection_agreement": all_pairwise,
        "aggregate_reconstruction_validations": all_validations,
        "reconstruction_audits": reconstruction_audits,
        "interpretation": protocol["interpretation"],
        "bootstrap_policy": protocol["bootstrap_policy"],
        "primary_or_reserve_seed_used": False,
        "model_fit_or_prediction_executed": False,
        "weight_reestimation_executed": False,
        "shap_or_pi_executed": False,
        "random_weights_executed": False,
        "paired_context_bootstrap_executed": False,
        "closed_pilot_b_decision_or_thresholds_changed": False,
        "primary_factorial_authorized": False,
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute the frozen Pilot-B fixed-weight selection diagnostic once."
    )
    parser.add_argument(
        "--execute", action="store_true", help="Required explicit diagnostic-execution flag."
    )
    args = parser.parse_args(argv)
    if not args.execute:
        raise SystemExit("Refusing diagnostic execution without explicit --execute.")
    payload = execute_diagnostic_once(
        progress=lambda world: print(
            f"FIXED_WEIGHT_SELECTION_DEVELOPMENT_WORLD_COMPLETE: {world}", flush=True
        )
    )
    print("PILOT_B_FIXED_WEIGHT_SELECTION_DIAGNOSTIC_EXECUTION_COMPLETE: True")
    print("DEVELOPMENT_WORLDS:", ",".join(map(str, diagnostic.DEVELOPMENT_WORLDS)))
    print("CONTEXT_RECORDS:", len(payload["context_records"]))
    print("ARCHIVED_AGGREGATES_RECONSTRUCTED: True")
    print("MODEL_FIT_OR_PREDICTION_EXECUTED: False")
    print("WEIGHT_REESTIMATION_EXECUTED: False")
    print("SHAP_OR_PI_EXECUTED: False")
    print("RANDOM_WEIGHTS_EXECUTED: False")
    print("PAIRED_CONTEXT_BOOTSTRAP_EXECUTED: False")
    print("PRIMARY_OR_RESERVE_SEED_USED: False")
    print("PRIMARY_FACTORIAL_AUTHORIZED: False")
    print("OUTPUT:", DEFAULT_OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
