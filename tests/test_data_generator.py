"""
Unit tests for the controlled latent-context generator.

These tests validate:

1. dimensions and variable domains;
2. exact FIT / WEIGHT / TEST proportions;
3. deterministic reproducibility;
4. nested sample preservation;
5. CRN preservation across rho;
6. latent Gaussian correlation;
7. context IDs and uniqueness.

No ITS performance or oracle logic is tested here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "01_generate_contexts.py"
)


def load_context_module():
    """Import the numbered generator script dynamically."""

    spec = importlib.util.spec_from_file_location(
        "generate_contexts_module",
        MODULE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load context-generator module."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


generator = load_context_module()

benchmark, experiment, seeds = (
    generator.load_project_configuration()
)

DEVELOPMENT_SEED = 21001

FACTOR_NAMES = list(
    benchmark[
        "context_generator"
    ]["latent_factors"]
)


def generate(
    rho: float,
):
    """Generate one complete master context pool."""

    return generator.generate_master_contexts(
        replication_seed=DEVELOPMENT_SEED,
        rho=rho,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )


def test_master_context_dimensions() -> None:
    """Master pool must contain exactly 1000 contexts."""

    contexts, audit = generate(
        rho=0.4
    )

    assert len(contexts) == 1000
    assert len(audit) == 1000

    assert len(
        contexts["context_id"].unique()
    ) == 1000


def test_context_factor_domains() -> None:
    """Every transformed context factor must lie in [0,1]."""

    contexts, _ = generate(
        rho=0.4
    )

    for factor in FACTOR_NAMES:

        assert contexts[
            factor
        ].between(
            0.0,
            1.0,
            inclusive="both",
        ).all()


@pytest.mark.parametrize(
    "n_contexts",
    [
        25,
        50,
        100,
        250,
        1000,
    ],
)
def test_exact_partition_proportions(
    n_contexts: int,
) -> None:
    """
    Every configured nested N must have an exact
    60/20/20 context split.
    """

    contexts_master, audit_master = (
        generate(
            rho=0.4
        )
    )

    contexts, _ = (
        generator.extract_nested_sample(
            contexts_master,
            audit_master,
            n_contexts,
        )
    )

    counts = (
        contexts["partition"]
        .value_counts()
        .to_dict()
    )

    assert counts["fit"] == int(
        n_contexts * 0.60
    )

    assert counts["weight"] == int(
        n_contexts * 0.20
    )

    assert counts["test"] == int(
        n_contexts * 0.20
    )


def test_nested_samples_are_exact_prefixes() -> None:
    """
    S25 must be contained unchanged in S50,
    S50 in S100, etc.
    """

    contexts_master, audit_master = (
        generate(
            rho=0.4
        )
    )

    sample_sizes = [
        25,
        50,
        100,
        250,
        1000,
    ]

    samples: dict[
        int,
        pd.DataFrame,
    ] = {}

    for n_contexts in sample_sizes:

        subset, _ = (
            generator.extract_nested_sample(
                contexts_master,
                audit_master,
                n_contexts,
            )
        )

        samples[
            n_contexts
        ] = subset

    for smaller, larger in zip(
        sample_sizes[:-1],
        sample_sizes[1:],
    ):

        pd.testing.assert_frame_equal(
            samples[smaller],
            samples[larger].iloc[
                :smaller
            ].reset_index(drop=True),
            check_exact=True,
        )


def test_generator_is_deterministic() -> None:
    """Same seed and rho must reproduce exactly."""

    contexts_a, audit_a = generate(
        rho=0.4
    )

    contexts_b, audit_b = generate(
        rho=0.4
    )

    pd.testing.assert_frame_equal(
        contexts_a,
        contexts_b,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        audit_a,
        audit_b,
        check_exact=True,
    )


def test_base_random_numbers_are_reused_across_rho() -> None:
    """
    The same z_shared and z_k values must be reused
    across rho = 0, 0.4 and 0.8.
    """

    _, audit_0 = generate(
        rho=0.0
    )

    _, audit_4 = generate(
        rho=0.4
    )

    _, audit_8 = generate(
        rho=0.8
    )

    base_columns = [
        "z_shared",
        *[
            f"z_{factor}"
            for factor in FACTOR_NAMES
        ],
    ]

    np.testing.assert_array_equal(
        audit_0[
            base_columns
        ].to_numpy(),
        audit_4[
            base_columns
        ].to_numpy(),
    )

    np.testing.assert_array_equal(
        audit_0[
            base_columns
        ].to_numpy(),
        audit_8[
            base_columns
        ].to_numpy(),
    )


def test_partition_assignment_is_reused_across_rho() -> None:
    """
    A context must retain its FIT / WEIGHT / TEST role
    across all rho conditions.
    """

    contexts_0, _ = generate(
        rho=0.0
    )

    contexts_4, _ = generate(
        rho=0.4
    )

    contexts_8, _ = generate(
        rho=0.8
    )

    np.testing.assert_array_equal(
        contexts_0[
            "partition"
        ].to_numpy(),
        contexts_4[
            "partition"
        ].to_numpy(),
    )

    np.testing.assert_array_equal(
        contexts_0[
            "partition"
        ].to_numpy(),
        contexts_8[
            "partition"
        ].to_numpy(),
    )


@pytest.mark.parametrize(
    "rho",
    [
        0.0,
        0.4,
        0.8,
    ],
)
def test_latent_normal_correlation(
    rho: float,
) -> None:
    """
    Mean off-diagonal correlation of the latent
    Gaussian variables should approximate configured rho.

    We test the latent Gaussian variables rather than the
    transformed Uniform variables because rho parameterizes
    the Gaussian copula.
    """

    _, audit = generate(
        rho=rho
    )

    realized = (
        generator.mean_off_diagonal_correlation(
            audit=audit,
            factor_names=FACTOR_NAMES,
        )
    )

    assert abs(
        realized - rho
    ) < 0.08, (
        f"Configured rho={rho}, "
        f"realized latent correlation={realized}"
    )


def test_rho_changes_latent_contexts() -> None:
    """
    CRN means base draws are shared, not that the
    generated contextual factors should be identical.
    """

    contexts_0, _ = generate(
        rho=0.0
    )

    contexts_8, _ = generate(
        rho=0.8
    )

    values_0 = contexts_0[
        FACTOR_NAMES
    ].to_numpy()

    values_8 = contexts_8[
        FACTOR_NAMES
    ].to_numpy()

    assert not np.array_equal(
        values_0,
        values_8,
    )


def test_context_identity_preserved_across_rho() -> None:
    """Context identifiers must remain stable across rho."""

    contexts_0, _ = generate(
        rho=0.0
    )

    contexts_8, _ = generate(
        rho=0.8
    )

    np.testing.assert_array_equal(
        contexts_0[
            "context_id"
        ].to_numpy(),
        contexts_8[
            "context_id"
        ].to_numpy(),
    )


def test_invalid_sample_size_is_rejected() -> None:
    """Unconfigured sample sizes must fail explicitly."""

    with pytest.raises(
        ValueError
    ):
        generator.validate_requested_design(
            n_contexts=123,
            rho=0.4,
            experiment=experiment,
        )


def test_invalid_rho_is_rejected() -> None:
    """Unconfigured rho values must fail explicitly."""

    with pytest.raises(
        ValueError
    ):
        generator.validate_requested_design(
            n_contexts=250,
            rho=0.6,
            experiment=experiment,
        )