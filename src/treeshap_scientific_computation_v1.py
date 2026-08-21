from __future__ import annotations

"""
Scientific XGBoost -> TreeSHAP -> global surrogate-weight computation.

This module implements the already-frozen TreeSHAP scientific computation
protocol. It does not generate benchmark data, evaluate external TEST,
run MCDM, tune any scientific choice, or write result files.

Required scientific flow:
    FIT -> frozen XGBoost
        -> frozen 100-row FIT TreeSHAP background
        -> explain WEIGHT
        -> local-accuracy invariant
        -> mean absolute SHAP importance
        -> normalized SHAP surrogate weights when defined
"""

from dataclasses import dataclass
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

import numpy as np
import pandas as pd
import shap
import yaml
from xgboost import XGBRegressor

from src import treeshap_background_v1 as background_v1


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

XGBOOST_CONFIG_PATH = CONFIG / "xgboost.yaml"
SEEDS_CONFIG_PATH = CONFIG / "seeds.yaml"
PROTOCOL_JSON_PATH = CONFIG / "treeshap_computation_protocol_v1.json"

FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
TARGET = "Y"
SORT_COLUMNS = ("context_number", "alternative_id")

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_FIT_ROWS = {25: 120, 50: 240, 100: 480, 250: 1200, 1000: 4800}
EXPECTED_WEIGHT_ROWS = {25: 30, 50: 60, 100: 120, 250: 300, 1000: 1200}

FROZEN_RANDOM_STATE = 82002
FROZEN_BACKGROUND_SIZE = 100
LOCAL_ACCURACY_ATOL = 1.0e-5
LOCAL_ACCURACY_RTOL = 1.0e-5
IMPORTANCE_EPSILON = 1.0e-12


class TreeSHAPNumericalError(RuntimeError):
    """Raised when the frozen local-accuracy invariant fails."""


@dataclass(frozen=True)
class TreeSHAPComputationResult:
    replication_seed: int
    n_contexts: int
    weights_defined: bool
    importance_by_feature: dict[str, float]
    weights_by_feature: dict[str, float] | None
    diagnostics: dict[str, Any]


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


