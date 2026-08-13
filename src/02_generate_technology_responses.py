"""
Alternative-specific ITS performance generator.

Step 2 of the controlled XAI-MCDM benchmark.

This module takes the latent transport contexts produced by
01_generate_contexts.py and generates alternative-specific
performance values for the ten decision criteria.

It implements:

C1-C7
-----
x_asj = clip(
    theta_aj * opportunity_js ** gamma + eta_asj,
    0,
    1
)

where theta_aj is sampled ONCE per alternative / criterion /
replication according to the structural capability class:

    0 -> 0
    I -> U(0.05, 0.20)
    D -> U(0.20, 0.40)

C8
--
One-sided infrastructure-readiness shortfall:

x_as8 = clip(
    1 - max(0, r_a - h_R,s) + eta_as8,
    0,
    1
)

An environment that is more ready than required is therefore
not penalised.

C9
--
x_as9 = clip(
    iota_a + 0.10 * h_R,s + eta_as9,
    0,
    1
)

C10
---
Raw annualised lifecycle deployment burden:

x_as10 = clip(
    kappa_a
    + 0.20 * (1 - h_R,s) * r_a
    + eta_as10,
    0,
    1
)

Direction-adjusted decision variables are then:

    g_j = x_j        for C1-C9
    g_10 = 1 - x_10

All stochastic components use deterministic SeedSequence
namespaces so that common random numbers are preserved across
rho and nested sample-size conditions.

No oracle utility, target noise, XGBoost, SHAP, or MCDM
calculation is performed in this module.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_CONFIG = PROJECT_ROOT / "config" / "benchmark.yaml"
EXPERIMENT_CONFIG = PROJECT_ROOT / "config" / "experiment.yaml"
SEEDS_CONFIG = PROJECT_ROOT / "config" / "seeds.yaml"

CONTEXT_MODULE_PATH = (
    PROJECT_ROOT / "src" / "01_generate_contexts.py"
)

GENERATED_DIR = PROJECT_ROOT / "data" / "generated"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"


# ============================================================
# Independent random-stream namespaces
# ============================================================

CAPABILITY_STREAM_NAMESPACE = 2001
DEPLOYMENT_STREAM_NAMESPACE = 2002
CRITERION_NOISE_STREAM_NAMESPACE = 2003


# ============================================================
# Dynamic import of Step 1
# ============================================================


def load_context_module():
    """Load the numbered Step-1 generator module."""

    spec = importlib.util.spec_from_file_location(
        "generate_contexts_module",
        CONTEXT_MODULE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load 01_generate_contexts.py"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


context_generator = load_context_module()


# ============================================================
# YAML utilities
# ============================================================


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a UTF-8 YAML file."""

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid YAML structure in {path}"
        )

    return data


