from __future__ import annotations

"""
Pre-oracle diagnostics for the controlled ITS technology-response generator.

Scope
-----
This module audits only the generated technology-response matrices from the
development seeds. It deliberately excludes the fixed external TEST pool from
all scientific diagnostics.

It does NOT compute any utility, criterion-weight vector, predictive model,
attribution, MCDM score, or decision winner.

Hard failures are limited to implementation/data invariants:
- required schema,
- expected v2.1 dimensions,
- six alternatives per context,
- no duplicated context-alternative rows,
- g_j in [0, 1],
- exact C10 direction identity g_C10 = 1 - x_C10,
- fixed external TEST exclusion from the audit sample.

Distributional concentration, clipping, saturation, criterion separation, and
Pareto dominance are reported descriptively and are not converted into ad hoc
post-hoc pass/fail thresholds.
"""

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEVELOPMENT_SEEDS = (21001, 21002, 21003, 21004, 21005)
RHOS = (0.0, 0.4, 0.8)
N_ESTIMATION = 1000

EXPECTED_ALTERNATIVES = (
    "ATSC",
    "TSP",
    "TIDM",
    "RMTI-DRG",
    "V2X-CS",
    "DSM",
)

CRITERIA = tuple(f"C{i}" for i in range(1, 11))
G_COLUMNS = tuple(f"g_{criterion}" for criterion in CRITERIA)
X_COLUMNS = tuple(f"x_{criterion}" for criterion in CRITERIA)

ESTIMATION_PARTITIONS = ("fit", "weight")
EXTERNAL_TEST_LABEL = "test"

EXPECTED_CONTEXTS_TOTAL = 1200
EXPECTED_CONTEXTS_ESTIMATION = 1000
EXPECTED_CONTEXTS_TEST = 200
EXPECTED_ROWS_TOTAL = 7200
EXPECTED_ROWS_ESTIMATION = 6000
EXPECTED_ROWS_FIT = 4800
EXPECTED_ROWS_WEIGHT = 1200
EXPECTED_ROWS_TEST = 1200

NEAR_BOUNDARY_EPS = 0.01
NUMERICAL_TOL = 1.0e-12

OUTPUT_FILENAMES = {
    "criterion_summary": "pre_oracle_criterion_summary.csv",
    "criterion_stability": "pre_oracle_criterion_stability.csv",
    "alternative_summary": "pre_oracle_alternative_summary.csv",
    "separation_summary": "pre_oracle_separation_summary.csv",
    "pairwise_dominance": "pre_oracle_pairwise_dominance.csv",
    "nondominance_summary": "pre_oracle_nondominance_summary.csv",
    "special_diagnostics": "pre_oracle_special_diagnostics.csv",
    "manifest": "pre_oracle_manifest.json",
}


def rho_tag(rho: float) -> str:
    return f"{rho:.2f}".replace(".", "p")


def expected_response_path(data_dir: Path, seed: int, rho: float) -> Path:
    return data_dir / (
        f"technology_responses_seed{seed}_N{N_ESTIMATION}_rho{rho_tag(rho)}.csv"
    )


def discover_expected_files(data_dir: Path) -> list[tuple[int, float, Path]]:
    records: list[tuple[int, float, Path]] = []
    missing: list[str] = []

    for seed in DEVELOPMENT_SEEDS:
        for rho in RHOS:
            path = expected_response_path(data_dir, seed, rho)
            if not path.exists():
                missing.append(str(path))
            records.append((seed, rho, path))

    if missing:
        raise FileNotFoundError(
            "Missing expected v2.1 development response files:\n"
            + "\n".join(missing)
        )

    return records


def required_columns() -> set[str]:
    return {
        "context_id",
        "context_number",
        "replication_seed",
        "rho",
        "partition",
        "alternative_key",
        "alternative_id",
        "alternative_name",
        *X_COLUMNS,
        *G_COLUMNS,
    }


def _sort_by_criterion(
    frame: pd.DataFrame,
    *,
    leading_columns: tuple[str, ...] = (),
    categories: tuple[str, ...] = CRITERIA,
) -> pd.DataFrame:
    result = frame.copy()
    result["criterion"] = pd.Categorical(
        result["criterion"], categories=categories, ordered=True
    )
    result = result.sort_values(
        [*leading_columns, "criterion"], kind="stable"
    ).reset_index(drop=True)
    result["criterion"] = result["criterion"].astype(str)
    return result


