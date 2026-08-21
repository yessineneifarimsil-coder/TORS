from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import GroupKFold, ParameterSampler, RandomizedSearchCV
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONFIG = ROOT / "config"
RESULTS = ROOT / "results"

PROTOCOL_PATH = CONFIG / "xgboost_development_calibration_v1.json"
XGBOOST_CONFIG_PATH = CONFIG / "xgboost.yaml"
BENCHMARK_PATH = CONFIG / "benchmark.yaml"
EXPERIMENT_PATH = CONFIG / "experiment.yaml"
SEEDS_PATH = CONFIG / "seeds.yaml"

OUTPUT_DIR = RESULTS / "xgboost_development_calibration_v1"
TEMP_DIR = RESULTS / ".xgboost_development_calibration_v1_tmp"

FEATURES = [f"g_C{i}" for i in range(1, 11)]
PARAMETER_ORDER = [
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "min_child_weight",
    "reg_alpha",
    "reg_lambda",
]


def load_numbered_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a mapping.")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain an object.")
    return data


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout.strip()


def assert_clean_worktree_before_execution() -> None:
    if git("status", "--porcelain"):
        raise RuntimeError(
            "Calibration execution requires a clean Git worktree. "
            "Commit the evaluator implementation before running it."
        )


def load_configs() -> dict[str, dict[str, Any]]:
    return {
        "protocol": load_json(PROTOCOL_PATH),
        "xgboost": load_yaml(XGBOOST_CONFIG_PATH),
        "benchmark": load_yaml(BENCHMARK_PATH),
        "experiment": load_yaml(EXPERIMENT_PATH),
        "seeds": load_yaml(SEEDS_PATH),
    }


def load_pipeline_modules() -> dict[str, Any]:
    return {
        "step1": load_numbered_module(
            "xgbcal_step1_contexts", SRC / "01_generate_contexts.py"
        ),
        "step2": load_numbered_module(
            "xgbcal_step2_responses", SRC / "02_generate_technology_responses.py"
        ),
        "step3": load_numbered_module(
            "xgbcal_step3_oracle", SRC / "03_generate_oracle_utility.py"
        ),
        "step4": load_numbered_module(
            "xgbcal_step4_noise", SRC / "04_generate_noisy_target.py"
        ),
        "d29": load_numbered_module(
            "xgbcal_d29_kernel",
            SRC / "v4_0_f1_terminal_d29_kernel_evaluator.py",
        ),
    }


