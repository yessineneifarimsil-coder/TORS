from __future__ import annotations

"""
v2.2 D2.7 positive-control calibration.

This module implements the protocol preregistered in
docs/v2_2_design_specification.md before execution.

IMPORTANT
---------
- This is a measurement-calibration device, not a candidate generator.
- Only development/design seeds 21001..21005 are used.
- External TEST, structural-validation seeds, and primary seeds are excluded.
- A full calibration run refuses to execute from a dirty Git working tree.
"""

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[1]

DESIGN_SEEDS = (21001, 21002, 21003, 21004, 21005)
RHO = 0.4
LAMBDA_VALUE = 0.5
DELTA = 0.05
POSITIVE_FLOOR = 1.0e-12
EPS = 1.0e-12
REGRET_NUM_THRESHOLD = 1.0e-12

C1_C7 = tuple(f"C{i}" for i in range(1, 8))
C8_C10 = ("C8", "C9", "C10")
CONTRAST = np.asarray(
    [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0],
    dtype=float,
)


def load_numbered_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return data


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = git_output("status", "--porcelain")
    if status:
        raise RuntimeError(
            "D2.7 REFUSES TO RUN FROM A DIRTY WORKING TREE.\n"
            "Commit or restore all changes before calibration.\n"
            f"Current status:\n{status}"
        )

    commit = git_output("rev-parse", "HEAD")
    branch = git_output("rev-parse", "--abbrev-ref", "HEAD")
    return commit, branch


def ordered_alternatives(
    benchmark: dict[str, Any],
) -> list[tuple[str, str]]:
    items = [
        (key, str(value["id"]))
        for key, value in benchmark["alternatives"].items()
    ]
    return sorted(items, key=lambda x: x[1])


def rotation_coefficients(
    alternative_ids: list[str],
    rotation: int,
) -> dict[str, float]:
    if len(alternative_ids) != 6:
        raise ValueError("D2.7 requires exactly six alternatives.")
    if rotation not in range(6):
        raise ValueError("rotation must be in {0,1,2,3,4,5}")

    return {
        alt_id: float(CONTRAST[(i + rotation) % 6])
        for i, alt_id in enumerate(alternative_ids)
    }


def quantile_linear(
    values: np.ndarray,
    q: float,
) -> float:
    return float(
        np.quantile(
            np.asarray(values, dtype=float),
            q,
            method="linear",
        )
    )