def load_project_configuration() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Load benchmark, experiment, and seed configuration."""

    return (
        load_yaml(BENCHMARK_CONFIG),
        load_yaml(EXPERIMENT_CONFIG),
        load_yaml(SEEDS_CONFIG),
    )


# ============================================================
# Ordering utilities
# ============================================================


def ordered_alternative_keys(
    benchmark: dict[str, Any],
) -> list[str]:
    """Return alternatives ordered by A1, A2, ..., A6."""

    alternatives = benchmark["alternatives"]

    return sorted(
        alternatives.keys(),
        key=lambda key: int(
            alternatives[key]["id"][1:]
        ),
    )


def ordered_criterion_keys(
    benchmark: dict[str, Any],
) -> list[str]:
    """Return C1, ..., C10 in configured index order."""

    criteria = benchmark["criteria"]

    return sorted(
        criteria.keys(),
        key=lambda key: int(
            criteria[key]["index"]
        ),
    )


# ============================================================
# Technology effect-band sampling
# ============================================================


def sample_effect_band(
    rng: np.random.Generator,
    band_name: str,
    benchmark: dict[str, Any],
) -> float:
    """Sample one alternative-criterion response amplitude."""

    band = benchmark[
        "technology_response"
    ]["effect_bands"][band_name]

    distribution = band["distribution"]

    if distribution == "fixed":
        return float(band["value"])

    if distribution == "uniform":
        return float(
            rng.uniform(
                float(band["low"]),
                float(band["high"]),
            )
        )

    raise ValueError(
        f"Unsupported effect-band distribution: "
        f"{distribution}"
    )


def sample_capability_parameters(
    replication_seed: int,
    benchmark: dict[str, Any],
) -> pd.DataFrame:
    """
    Sample C1-C7 amplitudes once per replication.

    The draws do NOT depend on rho or N.
    """

    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                replication_seed,
                CAPABILITY_STREAM_NAMESPACE,
            ]
        )
    )

    rows: list[dict[str, Any]] = []

    for alternative_key in ordered_alternative_keys(
        benchmark
    ):
        alternative = benchmark[
            "alternatives"
        ][alternative_key]

        for criterion_number in range(1, 8):

            criterion = f"C{criterion_number}"

            capability_class = alternative[
                "capability"
            ][criterion]

            amplitude = sample_effect_band(
                rng=rng,
                band_name=capability_class,
                benchmark=benchmark,
            )

            rows.append(
                {
                    "alternative_key": alternative_key,
                    "alternative_id": alternative["id"],
                    "criterion": criterion,
                    "capability_class": capability_class,
                    "amplitude": amplitude,
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# Deployment-class sampling
# ============================================================


def sample_base_class(
    rng: np.random.Generator,
    class_name: str,
    benchmark: dict[str, Any],
) -> float:
    """Sample a simple L/M/H deployment class."""

    config = benchmark[
        "deployment_classes"
    ]["base"][class_name]

    if config["distribution"] != "uniform":
        raise ValueError(
            "Base deployment classes must use "
            "uniform distributions."
        )

    return float(
        rng.uniform(
            float(config["low"]),
            float(config["high"]),
        )
    )


def sample_deployment_class(
    rng: np.random.Generator,
    class_name: str,
    benchmark: dict[str, Any],
) -> tuple[float, str]:
    """
    Sample L, M, H, L-M, or M-H.

    Compound classes are equal mixtures of component
    distributions, rather than continuous intervals that
    incorrectly fill the gap between classes.
    """

    base_classes = benchmark[
        "deployment_classes"
    ]["base"]

    if class_name in base_classes:
        return (
            sample_base_class(
                rng=rng,
                class_name=class_name,
                benchmark=benchmark,
            ),
            class_name,
        )

    compound_classes = benchmark[
        "deployment_classes"
    ]["compound"]

    if class_name not in compound_classes:
        raise ValueError(
            f"Unknown deployment class: {class_name}"
        )

    specification = compound_classes[
        class_name
    ]

    if specification[
        "distribution"
    ] != "equal_mixture":
        raise ValueError(
            "Unsupported compound-class distribution."
        )

    components = list(
        specification["components"]
    )

    probabilities = np.asarray(
        specification["probabilities"],
        dtype=float,
    )

    probabilities = (
        probabilities
        / probabilities.sum()
    )

    chosen_component = str(
        rng.choice(
            components,
            p=probabilities,
        )
    )

    sampled_value = sample_base_class(
        rng=rng,
        class_name=chosen_component,
        benchmark=benchmark,
    )

    return sampled_value, chosen_component


def sample_deployment_parameters(
    replication_seed: int,
    benchmark: dict[str, Any],
) -> pd.DataFrame:
    """
    Sample r_a, iota_a, and kappa_a once per alternative.

    r_a     -> readiness requirement used by C8 and C10
    iota_a  -> interoperability baseline used by C9
    kappa_a -> lifecycle-burden baseline used by C10
    """

    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                replication_seed,
                DEPLOYMENT_STREAM_NAMESPACE,
            ]
        )
    )

    rows: list[dict[str, Any]] = []

    for alternative_key in ordered_alternative_keys(
        benchmark
    ):
        alternative = benchmark[
            "alternatives"
        ][alternative_key]

        readiness, readiness_component = (
            sample_deployment_class(
                rng=rng,
                class_name=alternative[
                    "readiness_class"
                ],
                benchmark=benchmark,
            )
        )

        interoperability, interoperability_component = (
            sample_deployment_class(
                rng=rng,
                class_name=alternative[
                    "interoperability_class"
                ],
                benchmark=benchmark,
            )
        )

        burden, burden_component = (
            sample_deployment_class(
                rng=rng,
                class_name=alternative[
                    "burden_class"
                ],
                benchmark=benchmark,
            )
        )

        rows.append(
            {
                "alternative_key": alternative_key,
                "alternative_id": alternative["id"],
                "alternative_name": alternative["name"],

                "readiness_class": alternative[
                    "readiness_class"
                ],
                "readiness_component": readiness_component,
                "readiness_requirement": readiness,

                "interoperability_class": alternative[
                    "interoperability_class"
                ],
                "interoperability_component":
                    interoperability_component,
                "interoperability_baseline":
                    interoperability,

                "burden_class": alternative[
                    "burden_class"
                ],
                "burden_component": burden_component,
                "burden_baseline": burden,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# Opportunity functions C1-C7
# ============================================================


def compute_opportunities(
    contexts: pd.DataFrame,
    benchmark: dict[str, Any],
) -> pd.DataFrame:
    """
    Compute context-specific criterion opportunities.

    Each configured opportunity is a weighted combination
    of latent context factors.
    """

    specifications = benchmark[
        "context_generator"
    ]["opportunity_functions"]

    result = pd.DataFrame(
        {
            "context_id": contexts["context_id"].copy(),
            "context_number":
                contexts["context_number"].copy(),
        }
    )

    for criterion_number in range(1, 8):

        criterion = f"C{criterion_number}"

        weights = specifications[
            criterion
        ]

        opportunity = np.zeros(
            len(contexts),
            dtype=float,
        )

        total_weight = 0.0

        for factor_name, coefficient in (
            weights.items()
        ):
            coefficient = float(coefficient)

            opportunity += (
                coefficient
                * contexts[
                    factor_name
                ].to_numpy(dtype=float)
            )

            total_weight += coefficient

        if not np.isclose(
            total_weight,
            1.0,
            atol=1e-12,
        ):
            raise ValueError(
                f"Opportunity coefficients for "
                f"{criterion} sum to "
                f"{total_weight}, not 1."
            )

        result[
            f"opportunity_{criterion}"
        ] = opportunity

    return result


# ============================================================
# Criterion-noise CRN
# ============================================================


def generate_base_criterion_noise(
    replication_seed: int,
    n_contexts: int,
    n_alternatives: int,
    n_criteria: int,
) -> np.ndarray:
    """
    Generate standard-normal criterion-noise base draws.

    Shape:
        (context, alternative, criterion)

    These draws depend on replication seed but not on rho or N.
    """

    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                replication_seed,
                CRITERION_NOISE_STREAM_NAMESPACE,
            ]
        )
    )

    return rng.standard_normal(
        size=(
            n_contexts,
            n_alternatives,
            n_criteria,
        )
    )


# ============================================================
# Response generation
# ============================================================


def clip01(
    values: np.ndarray,
) -> np.ndarray:
    """Clip values to [0,1]."""

    return np.clip(
        values,
        0.0,
        1.0,
    )


def generate_master_technology_responses(
    contexts: pd.DataFrame,
    replication_seed: int,
    benchmark: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Generate the full alternative-context criterion matrix.

    Returns
    -------
    responses
        One row per context-alternative pair.

    capability_parameters
        Frozen C1-C7 amplitudes.

    deployment_parameters
        Frozen C8-C10 alternative parameters.

    response_audit
        Opportunity values and base noise needed for exact
        formula reconstruction.
    """

    alternative_keys = (
        ordered_alternative_keys(
            benchmark
        )
    )

    criterion_keys = (
        ordered_criterion_keys(
            benchmark
        )
    )

    n_contexts = len(contexts)
    n_alternatives = len(alternative_keys)
    n_criteria = len(criterion_keys)

    if n_alternatives != int(
        benchmark["dimensions"]["alternatives"]
    ):
        raise ValueError(
            "Alternative count is inconsistent "
            "with benchmark dimensions."
        )

    if n_criteria != int(
        benchmark["dimensions"]["criteria"]
    ):
        raise ValueError(
            "Criterion count is inconsistent "
            "with benchmark dimensions."
        )

    capability_parameters = (
        sample_capability_parameters(
            replication_seed=replication_seed,
            benchmark=benchmark,
        )
    )

    deployment_parameters = (
        sample_deployment_parameters(
            replication_seed=replication_seed,
            benchmark=benchmark,
        )
    )

    opportunities = compute_opportunities(
        contexts=contexts,
        benchmark=benchmark,
    )

    base_noise = generate_base_criterion_noise(
        replication_seed=replication_seed,
        n_contexts=n_contexts,
        n_alternatives=n_alternatives,
        n_criteria=n_criteria,
    )

    sigma_x = float(
        benchmark[
            "technology_response"
        ]["criterion_noise"]["sigma_x"]
    )

    gamma = float(
        benchmark[
            "technology_response"
        ]["response_exponent"][
            "reference_value"
        ]
    )

    c9_readiness_coefficient = float(
        benchmark[
            "technical_criteria"
        ]["C9"]["readiness_coefficient"]
    )

    c10_readiness_penalty = float(
        benchmark[
            "technical_criteria"
        ]["C10"]["low_readiness_penalty"]
    )

    capability_lookup = (
        capability_parameters.set_index(
            [
                "alternative_key",
                "criterion",
            ]
        )["amplitude"]
        .to_dict()
    )

    deployment_lookup = (
        deployment_parameters.set_index(
            "alternative_key"
        ).to_dict(
            orient="index"
        )
    )

    opportunity_lookup = (
        opportunities.set_index(
            "context_id"
        )
    )

    response_rows: list[
        dict[str, Any]
    ] = []

    audit_rows: list[
        dict[str, Any]
    ] = []

    for context_index, context_row in (
        contexts.reset_index(
            drop=True
        ).iterrows()
    ):

        context_id = str(
            context_row["context_id"]
        )

        h_R = float(
            context_row["h_R"]
        )

        for alternative_index, alternative_key in (
            enumerate(alternative_keys)
        ):

            alternative = benchmark[
                "alternatives"
            ][alternative_key]

            deployment = deployment_lookup[
                alternative_key
            ]

            readiness_requirement = float(
                deployment[
                    "readiness_requirement"
                ]
            )

            interoperability_baseline = float(
                deployment[
                    "interoperability_baseline"
                ]
            )

            burden_baseline = float(
                deployment[
                    "burden_baseline"
                ]
            )

            row: dict[str, Any] = {
                "context_id": context_id,
                "context_number": int(
                    context_row[
                        "context_number"
                    ]
                ),
                "replication_seed":
                    replication_seed,
                "rho": float(
                    context_row["rho"]
                ),
                "partition": str(
                    context_row["partition"]
                ),
                "alternative_key":
                    alternative_key,
                "alternative_id":
                    alternative["id"],
                "alternative_name":
                    alternative["name"],
            }

            # Keep latent factors in the generated file for
            # auditing. Later model code will explicitly select
            # only the intended criterion features.
            for factor_name in benchmark[
                "context_generator"
            ]["latent_factors"]:
                row[factor_name] = float(
                    context_row[
                        factor_name
                    ]
                )

            audit_row: dict[str, Any] = {
                "context_id": context_id,
                "context_number": int(
                    context_row[
                        "context_number"
                    ]
                ),
                "replication_seed":
                    replication_seed,
                "rho": float(
                    context_row["rho"]
                ),
                "alternative_key":
                    alternative_key,
                "alternative_id":
                    alternative["id"],
            }

            # -----------------------------------------------
            # C1-C7
            # -----------------------------------------------

            for criterion_number in range(
                1,
                8,
            ):

                criterion = (
                    f"C{criterion_number}"
                )

                amplitude = float(
                    capability_lookup[
                        (
                            alternative_key,
                            criterion,
                        )
                    ]
                )

                opportunity = float(
                    opportunity_lookup.loc[
                        context_id,
                        f"opportunity_{criterion}",
                    ]
                )

                base_e = float(
                    base_noise[
                        context_index,
                        alternative_index,
                        criterion_number - 1,
                    ]
                )

                eta = (
                    sigma_x
                    * base_e
                )

                deterministic_component = (
                    amplitude
                    * (
                        opportunity
                        ** gamma
                    )
                )

                raw_value = (
                    deterministic_component
                    + eta
                )

                x_value = float(
                    np.clip(
                        raw_value,
                        0.0,
                        1.0,
                    )
                )

                row[
                    f"x_{criterion}"
                ] = x_value

                row[
                    f"g_{criterion}"
                ] = x_value

                audit_row[
                    f"opportunity_{criterion}"
                ] = opportunity

                audit_row[
                    f"amplitude_{criterion}"
                ] = amplitude

                audit_row[
                    f"base_noise_{criterion}"
                ] = base_e

                audit_row[
                    f"eta_{criterion}"
                ] = eta

                audit_row[
                    f"preclip_{criterion}"
                ] = raw_value

            # -----------------------------------------------
            # C8: one-sided readiness shortfall
            # -----------------------------------------------

            c8_index = 7

            base_e_c8 = float(
                base_noise[
                    context_index,
                    alternative_index,
                    c8_index,
                ]
            )

            eta_c8 = (
                sigma_x
                * base_e_c8
            )

            readiness_shortfall = max(
                0.0,
                readiness_requirement
                - h_R,
            )

            preclip_c8 = (
                1.0
                - readiness_shortfall
                + eta_c8
            )

            x_c8 = float(
                np.clip(
                    preclip_c8,
                    0.0,
                    1.0,
                )
            )

            row["x_C8"] = x_c8
            row["g_C8"] = x_c8

            audit_row[
                "readiness_requirement"
            ] = readiness_requirement

            audit_row[
                "readiness_shortfall"
            ] = readiness_shortfall

            audit_row[
                "base_noise_C8"
            ] = base_e_c8

            audit_row[
                "eta_C8"
            ] = eta_c8

            audit_row[
                "preclip_C8"
            ] = preclip_c8

            # -----------------------------------------------
            # C9: interoperability and scalability
            # -----------------------------------------------

            c9_index = 8

            base_e_c9 = float(
                base_noise[
                    context_index,
                    alternative_index,
                    c9_index,
                ]
            )

            eta_c9 = (
                sigma_x
                * base_e_c9
            )

            preclip_c9 = (
                interoperability_baseline
                + c9_readiness_coefficient
                * h_R
                + eta_c9
            )

            x_c9 = float(
                np.clip(
                    preclip_c9,
                    0.0,
                    1.0,
                )
            )

            row["x_C9"] = x_c9
            row["g_C9"] = x_c9

            audit_row[
                "interoperability_baseline"
            ] = interoperability_baseline

            audit_row[
                "base_noise_C9"
            ] = base_e_c9

            audit_row[
                "eta_C9"
            ] = eta_c9

            audit_row[
                "preclip_C9"
            ] = preclip_c9

            # -----------------------------------------------
            # C10: raw lifecycle burden
            # -----------------------------------------------

            c10_index = 9

            base_e_c10 = float(
                base_noise[
                    context_index,
                    alternative_index,
                    c10_index,
                ]
            )

            eta_c10 = (
                sigma_x
                * base_e_c10
            )

            readiness_penalty = (
                c10_readiness_penalty
                * (1.0 - h_R)
                * readiness_requirement
            )

            preclip_c10 = (
                burden_baseline
                + readiness_penalty
                + eta_c10
            )

            x_c10 = float(
                np.clip(
                    preclip_c10,
                    0.0,
                    1.0,
                )
            )

            g_c10 = (
                1.0
                - x_c10
            )

            row["x_C10"] = x_c10
            row["g_C10"] = g_c10

            audit_row[
                "burden_baseline"
            ] = burden_baseline

            audit_row[
                "readiness_penalty_C10"
            ] = readiness_penalty

            audit_row[
                "base_noise_C10"
            ] = base_e_c10

            audit_row[
                "eta_C10"
            ] = eta_c10

            audit_row[
                "preclip_C10"
            ] = preclip_c10

            response_rows.append(
                row
            )

            audit_rows.append(
                audit_row
            )

    responses = pd.DataFrame(
        response_rows
    )

    response_audit = pd.DataFrame(
        audit_rows
    )

    return (
        responses,
        capability_parameters,
        deployment_parameters,
        response_audit,
    )