def validate_frozen_protocol(configs: Mapping[str, Mapping[str, Any]]) -> None:
    p = configs["protocol"]
    x = configs["xgboost"]
    e = configs["experiment"]
    s = configs["seeds"]

    if p["status"] != "FROZEN_BEFORE_CALIBRATION_EXECUTION":
        raise ValueError("XGBoost calibration protocol is not frozen.")
    if p["development_data"]["replication_seeds"] != [21001, 21002, 21003, 21004, 21005]:
        raise ValueError("Unexpected development-seed set.")

    ref = p["development_data"]["reference_condition"]
    expected_ref = {"N": 250, "c": 0.3, "rho": 0.4, "lambda": 0.5, "alpha_structure": "heterogeneous_fixed"}
    if ref != expected_ref:
        raise ValueError(f"Unexpected calibration reference condition: {ref}")

    if list(s["development"]) != p["development_data"]["replication_seeds"]:
        raise ValueError("Protocol development seeds differ from seeds.yaml.")

    if int(s["xgboost_calibration"]["search_random_state"]) != 82001:
        raise ValueError("Unexpected candidate-sampling random state.")
    if int(s["xgboost_calibration"]["estimator_random_state"]) != 82002:
        raise ValueError("Unexpected estimator random state.")

    dev = x["development"]
    if dev["search"]["method"] != "RandomizedSearchCV":
        raise ValueError("Search method must be RandomizedSearchCV.")
    if int(dev["search"]["number_of_candidates"]) != 60:
        raise ValueError("Exactly 60 candidate configurations are required.")
    if dev["cross_validation"]["method"] != "GroupKFold":
        raise ValueError("CV method must be GroupKFold.")
    if int(dev["cross_validation"]["folds"]) != 5:
        raise ValueError("Exactly five grouped CV folds are required.")
    if dev["optimization_metric"] != "RMSE":
        raise ValueError("Optimization metric must be RMSE.")
    if x["frozen_parameters"]["calibrated"] is not False:
        raise ValueError("Frozen XGBoost parameters must still be uncalibrated.")

    if int(e["reference_condition"]["N"]) != 250:
        raise ValueError("experiment.yaml reference N mismatch.")
    if not math.isclose(float(e["reference_condition"]["c"]), 0.3):
        raise ValueError("experiment.yaml reference c mismatch.")
    if not math.isclose(float(e["reference_condition"]["rho"]), 0.4):
        raise ValueError("experiment.yaml reference rho mismatch.")
    if not math.isclose(float(e["reference_condition"]["lambda"]), 0.5):
        raise ValueError("experiment.yaml reference lambda mismatch.")

    protected = set(int(v) for v in s.get("primary", []))
    protected.update(range(30001, 30006))
    development = set(int(v) for v in p["development_data"]["replication_seeds"])
    if protected & development:
        raise ValueError("Development seeds collide with protected primary/reserve seeds.")

    fw = p["firewalls"]
    required_false = [
        "primary_seeds_11001_11030_used",
        "reserve_seeds_30001_30005_used",
        "external_TEST_used",
        "SHAP_used_for_selection",
        "MCDM_used_for_selection",
        "winner_identity_used_for_selection",
        "preferred_ITS_used_for_selection",
        "treeSHAP_background_selected_here",
    ]
    if any(fw[key] is not False for key in required_false):
        raise ValueError("One or more frozen calibration firewalls are not false.")

    if p["development_data"]["cached_legacy_csvs_allowed_as_calibration_input"] is not False:
        raise ValueError("Legacy cached CSV inputs must remain forbidden.")


def canonical_parameter_tuple(params: Mapping[str, Any]) -> tuple[float, ...]:
    return tuple(float(params[name]) for name in PARAMETER_ORDER)


