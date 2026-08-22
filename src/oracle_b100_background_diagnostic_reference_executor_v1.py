from __future__ import annotations

"""Guarded one-shot development reference for the Oracle B100 diagnostic.

The executor is locked to development seed 21001 and the prospectively frozen
condition (N=250, rho=0.4, lambda=0.5).  It generates no target Y, fits no
predictive model, imports no SHAP package, evaluates no external TEST utility,
executes no MCDM operator, and refuses to overwrite an existing result.
"""

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONFIG = ROOT / "config"
RESULTS = ROOT / "results"

PROTOCOL_COMMIT = "f98c23f"
EXPECTED_BRANCH = "implement-weighting-mcdm-v1"
REFERENCE_DEVELOPMENT_SEED = 21001
REFERENCE_CONDITION = {"N": 250, "rho": 0.4, "lambda": 0.5}
EXPECTED_DEVELOPMENT_SEEDS = [21001, 21002, 21003, 21004, 21005]
EXPECTED_MASTER_CONTEXTS = 1200
EXPECTED_MASTER_ROWS = 7200
EXPECTED_ESTIMATION_CONTEXTS = 1000
EXPECTED_ESTIMATION_ROWS = 6000
EXPECTED_TEST_ROWS = 1200
EXPECTED_REFERENCE_FIT_ROWS = 1200
EXPECTED_REFERENCE_WEIGHT_ROWS = 300
FROZEN_TREESHAP_REFERENCE_BACKGROUND_IDENTITY_SHA256 = (
    "3184c675397c8caf547a8da7f68d04a589b949ce39a1953bbf55d4461646eda1"
)

DEFAULT_OUTPUT = (
    RESULTS
    / "oracle_b100_background_diagnostic_reference_v1"
    / "seed21001_N250_rho0p4_lambda0p5.json"
)

BENCHMARK_PATH = CONFIG / "benchmark.yaml"
EXPERIMENT_PATH = CONFIG / "experiment.yaml"
SEEDS_PATH = CONFIG / "seeds.yaml"
B100_PROTOCOL_PATH = CONFIG / "oracle_b100_background_diagnostic_v1.json"

STEP1_PATH = SRC / "01_generate_contexts.py"
STEP2_PATH = SRC / "02_generate_technology_responses.py"
STEP3_PATH = SRC / "03_generate_oracle_utility.py"
D29_PATH = SRC / "v4_0_f1_terminal_d29_kernel_evaluator.py"
DIAGNOSTIC_PATH = SRC / "oracle_b100_background_diagnostic_v1.py"

