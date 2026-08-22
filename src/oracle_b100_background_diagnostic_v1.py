from __future__ import annotations

"""Oracle B100-matched background diagnostic.

The primary Oracle attribution reference continues to use all eligible FIT
rows.  This module computes a secondary Oracle vector with the exact frozen
TreeSHAP B100 FIT row identities.  Only the empirical marginal and same-row
joint background moments change; WEIGHT rows and all Oracle semantics are
shared with :mod:`src.oracle_attribution_weights_v1`.

This module is computation-only.  It writes no files, fits no predictive
model, imports no SHAP package, executes no MCDM operator, and does not inspect
an ITS winner.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from src import oracle_attribution_weights_v1 as oracle_v1
from src import treeshap_background_v1 as background_v1


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "oracle_b100_background_diagnostic_v1.json"

FEATURES = oracle_v1.FEATURES
CRITERIA = oracle_v1.CRITERIA
Q_COLUMNS = oracle_v1.Q_COLUMNS
ALLOWED_N = oracle_v1.ALLOWED_N
ALLOWED_LAMBDAS = oracle_v1.ALLOWED_LAMBDAS
IMPORTANCE_EPSILON = oracle_v1.IMPORTANCE_EPSILON
NUMERICAL_TOL = oracle_v1.NUMERICAL_TOL

BACKGROUND_SIZE = 100
BACKGROUND_NAMESPACE = 83001
IDENTITY_COLUMNS = (
    "replication_seed",
    "context_id",
    "context_number",
    "alternative_id",
)


@dataclass(frozen=True)
class OracleB100BackgroundDiagnosticResult:
    replication_seed: int
    n_contexts: int
    lambda_value: float
    full_fit_oracle: oracle_v1.OracleAttributionResult
    b100_oracle: oracle_v1.OracleAttributionResult
    per_feature: dict[str, dict[str, float | None]]
    vector_metrics: dict[str, float | bool | None]
    moment_metrics: dict[str, float]
    coverage: dict[str, bool]
    diagnostics: dict[str, Any]


def _load_protocol() -> dict[str, Any]:
    value = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Oracle B100 protocol must contain a JSON object.")
    return value


def validate_frozen_protocol() -> dict[str, Any]:
    """Fail closed unless the committed B100 diagnostic contract is intact."""
    protocol = _load_protocol()
    if protocol["protocol_name"] != "oracle_b100_background_diagnostic_v1":
        raise ValueError("Unexpected Oracle B100 protocol identity.")
    if protocol["status"] != "freeze_before_any_oracle_b100_diagnostic_result":
        raise ValueError("Oracle B100 protocol is not frozen before results.")

    primary = protocol["primary_oracle"]
    if primary["remains_primary"] is not True:
        raise ValueError("The full-FIT Oracle must remain primary.")
    if primary["can_be_replaced_by_b100"] is not False:
        raise ValueError("B100 may not replace the primary Oracle.")
    if primary["weight_evaluation_partition"] != "weight":
        raise ValueError("Primary Oracle evaluation must remain WEIGHT.")
    if primary["equal_fallback"] is not False:
        raise ValueError("Primary Oracle Equal fallback is forbidden.")
    if float(primary["undefined_total_importance_threshold"]) != IMPORTANCE_EPSILON:
        raise ValueError("Primary Oracle undefined threshold changed.")

    b100 = protocol["b100_diagnostic_oracle"]
    expected = {
        "background_partition": "fit",
        "background_selection_unit": "alternative_context_row",
        "background_selector_module": "src/treeshap_background_v1.py",
        "background_size": BACKGROUND_SIZE,
        "equal_fallback": False,
        "only_background_moments_change": True,
        "oracle_formula_identical_to_primary": True,
        "row_priority_namespace": BACKGROUND_NAMESPACE,
        "same_membership_as_treeshap": True,
        "selector_function": "select_background_rows",
        "status": "secondary_diagnostic_only",
        "undefined_total_importance_threshold": IMPORTANCE_EPSILON,
        "weight_evaluation_partition": "weight",
        "weight_evaluation_rows_identical_to_primary_oracle": True,
    }
    for key, value in expected.items():
        if b100[key] != value:
            raise ValueError(f"Frozen B100 field {key!r} changed: {b100[key]!r}.")
    for factor in ("rho", "c", "lambda"):
        if b100[f"reuse_membership_across_{factor}"] is not True:
            raise ValueError(f"B100 membership must remain reused across {factor}.")

    scope = protocol["comparison_scope"]
    if scope["sample_sizes"] != [25, 50, 100, 250, 1000]:
        raise ValueError("Frozen B100 sample-size grid changed.")
    if scope["rho_levels"] != [0.0, 0.4, 0.8]:
        raise ValueError("Frozen B100 rho grid changed.")
    if scope["lambda_levels"] != [0.0, 0.5, 1.0]:
        raise ValueError("Frozen B100 lambda grid changed.")
    if scope["c_dependence"] != "none" or scope["reuse_result_across_c_levels"] is not True:
        raise ValueError("B100 diagnostic must remain independent of c.")
    if scope["reserve_seeds_allowed_before_primary"] is not False:
        raise ValueError("Reserve seeds remain forbidden before primary execution.")

    metrics = protocol["metrics"]
    if metrics["vector_level"] != [
        "MAE_w",
        "TV_w",
        "max_absolute_weight_difference",
        "Spearman_rho_w",
        "top3_overlap",
        "top5_overlap",
    ]:
        raise ValueError("Frozen B100 vector metrics changed.")
    if metrics["moment_level"] != [
        "max_absolute_marginal_moment_difference",
        "max_absolute_joint_moment_difference",
    ]:
        raise ValueError("Frozen B100 moment metrics changed.")
    if metrics["coverage"] != [
        "full_fit_weights_defined",
        "b100_weights_defined",
        "jointly_defined",
    ]:
        raise ValueError("Frozen B100 coverage metrics changed.")

    undefined = protocol["undefined_policy"]
    if undefined["equal_fallback_forbidden"] is not True:
        raise ValueError("B100 Equal fallback must remain forbidden.")
    if undefined["report_both_defined_flags"] is not True:
        raise ValueError("B100 must report both defined flags.")
    if undefined["do_not_drop_or_redefine_primary_oracle"] is not True:
        raise ValueError("Primary Oracle protection changed.")

    interpretation = protocol["interpretation"]
    for key in (
        "not_a_new_weighting_method",
        "not_a_primary_oracle_replacement",
        "not_a_tuning_rule",
        "cannot_change_B_bg",
        "cannot_change_D29",
        "cannot_change_oracle_formula",
        "cannot_change_primary_factorial_design",
    ):
        if interpretation[key] is not True:
            raise ValueError(f"B100 interpretation firewall {key!r} changed.")
    if any(value is not False for value in protocol["firewalls"].values()):
        raise ValueError("One or more B100 protocol firewalls are not false.")
    return protocol


def _background_identity_hash(background_rows: pd.DataFrame) -> str:
    missing = [column for column in IDENTITY_COLUMNS if column not in background_rows.columns]
    if missing:
        raise ValueError(f"Background identity hash is missing columns: {missing}.")
    payload = "\n".join(
        f"{int(seed)}|{str(context_id)}|{int(context_number)}|{str(alternative_id)}"
        for seed, context_id, context_number, alternative_id in background_rows[
            list(IDENTITY_COLUMNS)
        ].itertuples(index=False, name=None)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _materialize_selected_fit_rows(
    fit_rows: pd.DataFrame,
    selected_identity_rows: pd.DataFrame,
) -> pd.DataFrame:
    selected_ids = selected_identity_rows.loc[:, IDENTITY_COLUMNS].copy()
    selected_ids["_b100_priority_order"] = np.arange(len(selected_ids), dtype=int)

    fit = fit_rows.copy()
    if fit.duplicated(list(IDENTITY_COLUMNS)).any():
        raise ValueError("FIT rows contain duplicate complete identities.")

    merged = selected_ids.merge(
        fit,
        on=list(IDENTITY_COLUMNS),
        how="left",
        sort=False,
        validate="one_to_one",
    )
    if len(merged) != BACKGROUND_SIZE:
        raise AssertionError("B100 mapping must yield exactly 100 FIT rows.")
    if merged.loc[:, Q_COLUMNS].isna().any().any():
        raise ValueError("A frozen B100 identity was not found in eligible Oracle FIT rows.")
    if "partition" not in merged.columns or not merged["partition"].eq("fit").all():
        raise AssertionError("B100 Oracle background contains non-FIT rows.")

    merged.sort_values("_b100_priority_order", kind="stable", inplace=True)
    merged.drop(columns="_b100_priority_order", inplace=True)
    merged.reset_index(drop=True, inplace=True)

    selected_sequence = list(
        selected_ids.loc[:, IDENTITY_COLUMNS].itertuples(index=False, name=None)
    )
    mapped_sequence = list(
        merged.loc[:, IDENTITY_COLUMNS].itertuples(index=False, name=None)
    )
    if mapped_sequence != selected_sequence:
        raise AssertionError("B100 Oracle identity order differs from TreeSHAP selection.")
    return merged


def _weights_from_moments(
    evaluation_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    oracle_spec: Any,
    lambda_value: float,
    moments: oracle_v1.OracleBackgroundMoments,
) -> oracle_v1.OracleAttributionResult:
    phi = oracle_v1.closed_form_oracle_shapley(
        evaluation_rows,
        oracle_spec=oracle_spec,
        lambda_value=lambda_value,
        background_moments=moments,
    )
    importance = np.mean(np.abs(phi), axis=0)
    if importance.shape != (len(FEATURES),):
        raise AssertionError("Unexpected B100 Oracle importance shape.")
    if not np.isfinite(importance).all() or np.any(importance < 0.0):
        raise ValueError("B100 Oracle global importances are invalid.")

    total = float(importance.sum())
    importance_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, importance, strict=True)
    }
    if total <= IMPORTANCE_EPSILON:
        defined = False
        weights_by_feature = None
    else:
        weights = importance / total
        if not np.isfinite(weights).all() or np.any(weights < 0.0):
            raise ValueError("B100 Oracle normalized weights are invalid.")
        if not np.isclose(float(weights.sum()), 1.0, atol=NUMERICAL_TOL, rtol=0.0):
            raise ValueError("B100 Oracle normalized weights do not sum to one.")
        defined = True
        weights_by_feature = {
            feature: float(value)
            for feature, value in zip(FEATURES, weights, strict=True)
        }

    diagnostics: dict[str, Any] = {
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "lambda": float(lambda_value),
        "fit_background_rows": BACKGROUND_SIZE,
        "weight_evaluation_rows": int(len(evaluation_rows)),
        "background_partition": "fit",
        "evaluation_partition": "weight",
        "total_importance": total,
        "importance_epsilon": IMPORTANCE_EPSILON,
        "undefined_oracle_attribution_weight_vector": not defined,
        "equal_weight_fallback_used": False,
        "external_test_rows_used_for_background": 0,
        "external_test_rows_used_for_global_oracle_weights": 0,
        "target_Y_used": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
    }
    return oracle_v1.OracleAttributionResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        lambda_value=float(lambda_value),
        weights_defined=defined,
        importance_by_feature=importance_by_feature,
        weights_by_feature=weights_by_feature,
        background_moments=moments,
        diagnostics=diagnostics,
    )


def _average_ranks_ascending(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = 0.5 * ((start + 1) + end)
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def _spearman_rho(left: np.ndarray, right: np.ndarray) -> float | None:
    left_ranks = _average_ranks_ascending(left)
    right_ranks = _average_ranks_ascending(right)
    left_centered = left_ranks - float(left_ranks.mean())
    right_centered = right_ranks - float(right_ranks.mean())
    denominator = float(
        np.sqrt(np.dot(left_centered, left_centered) * np.dot(right_centered, right_centered))
    )
    if denominator <= NUMERICAL_TOL:
        return None
    rho = float(np.dot(left_centered, right_centered) / denominator)
    return float(np.clip(rho, -1.0, 1.0))


def _top_k_features(weights: np.ndarray, k: int) -> tuple[str, ...]:
    order = sorted(range(len(FEATURES)), key=lambda index: (-float(weights[index]), index))
    return tuple(FEATURES[index] for index in order[: int(k)])


def _vector_comparison_metrics(
    full_result: oracle_v1.OracleAttributionResult,
    b100_result: oracle_v1.OracleAttributionResult,
) -> tuple[dict[str, dict[str, float | None]], dict[str, float | bool | None]]:
    jointly_defined = bool(full_result.weights_defined and b100_result.weights_defined)
    per_feature: dict[str, dict[str, float | None]] = {}

    full_weights = full_result.weights_by_feature
    b100_weights = b100_result.weights_by_feature
    for feature in FEATURES:
        full_value = None if full_weights is None else float(full_weights[feature])
        b100_value = None if b100_weights is None else float(b100_weights[feature])
        difference = (
            None
            if full_value is None or b100_value is None
            else float(abs(b100_value - full_value))
        )
        per_feature[feature] = {
            "full_fit_oracle_weight": full_value,
            "b100_oracle_weight": b100_value,
            "absolute_weight_difference": difference,
        }

    if not jointly_defined:
        return per_feature, {
            "MAE_w": None,
            "TV_w": None,
            "max_absolute_weight_difference": None,
            "Spearman_rho_w": None,
            "Spearman_rho_w_defined": False,
            "top3_overlap": None,
            "top5_overlap": None,
        }

    assert full_weights is not None and b100_weights is not None
    full = np.asarray([full_weights[feature] for feature in FEATURES], dtype=float)
    b100 = np.asarray([b100_weights[feature] for feature in FEATURES], dtype=float)
    absolute = np.abs(b100 - full)
    spearman = _spearman_rho(full, b100)
    top3_full = set(_top_k_features(full, 3))
    top3_b100 = set(_top_k_features(b100, 3))
    top5_full = set(_top_k_features(full, 5))
    top5_b100 = set(_top_k_features(b100, 5))
    return per_feature, {
        "MAE_w": float(np.mean(absolute)),
        "TV_w": float(0.5 * np.sum(absolute)),
        "max_absolute_weight_difference": float(np.max(absolute)),
        "Spearman_rho_w": spearman,
        "Spearman_rho_w_defined": spearman is not None,
        "top3_overlap": float(len(top3_full & top3_b100) / 3.0),
        "top5_overlap": float(len(top5_full & top5_b100) / 5.0),
    }


def _moment_comparison_metrics(
    full: oracle_v1.OracleBackgroundMoments,
    b100: oracle_v1.OracleBackgroundMoments,
) -> dict[str, float]:
    if set(full.marginal_by_criterion) != set(CRITERIA):
        raise ValueError("Full-FIT marginal moments do not contain exactly C1..C10.")
    if set(b100.marginal_by_criterion) != set(CRITERIA):
        raise ValueError("B100 marginal moments do not contain exactly C1..C10.")
    if set(full.joint_by_pair) != set(b100.joint_by_pair):
        raise ValueError("Full-FIT and B100 joint-moment keys differ.")

    marginal_difference = max(
        abs(float(b100.marginal_by_criterion[c]) - float(full.marginal_by_criterion[c]))
        for c in CRITERIA
    )
    joint_difference = max(
        abs(float(b100.joint_by_pair[key]) - float(full.joint_by_pair[key]))
        for key in full.joint_by_pair
    )
    return {
        "max_absolute_marginal_moment_difference": float(marginal_difference),
        "max_absolute_joint_moment_difference": float(joint_difference),
    }


def compute_oracle_b100_background_diagnostic(
    oracle_rows: pd.DataFrame,
    *,
    selection_master_rows: pd.DataFrame,
    replication_seed: int,
    n_contexts: int,
    oracle_spec: Any,
    lambda_value: float,
) -> OracleB100BackgroundDiagnosticResult:
    """Compare primary full-FIT and B100-matched Oracle attribution weights.

    ``selection_master_rows`` supplies only the complete frozen 1200-context
    alternative-row identity/partition master required by the already-frozen
    TreeSHAP selector.  Scientific q-values are read from ``oracle_rows`` only;
    external TEST values are neither required nor used.
    """
    validate_frozen_protocol()

    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")
    lam = oracle_v1._validated_lambda(lambda_value)
    oracle_v1._validated_spec(oracle_spec)

    fit_rows, weight_rows = oracle_v1.prepare_oracle_attribution_rows(
        oracle_rows,
        replication_seed=int(replication_seed),
        n_contexts=n,
    )
    full_result = oracle_v1.compute_oracle_attribution_weights(
        oracle_rows,
        replication_seed=int(replication_seed),
        n_contexts=n,
        oracle_spec=oracle_spec,
        lambda_value=lam,
    )

    selected_identity_rows, selector_audit = background_v1.select_background_rows(
        selection_master_rows,
        replication_seed=int(replication_seed),
        n_contexts=n,
        target_size=BACKGROUND_SIZE,
        namespace=BACKGROUND_NAMESPACE,
    )
    b100_fit_rows = _materialize_selected_fit_rows(fit_rows, selected_identity_rows)
    b100_moments = oracle_v1.compute_fit_background_moments(
        b100_fit_rows,
        oracle_spec=oracle_spec,
    )
    b100_result = _weights_from_moments(
        weight_rows,
        replication_seed=int(replication_seed),
        n_contexts=n,
        oracle_spec=oracle_spec,
        lambda_value=lam,
        moments=b100_moments,
    )

    per_feature, vector_metrics = _vector_comparison_metrics(full_result, b100_result)
    moment_metrics = _moment_comparison_metrics(
        full_result.background_moments,
        b100_result.background_moments,
    )
    jointly_defined = bool(full_result.weights_defined and b100_result.weights_defined)
    coverage = {
        "full_fit_weights_defined": bool(full_result.weights_defined),
        "b100_weights_defined": bool(b100_result.weights_defined),
        "jointly_defined": jointly_defined,
    }

    diagnostics: dict[str, Any] = {
        "replication_seed": int(replication_seed),
        "N": n,
        "lambda": lam,
        "c_dependence": "none",
        "reuse_result_across_c_levels": True,
        "full_fit_background_rows": int(len(fit_rows)),
        "b100_background_rows": int(len(b100_fit_rows)),
        "weight_evaluation_rows": int(len(weight_rows)),
        "same_weight_evaluation_rows": True,
        "only_background_moments_changed": True,
        "background_identity_sha256": _background_identity_hash(b100_fit_rows),
        "background_selector_module": "src/treeshap_background_v1.py",
        "background_selector_function": "select_background_rows",
        "background_namespace": BACKGROUND_NAMESPACE,
        "selector_audit": dict(selector_audit),
        "full_fit_total_importance": float(full_result.diagnostics["total_importance"]),
        "b100_total_importance": float(b100_result.diagnostics["total_importance"]),
        "full_fit_equal_fallback_used": False,
        "b100_equal_fallback_used": False,
        "external_test_rows_used_for_moments": 0,
        "external_test_rows_used_for_weight_evaluation": 0,
        "target_Y_used": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
        "winner_identity_used": False,
    }

    return OracleB100BackgroundDiagnosticResult(
        replication_seed=int(replication_seed),
        n_contexts=n,
        lambda_value=lam,
        full_fit_oracle=full_result,
        b100_oracle=b100_result,
        per_feature=per_feature,
        vector_metrics=vector_metrics,
        moment_metrics=moment_metrics,
        coverage=coverage,
        diagnostics=diagnostics,
    )