def _assert_exact_counts(df: pd.DataFrame) -> None:
    if len(df) != EXPECTED_ROWS_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_ROWS_TOTAL} rows, found {len(df)}."
        )

    if df["context_id"].nunique() != EXPECTED_CONTEXTS_TOTAL:
        raise ValueError(
            "Expected exactly "
            f"{EXPECTED_CONTEXTS_TOTAL} unique contexts."
        )

    context_partition = (
        df[["context_id", "partition"]]
        .drop_duplicates()
        .groupby("context_id")["partition"]
        .nunique()
    )
    if not (context_partition == 1).all():
        raise ValueError("At least one context has multiple partition labels.")

    context_counts = (
        df[["context_id", "partition"]]
        .drop_duplicates()["partition"]
        .value_counts()
        .to_dict()
    )
    expected_context_counts = {
        "fit": 800,
        "weight": 200,
        "test": 200,
    }
    if context_counts != expected_context_counts:
        raise ValueError(
            "Unexpected v2.1 context partition counts: "
            f"{context_counts}; expected {expected_context_counts}."
        )

    row_counts = df["partition"].value_counts().to_dict()
    expected_row_counts = {
        "fit": EXPECTED_ROWS_FIT,
        "weight": EXPECTED_ROWS_WEIGHT,
        "test": EXPECTED_ROWS_TEST,
    }
    if row_counts != expected_row_counts:
        raise ValueError(
            "Unexpected v2.1 row partition counts: "
            f"{row_counts}; expected {expected_row_counts}."
        )


def validate_response_frame(
    df: pd.DataFrame,
    *,
    expected_seed: int | None = None,
    expected_rho: float | None = None,
    strict_v21_dimensions: bool = True,
) -> None:
    missing = sorted(required_columns() - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df[list(G_COLUMNS)].isna().any().any():
        raise ValueError("Direction-adjusted criterion matrix contains NaN.")

    duplicated = df.duplicated(["context_id", "alternative_id"])
    if duplicated.any():
        raise ValueError("Duplicated context-alternative rows detected.")

    alternatives_per_context = df.groupby("context_id")["alternative_id"].nunique()
    if not (alternatives_per_context == 6).all():
        raise ValueError("Every context must contain exactly six alternatives.")

    observed_keys = tuple(sorted(df["alternative_key"].unique().tolist()))
    expected_keys = tuple(sorted(EXPECTED_ALTERNATIVES))
    if observed_keys != expected_keys:
        raise ValueError(
            f"Unexpected alternative set: {observed_keys}; expected {expected_keys}."
        )

    g = df.loc[:, G_COLUMNS].to_numpy(dtype=float)
    if np.any(g < -NUMERICAL_TOL) or np.any(g > 1.0 + NUMERICAL_TOL):
        raise ValueError("At least one direction-adjusted criterion lies outside [0, 1].")

    c10_error = np.abs(
        df["g_C10"].to_numpy(dtype=float)
        - (1.0 - df["x_C10"].to_numpy(dtype=float))
    )
    if np.max(c10_error, initial=0.0) > NUMERICAL_TOL:
        raise ValueError("C10 direction identity g_C10 = 1 - x_C10 failed.")

    if expected_seed is not None:
        observed_seeds = set(df["replication_seed"].astype(int).unique().tolist())
        if observed_seeds != {int(expected_seed)}:
            raise ValueError(
                f"Unexpected replication seed(s): {sorted(observed_seeds)}."
            )

    if expected_rho is not None:
        observed_rhos = df["rho"].astype(float).unique()
        if len(observed_rhos) != 1 or not np.isclose(
            observed_rhos[0], expected_rho, atol=NUMERICAL_TOL, rtol=0.0
        ):
            raise ValueError(
                f"Unexpected rho values {observed_rhos}; expected {expected_rho}."
            )

    if strict_v21_dimensions:
        _assert_exact_counts(df)


def estimation_rows(df: pd.DataFrame) -> pd.DataFrame:
    audit = df.loc[df["partition"].isin(ESTIMATION_PARTITIONS)].copy()
    if audit["partition"].eq(EXTERNAL_TEST_LABEL).any():
        raise AssertionError("External TEST leakage into pre-oracle audit.")

    if len(audit) != EXPECTED_ROWS_ESTIMATION:
        raise ValueError(
            f"Expected {EXPECTED_ROWS_ESTIMATION} FIT+WEIGHT rows, found {len(audit)}."
        )
    if audit["context_id"].nunique() != EXPECTED_CONTEXTS_ESTIMATION:
        raise ValueError(
            "Expected exactly "
            f"{EXPECTED_CONTEXTS_ESTIMATION} FIT+WEIGHT contexts."
        )

    return audit.reset_index(drop=True)


def criterion_summary(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []

    quantiles = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)

    for criterion, column in zip(CRITERIA, G_COLUMNS):
        values = audit[column].to_numpy(dtype=float)
        q = np.quantile(values, quantiles)

        records.append(
            {
                "seed": seed,
                "rho": rho,
                "criterion": criterion,
                "n_rows": len(values),
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=0)),
                "variance": float(values.var(ddof=0)),
                "min": float(values.min()),
                "q01": float(q[0]),
                "q05": float(q[1]),
                "q25": float(q[2]),
                "median": float(q[3]),
                "q75": float(q[4]),
                "q95": float(q[5]),
                "q99": float(q[6]),
                "max": float(values.max()),
                "exact_zero_rate": float(np.mean(values == 0.0)),
                "exact_one_rate": float(np.mean(values == 1.0)),
                "near_zero_rate_eps_0p01": float(
                    np.mean(values <= NEAR_BOUNDARY_EPS)
                ),
                "near_one_rate_eps_0p01": float(
                    np.mean(values >= 1.0 - NEAR_BOUNDARY_EPS)
                ),
                "unique_values": int(np.unique(values).size),
            }
        )

    return _sort_by_criterion(
        pd.DataFrame.from_records(records),
        leading_columns=("seed", "rho"),
    )


