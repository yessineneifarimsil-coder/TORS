"""
Controlled latent-context generator for the XAI-MCDM ITS benchmark.

This module implements ONLY the latent context layer:

    base random draws
        ->
    Gaussian equicorrelation construction
        ->
    Uniform(0,1) contextual factors
        ->
    nested context samples
        ->
    fixed FIT / WEIGHT / TEST partitions

No ITS criterion scores, oracle utility, model fitting, SHAP values,
or MCDM rankings are generated here.

Scientific design
-----------------
For each context s and latent factor k:

    h_tilde[k,s] =
        sqrt(rho) * z_shared[s]
        + sqrt(1-rho) * z_k[s]

where all base z variables are iid N(0,1).

The SAME z_shared and z_k draws are reused across all rho values
for a given replication seed. This implements the common-random-
number design.

The transformed contextual factors are:

    h[k,s] = Phi(h_tilde[k,s])

where Phi is the standard-normal CDF.

Each replication seed contains a 1000-context nested estimation /
calibration pool plus a fixed 200-context external TEST pool.

The estimation subsets are exact prefixes:

    S_25 subset S_50 subset S_100 subset S_250 subset S_1000

Within the estimation pool, each block of five contains four FIT
roles and one WEIGHT role in deterministic shuffled order. Contexts
1001..1200 are always external TEST contexts and are appended to every
N condition. Separate deterministic context streams preserve the
validated first 1000 context draws while adding the external TEST pool.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_CONFIG = PROJECT_ROOT / "config" / "benchmark.yaml"
EXPERIMENT_CONFIG = PROJECT_ROOT / "config" / "experiment.yaml"
SEEDS_CONFIG = PROJECT_ROOT / "config" / "seeds.yaml"

GENERATED_DIR = PROJECT_ROOT / "data" / "generated"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"


# ============================================================
# Fixed random-stream namespace
# ============================================================
#
# The context-generation stream is deliberately separated from
# future technology-response, criterion-noise, oracle, bootstrap,
# and robustness streams.
#
# Using SeedSequence([replication_seed, namespace]) makes the
# stream deterministic without depending on execution order.
# ============================================================

CONTEXT_STREAM_NAMESPACE = 1001


# ============================================================
# Configuration utilities
# ============================================================


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a UTF-8 YAML configuration file."""

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML structure in {path}")

    return data


def load_project_configuration() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Load benchmark, experiment, and seed configurations."""

    benchmark = load_yaml(BENCHMARK_CONFIG)
    experiment = load_yaml(EXPERIMENT_CONFIG)
    seeds = load_yaml(SEEDS_CONFIG)

    return benchmark, experiment, seeds


# ============================================================
# Input validation
# ============================================================


def get_allowed_sample_sizes(
    experiment: dict[str, Any],
) -> list[int]:
    """Return configured sample-size levels."""

    values = experiment["factors"]["sample_size"]["values"]

    return [int(value) for value in values]


def get_allowed_rho_values(
    experiment: dict[str, Any],
) -> list[float]:
    """Return configured dependence levels."""

    values = experiment["factors"][
        "predictor_dependence"
    ]["values"]

    return [float(value) for value in values]


def validate_requested_design(
    n_contexts: int,
    rho: float,
    experiment: dict[str, Any],
) -> None:
    """Validate requested N and rho against configuration."""

    allowed_n = get_allowed_sample_sizes(experiment)
    allowed_rho = get_allowed_rho_values(experiment)

    if n_contexts not in allowed_n:
        raise ValueError(
            f"N={n_contexts} is not configured. "
            f"Allowed values: {allowed_n}"
        )

    if not any(
        np.isclose(rho, configured_rho)
        for configured_rho in allowed_rho
    ):
        raise ValueError(
            f"rho={rho} is not configured. "
            f"Allowed values: {allowed_rho}"
        )

    if not 0.0 <= rho < 1.0:
        raise ValueError(
            "rho must satisfy 0 <= rho < 1."
        )


def validate_seed(
    seed: int,
    seed_family: str,
    seeds: dict[str, Any],
) -> None:
    """Ensure the requested seed belongs to the declared family."""

    if seed_family not in {"development", "primary"}:
        raise ValueError(
            "seed_family must be either "
            "'development' or 'primary'."
        )

    registered = [
        int(value)
        for value in seeds[seed_family]
    ]

    if seed not in registered:
        raise ValueError(
            f"Seed {seed} is not registered in "
            f"the '{seed_family}' seed family."
        )


# ============================================================
# Partition generation
# ============================================================


def generate_partition_assignment(
    replication_seed: int,
    experiment: dict[str, Any],
    seeds: dict[str, Any],
) -> np.ndarray:
    """
    Generate the frozen FIT / WEIGHT assignment for the 1000-context
    estimation/calibration master pool.

    Each block of five contains exactly four FIT roles and one WEIGHT
    role. Role order is shuffled with a deterministic partition stream.
    External TEST contexts are not assigned here; they are appended as
    a separate fixed pool in generate_master_contexts().
    """

    nested = experiment["partition"]["nested_assignment"]
    max_contexts = int(nested["maximum_contexts"])
    block_size = int(nested["block_size"])
    roles = list(nested["roles_per_block"])

    if len(roles) != block_size:
        raise ValueError(
            "roles_per_block length does not match configured block_size."
        )

    if max_contexts % block_size != 0:
        raise ValueError(
            "maximum_contexts must be divisible by partition block_size."
        )

    if roles.count("fit") != 4 or roles.count("weight") != 1:
        raise ValueError(
            "v2.1 nested estimation blocks must contain four FIT roles "
            "and one WEIGHT role."
        )

    if "test" in roles:
        raise ValueError(
            "External TEST must not appear in nested estimation roles."
        )

    partition_offset = int(
        seeds["partition_assignment"]["master_seed_offset"]
    )

    rng = np.random.default_rng(
        np.random.SeedSequence([replication_seed, partition_offset])
    )

    assignments: list[str] = []

    for _ in range(max_contexts // block_size):
        assignments.extend(rng.permutation(roles).tolist())

    return np.asarray(assignments, dtype=object)


# ============================================================
# Base random numbers
# ============================================================


def generate_base_normals(
    replication_seed: int,
    n_contexts: int,
    n_latent_factors: int,
    stream_namespace: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate CRN base Gaussian variables for one deterministic context stream.

    The estimation pool uses namespace 1001 and the fixed external TEST
    pool uses namespace 1002. Draws depend on replication seed and stream
    namespace but never on rho.
    """

    seed_sequence = np.random.SeedSequence(
        [replication_seed, int(stream_namespace)]
    )
    rng = np.random.default_rng(seed_sequence)

    z_shared = rng.standard_normal(size=n_contexts)
    z_idiosyncratic = rng.standard_normal(
        size=(n_contexts, n_latent_factors)
    )

    return z_shared, z_idiosyncratic


