from __future__ import annotations

"""Guarded, development-only executor for the frozen Pilot-B reference gate.

Execution is locked to seeds 21001--21005 and the frozen reference condition.
It must be committed in a clean worktree before ``--execute`` can run.  Results
are written once with exclusive creation; primary and reserve seeds are barred.
"""

import argparse
from dataclasses import asdict
from importlib import util as importlib_util
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from pathlib import Path
import platform
import subprocess
import sys
from types import ModuleType
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
import yaml

from src import critic_weights_v1 as critic
from src import decision_fidelity_metrics_v1 as metrics
from src import direct_xgboost_reference_v1 as direct_xgb
from src import entropy_weights_v1 as entropy
from src import equal_weights_v1 as equal
from src import moora_topsis_v1 as mcdm
from src import oracle_attribution_weights_v1 as oracle_weights
from src import permutation_importance_weights_v1 as permutation
from src import pilot_b_hard_stop_evaluator_v1 as evaluator
from src import random_weights_majority_winner_v1 as references
from src import ridge_plus_weights_v1 as ridge
from src import treeshap_scientific_computation_v1 as treeshap


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONFIG = ROOT / "config"
RESULTS = ROOT / "results"

BRANCH = "implement-weighting-mcdm-v1"
THRESHOLD_COMMIT = "90079c4b9917b0859878a855ed5fbeeac3d69282"
DEVELOPMENT_SEEDS = (21001, 21002, 21003, 21004, 21005)
PRIMARY_SEEDS = tuple(range(11001, 11031))
RESERVE_SEEDS = tuple(range(30001, 30006))
REFERENCE_CONDITION = {"N": 250, "c": 0.30, "rho": 0.4, "lambda": 0.5}
EXPECTED_EXPERIMENT_REFERENCE = {
    "N": 250,
    "c": 0.30,
    "rho": 0.4,
    "lambda": 0.5,
    "alpha_structure": "heterogeneous_fixed",
}
EXPECTED_MASTER_CONTEXTS = 1200
EXPECTED_MASTER_ROWS = 7200
EXPECTED_ESTIMATION_ROWS = 6000
EXPECTED_TEST_ROWS = 1200
EXPECTED_TEST_CONTEXTS = 200
FEATURES = tuple(f"g_C{i}" for i in range(1, 11))

DEFAULT_OUTPUT = (
    RESULTS
    / "pilot_b_reference_v1"
    / "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
)

BENCHMARK_PATH = CONFIG / "benchmark.yaml"
EXPERIMENT_PATH = CONFIG / "experiment.yaml"
SEEDS_PATH = CONFIG / "seeds.yaml"
PROTOCOL_PATH = CONFIG / "pilot_b_hard_stop_protocol_v1.json"
STEP1_PATH = SRC / "01_generate_contexts.py"
STEP2_PATH = SRC / "02_generate_technology_responses.py"
STEP3_PATH = SRC / "03_generate_oracle_utility.py"
STEP4_PATH = SRC / "04_generate_noisy_target.py"
D29_PATH = SRC / "v4_0_f1_terminal_d29_kernel_evaluator.py"


def _run_git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n{process.stderr.strip()}"
        )
    return process.stdout.strip()


def assert_execution_environment(output_path: Path = DEFAULT_OUTPUT) -> str:
    """Require the committed threshold ancestor, branch, cleanliness, and no result."""
    branch = _run_git("branch", "--show-current")
    if branch != BRANCH:
        raise RuntimeError(f"Pilot B requires branch {BRANCH}; found {branch!r}.")
    head = _run_git("rev-parse", "HEAD")
    if len(head) != 40 or head == THRESHOLD_COMMIT:
        raise RuntimeError(
            "Pilot-B implementation must be committed after the threshold commit."
        )
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", THRESHOLD_COMMIT, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("Frozen Pilot-B threshold commit is not an ancestor of HEAD.")
    if _run_git("status", "--porcelain"):
        raise RuntimeError("Pilot B requires a completely clean committed worktree.")
    if Path(output_path).exists():
        raise FileExistsError(f"Pilot-B result exists; refusing overwrite: {output_path}")
    return head


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    return value


