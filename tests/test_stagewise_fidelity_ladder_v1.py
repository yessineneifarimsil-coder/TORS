from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "stagewise_fidelity_ladder_v1.py"
spec = importlib.util.spec_from_file_location(
    "stagewise_fidelity_ladder_v1_test_module", MODULE_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load stagewise_fidelity_ladder_v1.py.")
ladder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ladder
spec.loader.exec_module(ladder)


ORACLE_WEIGHTS = np.array([0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.15, 0.17])
SHAP_WEIGHTS = np.array([0.17, 0.15, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05])


def make_rows(*, include_non_test=False):
    records = []
    alpha = np.asarray([ladder.PRIMARY_ALPHA_BY_FEATURE[f] for f in ladder.FEATURES])
    for offset, context_number in enumerate(range(1001, 1201)):
        context_g = []
        for alternative_number, alternative_id in enumerate(ladder.ALTERNATIVE_IDS, start=1):
            g = np.asarray([
                0.04 * criterion
                + 0.055 * alternative_number
                + 0.00005 * offset * ((criterion % 3) - 1)
                for criterion in range(1, 11)
            ])
            g = np.clip(g, 0.0, 1.0)
            context_g.append(g)
            record = {
                "context_id": f"test_{context_number}",
                "context_number": context_number,
                "replication_seed": 99991,
                "partition": "test",
                "alternative_id": alternative_id,
                "Y": -999.0,
            }
            record.update({feature: value for feature, value in zip(ladder.FEATURES, g, strict=True)})
            records.append(record)
        context_g = np.asarray(context_g)
        q = np.log1p(2.0 * context_g) / np.log(3.0)
        utility = q @ alpha
        start = len(records) - 6
        for index, value in enumerate(utility):
            records[start + index]["U_star"] = float(value)
    if include_non_test:
        for alternative_id in ladder.ALTERNATIVE_IDS:
            record = {
                "context_id": "fit_1",
                "context_number": 1,
                "replication_seed": np.nan,
                "partition": "fit",
                "alternative_id": alternative_id,
                "Y": np.inf,
                "U_star": np.inf,
            }
            for feature in ladder.FEATURES:
                record[feature] = np.inf
            records.append(record)
    return pd.DataFrame.from_records(records)


def make_direct(rows):
    selected = rows.loc[rows["partition"].eq("test")].sort_values(
        ["context_number", "alternative_id"], kind="stable"
    )
    result = selected.loc[:, [
        "context_id", "context_number", "partition", "alternative_id"
    ]].copy()
    result["method"] = "DirectXGBoost"
    g = selected.loc[:, ladder.FEATURES].to_numpy(dtype=float)
    result["score"] = np.sum(g * np.arange(1.0, 11.0)[None, :], axis=1)
    return result.reset_index(drop=True)


def compute(rows=None, oracle=ORACLE_WEIGHTS, shap=SHAP_WEIGHTS, direct=None):
    rows = make_rows() if rows is None else rows
    direct = make_direct(rows) if direct is None else direct
    return ladder.compute_stagewise_fidelity_ladder(
        rows,
        oracle_weights=oracle,
        shap_weights=shap,
        direct_xgboost_scored_rows=direct,
    )


def test_frozen_constants_and_stage_order():
    assert ladder.FEATURES == tuple(f"g_C{i}" for i in range(1, 11))
    assert ladder.ALTERNATIVE_IDS == ("A1", "A2", "A3", "A4", "A5", "A6")
    assert ladder.EXPECTED_TEST_CONTEXTS == 200
    assert ladder.EXPECTED_TEST_ROWS == 1200
    assert ladder.ZETA == 2.0
    assert len(ladder.STAGES) == 9
    assert ladder.STAGES[0] == "OracleUtility"
    assert ladder.STAGES[-1] == "DirectXGBoost"


def test_primary_alpha_is_frozen_and_normalized():
    assert ladder.PRIMARY_ALPHA_BY_FEATURE == {
        "g_C1": 0.11, "g_C2": 0.04, "g_C3": 0.05, "g_C4": 0.07,
        "g_C5": 0.10, "g_C6": 0.14, "g_C7": 0.12, "g_C8": 0.16,
        "g_C9": 0.08, "g_C10": 0.13,
    }
    assert sum(ladder.PRIMARY_ALPHA_BY_FEATURE.values()) == pytest.approx(1.0)


def test_frozen_protocol_validation_passes():
    configs = ladder.validate_frozen_stagewise_protocol()
    assert tuple(configs["protocol"]["stagewise_fidelity"]["stages"]) == ladder.STAGES
    assert configs["protocol"]["stagewise_fidelity"]["claim_additive_error_decomposition"] is False


def test_all_nine_stages_are_defined_when_both_weight_vectors_exist():
    result = compute()
    assert tuple(result.scores_by_stage) == ladder.STAGES
    assert tuple(result.evaluations_by_stage) == ladder.STAGES
    assert result.stage_summary["stage"].tolist() == list(ladder.STAGES)
    assert result.stage_summary["defined"].all()


def test_stages_one_through_six_match_independent_formulas():
    rows = make_rows()
    result = compute(rows=rows)
    selected = rows.sort_values(["context_number", "alternative_id"], kind="stable")
    g = selected.loc[:, ladder.FEATURES].to_numpy(dtype=float)
    q = np.log1p(2.0 * g) / np.log(3.0)
    alpha = np.asarray([ladder.PRIMARY_ALPHA_BY_FEATURE[f] for f in ladder.FEATURES])
    expected = {
        "OracleUtility": selected["U_star"].to_numpy(dtype=float),
        "OracleMainEffectReference": q @ alpha,
        "OracleGlobalAttributionNonlinearQ": q @ ORACLE_WEIGHTS,
        "SHAPGlobalAttributionNonlinearQ": q @ SHAP_WEIGHTS,
        "OracleGlobalAttributionLinearG": g @ ORACLE_WEIGHTS,
        "SHAPGlobalAttributionLinearG": g @ SHAP_WEIGHTS,
    }
    for stage, values in expected.items():
        np.testing.assert_allclose(
            result.scores_by_stage[stage]["score"].to_numpy(), values,
            rtol=0.0, atol=1e-14,
        )


def test_q_transform_reuses_frozen_oracle_implementation():
    values = np.array([[0.0, 0.5, 1.0]])
    observed = ladder._ORACLE_UTILITY.q_transform(values, zeta=2.0)
    expected = np.log1p(2.0 * values) / np.log(3.0)
    np.testing.assert_allclose(observed, expected, rtol=0.0, atol=1e-15)


def test_oracle_moora_stage_reuses_frozen_operator_exactly():
    rows = make_rows()
    result = compute(rows=rows)
    independent = ladder._MOORA.score_test_contexts(
        rows, ORACLE_WEIGHTS, method="MOORA"
    ).scored_rows
    np.testing.assert_allclose(
        result.scores_by_stage["OracleWeightMOORA"]["score"].to_numpy(),
        independent["score"].to_numpy(),
        rtol=0.0, atol=0.0,
    )


def test_shap_moora_stage_reuses_frozen_operator_exactly():
    rows = make_rows()
    result = compute(rows=rows)
    independent = ladder._MOORA.score_test_contexts(
        rows, SHAP_WEIGHTS, method="MOORA"
    ).scored_rows
    np.testing.assert_allclose(
        result.scores_by_stage["SHAPWeightMOORA"]["score"].to_numpy(),
        independent["score"].to_numpy(),
        rtol=0.0, atol=0.0,
    )


def test_direct_xgboost_scores_are_preserved_exactly():
    rows = make_rows()
    direct = make_direct(rows)
    result = compute(rows=rows, direct=direct)
    np.testing.assert_array_equal(
        result.scores_by_stage["DirectXGBoost"]["score"].to_numpy(),
        direct["score"].to_numpy(),
    )


def test_each_defined_stage_uses_frozen_decision_metrics():
    result = compute()
    for stage in ladder.STAGES:
        evaluation = result.evaluations_by_stage[stage]
        assert evaluation.method == stage
        assert evaluation.summary["contexts"] == 200
        assert evaluation.diagnostics["evaluation_partition"] == "test"


def test_oracle_utility_stage_is_the_perfect_reference():
    result = compute()
    summary = result.evaluations_by_stage["OracleUtility"].summary
    assert summary["top1_accuracy"] == 1.0
    assert summary["mean_normalized_oracle_regret"] == 0.0
    assert summary["mean_kendall_tau_b_defined_contexts"] == 1.0


def test_eight_prespecified_paired_contrasts_and_direction():
    result = compute()
    assert result.paired_contrasts["contrast"].tolist() == [
        item[0] for item in ladder.PAIRED_CONTRASTS
    ]
    assert result.paired_contrasts["reference"].tolist() == [
        item[1] for item in ladder.PAIRED_CONTRASTS
    ]
    assert result.paired_contrasts["comparison"].tolist() == [
        item[2] for item in ladder.PAIRED_CONTRASTS
    ]
    assert result.paired_contrasts["direction"].eq("comparison_minus_reference").all()
    assert result.paired_contrasts["defined"].all()


def test_contrast_values_are_comparison_minus_reference():
    result = compute()
    first = result.paired_contrasts.iloc[0]
    reference = result.evaluations_by_stage[first["reference"]].summary
    comparison = result.evaluations_by_stage[first["comparison"]].summary
    assert first["delta_top1_accuracy"] == pytest.approx(
        comparison["top1_accuracy"] - reference["top1_accuracy"]
    )
    assert first["delta_mean_normalized_oracle_regret"] == pytest.approx(
        comparison["mean_normalized_oracle_regret"]
        - reference["mean_normalized_oracle_regret"]
    )


def test_undefined_oracle_weights_propagate_only_to_oracle_weight_stages():
    result = compute(oracle=None)
    missing = {
        "OracleGlobalAttributionNonlinearQ",
        "OracleGlobalAttributionLinearG",
        "OracleWeightMOORA",
    }
    assert set(ladder.STAGES) - set(result.scores_by_stage) == missing
    undefined = result.stage_summary.loc[~result.stage_summary["defined"]]
    assert set(undefined["stage"]) == missing
    assert undefined["undefined_reason"].eq("oracle_attribution_weights_undefined").all()


def test_undefined_shap_weights_propagate_only_to_shap_weight_stages():
    result = compute(shap=None)
    missing = {
        "SHAPGlobalAttributionNonlinearQ",
        "SHAPGlobalAttributionLinearG",
        "SHAPWeightMOORA",
    }
    assert set(ladder.STAGES) - set(result.scores_by_stage) == missing
    undefined = result.stage_summary.loc[~result.stage_summary["defined"]]
    assert set(undefined["stage"]) == missing
    assert undefined["undefined_reason"].eq("shap_attribution_weights_undefined").all()


def test_both_undefined_weight_vectors_leave_three_independent_stages():
    result = compute(oracle=None, shap=None)
    assert tuple(result.scores_by_stage) == (
        "OracleUtility", "OracleMainEffectReference", "DirectXGBoost"
    )
    assert result.diagnostics["defined_stage_count"] == 3
    assert result.diagnostics["undefined_stage_count"] == 6
    assert result.diagnostics["mcdm_scoring_executed"] is False


def test_contrasts_record_undefined_without_substitution():
    result = compute(oracle=None)
    undefined = result.paired_contrasts.loc[~result.paired_contrasts["defined"]]
    assert not undefined.empty
    assert undefined["undefined_reason"].eq("one_or_both_representations_undefined").all()
    assert undefined["delta_mean_normalized_oracle_regret"].isna().all()


@pytest.mark.parametrize("bad", [
    np.ones(10),
    np.array([0.2] + [-0.01] + [0.10125] * 8),
    np.array([0.1] * 9 + [np.nan]),
])
def test_invalid_alpha_fails_closed(bad):
    rows = make_rows()
    with pytest.raises(ValueError):
        ladder.compute_stagewise_fidelity_ladder(
            rows,
            oracle_weights=ORACLE_WEIGHTS,
            shap_weights=SHAP_WEIGHTS,
            direct_xgboost_scored_rows=make_direct(rows),
            alpha_by_feature=bad,
        )


@pytest.mark.parametrize("which", ["oracle", "shap"])
def test_invalid_attribution_weights_fail_closed(which):
    bad = np.array([0.1] * 10)
    bad[0] = -0.1
    rows = make_rows()
    kwargs = {"oracle": ORACLE_WEIGHTS, "shap": SHAP_WEIGHTS}
    kwargs[which] = bad
    with pytest.raises(ValueError, match="nonnegative"):
        compute(rows=rows, **kwargs)


@pytest.mark.parametrize("missing", [
    "context_id", "context_number", "partition", "alternative_id",
    "U_star", "g_C1", "g_C5", "g_C10",
])
def test_missing_test_columns_fail_closed(missing):
    rows = make_rows().drop(columns=[missing])
    with pytest.raises(ValueError, match="missing columns"):
        compute(rows=rows, direct=make_direct(make_rows()))


def test_wrong_test_row_count_fails_closed():
    rows = make_rows().iloc[:-1].copy()
    with pytest.raises(ValueError, match="requires 1200 TEST rows"):
        compute(rows=rows, direct=make_direct(make_rows()))


def test_duplicate_test_identity_fails_closed():
    rows = make_rows()
    rows.iloc[-1] = rows.iloc[0]
    with pytest.raises(ValueError, match="Duplicate TEST"):
        compute(rows=rows, direct=make_direct(make_rows()))


def test_malformed_alternative_block_fails_closed():
    rows = make_rows()
    rows.loc[0, "alternative_id"] = "A7"
    with pytest.raises(ValueError, match="A1..A6"):
        compute(rows=rows, direct=make_direct(make_rows()))


def test_context_number_cannot_map_to_multiple_ids():
    rows = make_rows()
    rows.loc[0, "context_id"] = "different"
    with pytest.raises(ValueError, match="multiple context IDs"):
        compute(rows=rows, direct=make_direct(make_rows()))


@pytest.mark.parametrize("column,value,match", [
    ("g_C4", np.inf, "G contains non-finite"),
    ("g_C4", 1.1, "G must lie"),
    ("U_star", np.nan, "U_star contains non-finite"),
    ("U_star", -0.1, "U_star must lie"),
])
def test_invalid_scientific_test_values_fail_closed(column, value, match):
    rows = make_rows()
    rows.loc[0, column] = value
    with pytest.raises(ValueError, match=match):
        compute(rows=rows, direct=make_direct(make_rows()))


def test_non_test_rows_cannot_change_ladder():
    base = make_rows()
    expanded = make_rows(include_non_test=True)
    first = compute(rows=base)
    second = compute(rows=expanded, direct=make_direct(expanded))
    for stage in ladder.STAGES:
        pd.testing.assert_frame_equal(first.scores_by_stage[stage], second.scores_by_stage[stage])


def test_target_Y_is_never_used():
    rows = make_rows()
    changed = rows.copy()
    changed["Y"] = np.linspace(-1e100, 1e100, len(changed))
    first = compute(rows=rows)
    second = compute(rows=changed)
    for stage in ladder.STAGES:
        pd.testing.assert_frame_equal(first.scores_by_stage[stage], second.scores_by_stage[stage])


def test_inputs_are_not_mutated():
    rows = make_rows().sample(frac=1.0, random_state=18).reset_index(drop=True)
    direct = make_direct(rows).sample(frac=1.0, random_state=19).reset_index(drop=True)
    rows_before = rows.copy(deep=True)
    direct_before = direct.copy(deep=True)
    compute(rows=rows, direct=direct)
    pd.testing.assert_frame_equal(rows, rows_before)
    pd.testing.assert_frame_equal(direct, direct_before)


def test_direct_identity_mismatch_fails_closed():
    rows = make_rows()
    direct = make_direct(rows)
    direct.loc[0, "context_id"] = "wrong"
    with pytest.raises(ValueError, match="identities differ"):
        compute(rows=rows, direct=direct)


def test_direct_method_label_mismatch_fails_closed():
    rows = make_rows()
    direct = make_direct(rows)
    direct.loc[0, "method"] = "Other"
    with pytest.raises(ValueError, match="method labels"):
        compute(rows=rows, direct=direct)


def test_nonfinite_direct_score_fails_closed():
    rows = make_rows()
    direct = make_direct(rows)
    direct.loc[0, "score"] = np.inf
    with pytest.raises(ValueError, match="scores contain non-finite"):
        compute(rows=rows, direct=direct)


def test_raw_direct_near_ties_are_delegated_to_common_metrics():
    rows = make_rows()
    direct = make_direct(rows)
    direct.loc[:5, "score"] = [1.0, 1.0 - 0.5e-12, 0.8, 0.7, 0.6, 0.5]
    result = compute(rows=rows, direct=direct)
    first_context = result.scores_by_stage["DirectXGBoost"].iloc[:6]
    ranking = ladder._METRICS.rank_scores_anchor_ties(
        first_context["score"].to_numpy(), first_context["alternative_id"].tolist()
    )
    assert ranking.top_tie_set == ("A1", "A2")
    assert ranking.selected_top1 == "A1"


def test_diagnostics_state_nonadditive_parallel_reference_and_firewalls():
    d = compute().diagnostics
    assert d["claim_additive_error_decomposition"] is False
    assert d["interpretation"] == "prespecified_paired_contrasts_not_causal_decomposition"
    assert d["direct_xgboost_role"] == "parallel_reference_not_sequential_transformation_stage"
    assert d["evaluation_partition"] == "test"
    assert d["model_fit_executed"] is False
    assert d["weight_estimation_executed"] is False
    assert d["shap_estimation_executed"] is False
    assert d["direct_xgboost_prediction_executed"] is False
    assert d["target_Y_used"] is False
    assert d["mcdm_scoring_executed"] is True
    assert d["decision_metrics_computed"] is True
    assert d["bootstrap_executed"] is False
    assert d["results_written"] is False


def test_source_reuses_frozen_modules_and_contains_no_model_fit():
    source = inspect.getsource(ladder.compute_stagewise_fidelity_ladder)
    assert "_ORACLE_UTILITY.q_transform" in source
    assert source.count("_MOORA.score_test_contexts") == 2
    assert "_METRICS.evaluate_decision_fidelity_batch" in source
    assert ".fit(" not in source
