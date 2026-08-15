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
    """v2.1 master pool must contain exactly 1200 contexts."""

    contexts, audit = generate(rho=0.4)

    assert len(contexts) == 1200
    assert len(audit) == 1200
    assert contexts["context_id"].nunique() == 1200

    estimation = contexts.loc[
        contexts["partition"].isin(["fit", "weight"])
    ]
    external_test = contexts.loc[contexts["partition"].eq("test")]

    assert len(estimation) == 1000
    assert len(external_test) == 200
    assert estimation["context_number"].min() == 1
    assert estimation["context_number"].max() == 1000
    assert external_test["context_number"].min() == 1001
    assert external_test["context_number"].max() == 1200


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
    "n_contexts,expected_fit,expected_weight",
    [
        (25, 20, 5),
        (50, 40, 10),
        (100, 80, 20),
        (250, 200, 50),
        (1000, 800, 200),
    ],
)
def test_fixed_external_test_partition_counts(
    n_contexts: int,
    expected_fit: int,
    expected_weight: int,
) -> None:
    """Every N has 80/20 FIT/WEIGHT plus the same 200 TEST contexts."""

    contexts_master, audit_master = generate(rho=0.4)
    contexts, _ = generator.extract_nested_sample(
        contexts_master,
        audit_master,
        n_contexts,
    )

    counts = contexts["partition"].value_counts().to_dict()
    assert counts["fit"] == expected_fit
    assert counts["weight"] == expected_weight
    assert counts["test"] == 200
    assert len(contexts) == n_contexts + 200


def test_nested_estimation_samples_and_fixed_test_pool() -> None:
    """Estimation samples are nested; external TEST is identical across N."""

    contexts_master, audit_master = generate(rho=0.4)
    sample_sizes = [25, 50, 100, 250, 1000]
    samples: dict[int, pd.DataFrame] = {}

    for n_contexts in sample_sizes:
        subset, _ = generator.extract_nested_sample(
            contexts_master,
            audit_master,
            n_contexts,
        )
        samples[n_contexts] = subset

    reference_test = (
        samples[25].loc[samples[25]["partition"].eq("test")]
        .reset_index(drop=True)
    )

    for n_contexts in sample_sizes:
        sample = samples[n_contexts]
        estimation = (
            sample.loc[sample["partition"].isin(["fit", "weight"])]
            .reset_index(drop=True)
        )
        external_test = (
            sample.loc[sample["partition"].eq("test")]
            .reset_index(drop=True)
        )
        assert len(estimation) == n_contexts
        pd.testing.assert_frame_equal(
            external_test,
            reference_test,
            check_exact=True,
        )

    for smaller, larger in zip(sample_sizes[:-1], sample_sizes[1:]):
        small_est = samples[smaller].loc[
            samples[smaller]["partition"].isin(["fit", "weight"])
        ].reset_index(drop=True)
        large_est = samples[larger].loc[
            samples[larger]["partition"].isin(["fit", "weight"])
        ].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            small_est,
            large_est.iloc[:smaller].reset_index(drop=True),
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



def test_estimation_and_external_test_stream_namespaces() -> None:
    """Master audit must exactly use namespaces 1001 and 1002."""

    _, audit = generate(rho=0.4)
    stream_cfg = seeds["context_generation"]

    z_shared_est, z_idio_est = generator.generate_base_normals(
        replication_seed=DEVELOPMENT_SEED,
        n_contexts=1000,
        n_latent_factors=len(FACTOR_NAMES),
        stream_namespace=int(stream_cfg["estimation_stream_namespace"]),
    )
    z_shared_test, z_idio_test = generator.generate_base_normals(
        replication_seed=DEVELOPMENT_SEED,
        n_contexts=200,
        n_latent_factors=len(FACTOR_NAMES),
        stream_namespace=int(stream_cfg["external_test_stream_namespace"]),
    )

    np.testing.assert_array_equal(audit.iloc[:1000]["z_shared"], z_shared_est)
    np.testing.assert_array_equal(audit.iloc[1000:]["z_shared"], z_shared_test)

    for idx, factor in enumerate(FACTOR_NAMES):
        np.testing.assert_array_equal(
            audit.iloc[:1000][f"z_{factor}"].to_numpy(),
            z_idio_est[:, idx],
        )
        np.testing.assert_array_equal(
            audit.iloc[1000:][f"z_{factor}"].to_numpy(),
            z_idio_test[:, idx],
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