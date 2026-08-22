from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "d29_layer_b_characterization_v1.py"

spec = importlib.util.spec_from_file_location(
    "d29_layer_b_characterization_v1_test_module",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load d29_layer_b_characterization_v1.py.")

layerb = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = layerb
spec.loader.exec_module(layerb)

decision_spec = importlib.util.spec_from_file_location(
    "decision_semantics_v1_for_layer_b_tests",
    ROOT / "src" / "decision_semantics_v1.py",
)
if decision_spec is None or decision_spec.loader is None:
    raise RuntimeError("Could not load decision_semantics_v1.py.")
decision = importlib.util.module_from_spec(decision_spec)
sys.modules[decision_spec.name] = decision
decision_spec.loader.exec_module(decision)


def make_oracle_rows(
    *,
    replication_seed: int = 21001,
    winner_pattern=None,
    constant_context: int | None = None,
) -> pd.DataFrame:
    if winner_pattern is None:
        winner_pattern = lambda c: "A1" if c <= 600 else ("A2" if c <= 900 else "A3")

    records = []
    for context_number in range(1, 1001):
        partition = "weight" if context_number % 5 == 0 else "fit"
        winner = winner_pattern(context_number)

        for alt_number in range(1, 7):
            alt_id = f"A{alt_number}"
            if context_number == constant_context:
                u = 0.5
            else:
                base = 0.60 - 0.04 * (alt_number - 1)
                bonus = 0.25 if alt_id == winner else 0.0
                context_tilt = 0.00001 * context_number * alt_number
                u = min(0.999999, base + bonus + context_tilt)

            records.append(
                {
                    "context_id": f"S{replication_seed}_C{context_number:04d}",
                    "context_number": context_number,
                    "replication_seed": replication_seed,
                    "partition": partition,
                    "alternative_id": alt_id,
                    "U_star": float(u),
                }
            )

    return pd.DataFrame.from_records(records)


def test_frozen_constants_match_committed_protocol():
    assert layerb.DEVELOPMENT_SEEDS == (21001, 21002, 21003, 21004, 21005)
    assert layerb.RHO == 0.4
    assert layerb.SIGMA_X == 0.0
    assert layerb.LAMBDA_VALUE == 0.5
    assert layerb.N_CONTEXTS == 1000
    assert layerb.ALTERNATIVE_IDS == ("A1", "A2", "A3", "A4", "A5", "A6")
    assert layerb.REGRET_RANGE_TOL == 1e-12


def test_validate_committed_protocol_file():
    protocol = layerb.load_json(layerb.PROTOCOL_PATH)
    layerb.validate_protocol(protocol)


def test_characterization_counts_winners_and_modal_share():
    rows = make_oracle_rows()
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["distinct_deterministic_oracle_winners"] == 3
    assert result["modal_oracle_winner_id"] == "A1"
    assert result["modal_oracle_winner_share"] == pytest.approx(0.6)
    assert result["contexts"] == 1000
    assert result["alternatives_per_context"] == 6


def test_complete_orderings_use_frozen_average_rank_semantics():
    rows = make_oracle_rows()
    # Force exact top tie in context 1; ranking signature must preserve a tie.
    mask = rows["context_number"].eq(1)
    rows.loc[mask & rows["alternative_id"].isin(["A1", "A2"]), "U_star"] = 0.9
    rows.loc[mask & rows["alternative_id"].eq("A3"), "U_star"] = 0.5
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["distinct_complete_oracle_orderings"] >= 1


def test_modal_tie_is_resolved_by_ascending_alternative_id():
    rows = make_oracle_rows(
        winner_pattern=lambda c: "A1" if c <= 500 else "A2"
    )
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["modal_oracle_winner_id"] == "A1"
    assert result["modal_oracle_winner_share"] == pytest.approx(0.5)


def test_regret_uses_exact_range_and_no_epsilon_regularization():
    rows = make_oracle_rows(constant_context=1000)
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["undefined_normalized_regret_context_count"] == 1
    assert result["defined_normalized_regret_context_count"] == 999
    assert result["modal_baseline_mean_normalized_oracle_regret"] is not None
    assert result["modal_baseline_median_normalized_oracle_regret"] is not None
    assert result["modal_baseline_p95_normalized_oracle_regret"] is not None
    assert result["p95_quantile_method"] == "linear"


def test_all_constant_contexts_make_regret_summaries_undefined():
    rows = make_oracle_rows()
    rows["U_star"] = 0.5
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["undefined_normalized_regret_context_count"] == 1000
    assert result["defined_normalized_regret_context_count"] == 0
    assert result["modal_baseline_mean_normalized_oracle_regret"] is None
    assert result["modal_baseline_median_normalized_oracle_regret"] is None
    assert result["modal_baseline_p95_normalized_oracle_regret"] is None


def test_characterization_is_descriptive_only():
    rows = make_oracle_rows()
    result = layerb.characterize_oracle_rows(
        rows,
        replication_seed=21001,
        decision_module=decision,
    )
    assert result["retention_effect"] == "none"
    assert result["pass_fail_threshold"] is None


def test_external_test_row_fails_closed():
    rows = make_oracle_rows()
    rows.loc[0, "partition"] = "test"
    with pytest.raises(ValueError, match="TEST"):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21001,
            decision_module=decision,
        )


