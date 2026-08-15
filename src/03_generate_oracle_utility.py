from __future__ import annotations

"""
Noise-free oracle utility for the controlled XAI-MCDM benchmark.

Step 3 scope
------------
This module implements ONLY the deterministic oracle utility U_star:

    q(g) = log(1 + zeta*g) / log(1 + zeta)

    U_star = [sum_j alpha_j q_j(g_j)
              + lambda * sum_(j,k) beta_jk q_j(g_j)q_k(g_k)]
             / (1 + lambda)

It deliberately does NOT implement:
- observation noise Y,
- oracle Shapley values,
- XGBoost or TreeSHAP,
- global weight compression,
- MCDM rankings,
- decision winners.

Development leakage rule
------------------------
The CLI defaults to the estimation/calibration pool only (FIT + WEIGHT).
External TEST rows are excluded from development outputs and diagnostics unless
--include-external-test is explicitly supplied. Even when included, the console
summary remains estimation-only so TEST geometry is not used for development
choices.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_PATH = ROOT / "config" / "benchmark.yaml"
DEFAULT_EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"

CRITERIA = tuple(f"C{i}" for i in range(1, 11))
G_COLUMNS = tuple(f"g_{criterion}" for criterion in CRITERIA)
Q_COLUMNS = tuple(f"q_{criterion}" for criterion in CRITERIA)
ESTIMATION_PARTITIONS = ("fit", "weight")
TEST_PARTITION = "test"
NUMERICAL_TOL = 1.0e-12


@dataclass(frozen=True)
class Interaction:
    left: str
    right: str
    beta: float
    label: str


@dataclass(frozen=True)
class OracleSpec:
    zeta: float
    alphas: dict[str, float]
    interactions: tuple[Interaction, ...]


# ============================================================
# Configuration
# ============================================================


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return data


def load_oracle_spec(benchmark: Mapping[str, Any]) -> OracleSpec:
    oracle = benchmark["oracle"]
    transform = oracle["transform"]
    zeta = float(transform["reference_zeta"])

    if transform.get("family") != "normalized_log1p":
        raise ValueError("Oracle transform family must be normalized_log1p.")
    if zeta <= 0.0:
        raise ValueError("Oracle transform zeta must be strictly positive.")

    main_effects = oracle["main_effects"]
    alphas_raw = main_effects["values"]
    alphas = {criterion: float(alphas_raw[criterion]) for criterion in CRITERIA}

    if set(alphas_raw) != set(CRITERIA):
        raise ValueError("Oracle alpha mapping must contain exactly C1..C10.")
    if any(value < 0.0 for value in alphas.values()):
        raise ValueError("Oracle alpha coefficients must be nonnegative.")

    expected_sum = float(main_effects.get("expected_sum", 1.0))
    alpha_sum = float(sum(alphas.values()))
    if not np.isclose(alpha_sum, expected_sum, atol=NUMERICAL_TOL, rtol=0.0):
        raise ValueError(
            f"Oracle alpha coefficients sum to {alpha_sum}, expected {expected_sum}."
        )

    interactions: list[Interaction] = []
    seen_edges: set[tuple[str, str]] = set()

    for item in oracle["interactions"]:
        criteria = tuple(item["criteria"])
        if len(criteria) != 2:
            raise ValueError("Every oracle interaction must contain exactly two criteria.")
        left, right = str(criteria[0]), str(criteria[1])
        if left not in CRITERIA or right not in CRITERIA or left == right:
            raise ValueError(f"Invalid oracle interaction edge: {(left, right)}")

        canonical = tuple(sorted((left, right)))
        if canonical in seen_edges:
            raise ValueError(f"Duplicate oracle interaction edge: {canonical}")
        seen_edges.add(canonical)

        beta = float(item["beta"])
        if beta < 0.0:
            raise ValueError("Oracle interaction coefficients must be nonnegative.")

        interactions.append(
            Interaction(
                left=left,
                right=right,
                beta=beta,
                label=str(item.get("label", f"{left}_{right}")),
            )
        )

    if not interactions:
        raise ValueError("Oracle interaction graph must not be empty.")

    beta_sum = float(sum(edge.beta for edge in interactions))
    if not np.isclose(beta_sum, 1.0, atol=NUMERICAL_TOL, rtol=0.0):
        raise ValueError(
            f"Oracle interaction coefficients sum to {beta_sum}; expected 1.0."
        )

    return OracleSpec(
        zeta=zeta,
        alphas=alphas,
        interactions=tuple(interactions),
    )


def configured_lambdas(experiment: Mapping[str, Any]) -> tuple[float, ...]:
    values = experiment["factors"]["interaction_strength"]["values"]
    lambdas = tuple(float(value) for value in values)
    if any(value < 0.0 for value in lambdas):
        raise ValueError("Configured lambda values must be nonnegative.")
    return lambdas


def validate_lambda(lambda_value: float, experiment: Mapping[str, Any]) -> float:
    value = float(lambda_value)
    allowed = configured_lambdas(experiment)
    if not any(np.isclose(value, candidate, atol=NUMERICAL_TOL, rtol=0.0) for candidate in allowed):
        raise ValueError(f"lambda={value} is not one of the configured levels {allowed}.")
    return value


# ============================================================
# Oracle transformation and utility
# ============================================================


def q_transform(values: np.ndarray | Sequence[float] | float, zeta: float) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError("q-transform input contains non-finite values.")
    if np.any(arr < -NUMERICAL_TOL) or np.any(arr > 1.0 + NUMERICAL_TOL):
        raise ValueError("q-transform input must lie in [0, 1].")
    if zeta <= 0.0:
        raise ValueError("zeta must be strictly positive.")

    clipped = np.clip(arr, 0.0, 1.0)
    return np.log1p(zeta * clipped) / np.log1p(zeta)


def validate_response_schema(responses: pd.DataFrame) -> None:
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "rho",
        "partition",
        "alternative_id",
        "alternative_key",
        *G_COLUMNS,
    }
    missing = sorted(required - set(responses.columns))
    if missing:
        raise ValueError(f"Response frame is missing required columns: {missing}")

    if responses.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate context-alternative rows detected.")

    g = responses.loc[:, G_COLUMNS].to_numpy(dtype=float)
    if not np.all(np.isfinite(g)):
        raise ValueError("Direction-adjusted criterion matrix contains non-finite values.")
    if np.any(g < -NUMERICAL_TOL) or np.any(g > 1.0 + NUMERICAL_TOL):
        raise ValueError("Direction-adjusted criterion matrix must lie in [0, 1].")


def compute_oracle_utility(
    responses: pd.DataFrame,
    *,
    oracle_spec: OracleSpec,
    lambda_value: float,
) -> pd.DataFrame:
    """Return input rows plus q_C1..q_C10 and deterministic oracle components."""
    validate_response_schema(responses)

    lam = float(lambda_value)
    if lam < 0.0:
        raise ValueError("lambda must be nonnegative.")

    result = responses.copy()

    q_matrix = np.column_stack(
        [
            q_transform(result[column].to_numpy(dtype=float), oracle_spec.zeta)
            for column in G_COLUMNS
        ]
    )

    for index, q_column in enumerate(Q_COLUMNS):
        result[q_column] = q_matrix[:, index]

    alpha_vector = np.asarray(
        [oracle_spec.alphas[criterion] for criterion in CRITERIA], dtype=float
    )
    main_component = q_matrix @ alpha_vector

    criterion_index = {criterion: index for index, criterion in enumerate(CRITERIA)}
    interaction_component = np.zeros(len(result), dtype=float)

    for edge in oracle_spec.interactions:
        left = q_matrix[:, criterion_index[edge.left]]
        right = q_matrix[:, criterion_index[edge.right]]
        interaction_component += edge.beta * left * right

    utility = (main_component + lam * interaction_component) / (1.0 + lam)

    if np.any(utility < -NUMERICAL_TOL) or np.any(utility > 1.0 + NUMERICAL_TOL):
        raise AssertionError("Oracle utility escaped the theoretical [0, 1] bounds.")

    result["oracle_main_component"] = main_component
    result["oracle_interaction_component"] = interaction_component
    result["lambda"] = lam
    result["U_star"] = np.clip(utility, 0.0, 1.0)

    return result


# ============================================================
# Development-safe scope and CLI orchestration
# ============================================================


def select_development_scope(
    responses: pd.DataFrame,
    *,
    include_external_test: bool = False,
) -> pd.DataFrame:
    validate_response_schema(responses)

    if include_external_test:
        selected = responses.copy()
    else:
        selected = responses.loc[
            responses["partition"].isin(ESTIMATION_PARTITIONS)
        ].copy()

    if not include_external_test and selected["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leakage into development oracle scope.")

    return selected.reset_index(drop=True)


def estimation_summary(oracle_rows: pd.DataFrame) -> dict[str, float | int]:
    estimation = oracle_rows.loc[
        oracle_rows["partition"].isin(ESTIMATION_PARTITIONS)
    ]
    if estimation.empty:
        raise ValueError("No FIT/WEIGHT rows available for oracle summary.")

    values = estimation["U_star"].to_numpy(dtype=float)
    return {
        "rows": int(len(estimation)),
        "contexts": int(estimation["context_id"].nunique()),
        "mean": float(values.mean()),
        "sd": float(values.std(ddof=0)),
        "min": float(values.min()),
        "median": float(np.median(values)),
        "max": float(values.max()),
    }


def rho_tag(rho: float) -> str:
    return f"{rho:.2f}".replace(".", "p")


def lambda_tag(lambda_value: float) -> str:
    return f"{lambda_value:.2f}".replace(".", "p")


def response_path(data_dir: Path, seed: int, n: int, rho: float) -> Path:
    return data_dir / f"technology_responses_seed{seed}_N{n}_rho{rho_tag(rho)}.csv"


def oracle_output_path(
    output_dir: Path,
    seed: int,
    n: int,
    rho: float,
    lambda_value: float,
    *,
    include_external_test: bool,
) -> Path:
    scope = "all" if include_external_test else "estimation"
    return output_dir / (
        f"oracle_utility_seed{seed}_N{n}_rho{rho_tag(rho)}_"
        f"lambda{lambda_tag(lambda_value)}_{scope}.csv"
    )


def run_condition(
    *,
    seed: int,
    n: int,
    rho: float,
    lambda_value: float,
    benchmark_path: Path = DEFAULT_BENCHMARK_PATH,
    experiment_path: Path = DEFAULT_EXPERIMENT_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_external_test: bool = False,
    save: bool = True,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    benchmark = load_yaml(benchmark_path)
    experiment = load_yaml(experiment_path)
    spec = load_oracle_spec(benchmark)
    lam = validate_lambda(lambda_value, experiment)

    source = response_path(data_dir, seed, n, rho)
    if not source.exists():
        raise FileNotFoundError(f"Technology-response file not found: {source}")

    responses = pd.read_csv(source)
    scope = select_development_scope(
        responses,
        include_external_test=include_external_test,
    )
    oracle_rows = compute_oracle_utility(
        scope,
        oracle_spec=spec,
        lambda_value=lam,
    )
    summary = estimation_summary(oracle_rows)

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = oracle_output_path(
            output_dir,
            seed,
            n,
            rho,
            lam,
            include_external_test=include_external_test,
        )
        oracle_rows.to_csv(target, index=False)
    else:
        target = None

    print("=" * 80)
    print("NOISE-FREE ORACLE UTILITY — STEP 3")
    print("=" * 80)
    print(f"Replication seed          : {seed}")
    print(f"Estimation N             : {n}")
    print(f"rho                      : {rho:.3f}")
    print(f"lambda                   : {lam:.3f}")
    print(f"zeta                     : {spec.zeta:.3f}")
    print(f"Rows transformed         : {len(oracle_rows)}")
    print(f"External TEST included   : {include_external_test}")
    print()
    print("Development-safe FIT + WEIGHT U* summary:")
    print(f"  rows                    : {summary['rows']}")
    print(f"  contexts                : {summary['contexts']}")
    print(f"  mean                    : {summary['mean']:.6f}")
    print(f"  sd                      : {summary['sd']:.6f}")
    print(f"  min                     : {summary['min']:.6f}")
    print(f"  median                  : {summary['median']:.6f}")
    print(f"  max                     : {summary['max']:.6f}")
    print()
    print("Observation noise Y      : NOT GENERATED")
    print("Oracle Shapley           : NOT GENERATED")
    print("XGBoost / SHAP / MCDM    : NOT USED")
    if target is not None:
        print(f"Output                   : {target}")
    print("=" * 80)

    return oracle_rows, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic noise-free oracle utility U_star."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--rho", type=float, required=True)
    parser.add_argument("--lambda", dest="lambda_value", type=float, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--include-external-test",
        action="store_true",
        help=(
            "Transform TEST rows too. Do not use this during development calibration; "
            "the console summary remains FIT+WEIGHT only."
        ),
    )
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_condition(
        seed=args.seed,
        n=args.n,
        rho=args.rho,
        lambda_value=args.lambda_value,
        benchmark_path=args.benchmark,
        experiment_path=args.experiment,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        include_external_test=args.include_external_test,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
