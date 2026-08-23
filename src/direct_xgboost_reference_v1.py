from __future__ import annotations

"""Frozen DirectXGBoost TEST-scoring reference.

DirectXGBoost is a parallel predictive-decision reference, not a weighting
method and not a sequential stage of an additive error decomposition.  This
module receives an already-fitted XGBoost-compatible predictor, scores only the
fixed external TEST alternatives, and emits the common raw-score table consumed
by ``decision_fidelity_metrics_v1``.  It never fits/refits a model, reads Y or
U_star for scoring, estimates weights, invokes SHAP/MCDM, or writes results.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
WEIGHTING_PROTOCOL_PATH = ROOT / "config" / "weighting_mcdm_protocol_v1.json"
EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"
XGBOOST_PATH = ROOT / "config" / "xgboost.yaml"

METHOD = "DirectXGBoost"
FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
SORT_COLUMNS = ("context_number", "alternative_id")
EXPECTED_TEST_CONTEXTS = 200
ALTERNATIVES_PER_CONTEXT = 6
EXPECTED_TEST_ROWS = EXPECTED_TEST_CONTEXTS * ALTERNATIVES_PER_CONTEXT
SCORE_TIE_ABSOLUTE_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class DirectXGBoostReferenceResult:
    replication_seed: int
    scored_rows: pd.DataFrame
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


def validate_frozen_direct_xgboost_protocol() -> dict[str, Any]:
    """Fail closed unless the committed DirectXGBoost contract is intact."""
    protocol = _load_json(WEIGHTING_PROTOCOL_PATH)
    experiment = _load_yaml(EXPERIMENT_PATH)
    xgboost = _load_yaml(XGBOOST_PATH)

    reference = protocol["diagnostic_references"][METHOD]
    if reference != {
        "enabled": True,
        "required_before_pilot_B": True,
        "role": "parallel_predictive_decision_reference",
    }:
        raise ValueError("Frozen DirectXGBoost diagnostic-reference contract changed.")

    ladder = protocol["stagewise_fidelity"]
    if ladder["enabled"] is not True:
        raise ValueError("Frozen stage-wise fidelity diagnostic is disabled.")
    if ladder["claim_additive_error_decomposition"] is not False:
        raise ValueError("Stage-wise fidelity cannot be an additive decomposition.")
    if ladder["direct_xgboost_role"] != (
        "parallel_reference_not_sequential_transformation_stage"
    ):
        raise ValueError("Frozen DirectXGBoost stage-wise role changed.")
    if ladder["stages"][-1] != METHOD:
        raise ValueError("DirectXGBoost must remain the parallel ninth reference.")

    metrics = protocol["decision_metrics"]
    if metrics["kendall"] != "tau_b":
        raise ValueError("Frozen Kendall variant changed.")
    if metrics["score_tie_absolute_tolerance"] != SCORE_TIE_ABSOLUTE_TOLERANCE:
        raise ValueError("Frozen score-tie tolerance changed.")
    if metrics["tie_grouping_rule"] != "use_common_anchor_based_rule":
        raise ValueError("Frozen common tie-grouping rule changed.")
    if metrics["top1_tie_break"] != "alternative_id_ascending":
        raise ValueError("Frozen deterministic Top-1 tie break changed.")

    direct = experiment["direct_model_reference"]
    if direct["enabled"] is not True or direct["model"] != "XGBoost":
        raise ValueError("Frozen direct-model reference changed.")
    if direct["method"] != {
        "predict_each_test_alternative": True,
        "rank_predictions_within_context": True,
    }:
        raise ValueError("Frozen DirectXGBoost scoring method changed.")
    if direct["compare_against_oracle"] != [
        "KendallTauB",
        "Top1Accuracy",
        "NormalizedOracleRegret",
    ]:
        raise ValueError("Frozen DirectXGBoost evaluation metrics changed.")
    if xgboost["evaluation"]["primary_partition"] != "test":
        raise ValueError("Frozen predictive evaluation partition changed.")

    model_fit = xgboost["treeshap_computation"]["model_fit"]
    if model_fit["feature_columns"] != list(FEATURES):
        raise ValueError("Frozen XGBoost feature order changed.")
    if model_fit["target_column"] != "Y" or model_fit["fit_partition"] != "fit":
        raise ValueError("Frozen XGBoost FIT/Y model contract changed.")
    if model_fit["weight_partition_used_for_model_fit"] is not False:
        raise ValueError("WEIGHT must remain excluded from XGBoost fitting.")
    if model_fit["external_test_used_for_model_fit"] is not False:
        raise ValueError("External TEST must remain excluded from XGBoost fitting.")

    return {"protocol": protocol, "experiment": experiment, "xgboost": xgboost}


def prepare_direct_xgboost_test_rows(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
) -> pd.DataFrame:
    """Select and validate the fixed TEST alternative-context rows."""
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        *FEATURES,
    }
    missing = sorted(required - set(master_rows.columns))
    if missing:
        raise ValueError(f"DirectXGBoost input is missing columns: {missing}.")

    selected = master_rows.loc[
        master_rows["partition"].eq("test"), list(required)
    ].copy()
    if len(selected) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"DirectXGBoost requires {EXPECTED_TEST_ROWS} TEST rows; "
            f"found {len(selected)}."
        )
    if selected["replication_seed"].isna().any():
        raise ValueError("TEST replication_seed contains missing values.")
    seeds = set(selected["replication_seed"].astype(int).tolist())
    if seeds != {int(replication_seed)}:
        raise ValueError(
            f"DirectXGBoost TEST rows require replication_seed={replication_seed}; "
            f"found {sorted(seeds)}."
        )
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate TEST context-alternative identity detected.")

    selected.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)
    if selected["context_number"].nunique() != EXPECTED_TEST_CONTEXTS:
        raise ValueError(
            f"DirectXGBoost requires {EXPECTED_TEST_CONTEXTS} TEST contexts."
        )
    if selected.groupby("context_number")["context_id"].nunique().max() != 1:
        raise ValueError("A TEST context number maps to multiple context IDs.")
    for context_number, group in selected.groupby("context_number", sort=False):
        alternatives = tuple(group["alternative_id"].astype(str).tolist())
        if alternatives != ALTERNATIVE_IDS:
            raise ValueError(
                f"TEST context {context_number} must contain A1..A6 exactly once."
            )

    X_test = selected.loc[:, FEATURES].to_numpy(dtype=float)
    if not np.isfinite(X_test).all():
        raise ValueError("DirectXGBoost TEST features contain non-finite values.")
    return selected


def score_direct_xgboost_test_rows(
    fitted_predictor: Any,
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
) -> DirectXGBoostReferenceResult:
    """Predict every fixed TEST alternative with an already-fitted predictor."""
    validate_frozen_direct_xgboost_protocol()
    test = prepare_direct_xgboost_test_rows(
        master_rows, replication_seed=replication_seed
    )
    predict = getattr(fitted_predictor, "predict", None)
    if not callable(predict):
        raise TypeError("DirectXGBoost requires an already-fitted predictor with predict().")

    X_test = test.loc[:, FEATURES].to_numpy(dtype=float)
    raw_prediction = np.asarray(predict(X_test), dtype=float)
    if raw_prediction.shape != (len(test),):
        raise ValueError(
            f"DirectXGBoost prediction shape {raw_prediction.shape} is invalid; "
            f"expected {(len(test),)}."
        )
    if not np.isfinite(raw_prediction).all():
        raise ValueError("DirectXGBoost predictions contain non-finite values.")

    scored = test.loc[:, [
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
    ]].copy()
    scored["method"] = METHOD
    scored["score"] = raw_prediction

    diagnostics: dict[str, Any] = {
        "method": METHOD,
        "role": "parallel_predictive_decision_reference",
        "stagewise_role": "parallel_reference_not_sequential_transformation_stage",
        "evaluation_partition": "test",
        "test_contexts": EXPECTED_TEST_CONTEXTS,
        "test_rows": EXPECTED_TEST_ROWS,
        "feature_columns": list(FEATURES),
        "feature_order_matches_frozen_xgboost": True,
        "already_fitted_predictor_received": True,
        "predict_calls": 1,
        "raw_predictions_emitted_for_common_decision_metrics": True,
        "common_score_tie_absolute_tolerance": SCORE_TIE_ABSOLUTE_TOLERANCE,
        "model_fit_executed": False,
        "target_Y_used_for_scoring": False,
        "oracle_U_star_used_for_scoring": False,
        "weight_estimation_executed": False,
        "shap_executed": False,
        "mcdm_executed": False,
        "decision_metrics_computed": False,
        "results_written": False,
    }
    return DirectXGBoostReferenceResult(
        replication_seed=int(replication_seed),
        scored_rows=scored,
        diagnostics=diagnostics,
    )
