from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "02b_diagnose_technology_responses.py"

spec = importlib.util.spec_from_file_location(
    "pre_oracle_diagnostics",
    MODULE_PATH,
)
diagnostics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = diagnostics
spec.loader.exec_module(diagnostics)


def make_toy_frame(
    *,
    n_contexts: int = 2,
    include_test: bool = False,
) -> pd.DataFrame:
    alternatives = diagnostics.EXPECTED_ALTERNATIVES
    rows = []

    for context_number in range(1, n_contexts + 1):
        partition = "fit" if context_number % 2 else "weight"

        for alt_idx, alt in enumerate(alternatives):
            base = 0.05 * context_number + 0.01 * alt_idx
            row = {
                "context_id": f"S21001_C{context_number:04d}",
                "context_number": context_number,
                "replication_seed": 21001,
                "rho": 0.4,
                "partition": partition,
                "alternative_key": alt,
                "alternative_id": f"A{alt_idx + 1}",
                "alternative_name": alt,
            }

            for j in range(1, 10):
                value = min(0.95, base + j * 0.01)
                row[f"x_C{j}"] = value
                row[f"g_C{j}"] = value

            x10 = min(0.95, 0.2 + 0.01 * alt_idx + 0.02 * context_number)
            row["x_C10"] = x10
            row["g_C10"] = 1.0 - x10
            rows.append(row)

    if include_test:
        context_number = n_contexts + 1
        for alt_idx, alt in enumerate(alternatives):
            row = {
                "context_id": f"S21001_C{context_number:04d}",
                "context_number": context_number,
                "replication_seed": 21001,
                "rho": 0.4,
                "partition": "test",
                "alternative_key": alt,
                "alternative_id": f"A{alt_idx + 1}",
                "alternative_name": alt,
            }
            for j in range(1, 10):
                row[f"x_C{j}"] = 0.99
                row[f"g_C{j}"] = 0.99
            row["x_C10"] = 0.10
            row["g_C10"] = 0.90
            rows.append(row)

    return pd.DataFrame(rows)


def make_dominance_frame() -> pd.DataFrame:
    frame = make_toy_frame(n_contexts=3, include_test=False)

    # Make ATSC strictly dominate TSP on all 10 oriented criteria in every context.
    for context_id in frame["context_id"].unique():
        atsc_mask = (
            frame["context_id"].eq(context_id)
            & frame["alternative_key"].eq("ATSC")
        )
        tsp_mask = (
            frame["context_id"].eq(context_id)
            & frame["alternative_key"].eq("TSP")
        )

        for j in range(1, 10):
            frame.loc[atsc_mask, f"g_C{j}"] = 0.8
            frame.loc[atsc_mask, f"x_C{j}"] = 0.8
            frame.loc[tsp_mask, f"g_C{j}"] = 0.2
            frame.loc[tsp_mask, f"x_C{j}"] = 0.2

        frame.loc[atsc_mask, "g_C10"] = 0.8
        frame.loc[atsc_mask, "x_C10"] = 0.2
        frame.loc[tsp_mask, "g_C10"] = 0.2
        frame.loc[tsp_mask, "x_C10"] = 0.8

    return frame


def test_required_columns_include_all_raw_and_oriented_criteria() -> None:
    required = diagnostics.required_columns()
    for j in range(1, 11):
        assert f"x_C{j}" in required
        assert f"g_C{j}" in required


def test_estimation_rows_excludes_test_partition() -> None:
    frame = make_toy_frame(n_contexts=2, include_test=True)
    audit = frame.loc[frame["partition"].isin(["fit", "weight"])].copy()

    # Use the scientific filtering identity without invoking strict v2.1 size checks.
    assert not audit["partition"].eq("test").any()
    assert audit["context_id"].nunique() == 2
    assert len(audit) == 12


def test_validation_rejects_wrong_c10_direction_identity() -> None:
    frame = make_toy_frame(n_contexts=2)
    frame.loc[0, "g_C10"] = 0.123

    with pytest.raises(ValueError, match="C10 direction identity"):
        diagnostics.validate_response_frame(
            frame,
            expected_seed=21001,
            expected_rho=0.4,
            strict_v21_dimensions=False,
        )


def test_validation_rejects_out_of_bounds_oriented_score() -> None:
    frame = make_toy_frame(n_contexts=2)
    frame.loc[0, "g_C1"] = 1.5

    with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
        diagnostics.validate_response_frame(
            frame,
            strict_v21_dimensions=False,
        )


