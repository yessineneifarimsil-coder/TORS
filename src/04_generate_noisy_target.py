from __future__ import annotations

"""
Relative observation-noise construction for the controlled XAI-MCDM benchmark.

Step 4 scope
------------
This module implements ONLY:

    s_U = sd(U_star) on the complete 1000-context estimation/calibration
          master pool (6000 alternative-context rows), excluding external TEST

    e_as ~ N(0,1), one deterministic 7200-row master draw per replication seed

    Y = U_star + c * s_U * e_as

The same e_as identity is reused across N, rho, lambda, and c.  External TEST
rows receive Y for later final evaluation but never contribute to s_U or to
any development diagnostic printed by this module.

It deliberately does NOT implement:
- Oracle Shapley values,
- XGBoost or TreeSHAP,
- global weight compression,
- MCDM rankings,
- decision winners.
"""

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"
DEFAULT_SEEDS_PATH = ROOT / "config" / "seeds.yaml"
DEFAULT_BENCHMARK_PATH = ROOT / "config" / "benchmark.yaml"
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"
ORACLE_MODULE_PATH = ROOT / "src" / "03_generate_oracle_utility.py"

ESTIMATION_PARTITIONS = ("fit", "weight")
TEST_PARTITION = "test"
EXPECTED_MASTER_ROWS = 7200
EXPECTED_ESTIMATION_ROWS = 6000
EXPECTED_TEST_ROWS = 1200
EXPECTED_ESTIMATION_CONTEXTS = 1000
EXPECTED_TEST_CONTEXTS = 200
NUMERICAL_TOL = 1.0e-12


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return data


