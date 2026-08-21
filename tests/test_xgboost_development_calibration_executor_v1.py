from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_PATH = ROOT / "src" / "xgboost_development_calibration_executor_v1.py"


def load_executor():
    spec = importlib.util.spec_from_file_location("xgbcal_executor_test", EXECUTOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ex():
    return load_executor()


def test_executor_protocol_contract_is_frozen_and_uncalibrated(ex):
    configs = ex.load_configs()
    ex.validate_frozen_protocol(configs)
    assert configs["xgboost"]["frozen_parameters"]["calibrated"] is False
    assert configs["protocol"]["development_data"]["pooled_fit_contexts"] == 1000
    assert configs["protocol"]["development_data"]["pooled_fit_rows"] == 6000


def test_candidate_sampling_is_deterministic_unique_and_exactly_sixty(ex):
    configs = ex.load_configs()
    first = ex.deterministic_candidates(configs)
    second = ex.deterministic_candidates(configs)
    assert first == second
    assert len(first) == 60
    keys = [ex.canonical_parameter_tuple(item) for item in first]
    assert len(set(keys)) == 60


def test_deterministic_tie_break_uses_frozen_parameter_order(ex):
    p1 = {
        "n_estimators": 400,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "min_child_weight": 1,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
    }
    p2 = dict(p1)
    p2["n_estimators"] = 200
    frame = pd.DataFrame(
        [
            {"candidate_id": 1, "params": p1, "mean_cv_rmse": 0.123456789},
            {"candidate_id": 2, "params": p2, "mean_cv_rmse": 0.123456789 + 5e-13},
        ]
    )
    assert ex.select_candidate_from_results(frame) == 2


def test_one_seed_reconstruction_uses_d29_and_only_reference_fit_contexts(ex):
    configs = ex.load_configs()
    modules = ex.load_pipeline_modules()
    frame, audit = ex.build_seed_calibration_data(21001, configs, modules)

    assert audit["production_generator"] == "d29_kernel"
    assert audit["master_contexts"] == 1200
    assert audit["master_rows"] == 7200
    assert audit["estimation_rows"] == 6000
    assert audit["external_test_rows_generated"] == 1200
    assert audit["fit_contexts_used"] == 200
    assert audit["fit_rows_used"] == 1200
    assert audit["weight_rows_used_for_selection"] == 0
    assert audit["external_test_rows_used_for_selection"] == 0
    assert audit["external_test_used_for_signal_sd"] is False
    assert audit["signal_sd"] > 0.0

    assert len(frame) == 1200
    assert frame["context_id"].nunique() == 200
    assert frame["cv_group"].nunique() == 200
    assert set(frame["partition"]) == {"fit"}
    assert frame["context_number"].max() <= 250
    assert np.isfinite(frame[ex.FEATURES + ["Y"]].to_numpy(dtype=float)).all()


def test_executor_source_has_no_shap_or_mcdm_imports_and_does_not_write_xgboost_config(ex):
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")

    assert not any(name == "shap" or name.startswith("shap.") for name in imported)
    assert not any("moora" in name.lower() or "topsis" in name.lower() for name in imported)

    # Calibration results are written under results/. The executor must not
    # write selected hyperparameters back into config/xgboost.yaml.
    assert "XGBOOST_CONFIG_PATH.write_text" not in source
    assert "XGBOOST_CONFIG_PATH.write_bytes" not in source


def test_output_directory_is_one_shot_and_separate_from_protocol_config(ex):
    assert ex.OUTPUT_DIR == ROOT / "results" / "xgboost_development_calibration_v1"
    assert ex.TEMP_DIR == ROOT / "results" / ".xgboost_development_calibration_v1_tmp"
    assert ex.OUTPUT_DIR != ex.PROTOCOL_PATH.parent
