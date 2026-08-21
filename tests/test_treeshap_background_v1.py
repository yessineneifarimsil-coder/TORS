from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "treeshap_background_v1.py"
CONTEXT_PATH = ROOT / "src" / "01_generate_contexts.py"

EXPECTED_ELIGIBLE = {
    25: 120,
    50: 240,
    100: 480,
    250: 1200,
    1000: 4800,
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bgmod():
    return _load("treeshap_background_v1_tested", MODULE_PATH)


@pytest.fixture(scope="module")
def master(bgmod):
    step1 = _load("treeshap_bg_step1", CONTEXT_PATH)
    benchmark, experiment, seeds = step1.load_project_configuration()
    contexts, _ = step1.generate_master_contexts(
        replication_seed=21001,
        rho=0.4,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )

    alternatives = [f"A{i}" for i in range(1, 7)]
    rows = contexts.loc[contexts.index.repeat(6)].copy().reset_index(drop=True)
    rows["alternative_id"] = alternatives * len(contexts)

    # Deterministic dummy model features; membership tests must not depend on them.
    for j in range(1, 11):
        rows[f"g_C{j}"] = (
            (rows["context_number"].to_numpy(dtype=float) * (j + 1)
             + rows["alternative_id"].str[1:].astype(int).to_numpy(dtype=float))
            % 997
        ) / 997.0
    rows["Y"] = np.linspace(-0.1, 1.1, len(rows))
    rows["U_star"] = np.linspace(0.0, 1.0, len(rows))
    return rows


def _identity_sequence(frame: pd.DataFrame):
    return list(
        frame[["context_number", "alternative_id"]].itertuples(index=False, name=None)
    )


def test_frozen_protocol_contract(bgmod):
    configs = bgmod.load_configs()
    bgmod.validate_frozen_protocol(configs)
    assert bgmod.FROZEN_BACKGROUND_SIZE == 100
    assert bgmod.FROZEN_NAMESPACE == 83001
    assert bgmod.CANONICAL_SORT_COLUMNS == ("context_number", "alternative_id")


def test_complete_master_schema_and_fit_counts(bgmod, master):
    bgmod.validate_master_rows(master, replication_seed=21001)
    fit = bgmod.canonical_fit_identities(master, replication_seed=21001)
    assert len(master) == 7200
    assert len(fit) == 4800
    assert fit["context_id"].nunique() == 800


def test_priority_is_deterministic_and_input_order_invariant(bgmod, master):
    p1 = bgmod.build_priority_table(master, replication_seed=21001)
    shuffled = master.sample(frac=1.0, random_state=77123).reset_index(drop=True)
    p2 = bgmod.build_priority_table(shuffled, replication_seed=21001)

    assert len(p1) == 4800
    assert _identity_sequence(p1) == _identity_sequence(p2)
    assert np.array_equal(
        p1["background_priority_rank"].to_numpy(),
        np.arange(1, 4801),
    )


@pytest.mark.parametrize("n", [25, 50, 100, 250, 1000])
def test_exact_nested_N_eligibility_and_background_firewall(bgmod, master, n):
    selected, audit = bgmod.select_background_rows(
        master,
        replication_seed=21001,
        n_contexts=n,
    )

    assert len(selected) == 100
    assert selected["partition"].eq("fit").all()
    assert int(selected["context_number"].max()) <= n
    assert audit["eligible_fit_rows"] == EXPECTED_ELIGIBLE[n]
    assert audit["background_rows"] == 100
    assert audit["weight_rows_used"] == 0
    assert audit["external_test_rows_used"] == 0
    assert np.isclose(
        audit["background_to_fit_row_ratio"],
        100.0 / EXPECTED_ELIGIBLE[n],
    )


def test_selection_membership_ignores_features_targets_oracle_and_condition_values(bgmod, master):
    selected1, _ = bgmod.select_background_rows(
        master,
        replication_seed=21001,
        n_contexts=250,
    )

    altered = master.copy()
    rng = np.random.default_rng(99123)
    for column in [f"g_C{i}" for i in range(1, 11)]:
        altered[column] = rng.normal(size=len(altered))
    altered["Y"] = rng.normal(size=len(altered))
    altered["U_star"] = rng.normal(size=len(altered))
    altered["rho"] = 0.8
    altered["c"] = 0.6
    altered["lambda"] = 1.0

    selected2, _ = bgmod.select_background_rows(
        altered,
        replication_seed=21001,
        n_contexts=250,
    )

    assert _identity_sequence(selected1) == _identity_sequence(selected2)


def test_selection_matches_single_global_priority_filtered_to_each_N(bgmod, master):
    priority = bgmod.build_priority_table(master, replication_seed=21001)

    for n in [25, 50, 100, 250, 1000]:
        expected = priority.loc[priority["context_number"].le(n)].iloc[:100]
        selected, _ = bgmod.select_background_rows(
            master,
            replication_seed=21001,
            n_contexts=n,
        )
        assert _identity_sequence(selected) == _identity_sequence(expected)


def test_different_replication_seed_changes_priority_not_protocol(bgmod):
    step1 = _load("treeshap_bg_step1_seed2", CONTEXT_PATH)
    benchmark, experiment, seeds = step1.load_project_configuration()
    contexts, _ = step1.generate_master_contexts(
        replication_seed=21002,
        rho=0.4,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )
    rows = contexts.loc[contexts.index.repeat(6)].copy().reset_index(drop=True)
    rows["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts)

    p2 = bgmod.build_priority_table(rows, replication_seed=21002)
    assert len(p2) == 4800

    # Compare against seed 21001 using a separately generated identity master.
    contexts1, _ = step1.generate_master_contexts(
        replication_seed=21001,
        rho=0.4,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )
    rows1 = contexts1.loc[contexts1.index.repeat(6)].copy().reset_index(drop=True)
    rows1["alternative_id"] = [f"A{i}" for i in range(1, 7)] * len(contexts1)
    p1 = bgmod.build_priority_table(rows1, replication_seed=21001)

    seq1 = list(p1["context_number"].head(100))
    seq2 = list(p2["context_number"].head(100))
    assert seq1 != seq2


def test_insufficient_available_rows_raises_before_any_silent_reduction(bgmod, master):
    # The public primary selector rejects any attempt to alter B_bg.
    with pytest.raises(ValueError, match="frozen at 100"):
        bgmod.select_background_rows(
            master,
            replication_seed=21001,
            n_contexts=25,
            target_size=121,
        )

    # Corrupt the binding N=25 availability to 19 FIT contexts = 114 rows.
    damaged = master.copy()
    fit_contexts = (
        damaged.loc[
            damaged["partition"].eq("fit")
            & damaged["context_number"].le(25),
            "context_number",
        ]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    assert len(fit_contexts) == 20
    demote_context = fit_contexts[-1]
    damaged.loc[damaged["context_number"].eq(demote_context), "partition"] = "weight"

    with pytest.raises(ValueError):
        bgmod.select_background_rows(
            damaged,
            replication_seed=21001,
            n_contexts=25,
        )


def test_background_feature_matrix_is_exactly_100_by_10_and_finite(bgmod, master):
    selected, _ = bgmod.select_background_rows(
        master,
        replication_seed=21001,
        n_contexts=25,
    )
    X = bgmod.background_feature_matrix(selected)
    assert X.shape == (100, 10)
    assert np.isfinite(X).all()


def test_external_test_or_weight_cannot_enter_background(bgmod, master):
    selected, _ = bgmod.select_background_rows(
        master,
        replication_seed=21001,
        n_contexts=1000,
    )
    assert not selected["partition"].eq("weight").any()
    assert not selected["partition"].eq("test").any()
    assert not selected["context_number"].gt(1000).any()