def deterministic_candidates(configs: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    p = configs["protocol"]
    x = configs["xgboost"]
    n_iter = int(x["development"]["search"]["number_of_candidates"])
    random_state = int(p["randomness"]["candidate_sampling_random_state"])
    sampled = list(
        ParameterSampler(
            x["development"]["search_space"],
            n_iter=n_iter,
            random_state=random_state,
        )
    )
    if len(sampled) != 60:
        raise AssertionError("Expected exactly 60 sampled candidates.")
    keys = [canonical_parameter_tuple(item) for item in sampled]
    if len(set(keys)) != 60:
        raise AssertionError("Candidate sampling produced duplicates.")
    return sampled


def make_estimator(
    params: Mapping[str, Any],
    configs: Mapping[str, Mapping[str, Any]],
) -> XGBRegressor:
    p = configs["protocol"]
    m = configs["xgboost"]["model"]
    return XGBRegressor(
        objective=str(m["objective"]),
        n_jobs=int(m["n_jobs"]),
        verbosity=int(m["verbosity"]),
        random_state=int(p["randomness"]["xgboost_estimator_random_state"]),
        **dict(params),
    )


def build_seed_calibration_data(
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    p = configs["protocol"]
    b = configs["benchmark"]
    e = configs["experiment"]
    s = configs["seeds"]
    step1 = modules["step1"]
    step2 = modules["step2"]
    step3 = modules["step3"]
    step4 = modules["step4"]
    d29 = modules["d29"]

    if replication_seed not in p["development_data"]["replication_seeds"]:
        raise ValueError(f"Seed {replication_seed} is not a frozen development seed.")

    ref = p["development_data"]["reference_condition"]
    rho = float(ref["rho"])
    lam = float(ref["lambda"])
    c = float(ref["c"])
    n_ref = int(ref["N"])

    contexts, context_audit = step1.generate_master_contexts(
        replication_seed=replication_seed,
        rho=rho,
        benchmark=b,
        experiment=e,
        seeds=s,
    )
    if len(contexts) != 1200 or contexts["context_id"].nunique() != 1200:
        raise AssertionError("Development master must contain exactly 1200 contexts.")

    baseline, capability_parameters, deployment_parameters, response_audit = (
        step2.generate_master_technology_responses(
            contexts=contexts,
            replication_seed=replication_seed,
            benchmark=b,
        )
    )
    if len(baseline) != 7200:
        raise AssertionError("Development response master must contain exactly 7200 rows.")

    opportunities = step2.compute_opportunities(contexts=contexts, benchmark=b)
    d29_responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability_parameters,
        benchmark=b,
        replication_seed=replication_seed,
    )

    for criterion in ("C8", "C9", "C10"):
        col = f"g_{criterion}"
        if not np.array_equal(
            baseline[col].to_numpy(dtype=float),
            d29_responses[col].to_numpy(dtype=float),
        ):
            raise AssertionError(f"{col} changed under retained d29 kernel.")

    oracle_spec = step3.load_oracle_spec(b)
    oracle_master = step3.compute_oracle_utility(
        d29_responses,
        oracle_spec=oracle_spec,
        lambda_value=lam,
    )

    step4.validate_target_noise_protocol(e, s)
    signal_sd = float(step4.compute_signal_sd(oracle_master))
    namespace = int(s["target_noise"]["stream_namespace"])
    noise_table = step4.master_noise_table(
        d29_responses[["context_id", "context_number", "alternative_id"]],
        replication_seed=replication_seed,
        namespace=namespace,
    )
    noisy_master = step4.add_relative_noise(
        oracle_master,
        c=c,
        signal_sd=signal_sd,
        noise_table=noise_table,
    )

    estimation = noisy_master["partition"].isin(["fit", "weight"])
    external_test = noisy_master["partition"].eq("test")
    if int(estimation.sum()) != 6000:
        raise AssertionError("Expected 6000 FIT+WEIGHT rows in estimation master.")
    if int(external_test.sum()) != 1200:
        raise AssertionError("Expected 1200 external TEST rows in full master.")

    fit = noisy_master.loc[
        noisy_master["partition"].eq("fit")
        & noisy_master["context_number"].le(n_ref)
    ].copy()
    fit.sort_values(
        ["replication_seed", "context_number", "alternative_id"],
        kind="stable",
        inplace=True,
    )
    fit.reset_index(drop=True, inplace=True)

    if len(fit) != 1200:
        raise AssertionError("Each development seed must contribute exactly 1200 FIT rows.")
    if fit["context_id"].nunique() != 200:
        raise AssertionError("Each development seed must contribute exactly 200 FIT contexts.")
    if set(fit["partition"].unique()) != {"fit"}:
        raise AssertionError("Calibration frame contains a non-FIT partition.")
    if int(fit["context_number"].max()) > 250:
        raise AssertionError("Calibration frame escaped reference N=250.")
    if any(col not in fit.columns for col in FEATURES + ["Y"]):
        raise AssertionError("Calibration frame is missing model features or Y.")
    if not np.isfinite(fit[FEATURES + ["Y"]].to_numpy(dtype=float)).all():
        raise AssertionError("Calibration frame contains non-finite model data.")

    fit["cv_group"] = (
        fit["replication_seed"].astype(str)
        + "|"
        + fit["context_id"].astype(str)
    )
    if fit["cv_group"].nunique() != 200:
        raise AssertionError("Composite CV grouping did not yield 200 seed-context groups.")

    audit = {
        "replication_seed": int(replication_seed),
        "master_contexts": int(contexts["context_id"].nunique()),
        "master_rows": int(len(noisy_master)),
        "estimation_rows": int(estimation.sum()),
        "external_test_rows_generated": int(external_test.sum()),
        "reference_N": n_ref,
        "fit_contexts_used": int(fit["context_id"].nunique()),
        "fit_rows_used": int(len(fit)),
        "weight_rows_used_for_selection": 0,
        "external_test_rows_used_for_selection": 0,
        "signal_sd": signal_sd,
        "imposed_noise_sd": float(c * signal_sd),
        "external_test_used_for_signal_sd": False,
        "production_generator": "d29_kernel",
        "context_audit_rows_generated": int(len(context_audit)),
        "response_audit_rows_generated": int(len(response_audit)),
        "capability_parameter_rows": int(len(capability_parameters)),
        "deployment_parameter_rows": int(len(deployment_parameters)),
    }
    return fit, audit


def build_pooled_calibration_data(
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    audits: list[dict[str, Any]] = []
    for seed in configs["protocol"]["development_data"]["replication_seeds"]:
        frame, audit = build_seed_calibration_data(int(seed), configs, modules)
        frames.append(frame)
        audits.append(audit)

    pooled = pd.concat(frames, ignore_index=True)
    pooled.sort_values(
        ["replication_seed", "context_number", "alternative_id"],
        kind="stable",
        inplace=True,
    )
    pooled.reset_index(drop=True, inplace=True)

    if len(pooled) != 6000:
        raise AssertionError("Pooled XGBoost calibration frame must contain 6000 rows.")
    if pooled["cv_group"].nunique() != 1000:
        raise AssertionError("Pooled XGBoost calibration frame must contain 1000 context groups.")
    if set(pooled["replication_seed"].unique()) != {21001, 21002, 21003, 21004, 21005}:
        raise AssertionError("Pooled calibration frame contains an unexpected seed.")
    if set(pooled["partition"].unique()) != {"fit"}:
        raise AssertionError("Pooled calibration frame contains non-FIT rows.")
    return pooled, pd.DataFrame(audits)


def select_candidate_from_results(candidate_results: pd.DataFrame) -> int:
    if candidate_results.empty:
        raise ValueError("Candidate results are empty.")
    if candidate_results["mean_cv_rmse"].isna().any():
        raise ValueError("Candidate results contain missing mean CV RMSE.")

    minimum = float(candidate_results["mean_cv_rmse"].min())
    tol = 1e-12
    tied = candidate_results.loc[
        (candidate_results["mean_cv_rmse"] - minimum).abs().le(tol)
    ].copy()
    if tied.empty:
        raise AssertionError("No candidate survived the deterministic selection rule.")

    tied["_param_tuple"] = tied["params"].map(canonical_parameter_tuple)
    tied.sort_values("_param_tuple", kind="stable", inplace=True)
    return int(tied.iloc[0]["candidate_id"])


def run_randomized_search(
    pooled: pd.DataFrame,
    configs: Mapping[str, Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    p = configs["protocol"]
    xcfg = configs["xgboost"]
    candidates = deterministic_candidates(configs)

    X = pooled[FEATURES].to_numpy(dtype=float)
    y = pooled["Y"].to_numpy(dtype=float)
    groups = pooled["cv_group"].to_numpy()

    cv = GroupKFold(n_splits=int(xcfg["development"]["cross_validation"]["folds"]))
    base_estimator = make_estimator({}, configs)
    search = RandomizedSearchCV(
        estimator=base_estimator,
        param_distributions=xcfg["development"]["search_space"],
        n_iter=int(xcfg["development"]["search"]["number_of_candidates"]),
        scoring=str(p["selection"]["scikit_learn_scoring"]),
        n_jobs=1,
        cv=cv,
        refit=False,
        random_state=int(p["randomness"]["candidate_sampling_random_state"]),
        return_train_score=False,
        error_score="raise",
    )

    search.fit(X, y, groups=groups)
    result = pd.DataFrame(search.cv_results_)

    actual_params = list(result["params"])
    expected_keys = [canonical_parameter_tuple(item) for item in candidates]
    actual_keys = [canonical_parameter_tuple(item) for item in actual_params]
    if actual_keys != expected_keys:
        raise AssertionError("RandomizedSearchCV candidate sequence differs from frozen ParameterSampler sequence.")

    rows: list[dict[str, Any]] = []
    for idx, params in enumerate(actual_params):
        fold_rmse = [
            -float(result.loc[idx, f"split{k}_test_score"])
            for k in range(5)
        ]
        row: dict[str, Any] = {
            "candidate_id": idx + 1,
            "params": dict(params),
            "mean_cv_rmse": float(np.mean(fold_rmse)),
            "fold_sd_rmse_ddof0": float(np.std(fold_rmse, ddof=0)),
            "fold1_rmse": fold_rmse[0],
            "fold2_rmse": fold_rmse[1],
            "fold3_rmse": fold_rmse[2],
            "fold4_rmse": fold_rmse[3],
            "fold5_rmse": fold_rmse[4],
        }
        for name in PARAMETER_ORDER:
            row[name] = params[name]
        rows.append(row)

    candidate_results = pd.DataFrame(rows)
    selected_id = select_candidate_from_results(candidate_results)
    candidate_results["selected"] = candidate_results["candidate_id"].eq(selected_id)

    selected_row = candidate_results.loc[
        candidate_results["candidate_id"].eq(selected_id)
    ].iloc[0]
    selected = {
        name: selected_row["params"][name]
        for name in PARAMETER_ORDER
    }
    return candidate_results, selected


def selected_candidate_oof_diagnostics(
    pooled: pd.DataFrame,
    selected_params: Mapping[str, Any],
    configs: Mapping[str, Mapping[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    X = pooled[FEATURES].to_numpy(dtype=float)
    y = pooled["Y"].to_numpy(dtype=float)
    groups = pooled["cv_group"].to_numpy()
    cv = GroupKFold(n_splits=5)

    oof = np.full(len(pooled), np.nan, dtype=float)
    fold_rows: list[dict[str, Any]] = []

    for fold_index, (train_idx, valid_idx) in enumerate(cv.split(X, y, groups=groups), start=1):
        model = make_estimator(selected_params, configs)
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[valid_idx])
        oof[valid_idx] = pred
        fold_rows.append(
            {
                "fold": fold_index,
                "validation_groups": int(pd.Series(groups[valid_idx]).nunique()),
                "validation_rows": int(len(valid_idx)),
                "rmse": float(mean_squared_error(y[valid_idx], pred) ** 0.5),
            }
        )

    if not np.isfinite(oof).all():
        raise AssertionError("Selected-candidate OOF predictions are incomplete.")

    diag = pooled[["replication_seed", "context_id", "context_number", "alternative_id", "Y"]].copy()
    diag["oof_prediction"] = oof
    diag["squared_error"] = (diag["Y"] - diag["oof_prediction"]) ** 2

    per_seed = (
        diag.groupby("replication_seed", sort=True)["squared_error"]
        .mean()
        .pow(0.5)
        .rename("selected_candidate_oof_rmse")
        .reset_index()
    )
    per_seed["context_groups"] = 200
    per_seed["rows"] = 1200
    return per_seed, pd.DataFrame(fold_rows)


def package_versions() -> dict[str, str]:
    names = ["numpy", "pandas", "scikit-learn", "xgboost", "pyyaml"]
    out: dict[str, str] = {}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "NOT_INSTALLED"
    return out


def write_results(
    candidate_results: pd.DataFrame,
    selected_params: Mapping[str, Any],
    per_seed_oof: pd.DataFrame,
    selected_fold_oof: pd.DataFrame,
    seed_audit: pd.DataFrame,
    runtime_seconds: float,
    git_commit: str,
    git_branch: str,
) -> None:
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"{OUTPUT_DIR} already exists. Refusing to overwrite or rerun calibration."
        )
    if TEMP_DIR.exists():
        raise FileExistsError(
            f"{TEMP_DIR} already exists. Inspect/remove only after documenting an interrupted attempt."
        )

    TEMP_DIR.mkdir(parents=True, exist_ok=False)

    try:
        csv_results = candidate_results.copy()
        csv_results["params"] = csv_results["params"].map(
            lambda d: json.dumps(d, sort_keys=True)
        )
        csv_results.to_csv(TEMP_DIR / "candidate_results.csv", index=False)
        per_seed_oof.to_csv(TEMP_DIR / "selected_candidate_per_seed_oof_rmse.csv", index=False)
        selected_fold_oof.to_csv(TEMP_DIR / "selected_candidate_oof_folds.csv", index=False)
        seed_audit.to_csv(TEMP_DIR / "development_seed_audit.csv", index=False)

        selected_row = candidate_results.loc[candidate_results["selected"]].iloc[0]
        selected_payload = {
            "selected_candidate_id": int(selected_row["candidate_id"]),
            "selected_parameters": {
                key: (
                    int(value)
                    if key in {"n_estimators", "max_depth", "min_child_weight"}
                    else float(value)
                )
                for key, value in selected_params.items()
            },
            "mean_grouped_cv_rmse": float(selected_row["mean_cv_rmse"]),
            "fold_sd_rmse_ddof0_descriptive": float(selected_row["fold_sd_rmse_ddof0"]),
            "selection_rule": "minimum mean five-fold grouped-CV RMSE; <=1e-12 ties resolved by frozen lexicographic parameter tuple",
        }
        (TEMP_DIR / "selected_parameters.json").write_text(
            json.dumps(selected_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        summary = {
            "status": "XGBOOST_DEVELOPMENT_CALIBRATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT",
            "evaluation_commit": git_commit,
            "evaluation_branch": git_branch,
            "development_seeds": [21001, 21002, 21003, 21004, 21005],
            "reference_condition": {"N": 250, "c": 0.3, "rho": 0.4, "lambda": 0.5},
            "production_generator": "d29_kernel",
            "pooled_fit_context_groups": 1000,
            "pooled_fit_rows": 6000,
            "grouped_cv_folds": 5,
            "candidate_count": 60,
            "candidate_sampling_random_state": 82001,
            "estimator_random_state": 82002,
            "selection_metric": "mean grouped-CV RMSE",
            "selected_candidate_id": int(selected_row["candidate_id"]),
            "selected_parameters": selected_payload["selected_parameters"],
            "selected_mean_cv_rmse": float(selected_row["mean_cv_rmse"]),
            "runtime_seconds": float(runtime_seconds),
            "primary_11001_11030_used": False,
            "reserve_30001_30005_used": False,
            "weight_rows_used_for_selection": False,
            "external_test_used_for_signal_sd": False,
            "external_test_used_for_fit_or_cv": False,
            "external_test_metrics_computed_or_inspected": False,
            "SHAP_used_for_selection": False,
            "MCDM_used_for_selection": False,
            "winner_identity_used_for_selection": False,
            "treeSHAP_background_selected": False,
            "legacy_cached_csvs_used": False,
            "package_versions": package_versions(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
        (TEMP_DIR / "execution_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        lines = [
            "XGBOOST DEVELOPMENT CALIBRATION EXECUTION",
            f"git_commit: {git_commit}",
            f"git_branch: {git_branch}",
            "development_seeds: [21001, 21002, 21003, 21004, 21005]",
            "reference_condition: N=250, c=0.30, rho=0.4, lambda=0.5",
            "production_generator: d29_kernel",
            "pooled_fit_context_groups: 1000",
            "pooled_fit_rows: 6000",
            "candidate_count: 60",
            "grouped_cv_folds: 5",
            "candidate_sampling_random_state: 82001",
            "estimator_random_state: 82002",
            f"selected_candidate_id: {int(selected_row['candidate_id'])}",
            f"selected_mean_cv_rmse: {float(selected_row['mean_cv_rmse']):.12g}",
            f"selected_parameters: {json.dumps(selected_payload['selected_parameters'], sort_keys=True)}",
            "primary_11001_11030_used: False",
            "reserve_30001_30005_used: False",
            "weight_rows_used_for_selection: False",
            "external_test_used_for_signal_sd: False",
            "external_test_used_for_fit_or_cv: False",
            "external_test_metrics_computed_or_inspected: False",
            "SHAP_used_for_selection: False",
            "MCDM_used_for_selection: False",
            "winner_identity_used_for_selection: False",
            "treeSHAP_background_selected: False",
            "legacy_cached_csvs_used: False",
            "status: XGBOOST_DEVELOPMENT_CALIBRATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT",
        ]
        (TEMP_DIR / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

        TEMP_DIR.rename(OUTPUT_DIR)
    except Exception:
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        raise


def execute() -> None:
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"{OUTPUT_DIR} already exists. Calibration is one-shot and must not be rerun."
        )
    if TEMP_DIR.exists():
        raise FileExistsError(
            f"{TEMP_DIR} exists from an interrupted attempt. Do not proceed without audit documentation."
        )

    assert_clean_worktree_before_execution()
    git_commit = git("rev-parse", "HEAD")
    git_branch = git("branch", "--show-current")

    configs = load_configs()
    validate_frozen_protocol(configs)
    modules = load_pipeline_modules()

    start = time.perf_counter()
    pooled, seed_audit = build_pooled_calibration_data(configs, modules)
    candidate_results, selected_params = run_randomized_search(pooled, configs)
    per_seed_oof, selected_fold_oof = selected_candidate_oof_diagnostics(
        pooled, selected_params, configs
    )
    runtime = time.perf_counter() - start

    write_results(
        candidate_results=candidate_results,
        selected_params=selected_params,
        per_seed_oof=per_seed_oof,
        selected_fold_oof=selected_fold_oof,
        seed_audit=seed_audit,
        runtime_seconds=runtime,
        git_commit=git_commit,
        git_branch=git_branch,
    )

    summary = json.loads((OUTPUT_DIR / "execution_summary.json").read_text(encoding="utf-8"))
    print("XGBOOST DEVELOPMENT CALIBRATION EXECUTION")
    print("git_commit:", summary["evaluation_commit"])
    print("git_branch:", summary["evaluation_branch"])
    print("development_seeds:", summary["development_seeds"])
    print("reference_condition:", summary["reference_condition"])
    print("production_generator:", summary["production_generator"])
    print("pooled_fit_context_groups:", summary["pooled_fit_context_groups"])
    print("pooled_fit_rows:", summary["pooled_fit_rows"])
    print("candidate_count:", summary["candidate_count"])
    print("grouped_cv_folds:", summary["grouped_cv_folds"])
    print("candidate_sampling_random_state:", summary["candidate_sampling_random_state"])
    print("estimator_random_state:", summary["estimator_random_state"])
    print("selected_candidate_id:", summary["selected_candidate_id"])
    print("selected_mean_cv_rmse:", summary["selected_mean_cv_rmse"])
    print("selected_parameters:", summary["selected_parameters"])
    print("primary_11001_11030_used:", summary["primary_11001_11030_used"])
    print("reserve_30001_30005_used:", summary["reserve_30001_30005_used"])
    print("weight_rows_used_for_selection:", summary["weight_rows_used_for_selection"])
    print("external_test_used_for_signal_sd:", summary["external_test_used_for_signal_sd"])
    print("external_test_used_for_fit_or_cv:", summary["external_test_used_for_fit_or_cv"])
    print("external_test_metrics_computed_or_inspected:", summary["external_test_metrics_computed_or_inspected"])
    print("SHAP_used_for_selection:", summary["SHAP_used_for_selection"])
    print("MCDM_used_for_selection:", summary["MCDM_used_for_selection"])
    print("winner_identity_used_for_selection:", summary["winner_identity_used_for_selection"])
    print("treeSHAP_background_selected:", summary["treeSHAP_background_selected"])
    print("legacy_cached_csvs_used:", summary["legacy_cached_csvs_used"])
    print("status:", summary["status"])


if __name__ == "__main__":
    execute()