def alternative_summary(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []

    for alternative in EXPECTED_ALTERNATIVES:
        subset = audit.loc[audit["alternative_key"].eq(alternative)]
        if subset["context_id"].nunique() != EXPECTED_CONTEXTS_ESTIMATION:
            raise ValueError(
                f"Alternative {alternative} does not cover all estimation contexts."
            )

        for criterion, column in zip(CRITERIA, G_COLUMNS):
            values = subset[column].to_numpy(dtype=float)
            records.append(
                {
                    "seed": seed,
                    "rho": rho,
                    "alternative": alternative,
                    "criterion": criterion,
                    "mean": float(values.mean()),
                    "sd": float(values.std(ddof=0)),
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "exact_zero_rate": float(np.mean(values == 0.0)),
                    "exact_one_rate": float(np.mean(values == 1.0)),
                }
            )

    result = _sort_by_criterion(
        pd.DataFrame.from_records(records),
        leading_columns=("seed", "rho"),
    )
    return result.sort_values(
        ["seed", "rho", "criterion", "alternative"], kind="stable"
    ).reset_index(drop=True)


def separation_summary(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []

    for criterion, column in zip(CRITERIA, G_COLUMNS):
        alt_means = (
            audit.groupby("alternative_key", sort=True)[column]
            .mean()
            .reindex(EXPECTED_ALTERNATIVES)
        )
        alt_sds = (
            audit.groupby("alternative_key", sort=True)[column]
            .std(ddof=0)
            .reindex(EXPECTED_ALTERNATIVES)
        )

        context_ranges = (
            audit.pivot(index="context_id", columns="alternative_key", values=column)
            .reindex(columns=EXPECTED_ALTERNATIVES)
            .max(axis=1)
            - audit.pivot(
                index="context_id", columns="alternative_key", values=column
            )
            .reindex(columns=EXPECTED_ALTERNATIVES)
            .min(axis=1)
        )

        overall_sd = float(audit[column].std(ddof=0))
        mean_range = float(alt_means.max() - alt_means.min())

        records.append(
            {
                "seed": seed,
                "rho": rho,
                "criterion": criterion,
                "between_alternative_mean_range": mean_range,
                "between_alternative_sd_of_means": float(
                    alt_means.to_numpy(dtype=float).std(ddof=0)
                ),
                "mean_within_alternative_sd": float(alt_sds.mean()),
                "overall_sd": overall_sd,
                "mean_range_over_overall_sd": (
                    mean_range / overall_sd if overall_sd > 0.0 else np.nan
                ),
                "mean_context_alternative_range": float(context_ranges.mean()),
                "median_context_alternative_range": float(context_ranges.median()),
                "q95_context_alternative_range": float(
                    context_ranges.quantile(0.95)
                ),
            }
        )

    return _sort_by_criterion(
        pd.DataFrame.from_records(records),
        leading_columns=("seed", "rho"),
    )


def pairwise_dominance(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    matrices: dict[str, np.ndarray] = {}

    for alternative in EXPECTED_ALTERNATIVES:
        subset = (
            audit.loc[audit["alternative_key"].eq(alternative)]
            .sort_values("context_id", kind="stable")
            .set_index("context_id")
        )
        matrices[alternative] = subset.loc[:, G_COLUMNS].to_numpy(dtype=float)

    reference_contexts = (
        audit.loc[audit["alternative_key"].eq(EXPECTED_ALTERNATIVES[0]), "context_id"]
        .sort_values(kind="stable")
        .tolist()
    )
    n_contexts = len(reference_contexts)
    if n_contexts <= 0:
        raise ValueError("Dominance calculation requires at least one context.")

    if any(matrix.shape[0] != n_contexts for matrix in matrices.values()):
        raise ValueError("Alternatives do not share the same context support.")

    records: list[dict[str, float | int | str]] = []

    for dominator in EXPECTED_ALTERNATIVES:
        a = matrices[dominator]
        for dominated in EXPECTED_ALTERNATIVES:
            if dominator == dominated:
                continue

            b = matrices[dominated]
            weakly_better = np.all(a >= b - NUMERICAL_TOL, axis=1)
            strictly_better = np.any(a > b + NUMERICAL_TOL, axis=1)
            dominates = weakly_better & strictly_better

            records.append(
                {
                    "seed": seed,
                    "rho": rho,
                    "dominator": dominator,
                    "dominated": dominated,
                    "n_contexts": n_contexts,
                    "dominance_count": int(dominates.sum()),
                    "dominance_rate": float(dominates.mean()),
                }
            )

    result = pd.DataFrame.from_records(records).sort_values(
        ["seed", "rho", "dominator", "dominated"], kind="stable"
    ).reset_index(drop=True)

    if len(result) != 30:
        raise AssertionError("Expected exactly 30 ordered non-self alternative pairs.")

    return result


def nondominance_summary(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    context_ids = sorted(audit["context_id"].unique().tolist())
    nondominated_counts = {alt: 0 for alt in EXPECTED_ALTERNATIVES}
    number_nondominated_per_context: list[int] = []

    by_context = audit.set_index(["context_id", "alternative_key"])

    for context_id in context_ids:
        matrix = np.vstack(
            [
                by_context.loc[(context_id, alt), G_COLUMNS].to_numpy(dtype=float)
                for alt in EXPECTED_ALTERNATIVES
            ]
        )

        is_nondominated = np.ones(len(EXPECTED_ALTERNATIVES), dtype=bool)

        for target_idx in range(len(EXPECTED_ALTERNATIVES)):
            target = matrix[target_idx]
            for challenger_idx in range(len(EXPECTED_ALTERNATIVES)):
                if challenger_idx == target_idx:
                    continue
                challenger = matrix[challenger_idx]
                if (
                    np.all(challenger >= target - NUMERICAL_TOL)
                    and np.any(challenger > target + NUMERICAL_TOL)
                ):
                    is_nondominated[target_idx] = False
                    break

        n_nd = int(is_nondominated.sum())
        number_nondominated_per_context.append(n_nd)
        for idx, alt in enumerate(EXPECTED_ALTERNATIVES):
            if is_nondominated[idx]:
                nondominated_counts[alt] += 1

    records = [
        {
            "seed": seed,
            "rho": rho,
            "alternative": alt,
            "n_contexts": len(context_ids),
            "nondominated_count": nondominated_counts[alt],
            "nondominated_rate": nondominated_counts[alt] / len(context_ids),
            "mean_number_nondominated_alternatives_per_context": float(
                np.mean(number_nondominated_per_context)
            ),
            "median_number_nondominated_alternatives_per_context": float(
                np.median(number_nondominated_per_context)
            ),
            "min_number_nondominated_alternatives_per_context": int(
                np.min(number_nondominated_per_context)
            ),
            "max_number_nondominated_alternatives_per_context": int(
                np.max(number_nondominated_per_context)
            ),
        }
        for alt in EXPECTED_ALTERNATIVES
    ]

    return pd.DataFrame.from_records(records).sort_values(
        ["seed", "rho", "alternative"], kind="stable"
    ).reset_index(drop=True)


def special_diagnostics(
    audit: pd.DataFrame,
    *,
    seed: int,
    rho: float,
) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []

    for criterion in ("C8", "C9", "C10"):
        column = f"g_{criterion}"
        values = audit[column].to_numpy(dtype=float)
        records.append(
            {
                "seed": seed,
                "rho": rho,
                "criterion": criterion,
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=0)),
                "q05": float(np.quantile(values, 0.05)),
                "median": float(np.quantile(values, 0.50)),
                "q95": float(np.quantile(values, 0.95)),
                "q95_minus_q05": float(
                    np.quantile(values, 0.95) - np.quantile(values, 0.05)
                ),
                "exact_zero_rate": float(np.mean(values == 0.0)),
                "exact_one_rate": float(np.mean(values == 1.0)),
                "near_zero_rate_eps_0p01": float(
                    np.mean(values <= NEAR_BOUNDARY_EPS)
                ),
                "near_one_rate_eps_0p01": float(
                    np.mean(values >= 1.0 - NEAR_BOUNDARY_EPS)
                ),
            }
        )

    return _sort_by_criterion(
        pd.DataFrame.from_records(records),
        leading_columns=("seed", "rho"),
        categories=("C8", "C9", "C10"),
    )


def criterion_stability(criterion_frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat(list(criterion_frames), ignore_index=True)
    metrics = [
        "mean",
        "sd",
        "exact_zero_rate",
        "exact_one_rate",
        "near_zero_rate_eps_0p01",
        "near_one_rate_eps_0p01",
    ]

    records: list[dict[str, float | str]] = []
    for criterion in CRITERIA:
        subset = combined.loc[combined["criterion"].eq(criterion)]
        record: dict[str, float | str] = {"criterion": criterion}

        for metric in metrics:
            values = subset[metric].to_numpy(dtype=float)
            record[f"{metric}_min_across_cells"] = float(values.min())
            record[f"{metric}_median_across_cells"] = float(np.median(values))
            record[f"{metric}_max_across_cells"] = float(values.max())

        records.append(record)

    return _sort_by_criterion(pd.DataFrame.from_records(records))


def save_outputs(
    output_dir: Path,
    *,
    criterion: pd.DataFrame,
    stability: pd.DataFrame,
    alternative: pd.DataFrame,
    separation: pd.DataFrame,
    dominance: pd.DataFrame,
    nondominance: pd.DataFrame,
    special: pd.DataFrame,
    manifest: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = {
        "criterion_summary": criterion,
        "criterion_stability": stability,
        "alternative_summary": alternative,
        "separation_summary": separation,
        "pairwise_dominance": dominance,
        "nondominance_summary": nondominance,
        "special_diagnostics": special,
    }

    for key, frame in frames.items():
        frame.to_csv(output_dir / OUTPUT_FILENAMES[key], index=False)

    with (output_dir / OUTPUT_FILENAMES["manifest"]).open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def print_report(
    *,
    stability: pd.DataFrame,
    dominance: pd.DataFrame,
    nondominance: pd.DataFrame,
    special: pd.DataFrame,
) -> None:
    print("=" * 80)
    print("PRE-ORACLE TECHNOLOGY-RESPONSE AUDIT V2.1")
    print("=" * 80)
    print("Development cells        : 15")
    print("Audit rows per cell      : 6000 (FIT + WEIGHT only)")
    print("External TEST rows/cell  : 1200 (excluded)")
    print("Oracle / alpha / SHAP    : NOT USED")
    print("MCDM / decision winner   : NOT USED")
    print()

    columns = [
        "criterion",
        "mean_min_across_cells",
        "mean_max_across_cells",
        "sd_min_across_cells",
        "sd_max_across_cells",
        "exact_zero_rate_max_across_cells",
        "exact_one_rate_max_across_cells",
    ]
    print("Criterion stability across 5 development seeds x 3 rho levels:")
    print(stability[columns].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print()

    top_dom = dominance.sort_values(
        ["dominance_rate", "seed", "rho"],
        ascending=[False, True, True],
        kind="stable",
    ).head(10)
    print("Largest context-level ordered-pair Pareto dominance rates:")
    print(
        top_dom[
            ["seed", "rho", "dominator", "dominated", "dominance_rate"]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    print()

    special_ranges = (
        special.groupby("criterion", sort=False)
        .agg(
            mean_min=("mean", "min"),
            mean_max=("mean", "max"),
            sd_min=("sd", "min"),
            sd_max=("sd", "max"),
            exact_one_rate_min=("exact_one_rate", "min"),
            exact_one_rate_max=("exact_one_rate", "max"),
        )
        .reindex(["C8", "C9", "C10"])
        .reset_index()
    )
    print("C8 / C9 / C10 focused diagnostics:")
    print(
        special_ranges.to_string(
            index=False, float_format=lambda x: f"{x:.4f}"
        )
    )
    print()

    nd_context = (
        nondominance[
            [
                "seed",
                "rho",
                "mean_number_nondominated_alternatives_per_context",
            ]
        ]
        .drop_duplicates()
        .sort_values(["seed", "rho"], kind="stable")
    )
    print(
        "Mean number of Pareto-nondominated alternatives per context "
        "(cell range): "
        f"{nd_context['mean_number_nondominated_alternatives_per_context'].min():.4f}"
        " to "
        f"{nd_context['mean_number_nondominated_alternatives_per_context'].max():.4f}"
    )

    any_constant = bool(
        (stability["sd_min_across_cells"] <= NUMERICAL_TOL).any()
    )
    any_universal_pair_dominance = bool(
        (dominance["dominance_rate"] >= 1.0 - NUMERICAL_TOL).any()
    )

    print()
    print("Scientific degeneracy indicators (descriptive):")
    print(f"Any criterion constant in any cell : {any_constant}")
    print(
        "Any ordered pair universally dominates in a cell : "
        f"{any_universal_pair_dominance}"
    )
    print()
    print("No post-hoc winner or weighting-method tuning is performed here.")
    print("=" * 80)


def run_audit(data_dir: Path, output_dir: Path, *, save: bool = True) -> dict[str, pd.DataFrame]:
    criterion_frames: list[pd.DataFrame] = []
    alternative_frames: list[pd.DataFrame] = []
    separation_frames: list[pd.DataFrame] = []
    dominance_frames: list[pd.DataFrame] = []
    nondominance_frames: list[pd.DataFrame] = []
    special_frames: list[pd.DataFrame] = []

    manifest_cells: list[dict[str, object]] = []

    for seed, rho, path in discover_expected_files(data_dir):
        df = pd.read_csv(path)
        validate_response_frame(
            df,
            expected_seed=seed,
            expected_rho=rho,
            strict_v21_dimensions=True,
        )
        audit = estimation_rows(df)

        criterion_frames.append(criterion_summary(audit, seed=seed, rho=rho))
        alternative_frames.append(alternative_summary(audit, seed=seed, rho=rho))
        separation_frames.append(separation_summary(audit, seed=seed, rho=rho))
        dominance_frames.append(pairwise_dominance(audit, seed=seed, rho=rho))
        nondominance_frames.append(nondominance_summary(audit, seed=seed, rho=rho))
        special_frames.append(special_diagnostics(audit, seed=seed, rho=rho))

        manifest_cells.append(
            {
                "seed": seed,
                "rho": rho,
                "source_file": str(path),
                "total_rows": len(df),
                "audit_rows_fit_plus_weight": len(audit),
                "excluded_external_test_rows": int(
                    df["partition"].eq("test").sum()
                ),
            }
        )

    criterion = pd.concat(criterion_frames, ignore_index=True)
    stability = criterion_stability(criterion_frames)
    alternative = pd.concat(alternative_frames, ignore_index=True)
    separation = pd.concat(separation_frames, ignore_index=True)
    dominance = pd.concat(dominance_frames, ignore_index=True)
    nondominance = pd.concat(nondominance_frames, ignore_index=True)
    special = pd.concat(special_frames, ignore_index=True)

    manifest = {
        "protocol": "v2.1",
        "scope": "pre_oracle_technology_response_audit",
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "rho_levels": list(RHOS),
        "n_estimation": N_ESTIMATION,
        "external_test_contexts": EXPECTED_CONTEXTS_TEST,
        "external_test_used_in_scientific_diagnostics": False,
        "near_boundary_epsilon": NEAR_BOUNDARY_EPS,
        "hard_failures_limited_to_data_invariants": True,
        "scientific_concentration_and_dominance_thresholds": None,
        "cells": manifest_cells,
    }

    if save:
        save_outputs(
            output_dir,
            criterion=criterion,
            stability=stability,
            alternative=alternative,
            separation=separation,
            dominance=dominance,
            nondominance=nondominance,
            special=special,
            manifest=manifest,
        )

    print_report(
        stability=stability,
        dominance=dominance,
        nondominance=nondominance,
        special=special,
    )

    return {
        "criterion_summary": criterion,
        "criterion_stability": stability,
        "alternative_summary": alternative,
        "separation_summary": separation,
        "pairwise_dominance": dominance,
        "nondominance_summary": nondominance,
        "special_diagnostics": special,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the v2.1 pre-oracle technology-response diagnostics."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/generated"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/diagnostics"),
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Run diagnostics without writing result files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_audit(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