def load_configs() -> dict[str, dict[str, Any]]:
    benchmark = _load_yaml(BENCHMARK_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    seeds = _load_yaml(SEEDS_PATH)
    if experiment.get("reference_condition") != EXPECTED_EXPERIMENT_REFERENCE:
        raise ValueError("Frozen experiment reference condition changed.")
    if tuple(seeds.get("development", ())) != DEVELOPMENT_SEEDS:
        raise ValueError("Frozen development seeds changed.")
    if set(DEVELOPMENT_SEEDS) & (set(PRIMARY_SEEDS) | set(RESERVE_SEEDS)):
        raise AssertionError("Development seed firewall overlaps protected seeds.")
    evaluator.validate_frozen_protocol(PROTOCOL_PATH)
    return {"benchmark": benchmark, "experiment": experiment, "seeds": seeds}


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib_util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}.")
    module = importlib_util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_generator_modules() -> dict[str, ModuleType]:
    return {
        "step1": _load_module("pilot_b_step1", STEP1_PATH),
        "step2": _load_module("pilot_b_step2", STEP2_PATH),
        "step3": _load_module("pilot_b_step3", STEP3_PATH),
        "step4": _load_module("pilot_b_step4", STEP4_PATH),
        "d29": _load_module("pilot_b_d29", D29_PATH),
    }


def build_reference_master(
    *,
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, Any, dict[str, Any]]:
    """Reconstruct D29 -> oracle -> Y for one allowed development seed."""
    seed = int(replication_seed)
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError("Pilot B accepts only development seeds 21001--21005.")
    if seed in PRIMARY_SEEDS or seed in RESERVE_SEEDS:
        raise AssertionError("Protected primary/reserve seed reached Pilot B.")
    b, e, s = configs["benchmark"], configs["experiment"], configs["seeds"]
    step1, step2, step3, step4, d29 = (
        modules["step1"], modules["step2"], modules["step3"],
        modules["step4"], modules["d29"],
    )
    contexts, context_audit = step1.generate_master_contexts(
        replication_seed=seed,
        rho=REFERENCE_CONDITION["rho"],
        benchmark=b,
        experiment=e,
        seeds=s,
    )
    if len(contexts) != EXPECTED_MASTER_CONTEXTS or contexts["context_id"].nunique() != EXPECTED_MASTER_CONTEXTS:
        raise AssertionError("Pilot-B context master must contain 1200 unique contexts.")
    baseline, capability, deployment, response_audit = step2.generate_master_technology_responses(
        contexts=contexts, replication_seed=seed, benchmark=b
    )
    if len(baseline) != EXPECTED_MASTER_ROWS:
        raise AssertionError("Pilot-B response master must contain 7200 rows.")
    opportunities = step2.compute_opportunities(contexts=contexts, benchmark=b)
    responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability,
        benchmark=b,
        replication_seed=seed,
    )
    for criterion in ("C8", "C9", "C10"):
        column = f"g_{criterion}"
        if not np.array_equal(
            baseline[column].to_numpy(dtype=float),
            responses[column].to_numpy(dtype=float),
        ):
            raise AssertionError(f"Protected D29 column {column} changed.")
    oracle_spec = step3.load_oracle_spec(b)
    oracle_master = step3.compute_oracle_utility(
        responses,
        oracle_spec=oracle_spec,
        lambda_value=REFERENCE_CONDITION["lambda"],
    )
    step4.validate_target_noise_protocol(e, s)
    signal_sd = float(step4.compute_signal_sd(oracle_master))
    namespace = int(s["target_noise"]["stream_namespace"])
    noise_table = step4.master_noise_table(
        responses[["context_id", "context_number", "alternative_id"]],
        replication_seed=seed,
        namespace=namespace,
    )
    master = step4.add_relative_noise(
        oracle_master,
        c=REFERENCE_CONDITION["c"],
        signal_sd=signal_sd,
        noise_table=noise_table,
    )
    estimation = master["partition"].isin(["fit", "weight"])
    test = master["partition"].eq("test")
    if len(master) != EXPECTED_MASTER_ROWS or int(estimation.sum()) != EXPECTED_ESTIMATION_ROWS or int(test.sum()) != EXPECTED_TEST_ROWS:
        raise AssertionError("Pilot-B master partition geometry changed.")
    if master.loc[test, "context_id"].nunique() != EXPECTED_TEST_CONTEXTS:
        raise AssertionError("Pilot B requires exactly 200 external TEST contexts.")
    required = {*FEATURES, "Y", "U_star", *(f"q_C{i}" for i in range(1, 11))}
    if not required <= set(master.columns):
        raise AssertionError("Pilot-B master is missing frozen scientific columns.")
    audit = {
        "replication_seed": seed,
        "master_contexts": int(contexts["context_id"].nunique()),
        "master_rows": int(len(master)),
        "estimation_rows": int(estimation.sum()),
        "test_rows": int(test.sum()),
        "test_contexts": int(master.loc[test, "context_id"].nunique()),
        "signal_sd_from_estimation_only": signal_sd,
        "target_noise_namespace": namespace,
        "production_generator": "d29_kernel",
        "context_audit_rows": int(len(context_audit)),
        "response_audit_rows": int(len(response_audit)),
        "capability_parameter_rows": int(len(capability)),
        "deployment_parameter_rows": int(len(deployment)),
        "primary_or_reserve_seed_used": False,
    }
    return master, oracle_spec, audit