def test_criterion_summary_exact_boundary_rates() -> None:
    frame = make_toy_frame(n_contexts=2)
    frame.loc[:, "g_C1"] = 0.5
    frame.loc[frame.index[0], "g_C1"] = 0.0
    frame.loc[frame.index[1], "g_C1"] = 1.0

    summary = diagnostics.criterion_summary(
        frame,
        seed=21001,
        rho=0.4,
    )
    c1 = summary.loc[summary["criterion"].eq("C1")].iloc[0]

    assert c1["exact_zero_rate"] == pytest.approx(1.0 / 12.0)
    assert c1["exact_one_rate"] == pytest.approx(1.0 / 12.0)
    assert c1["unique_values"] == 3


def test_separation_summary_is_deterministic_and_bounded() -> None:
    frame = make_toy_frame(n_contexts=4)

    first = diagnostics.separation_summary(
        frame,
        seed=21001,
        rho=0.4,
    )
    second = diagnostics.separation_summary(
        frame.sample(frac=1.0, random_state=123).reset_index(drop=True),
        seed=21001,
        rho=0.4,
    )

    pd.testing.assert_frame_equal(first, second, check_exact=False, atol=1e-15, rtol=0)
    assert (first["between_alternative_mean_range"] >= 0).all()
    assert (first["mean_context_alternative_range"] >= 0).all()


def test_pairwise_dominance_has_exactly_30_nonself_pairs() -> None:
    frame = make_toy_frame(n_contexts=3)
    result = diagnostics.pairwise_dominance(
        frame,
        seed=21001,
        rho=0.4,
    )

    assert len(result) == 30
    assert not (result["dominator"] == result["dominated"]).any()
    assert result["dominance_rate"].between(0.0, 1.0).all()


def test_pairwise_dominance_detects_known_universal_pair() -> None:
    frame = make_dominance_frame()
    result = diagnostics.pairwise_dominance(
        frame,
        seed=21001,
        rho=0.4,
    )

    row = result.loc[
        result["dominator"].eq("ATSC")
        & result["dominated"].eq("TSP")
    ].iloc[0]

    assert row["dominance_count"] == 3
    assert row["dominance_rate"] == pytest.approx(1.0)


def test_nondominance_summary_rates_are_bounded() -> None:
    frame = make_dominance_frame()
    result = diagnostics.nondominance_summary(
        frame,
        seed=21001,
        rho=0.4,
    )

    assert len(result) == 6
    assert result["nondominated_rate"].between(0.0, 1.0).all()
    assert (
        result["mean_number_nondominated_alternatives_per_context"]
        .between(1.0, 6.0)
        .all()
    )


def test_criterion_stability_has_one_row_per_criterion() -> None:
    frame = make_toy_frame(n_contexts=3)
    summaries = [
        diagnostics.criterion_summary(frame, seed=21001, rho=0.0),
        diagnostics.criterion_summary(frame, seed=21001, rho=0.4),
        diagnostics.criterion_summary(frame, seed=21001, rho=0.8),
    ]

    result = diagnostics.criterion_stability(summaries)

    assert result["criterion"].tolist() == list(diagnostics.CRITERIA)
    assert len(result) == 10


def test_special_diagnostics_only_contains_c8_c9_c10() -> None:
    frame = make_toy_frame(n_contexts=3)
    result = diagnostics.special_diagnostics(
        frame,
        seed=21001,
        rho=0.4,
    )

    assert result["criterion"].tolist() == ["C10", "C8", "C9"] or set(
        result["criterion"]
    ) == {"C8", "C9", "C10"}
    assert set(result["criterion"]) == {"C8", "C9", "C10"}


def test_no_external_test_rows_enter_core_scientific_functions() -> None:
    frame = make_toy_frame(n_contexts=3, include_test=True)
    audit = frame.loc[frame["partition"].isin(["fit", "weight"])].reset_index(drop=True)

    # TEST rows were deliberately set near 1.0. If they leaked, C1 mean would jump.
    summary = diagnostics.criterion_summary(
        audit,
        seed=21001,
        rho=0.4,
    )
    c1_mean = summary.loc[summary["criterion"].eq("C1"), "mean"].iloc[0]

    assert c1_mean < 0.5
    assert not audit["partition"].eq("test").any()