def load_oracle_module():
    spec = importlib.util.spec_from_file_location("oracle_step3", ORACLE_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Step 3 oracle module: {ORACLE_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def configured_noise_levels(experiment: Mapping[str, Any]) -> tuple[float, ...]:
    raw = experiment["factors"]["relative_target_noise"]["values"]
    values = tuple(float(value) for value in raw)
    if any(value < 0.0 for value in values):
        raise ValueError("Configured relative-noise levels must be nonnegative.")
    return values


def validate_noise_level(c: float, experiment: Mapping[str, Any]) -> float:
    value = float(c)
    allowed = configured_noise_levels(experiment)
    if not any(
        np.isclose(value, candidate, atol=NUMERICAL_TOL, rtol=0.0)
        for candidate in allowed
    ):
        raise ValueError(f"c={value} is not one of the configured levels {allowed}.")
    return value


def target_noise_namespace(seeds: Mapping[str, Any]) -> int:
    namespace = int(seeds["target_noise"]["stream_namespace"])
    if namespace <= 0:
        raise ValueError("Target-noise stream namespace must be positive.")
    return namespace


def validate_target_noise_protocol(
    experiment: Mapping[str, Any],
    seeds: Mapping[str, Any],
) -> None:
    target = experiment["target_noise"]
    if target.get("base_distribution") != "standard_normal":
        raise ValueError("Target-noise base distribution must be standard_normal.")

    signal = target["signal_sd"]
    if signal.get("source") != "noise_free_1000_context_estimation_master_pool_for_condition":
        raise ValueError("Unexpected s_U source in experiment.yaml.")
    if signal.get("exclude_external_test") is not True:
        raise ValueError("External TEST must be excluded from s_U estimation.")
    if signal.get("computed_before_sample_size_subsetting") is not True:
        raise ValueError("s_U must be computed before N subsetting.")

    crn = target["common_random_numbers"]
    if crn.get("reuse_standard_normal_noise_draw") is not True:
        raise ValueError("Target-noise CRN reuse must be enabled.")
    if crn.get("seed_registry_key") != "target_noise.stream_namespace":
        raise ValueError("Target-noise seed registry key is not frozen correctly.")
    if int(crn.get("master_alternative_context_rows_per_seed")) != EXPECTED_MASTER_ROWS:
        raise ValueError("Target-noise master row count must be 7200.")
    expected_key = ["context_number", "alternative_id"]
    if list(crn.get("assignment_key", [])) != expected_key:
        raise ValueError("Target-noise assignment key must be context_number, alternative_id.")
    for field in ("reuse_across_N", "reuse_across_rho", "reuse_across_lambda", "reuse_across_c"):
        if crn.get(field) is not True:
            raise ValueError(f"Target-noise CRN flag {field} must be true.")

    _ = target_noise_namespace(seeds)


def master_noise_table(
    identities: pd.DataFrame,
    *,
    replication_seed: int,
    namespace: int,
) -> pd.DataFrame:
    """Assign one deterministic N(0,1) draw to each master row identity.

    Assignment is order-invariant: identities are sorted by
    (context_number, alternative_id), draws are assigned in that order, and the
    keyed table can then be merged back to any row ordering.
    """
    required = {"context_id", "context_number", "alternative_id"}
    missing = sorted(required - set(identities.columns))
    if missing:
        raise ValueError(f"Noise identity table missing columns: {missing}")

    keys = identities.loc[:, ["context_id", "context_number", "alternative_id"]].copy()
    if keys.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate context-alternative identities in noise master.")
    if len(keys) != EXPECTED_MASTER_ROWS:
        raise ValueError(
            f"Target-noise master requires {EXPECTED_MASTER_ROWS} rows, found {len(keys)}."
        )

    ordered = keys.sort_values(
        ["context_number", "alternative_id"],
        kind="stable",
    ).reset_index(drop=True)

    rng = np.random.default_rng(
        np.random.SeedSequence([int(replication_seed), int(namespace)])
    )
    ordered["target_noise_e"] = rng.standard_normal(size=len(ordered))
    return ordered


def compute_signal_sd(oracle_master: pd.DataFrame) -> float:
    estimation = oracle_master.loc[
        oracle_master["partition"].isin(ESTIMATION_PARTITIONS)
    ]
    test = oracle_master.loc[oracle_master["partition"].eq(TEST_PARTITION)]

    if len(oracle_master) != EXPECTED_MASTER_ROWS:
        raise ValueError("Oracle master must contain exactly 7200 rows.")
    if len(estimation) != EXPECTED_ESTIMATION_ROWS:
        raise ValueError("s_U source must contain exactly 6000 FIT+WEIGHT rows.")
    if len(test) != EXPECTED_TEST_ROWS:
        raise ValueError("Expected exactly 1200 external TEST rows.")
    if estimation["context_id"].nunique() != EXPECTED_ESTIMATION_CONTEXTS:
        raise ValueError("s_U source must contain exactly 1000 estimation contexts.")
    if test["context_id"].nunique() != EXPECTED_TEST_CONTEXTS:
        raise ValueError("Expected exactly 200 external TEST contexts.")

    values = estimation["U_star"].to_numpy(dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("U_star contains non-finite values.")

    signal_sd = float(values.std(ddof=0))
    if signal_sd <= 0.0:
        raise ValueError("s_U must be strictly positive.")
    return signal_sd


def add_relative_noise(
    oracle_master: pd.DataFrame,
    *,
    c: float,
    signal_sd: float,
    noise_table: pd.DataFrame,
) -> pd.DataFrame:
    if signal_sd <= 0.0 or not np.isfinite(signal_sd):
        raise ValueError("signal_sd must be finite and strictly positive.")
    if c < 0.0 or not np.isfinite(c):
        raise ValueError("c must be finite and nonnegative.")

    result = oracle_master.merge(
        noise_table[["context_id", "alternative_id", "target_noise_e"]],
        on=["context_id", "alternative_id"],
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if result["target_noise_e"].isna().any():
        raise ValueError("Missing target-noise draw after identity merge.")

    imposed_noise_sd = float(c * signal_sd)
    result["c"] = float(c)
    result["signal_sd"] = float(signal_sd)
    result["imposed_noise_sd"] = imposed_noise_sd
    result["target_noise"] = imposed_noise_sd * result["target_noise_e"].to_numpy(dtype=float)
    result["Y"] = result["U_star"].to_numpy(dtype=float) + result["target_noise"].to_numpy(dtype=float)

    if not np.all(np.isfinite(result["Y"].to_numpy(dtype=float))):
        raise ValueError("Noisy target Y contains non-finite values.")

    # Protocol safeguard: Y is deliberately not clipped and not multiplied by 100.
    return result


def development_noise_summary(noisy_master: pd.DataFrame) -> dict[str, float | int]:
    estimation = noisy_master.loc[
        noisy_master["partition"].isin(ESTIMATION_PARTITIONS)
    ]
    if estimation.empty:
        raise ValueError("No FIT+WEIGHT rows available for noise diagnostics.")
    if estimation["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leaked into development noise diagnostics.")

    u = estimation["U_star"].to_numpy(dtype=float)
    noise = estimation["target_noise"].to_numpy(dtype=float)
    y = estimation["Y"].to_numpy(dtype=float)
    e = estimation["target_noise_e"].to_numpy(dtype=float)

    signal_sd = float(u.std(ddof=0))
    realized_noise_sd = float(noise.std(ddof=0))
    realized_ratio = realized_noise_sd / signal_sd
    realized_snr = (
        (signal_sd * signal_sd) / (realized_noise_sd * realized_noise_sd)
        if realized_noise_sd > 0.0
        else float("inf")
    )

    return {
        "rows": int(len(estimation)),
        "contexts": int(estimation["context_id"].nunique()),
        "signal_sd": signal_sd,
        "imposed_noise_sd": float(estimation["imposed_noise_sd"].iloc[0]),
        "base_e_mean": float(e.mean()),
        "base_e_sd": float(e.std(ddof=0)),
        "realized_noise_mean": float(noise.mean()),
        "realized_noise_sd": realized_noise_sd,
        "realized_noise_to_signal_sd_ratio": float(realized_ratio),
        "realized_snr_variance_ratio": float(realized_snr),
        "y_mean": float(y.mean()),
        "y_sd": float(y.std(ddof=0)),
        "y_min": float(y.min()),
        "y_median": float(np.median(y)),
        "y_max": float(y.max()),
        "y_below_zero_rate": float(np.mean(y < 0.0)),
        "y_above_one_rate": float(np.mean(y > 1.0)),
    }


def rho_tag(rho: float) -> str:
    return f"{rho:.2f}".replace(".", "p")


def lambda_tag(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def c_tag(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def response_path(data_dir: Path, seed: int, rho: float) -> Path:
    return data_dir / f"technology_responses_seed{seed}_N1000_rho{rho_tag(rho)}.csv"


def output_path(
    output_dir: Path,
    *,
    seed: int,
    rho: float,
    lambda_value: float,
    c: float,
) -> Path:
    return output_dir / (
        f"noisy_target_seed{seed}_N1000_rho{rho_tag(rho)}_"
        f"lambda{lambda_tag(lambda_value)}_c{c_tag(c)}_master.csv"
    )


def run_condition(
    *,
    seed: int,
    rho: float,
    lambda_value: float,
    c: float,
    benchmark_path: Path = DEFAULT_BENCHMARK_PATH,
    experiment_path: Path = DEFAULT_EXPERIMENT_PATH,
    seeds_path: Path = DEFAULT_SEEDS_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    save: bool = True,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    experiment = load_yaml(experiment_path)
    seeds = load_yaml(seeds_path)
    benchmark = load_yaml(benchmark_path)
    validate_target_noise_protocol(experiment, seeds)
    noise_level = validate_noise_level(c, experiment)
    namespace = target_noise_namespace(seeds)

    oracle = load_oracle_module()
    oracle_spec = oracle.load_oracle_spec(benchmark)
    lam = oracle.validate_lambda(lambda_value, experiment)

    source = response_path(data_dir, seed, rho)
    if not source.exists():
        raise FileNotFoundError(f"Technology-response master not found: {source}")

    responses = pd.read_csv(source)
    oracle.validate_response_schema(responses)
    if len(responses) != EXPECTED_MASTER_ROWS:
        raise ValueError("Step 4 requires the complete N1000 + fixed TEST master response matrix.")

    oracle_master = oracle.compute_oracle_utility(
        responses,
        oracle_spec=oracle_spec,
        lambda_value=lam,
    )
    signal_sd = compute_signal_sd(oracle_master)

    noise_table = master_noise_table(
        oracle_master,
        replication_seed=seed,
        namespace=namespace,
    )
    noisy_master = add_relative_noise(
        oracle_master,
        c=noise_level,
        signal_sd=signal_sd,
        noise_table=noise_table,
    )
    summary = development_noise_summary(noisy_master)

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_path(
            output_dir,
            seed=seed,
            rho=rho,
            lambda_value=lam,
            c=noise_level,
        )
        noisy_master.to_csv(target, index=False)
    else:
        target = None

    print("=" * 80)
    print("RELATIVE OBSERVATION NOISE — STEP 4")
    print("=" * 80)
    print(f"Replication seed          : {seed}")
    print(f"rho                      : {rho:.3f}")
    print(f"lambda                   : {lam:.3f}")
    print(f"c                        : {noise_level:.3f}")
    print(f"Target-noise namespace   : {namespace}")
    print(f"Master rows              : {len(noisy_master)}")
    print(f"s_U source rows          : {summary['rows']} (FIT + WEIGHT only)")
    print(f"External TEST in s_U     : False")
    print()
    print("Development-safe noise diagnostics (FIT + WEIGHT only):")
    print(f"  signal sd s_U           : {summary['signal_sd']:.6f}")
    print(f"  imposed noise sd        : {summary['imposed_noise_sd']:.6f}")
    print(f"  base e mean             : {summary['base_e_mean']:.6f}")
    print(f"  base e sd               : {summary['base_e_sd']:.6f}")
    print(f"  realized noise mean     : {summary['realized_noise_mean']:.6f}")
    print(f"  realized noise sd       : {summary['realized_noise_sd']:.6f}")
    print(
        "  realized noise/signal  : "
        f"{summary['realized_noise_to_signal_sd_ratio']:.6f}"
    )
    print(
        "  realized SNR (variance): "
        f"{summary['realized_snr_variance_ratio']:.6f}"
    )
    print(f"  Y mean                  : {summary['y_mean']:.6f}")
    print(f"  Y sd                    : {summary['y_sd']:.6f}")
    print(f"  Y min                   : {summary['y_min']:.6f}")
    print(f"  Y median                : {summary['y_median']:.6f}")
    print(f"  Y max                   : {summary['y_max']:.6f}")
    print(f"  Y below 0 rate          : {summary['y_below_zero_rate']:.6f}")
    print(f"  Y above 1 rate          : {summary['y_above_one_rate']:.6f}")
    print()
    print("Y clipping               : NOT APPLIED")
    print("Y x100 scaling           : NOT APPLIED")
    print("Oracle Shapley           : NOT GENERATED")
    print("XGBoost / SHAP / MCDM    : NOT USED")
    if target is not None:
        print(f"Output                   : {target}")
    print("=" * 80)

    return noisy_master, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate signal-relative noisy target Y on the full v2.1 master."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--rho", type=float, required=True)
    parser.add_argument("--lambda", dest="lambda_value", type=float, required=True)
    parser.add_argument("--c", type=float, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT_PATH)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_condition(
        seed=args.seed,
        rho=args.rho,
        lambda_value=args.lambda_value,
        c=args.c,
        benchmark_path=args.benchmark,
        experiment_path=args.experiment,
        seeds_path=args.seeds,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