IDENTITY_COLUMNS = [
    "replication_seed",
    "context_id",
    "context_number",
    "partition",
    "alternative_id",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def load_configs() -> dict[str, dict[str, Any]]:
    benchmark = _load_yaml(BENCHMARK_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    seeds = _load_yaml(SEEDS_PATH)
    protocol = _load_json(B100_PROTOCOL_PATH)

    reference = experiment.get("reference_condition")
    for key, expected in REFERENCE_CONDITION.items():
        if reference is None or reference.get(key) != expected:
            raise ValueError(f"Frozen reference field {key!r} changed: {reference!r}.")
    if seeds.get("development") != EXPECTED_DEVELOPMENT_SEEDS:
        raise ValueError("Frozen development seed family changed.")

    scope = protocol["comparison_scope"]
    if scope["development_reference_seed"] != REFERENCE_DEVELOPMENT_SEED:
        raise ValueError("B100 development reference seed changed.")
    if scope["development_reference_condition"] != REFERENCE_CONDITION:
        raise ValueError("B100 development reference condition changed.")
    if scope["reserve_seeds_allowed_before_primary"] is not False:
        raise ValueError("Reserve seeds are forbidden before primary execution.")

    return {
        "benchmark": benchmark,
        "experiment": experiment,
        "seeds": seeds,
        "protocol": protocol,
    }


def _load_module(name: str, path: Path) -> ModuleType:
    if not path.is_file():
        raise FileNotFoundError(path)
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def load_modules() -> dict[str, ModuleType]:
    return {
        "step1": _load_module("oracle_b100_step1", STEP1_PATH),
        "step2": _load_module("oracle_b100_step2", STEP2_PATH),
        "step3": _load_module("oracle_b100_step3", STEP3_PATH),
        "d29": _load_module("oracle_b100_d29", D29_PATH),
        "diagnostic": _load_module("oracle_b100_diagnostic", DIAGNOSTIC_PATH),
    }


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "--no-pager", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with code {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    return completed


def require_clean_committed_state() -> tuple[str, str]:
    status = _git("status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
    if status:
        raise RuntimeError(
            "Oracle B100 development reference refuses to run from a dirty worktree.\n"
            f"Current status:\n{status}"
        )
    commit = _git("rev-parse", "HEAD").stdout.strip()
    branch = _git("branch", "--show-current").stdout.strip()
    if len(commit) != 40:
        raise RuntimeError("Could not resolve the committed execution provenance.")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"Expected branch {EXPECTED_BRANCH!r}; found {branch!r}.")
    ancestor = _git(
        "merge-base",
        "--is-ancestor",
        PROTOCOL_COMMIT,
        "HEAD",
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(
            f"Frozen protocol commit {PROTOCOL_COMMIT} is not an ancestor of HEAD."
        )
    return commit, branch


def build_reference_oracle_inputs(
    *,
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, Any, dict[str, Any]]:
    """Reconstruct Oracle estimation rows plus the identity-only selector master."""
    if int(replication_seed) != REFERENCE_DEVELOPMENT_SEED:
        raise ValueError("This executor is locked to development seed 21001.")

    benchmark = configs["benchmark"]
    experiment = configs["experiment"]
    seeds = configs["seeds"]
    step1 = modules["step1"]
    step2 = modules["step2"]
    step3 = modules["step3"]
    d29 = modules["d29"]

    contexts, context_audit = step1.generate_master_contexts(
        replication_seed=int(replication_seed),
        rho=float(REFERENCE_CONDITION["rho"]),
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )
    if len(contexts) != EXPECTED_MASTER_CONTEXTS:
        raise AssertionError("Reference master must contain exactly 1200 contexts.")
    if contexts["context_id"].nunique() != EXPECTED_MASTER_CONTEXTS:
        raise AssertionError("Reference master context IDs are not unique.")

    baseline, capability_parameters, deployment_parameters, response_audit = (
        step2.generate_master_technology_responses(
            contexts=contexts,
            replication_seed=int(replication_seed),
            benchmark=benchmark,
        )
    )
    if len(baseline) != EXPECTED_MASTER_ROWS:
        raise AssertionError("Baseline response master must contain exactly 7200 rows.")

    opportunities = step2.compute_opportunities(contexts=contexts, benchmark=benchmark)
    responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability_parameters,
        benchmark=benchmark,
        replication_seed=int(replication_seed),
    )
    if len(responses) != EXPECTED_MASTER_ROWS:
        raise AssertionError("D29 response master must contain exactly 7200 rows.")
    for criterion in ("C8", "C9", "C10"):
        column = f"g_{criterion}"
        if not np.array_equal(
            baseline[column].to_numpy(dtype=float),
            responses[column].to_numpy(dtype=float),
        ):
            raise AssertionError(f"{column} changed under retained D29 kernel.")

    selection_master = responses.loc[:, IDENTITY_COLUMNS].copy()
    if len(selection_master) != EXPECTED_MASTER_ROWS:
        raise AssertionError("Selector identity master must contain exactly 7200 rows.")
    if int(selection_master["partition"].eq("test").sum()) != EXPECTED_TEST_ROWS:
        raise AssertionError("Selector identity master must contain 1200 TEST identities.")

    estimation_responses = responses.loc[
        responses["partition"].isin(["fit", "weight"])
        & responses["context_number"].between(1, EXPECTED_ESTIMATION_CONTEXTS)
    ].copy()
    if len(estimation_responses) != EXPECTED_ESTIMATION_ROWS:
        raise AssertionError("Oracle input must contain exactly 6000 estimation rows.")
    if estimation_responses["partition"].eq("test").any():
        raise AssertionError("External TEST entered Oracle utility evaluation.")

    oracle_spec = step3.load_oracle_spec(benchmark)
    oracle_rows = step3.compute_oracle_utility(
        estimation_responses,
        oracle_spec=oracle_spec,
        lambda_value=float(REFERENCE_CONDITION["lambda"]),
    )
    if len(oracle_rows) != EXPECTED_ESTIMATION_ROWS:
        raise AssertionError("Oracle utility output must contain 6000 estimation rows.")
    if oracle_rows["partition"].eq("test").any():
        raise AssertionError("External TEST entered Oracle B100 scientific rows.")

    n = int(REFERENCE_CONDITION["N"])
    fit = oracle_rows.loc[
        oracle_rows["partition"].eq("fit") & oracle_rows["context_number"].le(n)
    ]
    weight = oracle_rows.loc[
        oracle_rows["partition"].eq("weight") & oracle_rows["context_number"].le(n)
    ]
    if len(fit) != EXPECTED_REFERENCE_FIT_ROWS:
        raise AssertionError("Reference N=250 must contain exactly 1200 FIT rows.")
    if len(weight) != EXPECTED_REFERENCE_WEIGHT_ROWS:
        raise AssertionError("Reference N=250 must contain exactly 300 WEIGHT rows.")

    pipeline_audit = {
        "replication_seed": int(replication_seed),
        "condition": dict(REFERENCE_CONDITION),
        "production_generator": "d29_kernel",
        "master_contexts_generated": int(contexts["context_id"].nunique()),
        "master_response_rows_generated": int(len(responses)),
        "selector_identity_rows": int(len(selection_master)),
        "external_test_identity_rows_available_to_frozen_selector": EXPECTED_TEST_ROWS,
        "external_test_rows_used_for_oracle_utility": 0,
        "external_test_rows_used_for_background_moments": 0,
        "external_test_rows_used_for_weight_evaluation": 0,
        "estimation_oracle_rows": int(len(oracle_rows)),
        "reference_fit_rows": int(len(fit)),
        "reference_weight_rows": int(len(weight)),
        "context_audit_rows_generated": int(len(context_audit)),
        "response_audit_rows_generated": int(len(response_audit)),
        "capability_parameter_rows": int(len(capability_parameters)),
        "deployment_parameter_rows": int(len(deployment_parameters)),
        "target_Y_generated": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
        "winner_identity_used": False,
    }
    return oracle_rows, selection_master, oracle_spec, pipeline_audit


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def execute_reference_once(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    configs: Mapping[str, Mapping[str, Any]] | None = None,
    modules: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute and exclusively persist the one allowed development reference."""
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(
            f"Oracle B100 reference result already exists; refusing rerun: {output_path}"
        )
    commit, branch = require_clean_committed_state()

    cfg = dict(configs) if configs is not None else load_configs()
    mods = dict(modules) if modules is not None else load_modules()
    oracle_rows, selection_master, oracle_spec, pipeline_audit = (
        build_reference_oracle_inputs(
            replication_seed=REFERENCE_DEVELOPMENT_SEED,
            configs=cfg,
            modules=mods,
        )
    )

    diagnostic_module = mods["diagnostic"]
    result = diagnostic_module.compute_oracle_b100_background_diagnostic(
        oracle_rows,
        selection_master_rows=selection_master,
        replication_seed=REFERENCE_DEVELOPMENT_SEED,
        n_contexts=int(REFERENCE_CONDITION["N"]),
        oracle_spec=oracle_spec,
        lambda_value=float(REFERENCE_CONDITION["lambda"]),
    )
    observed_hash = str(result.diagnostics["background_identity_sha256"])
    if observed_hash != FROZEN_TREESHAP_REFERENCE_BACKGROUND_IDENTITY_SHA256:
        raise RuntimeError(
            "B100 Oracle membership does not match the frozen TreeSHAP development "
            f"reference: {observed_hash}."
        )

    payload = {
        "schema": "oracle_b100_background_diagnostic_reference_result_v1",
        "status": "complete",
        "scientific_role": "secondary_diagnostic_development_reference_only",
        "protocol_commit": PROTOCOL_COMMIT,
        "execution_commit": commit,
        "execution_branch": branch,
        "replication_seed": REFERENCE_DEVELOPMENT_SEED,
        "condition": dict(REFERENCE_CONDITION),
        "c_dependence": "none",
        "pipeline_audit": pipeline_audit,
        "background_identity_matches_frozen_treeshap_reference": True,
        "frozen_treeshap_reference_background_identity_sha256": (
            FROZEN_TREESHAP_REFERENCE_BACKGROUND_IDENTITY_SHA256
        ),
        "diagnostic": _json_ready(asdict(result)),
        "primary_oracle_replaced": False,
        "new_weighting_method_created": False,
        "equal_fallback_used": False,
        "external_test_evaluated": False,
        "target_Y_used": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
        "winner_identity_used": False,
        "primary_or_reserve_seed_used": False,
    }
    payload = _json_ready(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the guarded Oracle B100 development-reference diagnostic."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required explicit flag; without it no scientific computation occurs.",
    )
    args = parser.parse_args(argv)
    if not args.execute:
        raise SystemExit(
            "Refusing to execute without explicit --execute. "
            "Commit and audit this implementation before scientific use."
        )

    payload = execute_reference_once()
    diagnostic = payload["diagnostic"]
    print("ORACLE B100 DEVELOPMENT REFERENCE EXECUTION COMPLETE")
    print("SEED:", payload["replication_seed"])
    print("CONDITION:", json.dumps(payload["condition"], sort_keys=True))
    print("BACKGROUND_IDENTITY_MATCHES_TREESHAP:", True)
    print("FULL_FIT_WEIGHTS_DEFINED:", diagnostic["coverage"]["full_fit_weights_defined"])
    print("B100_WEIGHTS_DEFINED:", diagnostic["coverage"]["b100_weights_defined"])
    print("JOINTLY_DEFINED:", diagnostic["coverage"]["jointly_defined"])
    print("MAE_W:", diagnostic["vector_metrics"]["MAE_w"])
    print("TV_W:", diagnostic["vector_metrics"]["TV_w"])
    print("MAX_ABSOLUTE_WEIGHT_DIFFERENCE:", diagnostic["vector_metrics"]["max_absolute_weight_difference"])
    print("SPEARMAN_RHO_W:", diagnostic["vector_metrics"]["Spearman_rho_w"])
    print("TOP3_OVERLAP:", diagnostic["vector_metrics"]["top3_overlap"])
    print("TOP5_OVERLAP:", diagnostic["vector_metrics"]["top5_overlap"])
    print("PRIMARY_ORACLE_REPLACED:", payload["primary_oracle_replaced"])
    print("TARGET_Y_USED:", payload["target_Y_used"])
    print("SHAP_PACKAGE_USED:", payload["shap_package_used"])
    print("MCDM_EXECUTED:", payload["mcdm_executed"])
    print("OUTPUT:", DEFAULT_OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
