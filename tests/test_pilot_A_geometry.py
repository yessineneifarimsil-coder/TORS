from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "05_run_pilot_A.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pilot = load_module("pilot_A_test_module", MODULE_PATH)


def toy_experiment() -> dict:
    return {
        "development": {
            "pilot_A": {
                "model_independent": True,
                "reference_scope": {
                    "N": 250,
                    "c": 0.30,
                    "rho": 0.4,
                    "lambda": 0.5,
                    "development_seeds": 5,
                    "contexts_per_seed": 250,
                    "pooled_contexts": 1250,
                    "use_estimation_contexts_only": True,
                    "use_external_test": False,
                },
                "oracle_winner": {
                    "score": "U_star",
                    "rule": "maximum_within_context",
                    "tie_break": "alternative_id_ascending",
                    "record_tie_rate": True,
                },
                "decision_margin": {
                    "primary": "top1_U_star_minus_top2_U_star",
                    "secondary_normalized": (
                        "primary_divided_by_within_context_U_star_range_plus_epsilon"
                    ),
                    "epsilon": 1.0e-12,
                },
                "signal_sd": {
                    "source": "complete_1000_context_estimation_master_pool",
                    "exclude_external_test": True,
                },
                "realized_snr": {
                    "evaluation_scope": "reference_N250_estimation_contexts_only"
                },
                "structural_pareto": {
                    "input": "direction_adjusted_g",
                    "unit": "context",
                    "ordered_alternative_pairs": True,
                },
                "diagnostics": {},
                "warning_flags": {
                    "modal_winner_share_above": 0.60,
                    "fewer_than_distinct_oracle_winners": 3,
                    "evaluation_scope": (
                        "pooled_five_development_seeds_reference_contexts"
                    ),
                },
                "warning_flags_are_automatic_rejection_rules": False,
            }
        }
    }


def toy_seeds() -> dict:
    return {"development": [21001, 21002, 21003, 21004, 21005]}


def make_reference_frame(n_contexts: int = 250, include_test: bool = True) -> pd.DataFrame:
    rows = []
    end = n_contexts + (2 if include_test else 0)
    for context_number in range(1, end + 1):
        if context_number <= n_contexts:
            partition = "weight" if context_number % 5 == 0 else "fit"
        else:
            partition = "test"
        for alt in range(1, 7):
            row = {
                "context_id": f"C{context_number:04d}",
                "context_number": context_number,
                "alternative_id": f"A{alt}",
                "partition": partition,
                "U_star": 0.1 * alt + 0.0001 * context_number,
                "target_noise": 0.01 * (alt - 3),
                "target_noise_e": 0.1 * (alt - 3),
                "imposed_noise_sd": 0.02,
            }
            for j in range(1, 11):
                row[f"g_C{j}"] = min(1.0, 0.05 * alt + 0.001 * j)
            rows.append(row)
    return pd.DataFrame(rows)


def make_small_decision_frame() -> pd.DataFrame:
    rows = []
    utilities = {
        "C1": [0.90, 0.80, 0.70, 0.60, 0.50, 0.40],
        "C2": [0.50, 0.50, 0.40, 0.30, 0.20, 0.10],
    }
    for context_id, values in utilities.items():
        for alt, value in enumerate(values, start=1):
            rows.append(
                {
                    "context_id": context_id,
                    "alternative_id": f"A{alt}",
                    "U_star": value,
                }
            )
    return pd.DataFrame(rows)


def test_current_config_matches_frozen_pilot_A_protocol() -> None:
    experiment = yaml.safe_load(
        (ROOT / "config" / "experiment.yaml").read_text(encoding="utf-8")
    )
    seeds = yaml.safe_load(
        (ROOT / "config" / "seeds.yaml").read_text(encoding="utf-8")
    )
    config = pilot.frozen_pilot_A_config(experiment, seeds)

    assert config["N"] == 250
    assert config["c"] == pytest.approx(0.30)
    assert config["rho"] == pytest.approx(0.4)
    assert config["lambda"] == pytest.approx(0.5)
    assert config["pooled_contexts"] == 1250
    assert config["development_seeds"] == (21001, 21002, 21003, 21004, 21005)


def test_reference_scope_uses_first_250_estimation_contexts_and_excludes_test() -> None:
    frame = make_reference_frame()
    selected = pilot.select_reference_scope(frame, n_contexts=250)

    assert selected["context_id"].nunique() == 250
    assert len(selected) == 1500
    assert not selected["partition"].eq("test").any()
    assert selected["context_number"].max() == 250


def test_reference_scope_rejects_missing_alternative() -> None:
    frame = make_reference_frame()
    frame = frame.loc[
        ~(
            frame["context_id"].eq("C0001")
            & frame["alternative_id"].eq("A6")
        )
    ]
    with pytest.raises(ValueError, match="1500 alternative-context rows"):
        pilot.select_reference_scope(frame, n_contexts=250)


def test_context_decision_margin_is_top1_minus_top2() -> None:
    decisions = pilot.context_decisions(
        make_small_decision_frame(),
        epsilon=1.0e-12,
    )
    c1 = decisions.loc[decisions["context_id"].eq("C1")].iloc[0]

    assert c1["winner"] == "A1"
    assert c1["decision_margin"] == pytest.approx(0.10)
    assert c1["within_context_U_star_range"] == pytest.approx(0.50)
    assert c1["normalized_decision_margin"] == pytest.approx(
        0.10 / (0.50 + 1.0e-12)
    )