# ============================================================
# Nested sample extraction
# ============================================================


def extract_nested_responses(
    responses: pd.DataFrame,
    audit: pd.DataFrame,
    n_contexts: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract responses belonging to contexts 1..N.
    """

    response_subset = (
        responses.loc[
            responses[
                "context_number"
            ] <= n_contexts
        ]
        .copy()
        .reset_index(drop=True)
    )

    audit_subset = (
        audit.loc[
            audit[
                "context_number"
            ] <= n_contexts
        ]
        .copy()
        .reset_index(drop=True)
    )

    return (
        response_subset,
        audit_subset,
    )


# ============================================================
# Diagnostics
# ============================================================


def criterion_summary(
    responses: pd.DataFrame,
) -> pd.DataFrame:
    """Return min/mean/median/max for g_C1..g_C10."""

    rows: list[
        dict[str, float | str]
    ] = []

    for criterion_number in range(
        1,
        11,
    ):
        criterion = f"C{criterion_number}"

        values = responses[
            f"g_{criterion}"
        ]

        rows.append(
            {
                "criterion": criterion,
                "min": float(
                    values.min()
                ),
                "mean": float(
                    values.mean()
                ),
                "median": float(
                    values.median()
                ),
                "max": float(
                    values.max()
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# File output
# ============================================================


def rho_to_filename(
    rho: float,
) -> str:
    """Filesystem-safe rho token."""

    return (
        f"{rho:.2f}"
        .replace(".", "p")
    )


def save_outputs(
    responses: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    deployment_parameters: pd.DataFrame,
    response_audit: pd.DataFrame,
    replication_seed: int,
    n_contexts: int,
    rho: float,
) -> dict[str, Path]:
    """Write generated and audit outputs."""

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

    response_path = (
        GENERATED_DIR
        / (
            f"technology_responses_seed"
            f"{replication_seed}"
            f"_N{n_contexts:04d}"
            f"_rho{rho_token}.csv"
        )
    )

    response_audit_path = (
        AUDIT_DIR
        / (
            f"technology_response_audit_seed"
            f"{replication_seed}"
            f"_N{n_contexts:04d}"
            f"_rho{rho_token}.csv"
        )
    )

    capability_path = (
        AUDIT_DIR
        / (
            f"capability_parameters_seed"
            f"{replication_seed}.csv"
        )
    )

    deployment_path = (
        AUDIT_DIR
        / (
            f"deployment_parameters_seed"
            f"{replication_seed}.csv"
        )
    )

    responses.to_csv(
        response_path,
        index=False,
        float_format="%.12f",
    )

    response_audit.to_csv(
        response_audit_path,
        index=False,
        float_format="%.12f",
    )

    capability_parameters.to_csv(
        capability_path,
        index=False,
        float_format="%.12f",
    )

    deployment_parameters.to_csv(
        deployment_path,
        index=False,
        float_format="%.12f",
    )

    return {
        "responses": response_path,
        "response_audit":
            response_audit_path,
        "capability_parameters":
            capability_path,
        "deployment_parameters":
            deployment_path,
    }


# ============================================================
# CLI
# ============================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate alternative-specific ITS "
            "criterion responses."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--seed-family",
        choices=[
            "development",
            "primary",
        ],
        default="development",
    )

    parser.add_argument(
        "--n",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--rho",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
    )

    return parser.parse_args()


def main() -> None:
    """Command-line entry point."""

    args = parse_arguments()

    benchmark, experiment, seeds = (
        load_project_configuration()
    )

    context_generator.validate_requested_design(
        n_contexts=args.n,
        rho=args.rho,
        experiment=experiment,
    )

    context_generator.validate_seed(
        seed=args.seed,
        seed_family=args.seed_family,
        seeds=seeds,
    )

    contexts_master, _ = (
        context_generator.generate_master_contexts(
            replication_seed=args.seed,
            rho=args.rho,
            benchmark=benchmark,
            experiment=experiment,
            seeds=seeds,
        )
    )

    (
        responses_master,
        capability_parameters,
        deployment_parameters,
        response_audit_master,
    ) = generate_master_technology_responses(
        contexts=contexts_master,
        replication_seed=args.seed,
        benchmark=benchmark,
    )

    responses, response_audit = (
        extract_nested_responses(
            responses=responses_master,
            audit=response_audit_master,
            n_contexts=args.n,
        )
    )

    summary = criterion_summary(
        responses
    )

    n_alternatives = int(
        benchmark[
            "dimensions"
        ]["alternatives"]
    )

    print("=" * 76)
    print(
        "ALTERNATIVE-SPECIFIC ITS PERFORMANCE GENERATOR"
    )
    print("=" * 76)

    print(
        f"Seed family              : "
        f"{args.seed_family}"
    )

    print(
        f"Replication seed         : "
        f"{args.seed}"
    )

    print(
        f"Contexts                 : "
        f"{args.n}"
    )

    print(
        f"Alternatives             : "
        f"{n_alternatives}"
    )

    print(
        f"Alternative-context rows : "
        f"{len(responses)}"
    )

    print(
        f"Configured rho           : "
        f"{args.rho:.3f}"
    )

    print()
    print(
        "Direction-adjusted criterion distributions:"
    )

    for row in summary.itertuples(
        index=False
    ):
        print(
            f"{row.criterion:4s} "
            f"min={row.min:.4f} "
            f"mean={row.mean:.4f} "
            f"median={row.median:.4f} "
            f"max={row.max:.4f}"
        )

    print()
    print(
        "Sampled deployment parameters:"
    )

    print(
        deployment_parameters[
            [
                "alternative_id",
                "alternative_key",
                "readiness_requirement",
                "interoperability_baseline",
                "burden_baseline",
            ]
        ].to_string(
            index=False
        )
    )

    if not args.no_save:

        paths = save_outputs(
            responses=responses,
            capability_parameters=
                capability_parameters,
            deployment_parameters=
                deployment_parameters,
            response_audit=
                response_audit,
            replication_seed=args.seed,
            n_contexts=args.n,
            rho=args.rho,
        )

        print()

        for name, path in paths.items():
            print(
                f"{name:25s}: {path}"
            )

    print()
    print(
        "TECHNOLOGY RESPONSE GENERATION COMPLETED"
    )
    print("=" * 76)


if __name__ == "__main__":
    main()