# ============================================================
# Correlated latent factors
# ============================================================


def construct_correlated_normals(
    z_shared: np.ndarray,
    z_idiosyncratic: np.ndarray,
    rho: float,
) -> np.ndarray:
    """
    Construct equicorrelated standard-normal latent variables.

    h_tilde_k =
        sqrt(rho) * z_shared
        + sqrt(1-rho) * z_k
    """

    shared_component = (
        np.sqrt(rho)
        * z_shared[:, None]
    )

    idiosyncratic_component = (
        np.sqrt(1.0 - rho)
        * z_idiosyncratic
    )

    latent_normal = (
        shared_component
        + idiosyncratic_component
    )

    return latent_normal


def transform_to_uniform(
    latent_normal: np.ndarray,
) -> np.ndarray:
    """
    Transform latent Gaussian values to Uniform(0,1)
    marginals using the standard-normal CDF.
    """

    return norm.cdf(
        latent_normal
    )


# ============================================================
# Master context generation
# ============================================================


def generate_master_contexts(
    replication_seed: int,
    rho: float,
    benchmark: dict[str, Any],
    experiment: dict[str, Any],
    seeds: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate the complete v2.1 1200-context master pool.

    Contexts 1..1000 are the nested estimation/calibration master pool.
    Contexts 1001..1200 are the fixed external TEST pool.
    """

    factor_names = list(
        benchmark["context_generator"]["latent_factors"]
    )
    n_factors = len(factor_names)
    expected_factors = int(
        benchmark["dimensions"]["latent_context_factors"]
    )
    if n_factors != expected_factors:
        raise ValueError(
            "Configured latent factor count does not match benchmark dimensions."
        )

    total_master = int(
        experiment["common_random_numbers"]["master_context_size_per_seed"]
    )
    estimation_master = int(
        experiment["partition"]["nested_assignment"]["maximum_contexts"]
    )
    external_cfg = experiment["partition"]["external_test"]
    external_n = int(external_cfg["contexts"])

    if total_master != estimation_master + external_n:
        raise ValueError(
            "Total master size must equal estimation master plus external TEST."
        )
    if int(external_cfg["first_context_number"]) != estimation_master + 1:
        raise ValueError("External TEST first context number is inconsistent.")
    if int(external_cfg["last_context_number"]) != total_master:
        raise ValueError("External TEST last context number is inconsistent.")

    stream_cfg = seeds["context_generation"]
    estimation_namespace = int(stream_cfg["estimation_stream_namespace"])
    external_namespace = int(stream_cfg["external_test_stream_namespace"])
    if estimation_namespace == external_namespace:
        raise ValueError("Estimation and external TEST namespaces must differ.")

    z_shared_est, z_idio_est = generate_base_normals(
        replication_seed=replication_seed,
        n_contexts=estimation_master,
        n_latent_factors=n_factors,
        stream_namespace=estimation_namespace,
    )
    z_shared_test, z_idio_test = generate_base_normals(
        replication_seed=replication_seed,
        n_contexts=external_n,
        n_latent_factors=n_factors,
        stream_namespace=external_namespace,
    )

    z_shared = np.concatenate([z_shared_est, z_shared_test], axis=0)
    z_idiosyncratic = np.concatenate(
        [z_idio_est, z_idio_test], axis=0
    )

    latent_normal = construct_correlated_normals(
        z_shared=z_shared,
        z_idiosyncratic=z_idiosyncratic,
        rho=rho,
    )
    latent_uniform = transform_to_uniform(latent_normal)

    estimation_partitions = generate_partition_assignment(
        replication_seed=replication_seed,
        experiment=experiment,
        seeds=seeds,
    )
    external_partitions = np.full(external_n, "test", dtype=object)
    partitions = np.concatenate(
        [estimation_partitions, external_partitions], axis=0
    )

    if len(partitions) != total_master:
        raise ValueError("Partition vector length does not match master size.")

    context_number = np.arange(1, total_master + 1, dtype=int)
    context_ids = [
        f"S{replication_seed}_C{number:04d}"
        for number in context_number
    ]

    context_data: dict[str, Any] = {
        "context_id": context_ids,
        "context_number": context_number,
        "replication_seed": replication_seed,
        "rho": float(rho),
        "partition": partitions,
    }
    for factor_index, factor_name in enumerate(factor_names):
        context_data[factor_name] = latent_uniform[:, factor_index]
    contexts = pd.DataFrame(context_data)

    audit_data: dict[str, Any] = {
        "context_id": context_ids,
        "context_number": context_number,
        "replication_seed": replication_seed,
        "rho": float(rho),
        "partition": partitions,
        "z_shared": z_shared,
    }
    for factor_index, factor_name in enumerate(factor_names):
        audit_data[f"z_{factor_name}"] = z_idiosyncratic[:, factor_index]
        audit_data[f"latent_{factor_name}"] = latent_normal[:, factor_index]
    audit = pd.DataFrame(audit_data)

    return contexts, audit


# ============================================================
# Nested sample extraction
# ============================================================


def extract_nested_sample(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    n_contexts: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return the first N estimation/calibration contexts plus all fixed
    external TEST contexts.

    N excludes the 200-context external TEST pool.
    """

    if len(contexts) != len(audit):
        raise ValueError("Context and audit master pools must have equal length.")

    estimation_mask = contexts["partition"].isin(["fit", "weight"])
    test_mask = contexts["partition"].eq("test")

    estimation_master = contexts.loc[estimation_mask]
    test_master = contexts.loc[test_mask]

    if n_contexts > len(estimation_master):
        raise ValueError(
            "Requested estimation sample size exceeds estimation master pool."
        )

    estimation_contexts = (
        estimation_master.loc[
            estimation_master["context_number"] <= n_contexts
        ]
        .copy()
        .reset_index(drop=True)
    )
    external_test_contexts = test_master.copy().reset_index(drop=True)

    selected_ids = pd.concat(
        [
            estimation_contexts[["context_id"]],
            external_test_contexts[["context_id"]],
        ],
        ignore_index=True,
    )["context_id"]

    context_subset = pd.concat(
        [estimation_contexts, external_test_contexts],
        ignore_index=True,
    )

    audit_by_id = audit.set_index("context_id", drop=False)
    audit_subset = (
        audit_by_id.loc[selected_ids.tolist()]
        .reset_index(drop=True)
    )

    return context_subset, audit_subset


# ============================================================
# Diagnostics
# ============================================================


def mean_off_diagonal_correlation(
    audit: pd.DataFrame,
    factor_names: list[str],
) -> float:
    """
    Return mean off-diagonal Pearson correlation among
    latent-normal variables.

    Correlation is checked BEFORE the Gaussian-CDF transform,
    because rho is the Gaussian-copula latent correlation.
    """

    latent_columns = [
        f"latent_{name}"
        for name in factor_names
    ]

    matrix = (
        audit[latent_columns]
        .corr()
        .to_numpy()
    )

    upper_indices = np.triu_indices_from(
        matrix,
        k=1,
    )

    return float(
        matrix[upper_indices].mean()
    )


def partition_counts(
    contexts: pd.DataFrame,
) -> dict[str, int]:
    """Return context counts by partition."""

    counts = (
        contexts["partition"]
        .value_counts()
        .to_dict()
    )

    return {
        str(key): int(value)
        for key, value in counts.items()
    }


# ============================================================
# Output utilities
# ============================================================


def rho_to_filename(
    rho: float,
) -> str:
    """Convert rho into a filesystem-safe token."""

    return (
        f"{rho:.2f}"
        .replace(".", "p")
    )


def save_generated_data(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    replication_seed: int,
    n_contexts: int,
    rho: float,
) -> tuple[Path, Path]:
    """Save context and audit datasets."""

    GENERATED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rho_token = rho_to_filename(
        rho
    )

    context_path = (
        GENERATED_DIR
        / (
            f"contexts_seed{replication_seed}"
            f"_N{n_contexts:04d}"
            f"_rho{rho_token}.csv"
        )
    )

    audit_path = (
        AUDIT_DIR
        / (
            f"context_audit_seed{replication_seed}"
            f"_N{n_contexts:04d}"
            f"_rho{rho_token}.csv"
        )
    )

    contexts.to_csv(
        context_path,
        index=False,
        float_format="%.12f",
    )

    audit.to_csv(
        audit_path,
        index=False,
        float_format="%.12f",
    )

    return (
        context_path,
        audit_path,
    )


# ============================================================
# CLI
# ============================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate controlled latent transport contexts."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Registered replication seed.",
    )

    parser.add_argument(
        "--seed-family",
        choices=[
            "development",
            "primary",
        ],
        default="development",
        help=(
            "Seed registry family. "
            "Default: development."
        ),
    )

    parser.add_argument(
        "--n",
        type=int,
        required=True,
        help="Number of contexts.",
    )

    parser.add_argument(
        "--rho",
        type=float,
        required=True,
        help="Gaussian-copula dependence level.",
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help=(
            "Run generation and diagnostics "
            "without writing CSV files."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Command-line entry point."""

    args = parse_arguments()

    benchmark, experiment, seeds = (
        load_project_configuration()
    )

    validate_requested_design(
        n_contexts=args.n,
        rho=args.rho,
        experiment=experiment,
    )

    validate_seed(
        seed=args.seed,
        seed_family=args.seed_family,
        seeds=seeds,
    )

    contexts_master, audit_master = (
        generate_master_contexts(
            replication_seed=args.seed,
            rho=args.rho,
            benchmark=benchmark,
            experiment=experiment,
            seeds=seeds,
        )
    )

    contexts, audit = (
        extract_nested_sample(
            contexts=contexts_master,
            audit=audit_master,
            n_contexts=args.n,
        )
    )

    factor_names = list(
        benchmark[
            "context_generator"
        ]["latent_factors"]
    )

    estimation_audit = audit.loc[
        audit["partition"].isin(["fit", "weight"])
    ].reset_index(drop=True)

    empirical_latent_rho = (
        mean_off_diagonal_correlation(
            audit=estimation_audit,
            factor_names=factor_names,
        )
    )

    counts = partition_counts(
        contexts
    )

    print("=" * 72)
    print("CONTROLLED LATENT CONTEXT GENERATOR")
    print("=" * 72)

    print(
        f"Seed family             : "
        f"{args.seed_family}"
    )

    print(
        f"Replication seed        : "
        f"{args.seed}"
    )

    print(
        f"Estimation N requested : "
        f"{args.n}"
    )

    print(
        f"Total contexts returned: "
        f"{len(contexts)}"
    )

    print(
        f"Configured rho          : "
        f"{args.rho:.3f}"
    )

    print(
        f"Realized latent corr.   : "
        f"{empirical_latent_rho:.4f}"
    )

    print(
        f"FIT contexts            : "
        f"{counts.get('fit', 0)}"
    )

    print(
        f"WEIGHT contexts         : "
        f"{counts.get('weight', 0)}"
    )

    print(
        f"TEST contexts           : "
        f"{counts.get('test', 0)}"
    )

    print()

    for factor_name in factor_names:
        values = contexts[
            factor_name
        ]

        print(
            f"{factor_name:4s} "
            f"min={values.min():.4f} "
            f"mean={values.mean():.4f} "
            f"max={values.max():.4f}"
        )

    if not args.no_save:

        context_path, audit_path = (
            save_generated_data(
                contexts=contexts,
                audit=audit,
                replication_seed=args.seed,
                n_contexts=args.n,
                rho=args.rho,
            )
        )

        print()
        print(
            f"Context dataset         : "
            f"{context_path}"
        )

        print(
            f"Audit dataset           : "
            f"{audit_path}"
        )

    print()
    print("CONTEXT GENERATION COMPLETED")
    print("=" * 72)


if __name__ == "__main__":
    main()