def fit_frozen_xgboost(master: pd.DataFrame, *, replication_seed: int) -> Any:
    """Fit one committed frozen XGBoost predictor on N=250 FIT only."""
    configs = treeshap.validate_frozen_computation_protocol()
    fit, _ = treeshap.prepare_fit_weight_rows(
        master,
        replication_seed=replication_seed,
        n_contexts=REFERENCE_CONDITION["N"],
    )
    model = treeshap._build_frozen_model(configs)
    model.fit(
        fit.loc[:, FEATURES].to_numpy(dtype=float),
        fit["Y"].to_numpy(dtype=float),
    )
    return model


def _batch_record(batch: Any, *, label_key: str, label: str, seed: int) -> dict[str, Any]:
    summary = batch.summary
    return {
        label_key: label,
        "replication_seed": int(seed),
        "test_contexts": int(summary["contexts"]),
        "kendall_defined_contexts": int(summary.get("kendall_tau_b_defined_contexts", 0)),
        "mean_kendall_tau_b": summary.get("mean_kendall_tau_b_defined_contexts"),
        "top1_accuracy": float(summary["top1_accuracy"]),
        "mean_normalized_oracle_regret": float(summary["mean_normalized_oracle_regret"]),
        "median_normalized_oracle_regret": float(summary["median_normalized_oracle_regret"]),
        "p95_normalized_oracle_regret": float(summary["p95_normalized_oracle_regret"]),
    }


def _score_weights(master: pd.DataFrame, weights: Mapping[str, float] | np.ndarray, *, label: str) -> Any:
    scored = mcdm.score_test_contexts(master, weights, method="MOORA")
    return metrics.evaluate_decision_fidelity_batch(scored.scored_rows, master, method="MOORA")


def _oracle_winner_records(context_metrics: pd.DataFrame, *, seed: int) -> list[dict[str, Any]]:
    required = {"context_number", "oracle_selected_top1"}
    if not required <= set(context_metrics.columns) or len(context_metrics) != 200:
        raise AssertionError("Oracle winner reconstruction requires 200 context metrics.")
    return [
        {
            "replication_seed": int(seed),
            "context_number": int(row.context_number),
            "oracle_selected_top1": str(row.oracle_selected_top1),
        }
        for row in context_metrics.itertuples(index=False)
    ]