def iqr_linear(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    return (
        quantile_linear(arr, 0.75)
        - quantile_linear(arr, 0.25)
    )


def active_alternative_ids(
    benchmark: dict[str, Any],
    criterion: str,
) -> list[str]:
    result = []
    for _, alternative in benchmark["alternatives"].items():
        if criterion in C1_C7:
            if str(alternative["capability"][criterion]) == "0":
                continue
        result.append(str(alternative["id"]))
    return sorted(result)


def capability_lookup(
    capability_parameters: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    required = {
        "alternative_id",
        "criterion",
        "amplitude",
    }
    missing = required - set(capability_parameters.columns)
    if missing:
        raise ValueError(
            f"Capability table missing columns: {sorted(missing)}"
        )

    lookup: dict[tuple[str, str], float] = {}
    for row in capability_parameters.itertuples(index=False):
        lookup[
            (str(row.alternative_id), str(row.criterion))
        ] = float(row.amplitude)
    return lookup


def opportunity_map(
    opportunities: pd.DataFrame,
    criterion: str,
) -> dict[int, float]:
    return {
        int(row.context_number):
            float(getattr(row, f"opportunity_{criterion}"))
        for row in opportunities.itertuples(index=False)
    }


def build_positive_control(
    baseline: pd.DataFrame,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    rotation: int,
) -> pd.DataFrame:
    """
    Apply the frozen D2.7 positive control to C1-C7 only.
    """

    pc = baseline.copy()
    alt_ids = [
        alt_id
        for _, alt_id in ordered_alternatives(benchmark)
    ]
    coeff = rotation_coefficients(
        alt_ids,
        rotation,
    )
    theta = capability_lookup(
        capability_parameters
    )

    for criterion in C1_C7:
        omap = opportunity_map(
            opportunities,
            criterion,
        )

        for _, alternative in benchmark[
            "alternatives"
        ].items():
            alt_id = str(alternative["id"])
            capability_class = str(
                alternative["capability"][criterion]
            )
            row_mask = (
                pc["alternative_id"].astype(str)
                == alt_id
            )

            if capability_class == "0":
                values = np.zeros(
                    int(row_mask.sum()),
                    dtype=float,
                )
            else:
                key = (alt_id, criterion)
                theta_value = float(theta[key])

                context_numbers = (
                    pc.loc[row_mask, "context_number"]
                    .to_numpy(dtype=int)
                )
                o = np.asarray(
                    [omap[int(n)] for n in context_numbers],
                    dtype=float,
                )

                effective_amplitude = (
                    theta_value
                    + DELTA
                    * coeff[alt_id]
                    * (2.0 * o - 1.0)
                )

                if np.any(
                    effective_amplitude < -EPS
                ):
                    raise AssertionError(
                        "Positive control crossed below zero amplitude."
                    )
                if np.any(
                    effective_amplitude > 0.45 + EPS
                ):
                    raise AssertionError(
                        "Positive control exceeded 0.45 amplitude."
                    )

                values = (
                    effective_amplitude * o
                )

                if np.any(values < -EPS):
                    raise AssertionError(
                        "Positive-control response below zero."
                    )
                if np.any(values > 0.45 + EPS):
                    raise AssertionError(
                        "Positive-control response exceeded 0.45."
                    )

            pc.loc[row_mask, f"g_{criterion}"] = values

            x_column = f"x_{criterion}"
            if x_column in pc.columns:
                pc.loc[row_mask, x_column] = values

    return pc


def matrix_for(
    frame: pd.DataFrame,
    criterion: str,
) -> pd.DataFrame:
    return (
        frame.pivot(
            index="context_number",
            columns="alternative_id",
            values=f"g_{criterion}",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )


def rank_one_energy(
    values: np.ndarray,
) -> float:
    singular = np.linalg.svd(
        np.asarray(values, dtype=float),
        compute_uv=False,
        full_matrices=False,
    )
    return float(
        1.0
        - singular[0] ** 2
        / (
            np.sum(singular ** 2)
            + EPS
        )
    )


def pairwise_lrv(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    criterion: str,
) -> list[dict[str, Any]]:
    pivot = matrix_for(
        frame,
        criterion,
    )

    ids = [
        alt_id
        for alt_id in active_alternative_ids(
            benchmark,
            criterion,
        )
        if alt_id in pivot.columns
    ]

    rows: list[dict[str, Any]] = []

    for a, b in combinations(ids, 2):
        xa = pivot[a].to_numpy(dtype=float)
        xb = pivot[b].to_numpy(dtype=float)

        mask = (
            (xa > POSITIVE_FLOOR)
            & (xb > POSITIVE_FLOOR)
        )

        if int(mask.sum()) < 2:
            raise RuntimeError(
                f"Insufficient positive support for "
                f"{criterion} pair {a}-{b}."
            )

        log_ratio = np.log(
            xa[mask] / xb[mask]
        )

        rows.append(
            {
                "criterion": criterion,
                "alternative_a": a,
                "alternative_b": b,
                "contexts_used": int(mask.sum()),
                "lrv": float(
                    np.std(
                        log_ratio,
                        ddof=0,
                    )
                ),
            }
        )

    if not rows:
        raise RuntimeError(
            f"No active pairs for {criterion}"
        )

    return rows


def normalize_rows(
    values: np.ndarray,
    method: str,
) -> np.ndarray:
    x = np.asarray(values, dtype=float)

    if method == "vector":
        denom = np.sqrt(
            np.sum(
                x * x,
                axis=1,
                keepdims=True,
            )
        )
        return x / (denom + EPS)

    if method == "sum":
        denom = np.sum(
            x,
            axis=1,
            keepdims=True,
        )
        return x / (denom + EPS)

    if method == "max":
        denom = np.max(
            x,
            axis=1,
            keepdims=True,
        )
        return x / (denom + EPS)

    if method == "minmax":
        lo = np.min(
            x,
            axis=1,
            keepdims=True,
        )
        hi = np.max(
            x,
            axis=1,
            keepdims=True,
        )
        return (
            (x - lo)
            / (hi - lo + EPS)
        )

    raise ValueError(method)


def nsv(
    values: np.ndarray,
    method: str,
) -> float:
    normalized = normalize_rows(
        values,
        method,
    )
    mean_vector = normalized.mean(
        axis=0,
        keepdims=True,
    )
    return float(
        np.sqrt(
            np.mean(
                np.sum(
                    (
                        normalized
                        - mean_vector
                    ) ** 2,
                    axis=1,
                )
            )
        )
    )


def layer_a_metrics(
    pc: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
    rotation: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    summary_rows = []
    pair_rows = []

    for criterion in C1_C7:
        pivot = matrix_for(
            pc,
            criterion,
        )
        values = pivot.to_numpy(dtype=float)

        pair_metrics = pairwise_lrv(
            pc,
            benchmark,
            criterion,
        )
        lrv_values = np.asarray(
            [x["lrv"] for x in pair_metrics],
            dtype=float,
        )

        for row in pair_metrics:
            pair_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    **row,
                }
            )

        summary_rows.append(
            {
                "seed": seed,
                "rotation": rotation,
                "criterion": criterion,
                "rank_one_energy":
                    rank_one_energy(values),
                "lrv50":
                    quantile_linear(
                        lrv_values,
                        0.5,
                    ),
                "lrv_max":
                    float(lrv_values.max()),
                "nsv_vector":
                    nsv(values, "vector"),
                "nsv_sum":
                    nsv(values, "sum"),
                "nsv_max":
                    nsv(values, "max"),
                "nsv_minmax":
                    nsv(values, "minmax"),
            }
        )

    return summary_rows, pair_rows


def reflected_contexts_for_factor(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    factor_name: str,
    rho: float,
) -> pd.DataFrame:
    result = contexts.copy()

    z_shared = audit[
        "z_shared"
    ].to_numpy(dtype=float)

    z_idio = audit[
        f"z_{factor_name}"
    ].to_numpy(dtype=float)

    latent_reflected = (
        np.sqrt(rho) * z_shared
        - np.sqrt(1.0 - rho) * z_idio
    )

    result[factor_name] = norm.cdf(
        latent_reflected
    )

    return result


def pc_matrix_for_opportunity(
    criterion: str,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    rotation: int,
) -> tuple[list[int], list[str], np.ndarray]:
    alt_ids = [
        alt_id
        for _, alt_id in ordered_alternatives(
            benchmark
        )
    ]
    coeff = rotation_coefficients(
        alt_ids,
        rotation,
    )
    theta = capability_lookup(
        capability_parameters
    )

    opp = (
        opportunities[
            [
                "context_number",
                f"opportunity_{criterion}",
            ]
        ]
        .sort_values("context_number")
    )

    context_numbers = opp[
        "context_number"
    ].to_numpy(dtype=int).tolist()

    o = opp[
        f"opportunity_{criterion}"
    ].to_numpy(dtype=float)

    columns = []
    values = []

    by_id = {
        str(value["id"]): value
        for value in benchmark[
            "alternatives"
        ].values()
    }

    for alt_id in alt_ids:
        alternative = by_id[alt_id]
        capability_class = str(
            alternative["capability"][criterion]
        )

        if capability_class == "0":
            g = np.zeros_like(o)
        else:
            theta_value = theta[
                (alt_id, criterion)
            ]
            amplitude = (
                theta_value
                + DELTA
                * coeff[alt_id]
                * (2.0 * o - 1.0)
            )
            g = amplitude * o

        columns.append(alt_id)
        values.append(g)

    matrix = np.column_stack(values)

    return context_numbers, columns, matrix


def declared_factor_criterion_pairs(
    benchmark: dict[str, Any],
) -> list[tuple[str, str]]:
    specs = benchmark[
        "context_generator"
    ]["opportunity_functions"]

    pairs = []
    for criterion in C1_C7:
        for factor, coefficient in specs[
            criterion
        ].items():
            if not np.isclose(
                float(coefficient),
                0.0,
            ):
                pairs.append(
                    (str(factor), criterion)
                )

    return sorted(pairs)


def reachability_metrics(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    base_opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    step2,
    seed: int,
    rotation: int,
) -> list[dict[str, Any]]:
    rows = []

    for factor, criterion in (
        declared_factor_criterion_pairs(
            benchmark
        )
    ):
        reflected_contexts = (
            reflected_contexts_for_factor(
                contexts=contexts,
                audit=audit,
                factor_name=factor,
                rho=RHO,
            )
        )

        reflected_opportunities = (
            step2.compute_opportunities(
                reflected_contexts,
                benchmark,
            )
        )

        base_ids, base_alts, base_matrix = (
            pc_matrix_for_opportunity(
                criterion=criterion,
                opportunities=base_opportunities,
                capability_parameters=
                    capability_parameters,
                benchmark=benchmark,
                rotation=rotation,
            )
        )

        int_ids, int_alts, int_matrix = (
            pc_matrix_for_opportunity(
                criterion=criterion,
                opportunities=
                    reflected_opportunities,
                capability_parameters=
                    capability_parameters,
                benchmark=benchmark,
                rotation=rotation,
            )
        )

        if base_ids != int_ids:
            raise AssertionError(
                "Context order changed under intervention."
            )
        if base_alts != int_alts:
            raise AssertionError(
                "Alternative order changed under intervention."
            )

        active = active_alternative_ids(
            benchmark,
            criterion,
        )
        active_indices = [
            base_alts.index(a)
            for a in active
        ]

        base_active = base_matrix[
            :,
            active_indices,
        ]
        int_active = int_matrix[
            :,
            active_indices,
        ]

        absolute_difference = np.abs(
            int_active - base_active
        ).reshape(-1)

        re = float(
            np.median(
                absolute_difference
            )
        )

        denominator = (
            iqr_linear(
                base_active.reshape(-1)
            )
            + EPS
        )

        rows.append(
            {
                "seed": seed,
                "rotation": rotation,
                "factor": factor,
                "criterion": criterion,
                "active_alternatives":
                    len(active),
                "re": re,
                "sre": re / denominator,
                "base_iqr": denominator - EPS,
            }
        )

    return rows


def oracle_matrix(
    oracle: pd.DataFrame,
) -> tuple[list[str], np.ndarray]:
    pivot = (
        oracle.pivot(
            index="context_number",
            columns="alternative_id",
            values="U_star",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    return (
        [str(x) for x in pivot.columns],
        pivot.to_numpy(dtype=float),
    )


def modal_regret_summary(
    oracle: pd.DataFrame,
) -> dict[str, Any]:
    alt_ids, values = oracle_matrix(
        oracle
    )

    winner_indices = np.argmax(
        values,
        axis=1,
    )
    winners = [
        alt_ids[int(i)]
        for i in winner_indices
    ]

    counts = Counter(winners)
    modal_alt, modal_count = sorted(
        counts.items(),
        key=lambda kv: (
            -kv[1],
            str(kv[0]),
        ),
    )[0]

    modal_index = alt_ids.index(
        modal_alt
    )

    u_max = values.max(axis=1)
    u_min = values.min(axis=1)
    chosen = values[:, modal_index]

    regret = (
        (u_max - chosen)
        / (u_max - u_min + EPS)
    )

    nonoptimal = (
        np.asarray(
            winners,
            dtype=object,
        )
        != modal_alt
    )

    conditional = regret[
        nonoptimal
    ]

    return {
        "modal_alternative": modal_alt,
        "modal_count": int(modal_count),
        "modal_share":
            float(modal_count / len(winners)),
        "nonoptimal_contexts":
            int(nonoptimal.sum()),
        "regret_mean":
            float(regret.mean()),
        "regret_median":
            quantile_linear(
                regret,
                0.5,
            ),
        "regret_p95":
            quantile_linear(
                regret,
                0.95,
            ),
        "conditional_regret_mean":
            float(
                conditional.mean()
            )
            if len(conditional)
            else 0.0,
        "conditional_regret_median":
            quantile_linear(
                conditional,
                0.5,
            )
            if len(conditional)
            else 0.0,
        "conditional_regret_p95":
            quantile_linear(
                conditional,
                0.95,
            )
            if len(conditional)
            else 0.0,
    }


def median_over_rotations(
    frame: pd.DataFrame,
    group_columns: list[str],
    value_column: str,
) -> pd.DataFrame:
    return (
        frame.groupby(
            group_columns,
            as_index=False,
        )[value_column]
        .median()
    )


def build_references(
    layer_a: pd.DataFrame,
    reachability: pd.DataFrame,
    layer_b: pd.DataFrame,
    baseline_b: pd.DataFrame,
) -> dict[str, Any]:
    references: dict[str, Any] = {
        "layer_a": {},
        "reachability": {},
        "layer_b": {},
    }

    # Per-seed rotation medians, then median across seeds.
    for criterion in C1_C7:
        subset = layer_a.loc[
            layer_a["criterion"]
            == criterion
        ]

        lrv_seed = (
            subset.groupby(
                "seed"
            )["lrv50"]
            .median()
        )
        nsv_seed = (
            subset.groupby(
                "seed"
            )["nsv_vector"]
            .median()
        )

        references["layer_a"][
            criterion
        ] = {
            "T_sci_LRV": float(
                lrv_seed.median()
            ),
            "T_sci_NSV_vector": float(
                nsv_seed.median()
            ),
            "per_seed_rotation_median_LRV50":
                {
                    str(int(k)): float(v)
                    for k, v in
                    lrv_seed.items()
                },
            "per_seed_rotation_median_NSV":
                {
                    str(int(k)): float(v)
                    for k, v in
                    nsv_seed.items()
                },
        }

    for (
        factor,
        criterion,
    ), subset in reachability.groupby(
        ["factor", "criterion"]
    ):
        seed_values = (
            subset.groupby(
                "seed"
            )["sre"]
            .median()
        )

        key = f"{factor}->{criterion}"

        references["reachability"][
            key
        ] = {
            "T_sci_SRE": float(
                seed_values.median()
            ),
            "per_seed_rotation_median_SRE":
                {
                    str(int(k)): float(v)
                    for k, v in
                    seed_values.items()
                },
        }

    pc_seed = (
        layer_b.groupby(
            "seed"
        )["regret_mean"]
        .median()
    )

    baseline_map = (
        baseline_b.set_index(
            "seed"
        )["regret_mean"]
    )

    delta_by_seed = {
        int(seed):
            float(
                pc_seed.loc[seed]
                - baseline_map.loc[seed]
            )
        for seed in pc_seed.index
    }

    activated = all(
        value > REGRET_NUM_THRESHOLD
        for value in delta_by_seed.values()
    )

    references["layer_b"] = {
        "activation_threshold_numerical":
            REGRET_NUM_THRESHOLD,
        "activated": bool(activated),
        "T_R_sci":
            float(pc_seed.median())
            if activated
            else None,
        "per_seed_rotation_median_pc_regret_mean":
            {
                str(int(k)): float(v)
                for k, v in
                pc_seed.items()
            },
        "per_seed_historical_regret_mean":
            {
                str(int(k)): float(v)
                for k, v in
                baseline_map.items()
            },
        "paired_uplift_by_seed":
            {
                str(k): float(v)
                for k, v in
                delta_by_seed.items()
            },
    }

    return references


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_calibration(
    output_dir: Path,
) -> dict[str, Any]:
    commit, branch = require_clean_git()

    step1 = load_numbered_module(
        "d27_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = load_numbered_module(
        "d27_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )
    step3 = load_numbered_module(
        "d27_step3",
        ROOT / "src" / "03_generate_oracle_utility.py",
    )

    benchmark = load_yaml(
        ROOT / "config" / "benchmark.yaml"
    )
    experiment = load_yaml(
        ROOT / "config" / "experiment.yaml"
    )
    seeds_cfg = load_yaml(
        ROOT / "config" / "seeds.yaml"
    )

    if not np.isclose(
        float(
            benchmark[
                "technology_response"
            ][
                "response_exponent"
            ][
                "reference_value"
            ]
        ),
        1.0,
    ):
        raise RuntimeError(
            "D2.7 requires historical gamma=1.0."
        )

    benchmark0 = copy.deepcopy(
        benchmark
    )
    benchmark0[
        "technology_response"
    ][
        "criterion_noise"
    ][
        "sigma_x"
    ] = 0.0

    oracle_spec = step3.load_oracle_spec(
        benchmark
    )

    layer_a_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    reach_rows: list[dict[str, Any]] = []
    layer_b_rows: list[dict[str, Any]] = []
    baseline_b_rows: list[dict[str, Any]] = []

    for seed in DESIGN_SEEDS:
        contexts, audit = (
            step1.generate_master_contexts(
                replication_seed=seed,
                rho=RHO,
                benchmark=benchmark,
                experiment=experiment,
                seeds=seeds_cfg,
            )
        )

        estimation_mask = (
            contexts["partition"]
            .isin(("fit", "weight"))
        )

        contexts_est = (
            contexts.loc[
                estimation_mask
            ]
            .copy()
            .sort_values(
                "context_number"
            )
            .reset_index(drop=True)
        )

        audit_est = (
            audit.loc[
                audit["context_number"]
                .isin(
                    contexts_est[
                        "context_number"
                    ]
                )
            ]
            .copy()
            .sort_values(
                "context_number"
            )
            .reset_index(drop=True)
        )

        if len(contexts_est) != 1000:
            raise AssertionError(
                "D2.7 must use exactly 1000 "
                "FIT+WEIGHT contexts."
            )
        if (
            contexts_est["partition"]
            .eq("test")
            .any()
        ):
            raise AssertionError(
                "External TEST entered D2.7."
            )

        # Generate technology responses from the estimation/calibration
        # contexts only. External TEST rows are never passed into D2.7.
        responses, cap_params, _, _ = (
            step2.generate_master_technology_responses(
                contexts=contexts_est,
                replication_seed=seed,
                benchmark=benchmark0,
            )
        )

        estimation = (
            responses.copy()
            .sort_values(
                [
                    "context_number",
                    "alternative_id",
                ]
            )
            .reset_index(drop=True)
        )

        if len(estimation) != 6000:
            raise AssertionError(
                "Expected 6000 estimation "
                "alternative-context rows."
            )
        if (
            estimation["partition"]
            .eq("test")
            .any()
        ):
            raise AssertionError(
                "External TEST response entered D2.7."
            )
        if set(
            estimation["context_number"]
            .astype(int)
            .unique()
        ) != set(
            contexts_est["context_number"]
            .astype(int)
            .unique()
        ):
            raise AssertionError(
                "Response context set differs from FIT+WEIGHT context set."
            )

        opportunities = (
            step2.compute_opportunities(
                contexts_est,
                benchmark,
            )
        )

        baseline_oracle = (
            step3.compute_oracle_utility(
                estimation,
                oracle_spec=oracle_spec,
                lambda_value=LAMBDA_VALUE,
            )
        )

        baseline_summary = (
            modal_regret_summary(
                baseline_oracle
            )
        )
        baseline_b_rows.append(
            {
                "seed": seed,
                **baseline_summary,
            }
        )

        for rotation in range(6):
            pc = build_positive_control(
                baseline=estimation,
                opportunities=opportunities,
                capability_parameters=
                    cap_params,
                benchmark=benchmark,
                rotation=rotation,
            )

            a_rows, p_rows = (
                layer_a_metrics(
                    pc=pc,
                    benchmark=benchmark,
                    seed=seed,
                    rotation=rotation,
                )
            )
            layer_a_rows.extend(
                a_rows
            )
            pair_rows.extend(
                p_rows
            )

            reach_rows.extend(
                reachability_metrics(
                    contexts=contexts_est,
                    audit=audit_est,
                    base_opportunities=
                        opportunities,
                    capability_parameters=
                        cap_params,
                    benchmark=benchmark,
                    step2=step2,
                    seed=seed,
                    rotation=rotation,
                )
            )

            pc_oracle = (
                step3.compute_oracle_utility(
                    pc,
                    oracle_spec=oracle_spec,
                    lambda_value=
                        LAMBDA_VALUE,
                )
            )

            pc_summary = (
                modal_regret_summary(
                    pc_oracle
                )
            )

            layer_b_rows.append(
                {
                    "seed": seed,
                    "rotation": rotation,
                    **pc_summary,
                }
            )

    layer_a = pd.DataFrame(
        layer_a_rows
    )
    pairwise = pd.DataFrame(
        pair_rows
    )
    reachability = pd.DataFrame(
        reach_rows
    )
    layer_b = pd.DataFrame(
        layer_b_rows
    )
    baseline_b = pd.DataFrame(
        baseline_b_rows
    )

    references = build_references(
        layer_a=layer_a,
        reachability=reachability,
        layer_b=layer_b,
        baseline_b=baseline_b,
    )

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "design_seeds": list(
            DESIGN_SEEDS
        ),
        "rho": RHO,
        "lambda": LAMBDA_VALUE,
        "sigma_x": 0.0,
        "delta": DELTA,
        "contrast": CONTRAST.tolist(),
        "rotations": list(range(6)),
        "contexts_per_seed":
            1000,
        "partitions":
            ["fit", "weight"],
        "external_test_used":
            False,
        "structural_validation_seeds_used":
            False,
        "primary_seeds_used":
            False,
        "positive_floor":
            POSITIVE_FLOOR,
        "epsilon":
            EPS,
        "lrv_ddof":
            0,
        "quantile_method":
            "linear",
        "regret_activation_numerical_threshold":
            REGRET_NUM_THRESHOLD,
    }

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    layer_a.to_csv(
        output_dir
        / "layer_a_summary.csv",
        index=False,
    )
    pairwise.to_csv(
        output_dir
        / "layer_a_pairwise_lrv.csv",
        index=False,
    )
    reachability.to_csv(
        output_dir
        / "reachability_summary.csv",
        index=False,
    )
    layer_b.to_csv(
        output_dir
        / "layer_b_positive_control.csv",
        index=False,
    )
    baseline_b.to_csv(
        output_dir
        / "layer_b_historical_baseline.csv",
        index=False,
    )

    write_json(
        output_dir / "references.json",
        references,
    )
    write_json(
        output_dir / "run_metadata.json",
        metadata,
    )

    summary_lines = [
        "D2.7 POSITIVE-CONTROL CALIBRATION",
        f"git_commit: {commit}",
        f"git_branch: {branch}",
        f"design_seeds: {DESIGN_SEEDS}",
        f"rho: {RHO}",
        f"lambda: {LAMBDA_VALUE}",
        "sigma_x: 0.0",
        "external_TEST_used: False",
        "primary_seeds_used: False",
        "",
        "LAYER-A REFERENCES",
    ]

    for criterion in C1_C7:
        ref = references[
            "layer_a"
        ][criterion]
        summary_lines.append(
            f"{criterion}: "
            f"T_sci_LRV="
            f"{ref['T_sci_LRV']:.12g}; "
            f"T_sci_NSV_vector="
            f"{ref['T_sci_NSV_vector']:.12g}"
        )

    summary_lines.append("")
    summary_lines.append(
        "REACHABILITY REFERENCES"
    )
    for key, ref in sorted(
        references[
            "reachability"
        ].items()
    ):
        summary_lines.append(
            f"{key}: "
            f"T_sci_SRE="
            f"{ref['T_sci_SRE']:.12g}"
        )

    b_ref = references[
        "layer_b"
    ]
    summary_lines.append("")
    summary_lines.append(
        "LAYER-B ACTIVATION"
    )
    summary_lines.append(
        f"activated: "
        f"{b_ref['activated']}"
    )
    summary_lines.append(
        f"T_R_sci: "
        f"{b_ref['T_R_sci']}"
    )
    summary_lines.append(
        "paired_uplift_by_seed: "
        + json.dumps(
            b_ref[
                "paired_uplift_by_seed"
            ],
            sort_keys=True,
        )
    )

    (
        output_dir / "summary.txt"
    ).write_text(
        "\n".join(summary_lines)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        "\n".join(
            summary_lines
        )
    )
    print()
    print(
        f"WROTE: {output_dir}"
    )

    return {
        "metadata": metadata,
        "references": references,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run preregistered v2.2 "
            "D2.7 positive-control calibration."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "results"
            / "v2_2_d2_7_positive_control"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_calibration(
        args.output_dir
    )


if __name__ == "__main__":
    main()
