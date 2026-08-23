from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "direct_xgboost_reference_v1.py"
spec = importlib.util.spec_from_file_location(
    "direct_xgboost_reference_v1_test_module", MODULE_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load direct_xgboost_reference_v1.py.")
direct = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = direct
spec.loader.exec_module(direct)

METRICS_PATH = ROOT / "src" / "decision_fidelity_metrics_v1.py"
metrics_spec = importlib.util.spec_from_file_location(
    "decision_fidelity_metrics_v1_direct_integration_module", METRICS_PATH
)
if metrics_spec is None or metrics_spec.loader is None:
    raise RuntimeError("Could not load decision_fidelity_metrics_v1.py.")
metrics = importlib.util.module_from_spec(metrics_spec)
sys.modules[metrics_spec.name] = metrics
metrics_spec.loader.exec_module(metrics)


class RecordingPredictor:
    def __init__(self, coefficients=None):
        self.coefficients = np.asarray(
            coefficients if coefficients is not None else np.arange(1.0, 11.0),
            dtype=float,
        )
        self.predict_calls = 0
        self.last_X = None

    def predict(self, X):
        self.predict_calls += 1
        self.last_X = np.asarray(X, dtype=float).copy()
        return np.sum(self.last_X * self.coefficients[None, :], axis=1)

    def fit(self, *_args, **_kwargs):
        raise AssertionError("DirectXGBoost must never fit/refit the predictor.")


def make_master(replication_seed=12345, *, include_non_test=False):
    records = []
    for offset, context_number in enumerate(range(1001, 1201)):
        for alternative_number, alternative_id in enumerate(direct.ALTERNATIVE_IDS, start=1):
            record = {
                "context_id": f"test_{context_number}",
                "context_number": context_number,
                "replication_seed": replication_seed,
                "partition": "test",
                "alternative_id": alternative_id,
                "Y": -1000.0 - offset,
                "U_star": alternative_number / 10.0,
            }
            for criterion in range(1, 11):
                record[f"g_C{criterion}"] = (
                    alternative_number / 10.0 + criterion / 100.0 + offset / 100000.0
                )
            records.append(record)
    if include_non_test:
        for alternative_id in direct.ALTERNATIVE_IDS:
            record = {
                "context_id": "fit_1",
                "context_number": 1,
                "replication_seed": replication_seed,
                "partition": "fit",
                "alternative_id": alternative_id,
                "Y": np.inf,
                "U_star": -np.inf,
            }
            for feature in direct.FEATURES:
                record[feature] = np.inf
            records.append(record)
    return pd.DataFrame.from_records(records)


def test_frozen_constants():
    assert direct.METHOD == "DirectXGBoost"
    assert direct.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert direct.ALTERNATIVE_IDS == ("A1", "A2", "A3", "A4", "A5", "A6")
    assert direct.EXPECTED_TEST_CONTEXTS == 200
    assert direct.EXPECTED_TEST_ROWS == 1200
    assert direct.SCORE_TIE_ABSOLUTE_TOLERANCE == 1e-12


def test_frozen_protocol_validation_passes():
    configs = direct.validate_frozen_direct_xgboost_protocol()
    assert configs["protocol"]["diagnostic_references"]["DirectXGBoost"]["enabled"] is True
    assert configs["experiment"]["direct_model_reference"]["model"] == "XGBoost"


def test_prepare_selects_only_test_and_sorts_stably():
    rows = make_master(include_non_test=True).sample(frac=1.0, random_state=9)
    prepared = direct.prepare_direct_xgboost_test_rows(rows, replication_seed=12345)
    assert len(prepared) == 1200
    assert prepared["partition"].eq("test").all()
    assert prepared.iloc[0]["context_number"] == 1001
    assert prepared.iloc[0]["alternative_id"] == "A1"
    assert prepared.iloc[-1]["context_number"] == 1200
    assert prepared.iloc[-1]["alternative_id"] == "A6"


def test_scoring_calls_predict_once_in_frozen_feature_order():
    rows = make_master()
    predictor = RecordingPredictor()
    result = direct.score_direct_xgboost_test_rows(
        predictor, rows, replication_seed=12345
    )
    expected_X = rows.sort_values(
        ["context_number", "alternative_id"], kind="stable"
    ).loc[:, direct.FEATURES].to_numpy(dtype=float)
    assert predictor.predict_calls == 1
    np.testing.assert_array_equal(predictor.last_X, expected_X)
    np.testing.assert_allclose(
        result.scored_rows["score"].to_numpy(),
        np.sum(expected_X * predictor.coefficients[None, :], axis=1),
    )


def test_scored_rows_have_common_decision_metric_schema():
    result = direct.score_direct_xgboost_test_rows(
        RecordingPredictor(), make_master(), replication_seed=12345
    )
    assert list(result.scored_rows.columns) == [
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        "method",
        "score",
    ]
    assert result.scored_rows["method"].eq("DirectXGBoost").all()


def test_integration_with_frozen_decision_metrics_is_exact():
    rows = make_master()
    result = direct.score_direct_xgboost_test_rows(
        RecordingPredictor(coefficients=[1.0] + [0.0] * 9),
        rows,
        replication_seed=12345,
    )
    evaluated = metrics.evaluate_decision_fidelity_batch(
        result.scored_rows,
        rows,
        method="DirectXGBoost",
    )
    assert evaluated.summary["contexts"] == 200
    assert evaluated.summary["top1_accuracy"] == 1.0
    assert evaluated.summary["mean_normalized_oracle_regret"] == 0.0
    assert evaluated.summary["mean_kendall_tau_b_defined_contexts"] == 1.0


def test_scoring_does_not_read_target_or_oracle_utility():
    rows = make_master()
    changed = rows.copy()
    changed["Y"] = np.linspace(-1e99, 1e99, len(changed))
    changed["U_star"] = np.linspace(1.0, 0.0, len(changed))
    first = direct.score_direct_xgboost_test_rows(
        RecordingPredictor(), rows, replication_seed=12345
    )
    second = direct.score_direct_xgboost_test_rows(
        RecordingPredictor(), changed, replication_seed=12345
    )
    pd.testing.assert_frame_equal(first.scored_rows, second.scored_rows)


def test_non_test_values_are_not_scored_or_validated_as_test_features():
    rows = make_master(include_non_test=True)
    predictor = RecordingPredictor()
    result = direct.score_direct_xgboost_test_rows(
        predictor, rows, replication_seed=12345
    )
    assert len(result.scored_rows) == 1200
    assert predictor.last_X.shape == (1200, 10)


@pytest.mark.parametrize(
    "missing",
    [
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        "g_C1",
        "g_C5",
        "g_C10",
    ],
)
def test_missing_required_columns_fail_closed(missing):
    rows = make_master().drop(columns=[missing])
    with pytest.raises(ValueError, match="missing columns"):
        direct.prepare_direct_xgboost_test_rows(rows, replication_seed=12345)


def test_wrong_replication_seed_fails_closed():
    with pytest.raises(ValueError, match="replication_seed=99999"):
        direct.prepare_direct_xgboost_test_rows(
            make_master(), replication_seed=99999
        )


def test_duplicate_test_identity_fails_closed():
    rows = make_master()
    changed = pd.concat([rows, rows.iloc[[0]]], ignore_index=True).iloc[:-1].copy()
    changed.iloc[-1] = changed.iloc[0]
    with pytest.raises(ValueError, match="Duplicate TEST"):
        direct.prepare_direct_xgboost_test_rows(changed, replication_seed=12345)


def test_wrong_test_row_count_fails_closed():
    with pytest.raises(ValueError, match="requires 1200 TEST rows"):
        direct.prepare_direct_xgboost_test_rows(
            make_master().iloc[:-1], replication_seed=12345
        )


def test_malformed_alternative_block_fails_closed():
    rows = make_master()
    rows.loc[rows.index[0], "alternative_id"] = "A7"
    with pytest.raises(ValueError, match="A1..A6"):
        direct.prepare_direct_xgboost_test_rows(rows, replication_seed=12345)


def test_context_number_cannot_map_to_multiple_context_ids():
    rows = make_master()
    rows.loc[rows.index[0], "context_id"] = "different"
    with pytest.raises(ValueError, match="multiple context IDs"):
        direct.prepare_direct_xgboost_test_rows(rows, replication_seed=12345)


def test_nonfinite_test_feature_fails_closed():
    rows = make_master()
    rows.loc[rows.index[0], "g_C4"] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        direct.prepare_direct_xgboost_test_rows(rows, replication_seed=12345)


def test_predictor_without_predict_fails_closed():
    with pytest.raises(TypeError, match="already-fitted predictor"):
        direct.score_direct_xgboost_test_rows(
            object(), make_master(), replication_seed=12345
        )


@pytest.mark.parametrize("shape", [(1200, 1), (1199,), (2, 600)])
def test_invalid_prediction_shape_fails_closed(shape):
    class BadShapePredictor:
        def predict(self, _X):
            return np.zeros(shape)

    with pytest.raises(ValueError, match="prediction shape"):
        direct.score_direct_xgboost_test_rows(
            BadShapePredictor(), make_master(), replication_seed=12345
        )


def test_nonfinite_prediction_fails_closed():
    class NonfinitePredictor:
        def predict(self, X):
            result = np.zeros(len(X))
            result[0] = np.nan
            return result

    with pytest.raises(ValueError, match="predictions contain non-finite"):
        direct.score_direct_xgboost_test_rows(
            NonfinitePredictor(), make_master(), replication_seed=12345
        )


def test_scoring_does_not_mutate_input_rows():
    rows = make_master().sample(frac=1.0, random_state=12).reset_index(drop=True)
    before = rows.copy(deep=True)
    direct.score_direct_xgboost_test_rows(
        RecordingPredictor(), rows, replication_seed=12345
    )
    pd.testing.assert_frame_equal(rows, before)


def test_raw_near_ties_are_preserved_for_common_metrics_layer():
    class NearTiePredictor:
        def predict(self, X):
            values = np.zeros(len(X))
            values[0] = 1.0
            values[1] = 1.0 - 0.5e-12
            return values

    result = direct.score_direct_xgboost_test_rows(
        NearTiePredictor(), make_master(), replication_seed=12345
    )
    assert result.scored_rows.loc[0, "score"] == 1.0
    assert result.scored_rows.loc[1, "score"] == 1.0 - 0.5e-12


def test_diagnostics_record_all_scientific_firewalls():
    result = direct.score_direct_xgboost_test_rows(
        RecordingPredictor(), make_master(), replication_seed=12345
    )
    d = result.diagnostics
    assert d["role"] == "parallel_predictive_decision_reference"
    assert d["stagewise_role"] == "parallel_reference_not_sequential_transformation_stage"
    assert d["evaluation_partition"] == "test"
    assert d["already_fitted_predictor_received"] is True
    assert d["predict_calls"] == 1
    assert d["model_fit_executed"] is False
    assert d["target_Y_used_for_scoring"] is False
    assert d["oracle_U_star_used_for_scoring"] is False
    assert d["weight_estimation_executed"] is False
    assert d["shap_executed"] is False
    assert d["mcdm_executed"] is False
    assert d["decision_metrics_computed"] is False
    assert d["results_written"] is False


def test_scoring_function_contains_no_fit_call():
    source = inspect.getsource(direct.score_direct_xgboost_test_rows)
    assert ".fit(" not in source
    assert source.count("predict(X_test)") == 1