def execute_seed(
    *,
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    generator_modules: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute every frozen Pilot-B method/reference for one development seed."""
    seed = int(replication_seed)
    master, oracle_spec, pipeline_audit = build_reference_master(
        replication_seed=seed, configs=configs, modules=generator_modules
    )
    n = REFERENCE_CONDITION["N"]
    oracle = oracle_weights.compute_oracle_attribution_weights(
        master,
        replication_seed=seed,
        n_contexts=n,
        oracle_spec=oracle_spec,
        lambda_value=REFERENCE_CONDITION["lambda"],
    )
    shap_result = treeshap.compute_scientific_treeshap_weights(
        master, replication_seed=seed, n_contexts=n
    )
    fitted_model = fit_frozen_xgboost(master, replication_seed=seed)
    pi = permutation.compute_permutation_importance_weights(
        master, fitted_model=fitted_model, replication_seed=seed, n_contexts=n
    )
    ridge_result = ridge.compute_ridge_plus_weights(master, replication_seed=seed, n_contexts=n)
    critic_result = critic.compute_critic_weights(master, replication_seed=seed, n_contexts=n, partition_scope="weight")
    entropy_result = entropy.compute_entropy_weights(master, replication_seed=seed, n_contexts=n, partition_scope="weight")
    equal_result = equal.compute_equal_weights()

    structured_specs = {
        "OracleAttribution": (oracle.weights_by_feature, oracle.weights_defined, False, oracle.diagnostics),
        "SHAP": (shap_result.weights_by_feature, shap_result.weights_defined, False, shap_result.diagnostics),
        "PermutationImportance": (pi.weights_by_feature, True, pi.fallback_used, pi.diagnostics),
        "RidgePlus": (ridge_result.weights_by_feature, True, bool(ridge_result.diagnostics["fallback_used"]), ridge_result.diagnostics),
        "CRITIC": (critic_result.weights_by_feature, True, bool(critic_result.diagnostics["fallback_used"]), critic_result.diagnostics),
        "Entropy": (entropy_result.weights_by_feature, True, bool(entropy_result.diagnostics["fallback_used"]), entropy_result.diagnostics),
    }
    structured_records: list[dict[str, Any]] = []
    method_details: dict[str, Any] = {}
    oracle_winner_records: list[dict[str, Any]] | None = None
    for method in evaluator.STRUCTURED_METHODS:
        weights, defined, fallback, diagnostics = structured_specs[method]
        method_details[method] = {
            "weights_defined": bool(defined),
            "equal_fallback_used": bool(fallback),
            "weights_by_feature": weights,
            "diagnostics": diagnostics,
        }
        if not defined or weights is None:
            structured_records.append({
                "method": method, "replication_seed": seed,
                "weights_defined": False, "equal_fallback_used": False,
                "test_contexts": 200, "kendall_defined_contexts": 0,
                "mean_kendall_tau_b": None, "top1_accuracy": 0.0,
                "mean_normalized_oracle_regret": 1.0,
                "scientific_metrics_not_computed_because_weights_undefined": True,
            })
            continue
        batch = _score_weights(master, weights, label=method)
        record = _batch_record(batch, label_key="method", label=method, seed=seed)
        record.update({"weights_defined": True, "equal_fallback_used": bool(fallback)})
        structured_records.append(record)
        if oracle_winner_records is None:
            oracle_winner_records = _oracle_winner_records(batch.context_metrics, seed=seed)

    equal_batch = _score_weights(master, equal_result.weights_by_feature, label="Equal")
    equal_record = _batch_record(equal_batch, label_key="reference", label="Equal", seed=seed)
    direct_result = direct_xgb.score_direct_xgboost_test_rows(
        fitted_model, master, replication_seed=seed
    )
    direct_batch = metrics.evaluate_decision_fidelity_batch(
        direct_result.scored_rows, master, method="DirectXGBoost"
    )
    direct_record = _batch_record(direct_batch, label_key="reference", label="DirectXGBoost", seed=seed)
    if oracle_winner_records is None:
        oracle_winner_records = _oracle_winner_records(direct_batch.context_metrics, seed=seed)

    majority = references.estimate_majority_winner(master, replication_seed=seed, n_contexts=n)
    majority_predictions = references.build_majority_winner_test_predictions(master, reference=majority)
    majority_batch = metrics.evaluate_top1_reference_batch(
        majority_predictions, master, reference="MajorityWinner"
    )
    majority_record = _batch_record(majority_batch, label_key="reference", label="MajorityWinner", seed=seed)

    random_reference = references.generate_random_weight_reference(replication_seed=seed)
    random_records: list[dict[str, Any]] = []
    context_numbers: list[int] | None = None
    winner_counts = np.zeros((200, 6), dtype=int)
    for draw_index, weights in enumerate(random_reference.weights, start=1):
        batch = _score_weights(master, weights, label="RandomWeights")
        record = _batch_record(batch, label_key="reference", label="RandomWeights", seed=seed)
        record["random_draw_index"] = draw_index
        record.pop("reference")
        random_records.append(record)
        context_frame = batch.context_metrics.sort_values("context_number", kind="stable")
        observed_numbers = context_frame["context_number"].astype(int).tolist()
        if context_numbers is None:
            context_numbers = observed_numbers
        elif observed_numbers != context_numbers:
            raise AssertionError("RandomWeights TEST context order changed across draws.")
        for row_index, winner in enumerate(context_frame["method_selected_top1"].astype(str)):
            winner_counts[row_index, evaluator.ALTERNATIVE_IDS.index(winner)] += 1
    if context_numbers is None or not np.all(winner_counts.sum(axis=1) == 200):
        raise AssertionError("RandomWeights modal reconstruction is incomplete.")
    random_modal_records: list[dict[str, Any]] = []
    for row_index, context_number in enumerate(context_numbers):
        counts = winner_counts[row_index]
        maximum = int(counts.max())
        modal_index = int(np.flatnonzero(counts == maximum)[0])
        random_modal_records.append({
            "replication_seed": seed,
            "context_number": int(context_number),
            "random_draws": 200,
            "modal_winner_id": evaluator.ALTERNATIVE_IDS[modal_index],
            "modal_count": maximum,
            "modal_share": float(maximum / 200.0),
        })

    return {
        "replication_seed": seed,
        "pipeline_audit": pipeline_audit,
        "structured_seed_metrics": structured_records,
        "reference_seed_metrics": [equal_record, direct_record, majority_record],
        "random_draw_metrics": random_records,
        "oracle_winner_contexts": oracle_winner_records,
        "random_context_modal": random_modal_records,
        "method_details": method_details,
        "reference_details": {
            "Equal": equal_result.diagnostics,
            "DirectXGBoost": direct_result.diagnostics,
            "MajorityWinner": {
                "modal_winner_id": majority.modal_winner_id,
                "modal_winner_share": majority.modal_winner_share,
                "winner_counts_by_alternative": majority.winner_counts_by_alternative,
                "diagnostics": majority.diagnostics,
            },
            "RandomWeights": random_reference.diagnostics,
        },
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if pd.isna(value) if not isinstance(value, (str, bool)) else False:
        return None
    return value


def _runtime_provenance(execution_commit: str) -> dict[str, Any]:
    versions: dict[str, str] = {}
    for key, distribution in {
        "numpy": "numpy", "pandas": "pandas", "scikit_learn": "scikit-learn",
        "scipy": "scipy", "xgboost": "xgboost", "shap": "shap", "pyyaml": "pyyaml",
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


def execute_pilot_b_once(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Run the complete five-seed Pilot-B computation and persist exactly once."""
    output_path = Path(output_path)
    execution_commit = assert_execution_environment(output_path)
    configs = load_configs()
    generator_modules = load_generator_modules()
    seed_payloads: list[dict[str, Any]] = []
    for seed in DEVELOPMENT_SEEDS:
        seed_payloads.append(execute_seed(
            replication_seed=seed,
            configs=configs,
            generator_modules=generator_modules,
        ))
        if progress is not None:
            progress(seed)
    structured = [row for payload in seed_payloads for row in payload["structured_seed_metrics"]]
    random_draws = [row for payload in seed_payloads for row in payload["random_draw_metrics"]]
    reported = [row for payload in seed_payloads for row in payload["reference_seed_metrics"]]
    oracle_winners = [row for payload in seed_payloads for row in payload["oracle_winner_contexts"]]
    random_modal = [row for payload in seed_payloads for row in payload["random_context_modal"]]
    decision = evaluator.evaluate_pilot_b_hard_stops(
        structured_seed_metrics=structured,
        random_draw_metrics=random_draws,
        reference_seed_metrics=reported,
        oracle_winner_contexts=oracle_winners,
        random_context_modal=random_modal,
        protocol_path=PROTOCOL_PATH,
    )
    payload = _json_ready({
        "schema": "pilot_b_reference_result_v1",
        "status": "complete",
        "scientific_role": "development_only_benchmark_validity_gate_not_primary_evidence",
        "condition": REFERENCE_CONDITION,
        "development_seeds": DEVELOPMENT_SEEDS,
        "threshold_protocol_commit": THRESHOLD_COMMIT,
        "provenance": _runtime_provenance(execution_commit),
        "seed_results": seed_payloads,
        "evaluator_inputs": {
            "structured_seed_metrics": structured,
            "reference_seed_metrics": reported,
            "random_draw_metrics": random_draws,
            "oracle_winner_contexts": oracle_winners,
            "random_context_modal": random_modal,
        },
        "hard_stop_evaluation": asdict(decision),
        "primary_or_reserve_seed_used": False,
        "thresholds_changed_after_inspection": False,
        "topsis_used_for_hard_stop": False,
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute the committed Pilot-B reference gate once.")
    parser.add_argument("--execute", action="store_true", help="Required explicit scientific-execution flag.")
    args = parser.parse_args(argv)
    if not args.execute:
        raise SystemExit("Refusing Pilot-B execution without explicit --execute.")
    payload = execute_pilot_b_once(
        progress=lambda seed: print(f"PILOT_B_DEVELOPMENT_SEED_COMPLETE: {seed}", flush=True)
    )
    decision = payload["hard_stop_evaluation"]
    print("PILOT_B_REFERENCE_EXECUTION_COMPLETE: True")
    print("DEVELOPMENT_SEEDS:", ",".join(map(str, DEVELOPMENT_SEEDS)))
    for gate, value in decision["gates"].items():
        print(f"{gate.upper()}: {value}")
    print("PILOT_B_HARD_STOP:", decision["hard_stop"])
    print("PILOT_B_PASS:", decision["pilot_b_pass"])
    print("PRIMARY_OR_RESERVE_SEED_USED: False")
    print("OUTPUT:", DEFAULT_OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