def validate_frozen_computation_protocol() -> dict[str, Any]:
    """Fail closed unless the committed scientific-computation contract is intact."""
    xgb = _load_yaml(XGBOOST_CONFIG_PATH)
    seeds = _load_yaml(SEEDS_CONFIG_PATH)
    protocol = _load_json(PROTOCOL_JSON_PATH)

    frozen = xgb["frozen_parameters"]
    expected_params = {
        "n_estimators": 600,
        "max_depth": 2,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
    }
    if frozen.get("calibrated") is not True:
        raise ValueError("XGBoost frozen parameters are not marked calibrated.")
    for key, expected in expected_params.items():
        if frozen.get(key) != expected:
            raise ValueError(
                f"Frozen XGBoost parameter {key} changed: "
                f"{frozen.get(key)!r} != {expected!r}."
            )

    tree = xgb["tree_shap"]
    comp = xgb["treeshap_computation"]
    model_fit = comp["model_fit"]
    explanation = comp["explanation"]
    normalization = comp["weight_normalization"]

    if tree["background"]["frozen_target_size"] != FROZEN_BACKGROUND_SIZE:
        raise ValueError("TreeSHAP background size changed from 100.")
    if tree["feature_perturbation"] != "interventional":
        raise ValueError("TreeSHAP perturbation mode changed.")
    if tree["model_output"] != "raw":
        raise ValueError("TreeSHAP model output changed.")
    if tree["explanation_partition"] != "weight":
        raise ValueError("TreeSHAP explanation partition changed.")

    if model_fit["feature_columns"] != list(FEATURES):
        raise ValueError("Scientific XGBoost feature order changed.")
    if model_fit["target_column"] != TARGET:
        raise ValueError("Scientific XGBoost target changed.")
    if model_fit["fit_partition"] != "fit":
        raise ValueError("Scientific XGBoost fit partition changed.")
    if model_fit["row_sort_order"] != list(SORT_COLUMNS):
        raise ValueError("Scientific XGBoost row sort order changed.")
    if int(model_fit["estimator_random_state"]) != FROZEN_RANDOM_STATE:
        raise ValueError("Scientific XGBoost random_state changed.")
    if model_fit["early_stopping"] is not False or model_fit["eval_set"] is not None:
        raise ValueError("Early stopping/eval_set must remain disabled.")
    if model_fit["weight_partition_used_for_model_fit"] is not False:
        raise ValueError("WEIGHT must remain excluded from XGBoost fit.")
    if model_fit["external_test_used_for_model_fit"] is not False:
        raise ValueError("External TEST must remain excluded from XGBoost fit.")

    if explanation["partition"] != "weight":
        raise ValueError("TreeSHAP explanation must remain WEIGHT-only.")
    if explanation["feature_perturbation"] != "interventional":
        raise ValueError("TreeSHAP explanation perturbation changed.")
    if explanation["model_output"] != "raw":
        raise ValueError("TreeSHAP explanation output changed.")
    if explanation["values_source"] != "Explanation.values":
        raise ValueError("Unexpected SHAP values API.")
    if explanation["base_values_source"] != "Explanation.base_values":
        raise ValueError("Unexpected SHAP base-values API.")
    if explanation["external_test_used_for_shap_weight_estimation"] is not False:
        raise ValueError("External TEST must remain excluded from SHAP weights.")

    if comp["local_accuracy"]["absolute_tolerance"] != LOCAL_ACCURACY_ATOL:
        raise ValueError("Local-accuracy absolute tolerance changed.")
    if comp["local_accuracy"]["relative_tolerance"] != LOCAL_ACCURACY_RTOL:
        raise ValueError("Local-accuracy relative tolerance changed.")
    if comp["global_importance"]["definition"] != "mean_absolute_shap":
        raise ValueError("Global SHAP importance definition changed.")
    if normalization["epsilon"] != IMPORTANCE_EPSILON:
        raise ValueError("SHAP normalization epsilon changed.")
    if normalization["zero_or_near_zero_policy"] != "undefined_shap_weight_vector":
        raise ValueError("SHAP zero-sum policy changed.")
    if normalization["equal_weight_fallback"] is not False:
        raise ValueError("Equal-weight fallback must remain disabled.")

    if int(seeds["xgboost_production"]["estimator_random_state"]) != FROZEN_RANDOM_STATE:
        raise ValueError("Production XGBoost random_state registry changed.")
    if int(seeds["treeshap_background"]["row_priority_namespace"]) != 83001:
        raise ValueError("TreeSHAP background namespace changed.")

    if protocol["status"] != "FROZEN_BEFORE_FIRST_SCIENTIFIC_SHAP_WEIGHT_VECTOR":
        raise ValueError("Machine-readable TreeSHAP computation protocol is not frozen.")
    if protocol["model_fit"]["random_state"] != FROZEN_RANDOM_STATE:
        raise ValueError("JSON protocol XGBoost random_state changed.")
    if protocol["treeshap"]["background_size"] != FROZEN_BACKGROUND_SIZE:
        raise ValueError("JSON protocol background size changed.")
    if protocol["global_weight_compression"]["equal_weight_fallback"] is not False:
        raise ValueError("JSON protocol unexpectedly permits Equal fallback.")
    if not all(value is False for value in protocol["firewalls"].values()):
        raise ValueError("One or more JSON scientific firewalls are open.")
    if not all(value is False for value in comp["firewalls"].values()):
        raise ValueError("One or more YAML scientific firewalls are open.")

    # Also fail closed against the already-frozen deterministic background protocol.
    background_v1.validate_frozen_protocol(background_v1.load_configs())

    return {
        "xgboost": xgb,
        "seeds": seeds,
        "protocol": protocol,
    }


