from __future__ import annotations

"""
First development-only TreeSHAP reference executor.

This executable reconstructs the frozen production master using the exact
Step 1 -> Step 2 -> retained d29 -> oracle -> relative-noise pipeline already
used by the audited XGBoost development calibration executor, then calls the
committed scientific TreeSHAP computation layer.

Scientific scope is intentionally narrow:
- development seed 21001 only;
- frozen reference condition only;
- no primary or reserve seeds;
- no MCDM;
- no external-TEST evaluation;
- one guarded JSON result artifact.
"""

import argparse
import importlib.util
import json
from pathlib import Path
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

REFERENCE_DEVELOPMENT_SEED = 21001
EXPECTED_REFERENCE_CONDITION = {
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
EXPECTED_REFERENCE_FIT_ROWS = 1200
EXPECTED_REFERENCE_WEIGHT_ROWS = 300

DEFAULT_OUTPUT = (
    RESULTS
    / "treeshap_reference_development_v1"
    / "seed21001_N250_c0p30_rho0p4_lambda0p5.json"
)

BENCHMARK_PATH = CONFIG / "benchmark.yaml"
EXPERIMENT_PATH = CONFIG / "experiment.yaml"
SEEDS_PATH = CONFIG / "seeds.yaml"

STEP1_PATH = SRC / "01_generate_contexts.py"
STEP2_PATH = SRC / "02_generate_technology_responses.py"
STEP3_PATH = SRC / "03_generate_oracle_utility.py"
STEP4_PATH = SRC / "04_generate_noisy_target.py"
D29_PATH = SRC / "v4_0_f1_terminal_d29_kernel_evaluator.py"


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    return value


def load_configs() -> dict[str, dict[str, Any]]:
    benchmark = _load_yaml(BENCHMARK_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    seeds = _load_yaml(SEEDS_PATH)

    reference = experiment.get("reference_condition")
    if reference != EXPECTED_REFERENCE_CONDITION:
        raise ValueError(
            "Frozen reference condition changed: "
            f"{reference!r} != {EXPECTED_REFERENCE_CONDITION!r}."
        )

    development = seeds.get("development")
    if not isinstance(development, list):
        raise ValueError("seeds.development must be a list.")
    if development != [21001, 21002, 21003, 21004, 21005]:
        raise ValueError(f"Frozen development seed list changed: {development!r}.")
    if REFERENCE_DEVELOPMENT_SEED not in development:
        raise ValueError("Reference development seed 21001 is not registered.")

    return {
        "benchmark": benchmark,
        "experiment": experiment,
        "seeds": seeds,
    }


def _load_module(name: str, path: Path) -> ModuleType:
    if not path.exists():
        raise FileNotFoundError(path)
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_modules() -> dict[str, ModuleType]:
    return {
        "step1": _load_module("swfc_step1_contexts_ref", STEP1_PATH),
        "step2": _load_module("swfc_step2_responses_ref", STEP2_PATH),
        "step3": _load_module("swfc_step3_oracle_ref", STEP3_PATH),
        "step4": _load_module("swfc_step4_noise_ref", STEP4_PATH),
        "d29": _load_module("swfc_d29_kernel_ref", D29_PATH),
        "treeshap": _load_module(
            "swfc_treeshap_scientific_ref",
            SRC / "treeshap_scientific_computation_v1.py",
        ),
    }


def build_reference_master(
    *,
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconstruct the frozen reference noisy master without evaluating TEST."""
    if int(replication_seed) != REFERENCE_DEVELOPMENT_SEED:
        raise ValueError("This executor is locked to development seed 21001.")

    b = configs["benchmark"]
    e = configs["experiment"]
    s = configs["seeds"]
    ref = e["reference_condition"]

    n_ref = int(ref["N"])
    c = float(ref["c"])
    rho = float(ref["rho"])
    lam = float(ref["lambda"])

    step1 = modules["step1"]
    step2 = modules["step2"]
    step3 = modules["step3"]
    step4 = modules["step4"]
    d29 = modules["d29"]

    contexts, context_audit = step1.generate_master_contexts(
        replication_seed=replication_seed,
        rho=rho,
        benchmark=b,
        experiment=e,
        seeds=s,
    )
    if len(contexts) != EXPECTED_MASTER_CONTEXTS:
        raise AssertionError("Reference master must contain exactly 1200 contexts.")
    if contexts["context_id"].nunique() != EXPECTED_MASTER_CONTEXTS:
        raise AssertionError("Reference master context IDs are not unique.")

    baseline, capability_parameters, deployment_parameters, response_audit = (
        step2.generate_master_technology_responses(
            contexts=contexts,
            replication_seed=replication_seed,
            benchmark=b,
        )
    )
    if len(baseline) != EXPECTED_MASTER_ROWS:
        raise AssertionError("Baseline response master must contain exactly 7200 rows.")

    opportunities = step2.compute_opportunities(contexts=contexts, benchmark=b)
    responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability_parameters,
        benchmark=b,
        replication_seed=replication_seed,
    )

    for criterion in ("C8", "C9", "C10"):
        column = f"g_{criterion}"
        if not np.array_equal(
            baseline[column].to_numpy(dtype=float),
            responses[column].to_numpy(dtype=float),
        ):
            raise AssertionError(f"{column} changed under retained d29 kernel.")

    oracle_spec = step3.load_oracle_spec(b)
    oracle_master = step3.compute_oracle_utility(
        responses,
        oracle_spec=oracle_spec,
        lambda_value=lam,
    )

    step4.validate_target_noise_protocol(e, s)
    signal_sd = float(step4.compute_signal_sd(oracle_master))
    namespace = int(s["target_noise"]["stream_namespace"])
    noise_table = step4.master_noise_table(
        responses[["context_id", "context_number", "alternative_id"]],
        replication_seed=replication_seed,
        namespace=namespace,
    )
    noisy_master = step4.add_relative_noise(
        oracle_master,
        c=c,
        signal_sd=signal_sd,
        noise_table=noise_table,
    )

    if len(noisy_master) != EXPECTED_MASTER_ROWS:
        raise AssertionError("Noisy master must contain exactly 7200 rows.")

    estimation = noisy_master["partition"].isin(["fit", "weight"])
    external_test = noisy_master["partition"].eq("test")
    if int(estimation.sum()) != EXPECTED_ESTIMATION_ROWS:
        raise AssertionError("Expected exactly 6000 FIT+WEIGHT rows.")
    if int(external_test.sum()) != EXPECTED_TEST_ROWS:
        raise AssertionError("Expected exactly 1200 external TEST rows.")

    fit_ref = noisy_master.loc[
        noisy_master["partition"].eq("fit")
        & noisy_master["context_number"].le(n_ref)
    ]
    weight_ref = noisy_master.loc[
        noisy_master["partition"].eq("weight")
        & noisy_master["context_number"].le(n_ref)
    ]

    if len(fit_ref) != EXPECTED_REFERENCE_FIT_ROWS:
        raise AssertionError("Reference N=250 must contain exactly 1200 FIT rows.")
    if len(weight_ref) != EXPECTED_REFERENCE_WEIGHT_ROWS:
        raise AssertionError("Reference N=250 must contain exactly 300 WEIGHT rows.")

    required_model_columns = [f"g_C{i}" for i in range(1, 11)] + ["Y"]
    if any(column not in noisy_master.columns for column in required_model_columns):
        raise AssertionError("Reference noisy master is missing model features or Y.")
    if not np.isfinite(
        noisy_master.loc[estimation, required_model_columns].to_numpy(dtype=float)
    ).all():
        raise AssertionError("Estimation master contains non-finite model data.")

    audit = {
        "replication_seed": int(replication_seed),
        "reference_condition": {
            "N": n_ref,
            "c": c,
            "rho": rho,
            "lambda": lam,
            "alpha_structure": str(ref["alpha_structure"]),
        },
        "production_generator": "d29_kernel",
        "master_contexts_generated": int(contexts["context_id"].nunique()),
        "master_rows_generated": int(len(noisy_master)),
        "estimation_rows_generated": int(estimation.sum()),
        "external_test_rows_generated": int(external_test.sum()),
        "reference_fit_rows": int(len(fit_ref)),
        "reference_weight_rows": int(len(weight_ref)),
        "signal_sd": signal_sd,
        "imposed_noise_sd": float(c * signal_sd),
        "external_test_used_for_signal_sd": False,
        "external_test_used_for_model_fit": False,
        "external_test_used_for_background": False,
        "external_test_used_for_global_shap_weights": False,
        "context_audit_rows_generated": int(len(context_audit)),
        "response_audit_rows_generated": int(len(response_audit)),
        "capability_parameter_rows": int(len(capability_parameters)),
        "deployment_parameter_rows": int(len(deployment_parameters)),
        "mcdm_executed": False,
    }
    return noisy_master, audit


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_json_ready(v) for v in value.tolist()]
    return value


def execute_reference_once(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    configs: Mapping[str, Mapping[str, Any]] | None = None,
    modules: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute exactly one guarded development-reference TreeSHAP computation."""
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(
            f"Reference TreeSHAP result already exists; refusing rerun: {output_path}"
        )

    cfg = dict(configs) if configs is not None else load_configs()
    mods = dict(modules) if modules is not None else load_modules()

    master, pipeline_audit = build_reference_master(
        replication_seed=REFERENCE_DEVELOPMENT_SEED,
        configs=cfg,
        modules=mods,
    )

    treeshap = mods["treeshap"]
    result = treeshap.compute_scientific_treeshap_weights(
        master,
        replication_seed=REFERENCE_DEVELOPMENT_SEED,
        n_contexts=int(EXPECTED_REFERENCE_CONDITION["N"]),
    )

    payload = {
        "schema": "treeshap_reference_development_result_v1",
        "status": "complete",
        "scientific_role": "development_reference_only_not_primary_evidence",
        "interpretation": (
            "SHAP weights are predictive attribution-derived surrogate weights; "
            "they are not causal effects, stakeholder preferences, normative "
            "weights, or social-welfare weights."
        ),
        "replication_seed": REFERENCE_DEVELOPMENT_SEED,
        "condition": dict(EXPECTED_REFERENCE_CONDITION),
        "pipeline_audit": pipeline_audit,
        "treeshap": {
            "weights_defined": bool(result.weights_defined),
            "importance_by_feature": result.importance_by_feature,
            "weights_by_feature": result.weights_by_feature,
            "diagnostics": result.diagnostics,
        },
        "mcdm_executed": False,
        "external_test_evaluated": False,
        "primary_or_reserve_seed_used": False,
    }
    payload = _json_ready(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the guarded first development-only TreeSHAP reference computation."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required explicit flag. Without it, no scientific computation is run.",
    )
    args = parser.parse_args(argv)

    if not args.execute:
        raise SystemExit(
            "Refusing to execute without explicit --execute. "
            "Commit and audit this executor before scientific use."
        )

    payload = execute_reference_once()
    treeshap = payload["treeshap"]
    diagnostics = treeshap["diagnostics"]

    print("TREESHAP DEVELOPMENT REFERENCE EXECUTION COMPLETE")
    print("SEED:", payload["replication_seed"])
    print("CONDITION:", json.dumps(payload["condition"], sort_keys=True))
    print("WEIGHTS_DEFINED:", treeshap["weights_defined"])
    print("TOTAL_IMPORTANCE:", diagnostics["total_importance"])
    print(
        "LOCAL_ACCURACY_MAX_ABSOLUTE_ERROR:",
        diagnostics["local_accuracy_max_absolute_error"],
    )
    print(
        "LOCAL_ACCURACY_MAX_SCALED_ERROR:",
        diagnostics["local_accuracy_max_scaled_error"],
    )
    print("BACKGROUND_IDENTITY_SHA256:", diagnostics["background_identity_sha256"])
    print("EXTERNAL_TEST_EVALUATED:", payload["external_test_evaluated"])
    print("MCDM_EXECUTED:", payload["mcdm_executed"])
    print("OUTPUT:", DEFAULT_OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
