from __future__ import annotations

"""Frozen nine-representation stage-wise decision-fidelity ladder.

The ladder is descriptive and diagnostic, not an additive or causal error
decomposition.  It consumes already-generated TEST rows, already-estimated
Oracle/SHAP global weights, and already-produced DirectXGBoost TEST scores.
It reuses the frozen oracle q transform, MOORA operator, and decision metrics.
No model is fitted, no weights or SHAP values are estimated, and no files are
written here.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "weighting_mcdm_protocol_v1.json"
EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"

FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
EXPECTED_TEST_CONTEXTS = 200
EXPECTED_TEST_ROWS = 1200
EPSILON = 1.0e-12
ZETA = 2.0

STAGES = (
    "OracleUtility",
    "OracleMainEffectReference",
    "OracleGlobalAttributionNonlinearQ",
    "SHAPGlobalAttributionNonlinearQ",
    "OracleGlobalAttributionLinearG",
    "SHAPGlobalAttributionLinearG",
    "OracleWeightMOORA",
    "SHAPWeightMOORA",
    "DirectXGBoost",
)

PAIRED_CONTRASTS = (
    ("interaction_removal", "OracleUtility", "OracleMainEffectReference"),
    (
        "global_oracle_weight_compression",
        "OracleMainEffectReference",
        "OracleGlobalAttributionNonlinearQ",
    ),
    (
        "shap_attribution_estimation_nonlinear_q",
        "OracleGlobalAttributionNonlinearQ",
        "SHAPGlobalAttributionNonlinearQ",
    ),
    (
        "nonlinear_to_linear_oracle_weights",
        "OracleGlobalAttributionNonlinearQ",
        "OracleGlobalAttributionLinearG",
    ),
    (
        "nonlinear_to_linear_shap_weights",
        "SHAPGlobalAttributionNonlinearQ",
        "SHAPGlobalAttributionLinearG",
    ),
    (
        "mcdm_transformation_oracle_weights",
        "OracleGlobalAttributionLinearG",
        "OracleWeightMOORA",
    ),
    (
        "mcdm_transformation_shap_weights",
        "SHAPGlobalAttributionLinearG",
        "SHAPWeightMOORA",
    ),
    ("post_mcdm_attribution", "OracleWeightMOORA", "SHAPWeightMOORA"),
)

PRIMARY_ALPHA_BY_FEATURE = {
    "g_C1": 0.11,
    "g_C2": 0.04,
    "g_C3": 0.05,
    "g_C4": 0.07,
    "g_C5": 0.10,
    "g_C6": 0.14,
    "g_C7": 0.12,
    "g_C8": 0.16,
    "g_C9": 0.08,
    "g_C10": 0.13,
}


def _load_sibling(filename: str, module_name: str):
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load frozen sibling module {filename}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ORACLE_UTILITY = _load_sibling(
    "03_generate_oracle_utility.py", "stagewise_oracle_utility_v1_dependency"
)
_MOORA = _load_sibling("moora_topsis_v1.py", "stagewise_moora_v1_dependency")
_METRICS = _load_sibling(
    "decision_fidelity_metrics_v1.py", "stagewise_decision_metrics_v1_dependency"
)


@dataclass(frozen=True)
class StagewiseFidelityResult:
    scores_by_stage: dict[str, pd.DataFrame]
    evaluations_by_stage: dict[str, Any]
    stage_summary: pd.DataFrame
    paired_contrasts: pd.DataFrame
    diagnostics: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    return value


def validate_frozen_stagewise_protocol() -> dict[str, Any]:
    """Fail closed unless the committed ladder and contrasts are intact."""
    protocol = _load_json(PROTOCOL_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    frozen = protocol["stagewise_fidelity"]
    if frozen["enabled"] is not True:
        raise ValueError("Frozen stage-wise fidelity ladder is disabled.")
    if frozen["claim_additive_error_decomposition"] is not False:
        raise ValueError("The ladder may not be an additive error decomposition.")
    if tuple(frozen["stages"]) != STAGES:
        raise ValueError("Frozen nine-stage order changed.")
    if tuple(experiment["stagewise_fidelity"]["stages"]) != STAGES:
        raise ValueError("Experiment and protocol stage orders differ.")
    if frozen["direct_xgboost_role"] != (
        "parallel_reference_not_sequential_transformation_stage"
    ):
        raise ValueError("Frozen DirectXGBoost ladder role changed.")
    observed_contrasts = tuple(
        (item["name"], item["reference"], item["comparison"])
        for item in frozen["paired_contrasts"]
    )
    if observed_contrasts != PAIRED_CONTRASTS:
        raise ValueError("Frozen paired contrasts changed.")
    if frozen["report_for_each_representation"] != [
        "KendallTauB",
        "NormalizedOracleRegret",
    ]:
        raise ValueError("Frozen stage-wise reporting metrics changed.")
    if protocol["diagnostic_references"]["DirectXGBoost"]["role"] != (
        "parallel_predictive_decision_reference"
    ):
        raise ValueError("Frozen DirectXGBoost diagnostic role changed.")
    if protocol["moora"]["role"] != "primary_mcdm":
        raise ValueError("Frozen primary MCDM changed from MOORA.")
    return {"protocol": protocol, "experiment": experiment}


def _prepare_test_rows(rows: pd.DataFrame) -> pd.DataFrame:
    required = {
        "context_id",
        "context_number",
        "partition",
        "alternative_id",
        "U_star",
        *FEATURES,
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Stage-wise TEST input is missing columns: {missing}.")
    selected = rows.loc[rows["partition"].eq("test")].copy()
    if len(selected) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"Stage-wise ladder requires {EXPECTED_TEST_ROWS} TEST rows; "
            f"found {len(selected)}."
        )
    selected.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate TEST context-alternative identity detected.")
    if selected["context_number"].nunique() != EXPECTED_TEST_CONTEXTS:
        raise ValueError(
            f"Stage-wise ladder requires {EXPECTED_TEST_CONTEXTS} TEST contexts."
        )
    if selected.groupby("context_number")["context_id"].nunique().max() != 1:
        raise ValueError("A TEST context number maps to multiple context IDs.")
    for context_number, group in selected.groupby("context_number", sort=False):
        alternatives = tuple(group["alternative_id"].astype(str).tolist())
        if alternatives != ALTERNATIVE_IDS:
            raise ValueError(
                f"TEST context {context_number} must contain A1..A6 exactly once."
            )
    g = selected.loc[:, FEATURES].to_numpy(dtype=float)
    if not np.isfinite(g).all():
        raise ValueError("Stage-wise TEST G contains non-finite values.")
    if np.any(g < -EPSILON) or np.any(g > 1.0 + EPSILON):
        raise ValueError("Stage-wise TEST G must lie in [0,1].")
    utility = selected["U_star"].to_numpy(dtype=float)
    if not np.isfinite(utility).all():
        raise ValueError("Stage-wise TEST U_star contains non-finite values.")
    if np.any(utility < -EPSILON) or np.any(utility > 1.0 + EPSILON):
        raise ValueError("Stage-wise TEST U_star must lie in [0,1].")
    return selected


def _score_table(selected: pd.DataFrame, stage: str, scores: np.ndarray) -> pd.DataFrame:
    values = np.asarray(scores, dtype=float)
    if values.shape != (len(selected),):
        raise ValueError(f"Stage {stage} score shape is invalid: {values.shape}.")
    if not np.isfinite(values).all():
        raise ValueError(f"Stage {stage} scores contain non-finite values.")
    result = selected.loc[:, [
        "context_id", "context_number", "partition", "alternative_id"
    ]].copy()
    result["method"] = stage
    result["score"] = values
    return result


def _coerce_weights(
    weights: Mapping[str, float] | Sequence[float] | np.ndarray,
) -> np.ndarray:
    return _MOORA.coerce_weights(weights)


def _direct_score_table(
    selected: pd.DataFrame,
    direct_scored_rows: pd.DataFrame,
) -> pd.DataFrame:
    required = {"context_id", "context_number", "alternative_id", "score"}
    missing = sorted(required - set(direct_scored_rows.columns))
    if missing:
        raise ValueError(f"DirectXGBoost scored rows are missing columns: {missing}.")
    direct = direct_scored_rows.copy()
    if "partition" in direct:
        if not direct["partition"].eq("test").all():
            raise ValueError("DirectXGBoost scored rows must be TEST-only.")
    if "method" in direct:
        if not direct["method"].astype(str).eq("DirectXGBoost").all():
            raise ValueError("DirectXGBoost method labels changed.")
    direct.sort_values(["context_number", "alternative_id"], kind="stable", inplace=True)
    direct.reset_index(drop=True, inplace=True)
    if direct.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate DirectXGBoost context-alternative identity.")
    expected_identity = list(
        selected.loc[:, ["context_id", "context_number", "alternative_id"]]
        .itertuples(index=False, name=None)
    )
    observed_identity = list(
        direct.loc[:, ["context_id", "context_number", "alternative_id"]]
        .itertuples(index=False, name=None)
    )
    if observed_identity != expected_identity:
        raise ValueError("DirectXGBoost and TEST identities differ.")
    return _score_table(
        selected,
        "DirectXGBoost",
        direct["score"].to_numpy(dtype=float),
    )


def _stage_summary(
    evaluations: dict[str, Any],
    undefined_reasons: dict[str, str],
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for stage_index, stage in enumerate(STAGES, start=1):
        evaluation = evaluations.get(stage)
        if evaluation is None:
            records.append({
                "stage_index": stage_index,
                "stage": stage,
                "defined": False,
                "undefined_reason": undefined_reasons[stage],
                "top1_accuracy": None,
                "mean_kendall_tau_b_defined_contexts": None,
                "kendall_tau_b_defined_contexts": 0,
                "kendall_tau_b_undefined_contexts": 0,
                "mean_normalized_oracle_regret": None,
                "median_normalized_oracle_regret": None,
                "p95_normalized_oracle_regret": None,
            })
            continue
        summary = evaluation.summary
        records.append({
            "stage_index": stage_index,
            "stage": stage,
            "defined": True,
            "undefined_reason": None,
            "top1_accuracy": summary["top1_accuracy"],
            "mean_kendall_tau_b_defined_contexts": summary[
                "mean_kendall_tau_b_defined_contexts"
            ],
            "kendall_tau_b_defined_contexts": summary[
                "kendall_tau_b_defined_contexts"
            ],
            "kendall_tau_b_undefined_contexts": summary[
                "kendall_tau_b_undefined_contexts"
            ],
            "mean_normalized_oracle_regret": summary[
                "mean_normalized_oracle_regret"
            ],
            "median_normalized_oracle_regret": summary[
                "median_normalized_oracle_regret"
            ],
            "p95_normalized_oracle_regret": summary[
                "p95_normalized_oracle_regret"
            ],
        })
    return pd.DataFrame.from_records(records)


def _difference(comparison: Any, reference: Any, key: str) -> float | None:
    left = comparison.summary[key]
    right = reference.summary[key]
    if left is None or right is None:
        return None
    return float(left - right)


def _paired_contrast_table(evaluations: dict[str, Any]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for name, reference, comparison in PAIRED_CONTRASTS:
        reference_value = evaluations.get(reference)
        comparison_value = evaluations.get(comparison)
        defined = reference_value is not None and comparison_value is not None
        records.append({
            "contrast": name,
            "reference": reference,
            "comparison": comparison,
            "direction": "comparison_minus_reference",
            "defined": defined,
            "undefined_reason": None if defined else "one_or_both_representations_undefined",
            "delta_top1_accuracy": (
                _difference(comparison_value, reference_value, "top1_accuracy")
                if defined else None
            ),
            "delta_mean_kendall_tau_b_defined_contexts": (
                _difference(
                    comparison_value,
                    reference_value,
                    "mean_kendall_tau_b_defined_contexts",
                ) if defined else None
            ),
            "delta_mean_normalized_oracle_regret": (
                _difference(
                    comparison_value,
                    reference_value,
                    "mean_normalized_oracle_regret",
                ) if defined else None
            ),
        })
    return pd.DataFrame.from_records(records)


def compute_stagewise_fidelity_ladder(
    test_rows: pd.DataFrame,
    *,
    oracle_weights: Mapping[str, float] | Sequence[float] | np.ndarray | None,
    shap_weights: Mapping[str, float] | Sequence[float] | np.ndarray | None,
    direct_xgboost_scored_rows: pd.DataFrame,
    alpha_by_feature: Mapping[str, float] | Sequence[float] | np.ndarray = PRIMARY_ALPHA_BY_FEATURE,
) -> StagewiseFidelityResult:
    """Compute frozen TEST scores, fidelity metrics, and paired contrasts."""
    validate_frozen_stagewise_protocol()
    selected = _prepare_test_rows(test_rows)
    alpha = _coerce_weights(alpha_by_feature)
    oracle = None if oracle_weights is None else _coerce_weights(oracle_weights)
    shap = None if shap_weights is None else _coerce_weights(shap_weights)

    g = selected.loc[:, FEATURES].to_numpy(dtype=float)
    q = _ORACLE_UTILITY.q_transform(g, zeta=ZETA)
    if q.shape != g.shape or not np.isfinite(q).all():
        raise FloatingPointError("Frozen oracle q transform produced invalid values.")

    scores: dict[str, pd.DataFrame] = {}
    undefined: dict[str, str] = {}
    scores["OracleUtility"] = _score_table(
        selected, "OracleUtility", selected["U_star"].to_numpy(dtype=float)
    )
    scores["OracleMainEffectReference"] = _score_table(
        selected, "OracleMainEffectReference", q @ alpha
    )

    oracle_stages = (
        "OracleGlobalAttributionNonlinearQ",
        "OracleGlobalAttributionLinearG",
        "OracleWeightMOORA",
    )
    if oracle is None:
        for stage in oracle_stages:
            undefined[stage] = "oracle_attribution_weights_undefined"
    else:
        scores["OracleGlobalAttributionNonlinearQ"] = _score_table(
            selected, "OracleGlobalAttributionNonlinearQ", q @ oracle
        )
        scores["OracleGlobalAttributionLinearG"] = _score_table(
            selected, "OracleGlobalAttributionLinearG", g @ oracle
        )
        moora_oracle = _MOORA.score_test_contexts(
            selected, oracle, method="MOORA"
        ).scored_rows
        scores["OracleWeightMOORA"] = _score_table(
            selected,
            "OracleWeightMOORA",
            moora_oracle["score"].to_numpy(dtype=float),
        )

    shap_stages = (
        "SHAPGlobalAttributionNonlinearQ",
        "SHAPGlobalAttributionLinearG",
        "SHAPWeightMOORA",
    )
    if shap is None:
        for stage in shap_stages:
            undefined[stage] = "shap_attribution_weights_undefined"
    else:
        scores["SHAPGlobalAttributionNonlinearQ"] = _score_table(
            selected, "SHAPGlobalAttributionNonlinearQ", q @ shap
        )
        scores["SHAPGlobalAttributionLinearG"] = _score_table(
            selected, "SHAPGlobalAttributionLinearG", g @ shap
        )
        moora_shap = _MOORA.score_test_contexts(
            selected, shap, method="MOORA"
        ).scored_rows
        scores["SHAPWeightMOORA"] = _score_table(
            selected,
            "SHAPWeightMOORA",
            moora_shap["score"].to_numpy(dtype=float),
        )

    scores["DirectXGBoost"] = _direct_score_table(
        selected, direct_xgboost_scored_rows
    )
    scores = {stage: scores[stage] for stage in STAGES if stage in scores}

    evaluations = {
        stage: _METRICS.evaluate_decision_fidelity_batch(
            stage_scores,
            selected,
            method=stage,
        )
        for stage, stage_scores in scores.items()
    }
    summary = _stage_summary(evaluations, undefined)
    contrasts = _paired_contrast_table(evaluations)
    diagnostics: dict[str, Any] = {
        "stage_order": list(STAGES),
        "stage_count": len(STAGES),
        "defined_stage_count": len(scores),
        "undefined_stage_count": len(STAGES) - len(scores),
        "defined_stages": [stage for stage in STAGES if stage in scores],
        "undefined_stages": {
            stage: undefined[stage] for stage in STAGES if stage in undefined
        },
        "claim_additive_error_decomposition": False,
        "interpretation": "prespecified_paired_contrasts_not_causal_decomposition",
        "direct_xgboost_role": "parallel_reference_not_sequential_transformation_stage",
        "evaluation_partition": "test",
        "q_transform": "log(1+2g)/log(3)",
        "primary_mcdm": "MOORA",
        "model_fit_executed": False,
        "weight_estimation_executed": False,
        "shap_estimation_executed": False,
        "direct_xgboost_prediction_executed": False,
        "direct_xgboost_scores_received": True,
        "target_Y_used": False,
        "oracle_U_star_used_for_reference_and_evaluation": True,
        "mcdm_scoring_executed": oracle is not None or shap is not None,
        "decision_metrics_computed": True,
        "paired_contrasts_computed": True,
        "bootstrap_executed": False,
        "results_written": False,
    }
    return StagewiseFidelityResult(
        scores_by_stage=scores,
        evaluations_by_stage=evaluations,
        stage_summary=summary,
        paired_contrasts=contrasts,
        diagnostics=diagnostics,
    )