def prepare_fit_weight_rows(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return stable FIT and WEIGHT alternative-context rows for one nested N."""
    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")

    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        TARGET,
        *FEATURES,
    }
    missing = sorted(required - set(master_rows.columns))
    if missing:
        raise ValueError(f"Scientific TreeSHAP input is missing columns: {missing}.")

    background_v1.validate_master_rows(master_rows, replication_seed=replication_seed)

    nested = master_rows.loc[master_rows["context_number"].le(n)].copy()
    fit = nested.loc[nested["partition"].eq("fit")].copy()
    weight = nested.loc[nested["partition"].eq("weight")].copy()

    fit.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    weight.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    fit.reset_index(drop=True, inplace=True)
    weight.reset_index(drop=True, inplace=True)

    if len(fit) != EXPECTED_FIT_ROWS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_FIT_ROWS[n]} FIT rows; found {len(fit)}."
        )
    if len(weight) != EXPECTED_WEIGHT_ROWS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_WEIGHT_ROWS[n]} WEIGHT rows; found {len(weight)}."
        )
    if fit["partition"].ne("fit").any():
        raise AssertionError("Non-FIT row entered model-fitting data.")
    if weight["partition"].ne("weight").any():
        raise AssertionError("Non-WEIGHT row entered SHAP explanation data.")
    if fit["context_number"].gt(n).any() or weight["context_number"].gt(n).any():
        raise AssertionError("Nested estimation rows escaped requested N.")

    X_fit = fit.loc[:, FEATURES].to_numpy(dtype=float)
    X_weight = weight.loc[:, FEATURES].to_numpy(dtype=float)
    y_fit = fit[TARGET].to_numpy(dtype=float)

    if not np.isfinite(X_fit).all():
        raise ValueError("FIT features contain non-finite values.")
    if not np.isfinite(X_weight).all():
        raise ValueError("WEIGHT features contain non-finite values.")
    if not np.isfinite(y_fit).all():
        raise ValueError("FIT target contains non-finite values.")

    return fit, weight


def _build_frozen_model(configs: dict[str, Any]) -> XGBRegressor:
    frozen = configs["xgboost"]["frozen_parameters"]
    return XGBRegressor(
        n_estimators=int(frozen["n_estimators"]),
        max_depth=int(frozen["max_depth"]),
        learning_rate=float(frozen["learning_rate"]),
        subsample=float(frozen["subsample"]),
        colsample_bytree=float(frozen["colsample_bytree"]),
        min_child_weight=float(frozen["min_child_weight"]),
        reg_alpha=float(frozen["reg_alpha"]),
        reg_lambda=float(frozen["reg_lambda"]),
        objective="reg:squarederror",
        n_jobs=1,
        verbosity=0,
        random_state=FROZEN_RANDOM_STATE,
    )


def _coerce_base_values(base_values: Any, n_rows: int) -> np.ndarray:
    base = np.asarray(base_values, dtype=float)
    if base.ndim == 0:
        return np.full(n_rows, float(base), dtype=float)
    if base.size == n_rows:
        return base.reshape(n_rows)
    raise TreeSHAPNumericalError(
        f"Unexpected SHAP base_values shape {base.shape}; expected scalar or {n_rows} values."
    )


def _background_identity_hash(background_rows: pd.DataFrame) -> str:
    """Hash complete frozen background row identities, never feature values."""
    identity_columns = [
        "replication_seed",
        "context_id",
        "context_number",
        "alternative_id",
    ]
    missing = [c for c in identity_columns if c not in background_rows.columns]
    if missing:
        raise ValueError(f"Background identity hash is missing columns: {missing}.")

    payload = "\n".join(
        f"{int(seed)}|{str(context_id)}|{int(context_number)}|{str(alternative_id)}"
        for seed, context_id, context_number, alternative_id in background_rows[
            identity_columns
        ].itertuples(index=False, name=None)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _runtime_provenance() -> dict[str, Any]:
    """Return software and Git provenance required by the frozen output contract."""
    package_names = {
        "numpy": "numpy",
        "pandas": "pandas",
        "scikit_learn": "scikit-learn",
        "xgboost": "xgboost",
        "shap": "shap",
        "pyyaml": "pyyaml",
    }
    versions: dict[str, str] = {}
    for key, distribution in package_names.items():
        try:
            versions[key] = package_version(distribution)
        except PackageNotFoundError as exc:
            raise RuntimeError(
                f"Required package distribution not found for provenance: {distribution}."
            ) from exc

    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    git_head = proc.stdout.strip()
    if proc.returncode != 0 or len(git_head) != 40:
        raise RuntimeError("Could not resolve current Git commit for provenance.")

    return {
        "git_commit": git_head,
        "python": platform.python_version(),
        "software_versions": versions,
    }


def compute_scientific_treeshap_weights(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> TreeSHAPComputationResult:
    """Compute the frozen SHAP surrogate-weight vector for one benchmark instance.

    This function uses FIT and WEIGHT only. External TEST is not evaluated here.
    No files are written and no MCDM operator is executed.
    """
    configs = validate_frozen_computation_protocol()
    fit, weight = prepare_fit_weight_rows(
        master_rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )

    X_fit = fit.loc[:, FEATURES].to_numpy(dtype=float)
    y_fit = fit[TARGET].to_numpy(dtype=float)
    X_weight = weight.loc[:, FEATURES].to_numpy(dtype=float)

    model = _build_frozen_model(configs)
    # Frozen protocol: FIT only; no eval_set and no early stopping.
    model.fit(X_fit, y_fit)

    background_rows, bg_audit = background_v1.select_background_rows(
        master_rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )
    background_X = background_v1.background_feature_matrix(background_rows)

    explainer = shap.TreeExplainer(
        model=model,
        data=background_X,
        feature_perturbation="interventional",
        model_output="raw",
    )
    explanation = explainer(X_weight)

    phi = np.asarray(explanation.values, dtype=float)
    if phi.shape != (len(weight), len(FEATURES)):
        raise TreeSHAPNumericalError(
            f"Unexpected SHAP value shape {phi.shape}; "
            f"expected {(len(weight), len(FEATURES))}."
        )
    if not np.isfinite(phi).all():
        raise TreeSHAPNumericalError("SHAP values contain non-finite values.")

    base = _coerce_base_values(explanation.base_values, len(weight))
    if not np.isfinite(base).all():
        raise TreeSHAPNumericalError("SHAP base values contain non-finite values.")

    prediction = np.asarray(model.predict(X_weight), dtype=float).reshape(-1)
    if prediction.shape != (len(weight),):
        raise TreeSHAPNumericalError(
            f"Unexpected model prediction shape {prediction.shape}; "
            f"expected {(len(weight),)}."
        )
    if not np.isfinite(prediction).all():
        raise TreeSHAPNumericalError("XGBoost predictions contain non-finite values.")

    reconstructed = base + phi.sum(axis=1)
    abs_error = np.abs(reconstructed - prediction)
    tolerance = LOCAL_ACCURACY_ATOL + LOCAL_ACCURACY_RTOL * np.abs(prediction)
    scaled_error = abs_error / tolerance

    max_abs_error = float(abs_error.max(initial=0.0))
    max_scaled_error = float(scaled_error.max(initial=0.0))
    if np.any(abs_error > tolerance):
        raise TreeSHAPNumericalError(
            "TreeSHAP local-accuracy invariant failed: "
            f"max_abs_error={max_abs_error:.17g}, "
            f"max_scaled_error={max_scaled_error:.17g}."
        )

    importance = np.mean(np.abs(phi), axis=0)
    if importance.shape != (len(FEATURES),):
        raise AssertionError("Unexpected global SHAP-importance shape.")
    if not np.isfinite(importance).all() or np.any(importance < 0.0):
        raise TreeSHAPNumericalError("Global SHAP importances are invalid.")

    total_importance = float(importance.sum())
    importance_by_feature = {
        feature: float(value) for feature, value in zip(FEATURES, importance, strict=True)
    }

    if total_importance <= IMPORTANCE_EPSILON:
        weights_defined = False
        weights_by_feature = None
    else:
        weights = importance / total_importance
        if not np.isfinite(weights).all() or np.any(weights < 0.0):
            raise TreeSHAPNumericalError("Normalized SHAP weights are invalid.")
        if not np.isclose(float(weights.sum()), 1.0, atol=1e-12, rtol=1e-12):
            raise TreeSHAPNumericalError("Normalized SHAP weights do not sum to one.")
        weights_defined = True
        weights_by_feature = {
            feature: float(value) for feature, value in zip(FEATURES, weights, strict=True)
        }

    diagnostics: dict[str, Any] = {
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "fit_rows": int(len(fit)),
        "weight_rows": int(len(weight)),
        "background_rows": int(len(background_rows)),
        "background_to_fit_row_ratio": float(len(background_rows) / len(fit)),
        "background_identity_sha256": _background_identity_hash(background_rows),
        "model_random_state": FROZEN_RANDOM_STATE,
        "feature_perturbation": "interventional",
        "model_output": "raw",
        "local_accuracy_atol": LOCAL_ACCURACY_ATOL,
        "local_accuracy_rtol": LOCAL_ACCURACY_RTOL,
        "local_accuracy_max_absolute_error": max_abs_error,
        "local_accuracy_max_scaled_error": max_scaled_error,
        "total_importance": total_importance,
        "importance_normalization_epsilon": IMPORTANCE_EPSILON,
        "undefined_shap_weight_vector": not weights_defined,
        "equal_weight_fallback_used": False,
        "fit_partition_only": True,
        "background_partition_only_fit": bool(bg_audit["fit_only"]),
        "weight_partition_only": True,
        "external_test_rows_used_for_fit": 0,
        "external_test_rows_used_for_background": int(bg_audit["external_test_rows_used"]),
        "external_test_rows_used_for_global_shap_weights": 0,
        "mcdm_executed": False,
    }
    diagnostics.update(_runtime_provenance())

    return TreeSHAPComputationResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        weights_defined=weights_defined,
        importance_by_feature=importance_by_feature,
        weights_by_feature=weights_by_feature,
        diagnostics=diagnostics,
    )