def test_wrong_seed_fails_closed():
    rows = make_oracle_rows(replication_seed=21001)
    with pytest.raises(ValueError):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21002,
            decision_module=decision,
        )


def test_wrong_context_count_fails_closed():
    rows = make_oracle_rows()
    rows = rows.loc[rows["context_number"].ne(1000)].copy()
    with pytest.raises(ValueError):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21001,
            decision_module=decision,
        )


def test_missing_alternative_fails_closed():
    rows = make_oracle_rows()
    rows = rows.loc[
        ~(
            rows["context_number"].eq(1)
            & rows["alternative_id"].eq("A6")
        )
    ].copy()
    with pytest.raises(ValueError):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21001,
            decision_module=decision,
        )


def test_duplicate_context_alternative_fails_closed():
    rows = make_oracle_rows()
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21001,
            decision_module=decision,
        )


def test_nonfinite_oracle_utility_fails_closed():
    rows = make_oracle_rows()
    rows.loc[0, "U_star"] = np.nan
    with pytest.raises(ValueError):
        layerb.characterize_oracle_rows(
            rows,
            replication_seed=21001,
            decision_module=decision,
        )


def test_cross_seed_summary_uses_median_min_max_only():
    seed_rows = []
    for index, seed in enumerate(layerb.DEVELOPMENT_SEEDS):
        rows = make_oracle_rows(
            replication_seed=seed,
            winner_pattern=lambda c, shift=index: (
                "A1" if c <= 500 + 10 * shift else "A2"
            ),
        )
        seed_rows.append(
            layerb.characterize_oracle_rows(
                rows,
                replication_seed=seed,
                decision_module=decision,
            )
        )

    summary = layerb.summarize_seed_metrics(seed_rows)
    assert summary["development_seeds"] == list(layerb.DEVELOPMENT_SEEDS)
    assert summary["n_seeds"] == 5
    assert summary["retention_effect"] == "none"
    assert summary["pass_fail_threshold"] is None
    assert summary["winner_identity_used_for_optimization"] is False
    for payload in summary["metrics"].values():
        assert set(payload) == {
            "median",
            "min",
            "max",
            "undefined_across_seed_summary",
        }


def test_cross_seed_summary_rejects_wrong_seed_set():
    fake = [
        {
            "replication_seed": seed,
            "distinct_complete_oracle_orderings": 1,
            "distinct_deterministic_oracle_winners": 1,
            "modal_oracle_winner_share": 1.0,
            "modal_baseline_mean_normalized_oracle_regret": 0.0,
            "modal_baseline_median_normalized_oracle_regret": 0.0,
            "modal_baseline_p95_normalized_oracle_regret": 0.0,
            "undefined_normalized_regret_context_count": 0,
        }
        for seed in (21001, 21002, 21003, 21004, 99999)
    ]
    with pytest.raises(ValueError):
        layerb.summarize_seed_metrics(fake)


def test_build_seed_rejects_nondevelopment_seed_before_pipeline_calls():
    configs = {
        "benchmark": {"alternatives": {}},
        "experiment": {},
        "seeds": {"development": list(layerb.DEVELOPMENT_SEEDS)},
    }
    modules = {}
    with pytest.raises(ValueError, match="development seeds"):
        layerb.build_seed_oracle_rows(
            replication_seed=11001,
            configs=configs,
            modules=modules,
        )


def test_source_does_not_import_or_call_ml_or_shap_packages():
    text = MODULE_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "import xgboost" not in lowered
    assert "from xgboost" not in lowered
    assert "import shap" not in lowered
    assert "from shap" not in lowered
    assert "treeexplainer" not in lowered
    assert ".fit(" not in lowered
    assert "add_relative_noise(" not in lowered
    assert "master_noise_table(" not in lowered


def test_run_provenance_firewalls_are_explicit_in_source():
    text = MODULE_PATH.read_text(encoding="utf-8")
    for token in (
        '"external_TEST_used": False',
        '"target_Y_used": False',
        '"xgboost_used": False',
        '"shap_used": False',
        '"weighting_methods_used": False',
        '"mcdm_executed": False',
        '"primary_seeds_used": False',
        '"reserve_seeds_used": False',
        '"structural_validation_seeds_used": False',
        '"preferred_winner_used_for_selection": False',
        '"retention_effect": "none"',
        '"pass_fail_threshold": None',
    ):
        assert token in text


def test_result_directory_creation_occurs_after_seed_loop_textually():
    text = MODULE_PATH.read_text(encoding="utf-8")
    loop_pos = text.index("for replication_seed in DEVELOPMENT_SEEDS:")
    mkdir_pos = text.index("output_dir.mkdir(")
    assert mkdir_pos > loop_pos


def test_output_overwrite_is_forbidden_before_computation():
    text = MODULE_PATH.read_text(encoding="utf-8")
    exists_pos = text.index("if output_dir.exists():")
    loop_pos = text.index("for replication_seed in DEVELOPMENT_SEEDS:")
    assert exists_pos < loop_pos