def test_exact_top_tie_uses_ascending_alternative_id() -> None:
    decisions = pilot.context_decisions(
        make_small_decision_frame(),
        epsilon=1.0e-12,
    )
    c2 = decisions.loc[decisions["context_id"].eq("C2")].iloc[0]

    assert c2["winner"] == "A1"
    assert bool(c2["top_tie"]) is True
    assert c2["top_tie_count"] == 2
    assert c2["decision_margin"] == pytest.approx(0.0)


def test_normalized_winner_entropy_uniform_over_six_is_one() -> None:
    winners = ["A1", "A2", "A3", "A4", "A5", "A6"] * 10
    assert pilot.normalized_winner_entropy(winners) == pytest.approx(1.0)


def test_normalized_winner_entropy_single_winner_is_zero() -> None:
    assert pilot.normalized_winner_entropy(["A3"] * 20) == pytest.approx(0.0)


def test_winner_summary_uses_deterministic_modal_tie_break() -> None:
    decisions = pd.DataFrame(
        {
            "winner": ["A2", "A1", "A2", "A1"],
            "top_tie": [False, False, False, False],
        }
    )
    summary = pilot.winner_summary(decisions, seed_label="toy")
    assert summary["distinct_winners"] == 2
    assert summary["modal_winner"] == "A1"
    assert summary["modal_winner_share"] == pytest.approx(0.5)


def test_pareto_dominance_is_ordered_and_context_specific() -> None:
    rows = []
    for context_id in ["C1", "C2"]:
        for alt in range(1, 7):
            row = {
                "context_id": context_id,
                "alternative_id": f"A{alt}",
            }
            for j in range(1, 11):
                row[f"g_C{j}"] = float(7 - alt) / 6.0
            rows.append(row)
    frame = pd.DataFrame(rows)

    result = pilot.pareto_dominance(frame, seed_label="toy")
    a1_a2 = result.loc[
        result["dominant_alternative"].eq("A1")
        & result["dominated_alternative"].eq("A2")
    ].iloc[0]
    a2_a1 = result.loc[
        result["dominant_alternative"].eq("A2")
        & result["dominated_alternative"].eq("A1")
    ].iloc[0]

    assert len(result) == 30
    assert a1_a2["dominance_rate"] == pytest.approx(1.0)
    assert a2_a1["dominance_rate"] == pytest.approx(0.0)


def test_criterion_geometry_reports_exact_boundary_rates() -> None:
    frame = make_reference_frame(include_test=False)
    frame.loc[frame.index[0], "g_C1"] = 0.0
    frame.loc[frame.index[1], "g_C1"] = 1.0

    summary = pilot.criterion_geometry(frame, seed_label="toy")
    c1 = summary.loc[summary["criterion"].eq("C1")].iloc[0]

    assert c1["rows"] == 1500
    assert c1["exact_zero_rate"] == pytest.approx(1.0 / 1500.0)
    assert c1["exact_one_rate"] == pytest.approx(1.0 / 1500.0)


def test_reference_noise_summary_excludes_test_and_uses_reference_variances() -> None:
    frame = make_reference_frame(include_test=False)
    summary = pilot.reference_noise_summary(
        frame,
        full_master_signal_sd=0.25,
        seed_label="toy",
    )

    expected_signal = frame["U_star"].to_numpy().std(ddof=0)
    expected_noise = frame["target_noise"].to_numpy().std(ddof=0)
    assert summary["signal_sd_master_N1000"] == pytest.approx(0.25)
    assert summary["signal_sd_reference_N250"] == pytest.approx(expected_signal)
    assert summary["realized_noise_sd_reference_N250"] == pytest.approx(expected_noise)
    assert summary["realized_snr_variance_reference_N250"] == pytest.approx(
        expected_signal**2 / expected_noise**2
    )


def test_reference_noise_summary_rejects_test_rows() -> None:
    frame = make_reference_frame(include_test=True)
    with pytest.raises(AssertionError, match="External TEST leaked"):
        pilot.reference_noise_summary(
            frame,
            full_master_signal_sd=0.25,
            seed_label="toy",
        )


def test_warning_flags_use_strict_frozen_inequalities() -> None:
    warnings = pilot.pooled_warning_flags(
        {"modal_winner_share": 0.61, "distinct_winners": 2},
        modal_warning=0.60,
        distinct_warning=3,
    )
    assert warnings == {
        "modal_winner_share_warning": True,
        "fewer_than_distinct_winners_warning": True,
    }

    boundary = pilot.pooled_warning_flags(
        {"modal_winner_share": 0.60, "distinct_winners": 3},
        modal_warning=0.60,
        distinct_warning=3,
    )
    assert boundary == {
        "modal_winner_share_warning": False,
        "fewer_than_distinct_winners_warning": False,
    }


def test_seed_prefix_makes_context_identity_unique_across_replications() -> None:
    frame = make_reference_frame(n_contexts=1, include_test=False)
    first = pilot._prefix_seed_context(frame, 21001)
    second = pilot._prefix_seed_context(frame, 21002)

    assert set(first["context_id"]).isdisjoint(set(second["context_id"]))
    assert (first["replication_seed"] == 21001).all()
    assert (second["replication_seed"] == 21002).all()


def test_pilot_module_declares_no_model_or_mcdm_dependency() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "import xgboost" not in source
    assert "import shap" not in source
    assert "moora(" not in source
    assert "topsis(" not in source
    assert "oracle shapley" in source
    assert "not use" in source or "not used" in source
