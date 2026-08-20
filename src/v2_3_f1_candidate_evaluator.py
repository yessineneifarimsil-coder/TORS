from __future__ import annotations

"""
Pre-specified v2.3-F1 headroom-augmented candidate-family evaluator.

This module evaluates the version-frozen v2.3-F1 headroom-augmented
family without modifying the production technology response generator.

Selection rule
--------------
Select the smallest eta in the frozen ladder that passes:
1) all D2.8 numerical structural gates,
2) all D2.7 criterion-level LRV/NSV scientific gates,
3) all D2.7 pathway-level SRE reachability gates,
4) all frozen response/invariance gates.

Layer-B winner geometry is computed descriptively and is never used to
choose eta because D2.7 did not activate a numeric T_R_sci.
"""

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DESIGN_SEEDS = (21001, 21002, 21003, 21004, 21005)
RHO = 0.4
SIGMA_X = 0.0
LAMBDA_VALUE = 0.5

HEADROOM_NAMESPACE = 2005
TAU = 0.5
ETA_REFERENCE = 0.0
ETA_LADDER = tuple(
    round(x / 10.0, 1)
    for x in range(1, 11)
)

C1_C7 = tuple(f"C{i}" for i in range(1, 8))
C8_C10 = ("C8", "C9", "C10")

D27_REFERENCES = (
    ROOT
    / "results"
    / "v2_2_d2_7_positive_control"
    / "references.json"
)
D28_THRESHOLDS = (
    ROOT
    / "results"
    / "v2_2_d2_8_numerical_null"
    / "thresholds.json"
)

EPS = 1.0e-12


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


d27 = load_numbered_module(
    "v23_d27",
    ROOT / "src" / "v2_2_d2_7_positive_control.py",
)
d28 = load_numbered_module(
    "v23_d28",
    ROOT / "src" / "v2_2_d2_8_numerical_null.py",
)


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
            "v2.3-F1 REFUSES TO RUN FROM A DIRTY WORKING TREE.\n"
            "Commit or restore all changes before candidate evaluation.\n"
            f"Current status:\n{status}"
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("rev-parse", "--abbrev-ref", "HEAD"),
    )


def load_frozen_thresholds() -> tuple[dict[str, Any], dict[str, Any]]:
    d27_refs = json.loads(
        D27_REFERENCES.read_text(encoding="utf-8")
    )
    d28_thresholds = json.loads(
        D28_THRESHOLDS.read_text(encoding="utf-8")
    )

    if d27_refs["layer_b"]["activated"] is not False:
        raise RuntimeError(
            "v2.3-F1 evaluator assumes D2.7 Layer-B non-activation."
        )
    if d27_refs["layer_b"]["T_R_sci"] is not None:
        raise RuntimeError(
            "Unexpected numeric T_R_sci in frozen D2.7 references."
        )

    return d27_refs, d28_thresholds


def ordered_alternative_ids(
    benchmark: dict[str, Any],
) -> list[str]:
    return [
        alt_id
        for _, alt_id in d27.ordered_alternatives(benchmark)
    ]


def criterion_number(criterion: str) -> int:
    if not criterion.startswith("C"):
        raise ValueError(criterion)
    return int(criterion[1:])



def headroom_grid(m: int) -> np.ndarray:
    """Frozen C_m grid: 0, 1/(m-1), ..., 1."""
    if m < 2:
        raise ValueError(
            "Headroom grid requires at least two active alternatives."
        )
    return np.linspace(
        0.0,
        1.0,
        m,
        dtype=float,
    )


def headroom_profile(
    replication_seed: int,
    criterion: str,
    benchmark: dict[str, Any],
) -> dict[str, float]:
    """
    Build the frozen v2.3-F1 alternative-specific c_aj profile.

    The complete [0,1] grid is permuted once per benchmark instance and
    criterion using SeedSequence([seed, 2005, criterion_number]).
    """
    active_ids = sorted(
        d27.active_alternative_ids(
            benchmark,
            criterion,
        )
    )

    grid = headroom_grid(
        len(active_ids)
    )

    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                int(replication_seed),
                HEADROOM_NAMESPACE,
                criterion_number(criterion),
            ]
        )
    )

    permuted = rng.permutation(
        grid
    )

    return {
        alt_id: float(value)
        for alt_id, value in zip(
            active_ids,
            permuted,
        )
    }


def all_headroom_profiles(
    replication_seed: int,
    benchmark: dict[str, Any],
) -> dict[str, dict[str, float]]:
    return {
        criterion: headroom_profile(
            replication_seed,
            criterion,
            benchmark,
        )
        for criterion in C1_C7
    }


def class_ceiling(
    capability_class: str,
) -> float:
    """Frozen semantic ceiling for active C1-C7 capability classes."""
    value = str(capability_class)
    if value == "I":
        return 0.20
    if value == "D":
        return 0.40
    if value == "0":
        return 0.0
    raise ValueError(
        f"Unexpected C1-C7 capability class: {capability_class!r}"
    )



def candidate_response(
    theta: np.ndarray | float,
    opportunity: np.ndarray | float,
    eta: float,
    headroom: np.ndarray | float,
    c: np.ndarray | float,
    tau: float = TAU,
) -> np.ndarray:
    """
    Frozen v2.3-F1 response:
      theta*o + eta*h*[tau*o + (1-tau)*c*o^2].
    """
    theta_arr = np.asarray(theta, dtype=float)
    o = np.asarray(opportunity, dtype=float)
    h = np.asarray(headroom, dtype=float)
    c_arr = np.asarray(c, dtype=float)

    if not 0.0 <= float(eta) <= 1.0:
        raise ValueError("eta must satisfy 0 <= eta <= 1.")
    if not 0.0 <= float(tau) <= 1.0:
        raise ValueError("tau must satisfy 0 <= tau <= 1.")
    if np.any(h < -EPS):
        raise ValueError("headroom must be non-negative.")
    if np.any(c_arr < -EPS) or np.any(c_arr > 1.0 + EPS):
        raise ValueError("c must lie in [0,1].")
    if np.any(o < -EPS) or np.any(o > 1.0 + EPS):
        raise ValueError("opportunity must lie in [0,1].")

    values = (
        theta_arr * o
        + float(eta)
        * h
        * (
            float(tau) * o
            + (1.0 - float(tau))
            * c_arr
            * o ** 2
        )
    )

    return np.asarray(
        values,
        dtype=float,
    )

def capability_lookup(
    capability_parameters: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    return d27.capability_lookup(
        capability_parameters
    )


def opportunity_lookup(
    opportunities: pd.DataFrame,
    criterion: str,
) -> dict[int, float]:
    return d27.opportunity_map(
        opportunities,
        criterion,
    )



def build_candidate_responses(
    baseline: pd.DataFrame,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    replication_seed: int,
    eta: float,
) -> pd.DataFrame:
    """
    Overwrite only C1-C7 systematic responses with v2.3-F1.

    C8-C10 must remain byte-for-byte numerically unchanged in the returned
    frame. Structural zeros remain exactly zero.
    """
    if not 0.0 <= float(eta) <= 1.0:
        raise ValueError("eta must satisfy 0 <= eta <= 1.")

    result = baseline.copy()
    theta_map = capability_lookup(
        capability_parameters
    )
    profiles = all_headroom_profiles(
        replication_seed,
        benchmark,
    )

    protected = {}
    for criterion in C8_C10:
        col = f"g_{criterion}"
        protected[col] = baseline[col].to_numpy(
            dtype=float,
            copy=True,
        )

    for criterion in C1_C7:
        omap = opportunity_lookup(
            opportunities,
            criterion,
        )
        profile = profiles[
            criterion
        ]

        for _, alternative in benchmark[
            "alternatives"
        ].items():
            alt_id = str(
                alternative["id"]
            )
            capability_class = str(
                alternative["capability"][
                    criterion
                ]
            )

            mask = (
                result[
                    "alternative_id"
                ].astype(str)
                == alt_id
            )

            context_numbers = (
                result.loc[
                    mask,
                    "context_number",
                ]
                .to_numpy(dtype=int)
            )

            if capability_class == "0":
                values = np.zeros(
                    len(context_numbers),
                    dtype=float,
                )
            else:
                theta = float(
                    theta_map[
                        (alt_id, criterion)
                    ]
                )
                ceiling = class_ceiling(
                    capability_class
                )
                headroom = float(
                    ceiling - theta
                )

                if headroom < -EPS:
                    raise AssertionError(
                        f"{criterion}/{alt_id}: theta={theta} exceeds "
                        f"class ceiling={ceiling}."
                    )
                headroom = max(
                    headroom,
                    0.0,
                )

                o = np.asarray(
                    [
                        omap[int(n)]
                        for n in context_numbers
                    ],
                    dtype=float,
                )
                c = float(
                    profile[alt_id]
                )

                values = candidate_response(
                    theta=theta,
                    opportunity=o,
                    eta=eta,
                    headroom=headroom,
                    c=c,
                )

                derivative = (
                    theta
                    + float(eta)
                    * headroom
                    * (
                        TAU
                        + 2.0
                        * (1.0 - TAU)
                        * c
                        * o
                    )
                )

                if np.any(
                    values < -EPS
                ):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: negative v2.3-F1 response."
                    )
                if np.any(
                    values > ceiling + EPS
                ):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: response exceeded "
                        f"class ceiling {ceiling}."
                    )
                if np.any(
                    derivative < theta - EPS
                ):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: derivative fell below "
                        "historical baseline slope theta."
                    )

            result.loc[
                mask,
                f"g_{criterion}",
            ] = values

            x_col = f"x_{criterion}"
            if x_col in result.columns:
                result.loc[
                    mask,
                    x_col,
                ] = values

    for col, expected in protected.items():
        got = result[col].to_numpy(
            dtype=float,
        )
        if not np.array_equal(
            got,
            expected,
        ):
            raise AssertionError(
                f"{col} changed during v2.3-F1 candidate construction."
            )

    return result

def matrix_for_active(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    criterion: str,
) -> tuple[list[str], np.ndarray]:
    pivot = (
        frame.pivot(
            index="context_number",
            columns="alternative_id",
            values=f"g_{criterion}",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )

    active_ids = [
        alt
        for alt in d27.active_alternative_ids(
            benchmark,
            criterion,
        )
        if alt in pivot.columns
    ]

    return (
        active_ids,
        pivot[
            active_ids
        ].to_numpy(dtype=float),
    )


def layer_a_for_candidate(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
    eta: float,
    d28_thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []

    for criterion in C1_C7:
        active_ids, values = (
            matrix_for_active(
                frame,
                benchmark,
                criterion,
            )
        )

        pair_metrics = d27.pairwise_lrv(
            frame,
            benchmark,
            criterion,
        )
        lrv_values = np.asarray(
            [
                float(row["lrv"])
                for row in pair_metrics
            ],
            dtype=float,
        )

        ns_value = d28.rank_one_energy(
            values
        )
        lrv50 = d27.quantile_linear(
            lrv_values,
            0.5,
        )
        lrv_max = float(
            lrv_values.max()
        )
        nsv_vector = d27.nsv(
            values,
            "vector",
        )

        rows.append(
            {
                "seed": seed,
                "eta": float(eta),
                "criterion": criterion,
                "active_alternatives":
                    len(active_ids),
                "NS": ns_value,
                "LRV50": lrv50,
                "LRV_max": lrv_max,
                "NSV_vector":
                    nsv_vector,
                "pass_num_NS":
                    bool(
                        ns_value
                        > float(
                            d28_thresholds[
                                "T_num_NS"
                            ]
                        )
                    ),
                "pass_num_LRV":
                    bool(
                        lrv50
                        > float(
                            d28_thresholds[
                                "T_num_LRV"
                            ]
                        )
                    ),
                "pass_num_NSV":
                    bool(
                        nsv_vector
                        > float(
                            d28_thresholds[
                                "T_num_NSV_vector"
                            ]
                        )
                    ),
            }
        )

    return rows



def candidate_matrix_for_opportunity(
    criterion: str,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    replication_seed: int,
    eta: float,
) -> tuple[list[int], list[str], np.ndarray]:
    theta_map = capability_lookup(
        capability_parameters
    )
    profile = headroom_profile(
        replication_seed,
        criterion,
        benchmark,
    )

    opp = (
        opportunities[
            [
                "context_number",
                f"opportunity_{criterion}",
            ]
        ]
        .sort_values(
            "context_number"
        )
    )

    context_numbers = (
        opp["context_number"]
        .to_numpy(dtype=int)
        .tolist()
    )
    o = (
        opp[
            f"opportunity_{criterion}"
        ]
        .to_numpy(dtype=float)
    )

    active_ids = d27.active_alternative_ids(
        benchmark,
        criterion,
    )

    class_by_alt = {
        str(alternative["id"]):
            str(alternative["capability"][criterion])
        for _, alternative in benchmark[
            "alternatives"
        ].items()
    }

    values = []

    for alt_id in active_ids:
        theta = float(
            theta_map[
                (alt_id, criterion)
            ]
        )
        ceiling = class_ceiling(
            class_by_alt[alt_id]
        )
        headroom = max(
            float(ceiling - theta),
            0.0,
        )
        c = float(
            profile[
                alt_id
            ]
        )

        g = candidate_response(
            theta=theta,
            opportunity=o,
            eta=eta,
            headroom=headroom,
            c=c,
        )

        values.append(
            g
        )

    return (
        context_numbers,
        active_ids,
        np.column_stack(values),
    )

def reachability_for_candidate(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    base_opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    step2,
    seed: int,
    eta: float,
) -> list[dict[str, Any]]:
    rows = []

    for factor, criterion in (
        d27.declared_factor_criterion_pairs(
            benchmark
        )
    ):
        reflected_contexts = (
            d27.reflected_contexts_for_factor(
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
            candidate_matrix_for_opportunity(
                criterion=criterion,
                opportunities=base_opportunities,
                capability_parameters=
                    capability_parameters,
                benchmark=benchmark,
                replication_seed=seed,
                eta=eta,
            )
        )

        int_ids, int_alts, int_matrix = (
            candidate_matrix_for_opportunity(
                criterion=criterion,
                opportunities=
                    reflected_opportunities,
                capability_parameters=
                    capability_parameters,
                benchmark=benchmark,
                replication_seed=seed,
                eta=eta,
            )
        )

        if base_ids != int_ids:
            raise AssertionError(
                "Context order changed under reachability intervention."
            )
        if base_alts != int_alts:
            raise AssertionError(
                "Alternative order changed under reachability intervention."
            )

        abs_difference = np.abs(
            int_matrix - base_matrix
        ).reshape(-1)

        re_value = float(
            np.median(
                abs_difference
            )
        )
        base_flat = base_matrix.reshape(
            -1
        )
        base_iqr = d27.iqr_linear(
            base_flat
        )
        sre = (
            re_value
            / (
                base_iqr
                + d27.EPS
            )
        )

        rows.append(
            {
                "seed": seed,
                "eta": float(eta),
                "factor": factor,
                "criterion": criterion,
                "pathway":
                    f"{factor}->{criterion}",
                "active_alternatives":
                    len(base_alts),
                "RE": re_value,
                "base_IQR":
                    base_iqr,
                "SRE": sre,
            }
        )

    return rows



def boundary_diagnostics(
    frame: pd.DataFrame,
    baseline: pd.DataFrame,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
    eta: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    theta_map = capability_lookup(
        capability_parameters
    )
    profiles = all_headroom_profiles(
        seed,
        benchmark,
    )

    boundary_rows = []
    departure_rows = []

    class_by_criterion_alt = {}
    for criterion in C1_C7:
        class_by_criterion_alt[criterion] = {
            str(alternative["id"]):
                str(alternative["capability"][criterion])
            for _, alternative in benchmark[
                "alternatives"
            ].items()
        }

    for criterion in C1_C7:
        active_ids, values = matrix_for_active(
            frame,
            benchmark,
            criterion,
        )
        _, baseline_values = matrix_for_active(
            baseline,
            benchmark,
            criterion,
        )

        structural_zero_max = 0.0
        for _, alternative in benchmark[
            "alternatives"
        ].items():
            alt_id = str(
                alternative["id"]
            )
            if str(
                alternative[
                    "capability"
                ][criterion]
            ) != "0":
                continue
            subset = frame.loc[
                frame["alternative_id"]
                .astype(str)
                == alt_id,
                f"g_{criterion}",
            ].to_numpy(dtype=float)
            if len(subset):
                structural_zero_max = max(
                    structural_zero_max,
                    float(
                        np.max(
                            np.abs(
                                subset
                            )
                        )
                    ),
                )

        min_derivative_margin = np.inf
        max_ceiling_excess = -np.inf
        min_headroom = np.inf
        max_headroom = -np.inf

        omap = opportunity_lookup(
            opportunities,
            criterion,
        )
        profile = profiles[
            criterion
        ]

        for alt_id in active_ids:
            capability_class = (
                class_by_criterion_alt[
                    criterion
                ][
                    alt_id
                ]
            )
            ceiling = class_ceiling(
                capability_class
            )
            theta = float(
                theta_map[
                    (alt_id, criterion)
                ]
            )
            headroom = float(
                ceiling - theta
            )
            min_headroom = min(
                min_headroom,
                headroom,
            )
            max_headroom = max(
                max_headroom,
                headroom,
            )

            o = np.asarray(
                [
                    omap[int(n)]
                    for n in sorted(
                        frame["context_number"]
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                ],
                dtype=float,
            )
            c = float(
                profile[
                    alt_id
                ]
            )
            derivative = (
                theta
                + float(eta)
                * max(headroom, 0.0)
                * (
                    TAU
                    + 2.0
                    * (1.0 - TAU)
                    * c
                    * o
                )
            )
            min_derivative_margin = min(
                min_derivative_margin,
                float(
                    np.min(
                        derivative - theta
                    )
                ),
            )

            observed = frame.loc[
                frame["alternative_id"].astype(str)
                == alt_id,
                f"g_{criterion}",
            ].to_numpy(dtype=float)
            max_ceiling_excess = max(
                max_ceiling_excess,
                float(
                    np.max(
                        observed - ceiling
                    )
                ),
            )

        departure = np.abs(
            values - baseline_values
        )

        boundary_rows.append(
            {
                "seed": seed,
                "eta": float(eta),
                "criterion": criterion,
                "min_active_g":
                    float(values.min()),
                "max_active_g":
                    float(values.max()),
                "min_headroom":
                    float(min_headroom),
                "max_headroom":
                    float(max_headroom),
                "max_class_ceiling_excess":
                    float(max_ceiling_excess),
                "min_derivative_margin_vs_theta":
                    float(min_derivative_margin),
                "structural_zero_max_abs":
                    structural_zero_max,
                "lower_bound_ok":
                    bool(
                        values.min()
                        >= -EPS
                    ),
                "class_ceiling_ok":
                    bool(
                        max_ceiling_excess
                        <= EPS
                    ),
                "headroom_nonnegative_ok":
                    bool(
                        min_headroom
                        >= -EPS
                    ),
                "derivative_floor_ok":
                    bool(
                        min_derivative_margin
                        >= -EPS
                    ),
                "structural_zero_ok":
                    bool(
                        structural_zero_max
                        == 0.0
                    ),
                "profile_min":
                    float(
                        min(
                            profile.values()
                        )
                    ),
                "profile_max":
                    float(
                        max(
                            profile.values()
                        )
                    ),
                "profile_mean":
                    float(
                        np.mean(
                            list(
                                profile.values()
                            )
                        )
                    ),
            }
        )

        departure_rows.append(
            {
                "seed": seed,
                "eta": float(eta),
                "criterion": criterion,
                "mean_abs_departure":
                    float(
                        np.mean(
                            departure
                        )
                    ),
                "median_abs_departure":
                    float(
                        np.median(
                            departure
                        )
                    ),
                "max_abs_departure":
                    float(
                        np.max(
                            departure
                        )
                    ),
            }
        )

    c8_c10_max = {}
    for criterion in C8_C10:
        col = f"g_{criterion}"
        diff = np.abs(
            frame[col].to_numpy(dtype=float)
            - baseline[col].to_numpy(dtype=float)
        )
        c8_c10_max[criterion] = float(
            np.max(
                diff
            )
        )

    invariance = {
        "seed": seed,
        "eta": float(eta),
        "C8_max_abs_diff":
            c8_c10_max["C8"],
        "C9_max_abs_diff":
            c8_c10_max["C9"],
        "C10_max_abs_diff":
            c8_c10_max["C10"],
        "C8_C10_unchanged":
            bool(
                all(
                    value == 0.0
                    for value in c8_c10_max.values()
                )
            ),
    }

    return (
        boundary_rows,
        departure_rows,
        invariance,
    )

def dominance_diagnostics(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
    eta: float,
) -> list[dict[str, Any]]:
    """
    Descriptive context-wise Pareto dominance using benefit-oriented g_C1..g_C10.
    This never enters candidate selection.
    """
    alt_ids = ordered_alternative_ids(
        benchmark
    )

    context_ids = sorted(
        frame["context_number"]
        .astype(int)
        .unique()
        .tolist()
    )

    counts: Counter[tuple[str, str]] = Counter()

    for context_number in context_ids:
        sub = (
            frame.loc[
                frame["context_number"]
                .astype(int)
                == context_number
            ]
            .set_index(
                "alternative_id"
            )
        )

        matrix = {
            alt: sub.loc[
                alt,
                [
                    f"g_C{i}"
                    for i in range(1, 11)
                ],
            ].to_numpy(dtype=float)
            for alt in alt_ids
        }

        for a, b in permutations(
            alt_ids,
            2,
        ):
            ga = matrix[a]
            gb = matrix[b]
            if (
                np.all(
                    ga >= gb - EPS
                )
                and np.any(
                    ga > gb + EPS
                )
            ):
                counts[
                    (a, b)
                ] += 1

    rows = []
    denominator = len(
        context_ids
    )

    for a, b in permutations(
        alt_ids,
        2,
    ):
        count = int(
            counts[
                (a, b)
            ]
        )
        rows.append(
            {
                "seed": seed,
                "eta": float(eta),
                "dominant_alternative": a,
                "dominated_alternative": b,
                "contexts_dominated":
                    count,
                "context_count":
                    denominator,
                "dominance_share":
                    float(
                        count
                        / denominator
                    ),
                "structural_dominance":
                    bool(
                        count
                        == denominator
                    ),
            }
        )

    return rows


def aggregate_layer_a(
    layer_a: pd.DataFrame,
    d27_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []

    for eta in sorted(
        layer_a["eta"]
        .unique()
    ):
        for criterion in C1_C7:
            sub = layer_a.loc[
                (
                    layer_a["eta"]
                    == eta
                )
                & (
                    layer_a["criterion"]
                    == criterion
                )
            ]

            median_lrv = float(
                sub[
                    "LRV50"
                ].median()
            )
            median_nsv = float(
                sub[
                    "NSV_vector"
                ].median()
            )

            ref = d27_refs[
                "layer_a"
            ][criterion]

            rows.append(
                {
                    "eta":
                        float(eta),
                    "criterion":
                        criterion,
                    "median_LRV50":
                        median_lrv,
                    "T_sci_LRV":
                        float(
                            ref[
                                "T_sci_LRV"
                            ]
                        ),
                    "pass_sci_LRV":
                        bool(
                            median_lrv
                            >= float(
                                ref[
                                    "T_sci_LRV"
                                ]
                            )
                        ),
                    "median_NSV_vector":
                        median_nsv,
                    "T_sci_NSV_vector":
                        float(
                            ref[
                                "T_sci_NSV_vector"
                            ]
                        ),
                    "pass_sci_NSV":
                        bool(
                            median_nsv
                            >= float(
                                ref[
                                    "T_sci_NSV_vector"
                                ]
                            )
                        ),
                    "all_seed_num_NS":
                        bool(
                            sub[
                                "pass_num_NS"
                            ].all()
                        ),
                    "all_seed_num_LRV":
                        bool(
                            sub[
                                "pass_num_LRV"
                            ].all()
                        ),
                    "all_seed_num_NSV":
                        bool(
                            sub[
                                "pass_num_NSV"
                            ].all()
                        ),
                }
            )

    return pd.DataFrame(rows)


def aggregate_reachability(
    reachability: pd.DataFrame,
    d27_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []

    for eta in sorted(
        reachability["eta"]
        .unique()
    ):
        for pathway, ref in sorted(
            d27_refs[
                "reachability"
            ].items()
        ):
            sub = reachability.loc[
                (
                    reachability[
                        "eta"
                    ]
                    == eta
                )
                & (
                    reachability[
                        "pathway"
                    ]
                    == pathway
                )
            ]

            median_sre = float(
                sub[
                    "SRE"
                ].median()
            )
            threshold = float(
                ref[
                    "T_sci_SRE"
                ]
            )

            factor, criterion = (
                pathway.split(
                    "->",
                    1,
                )
            )

            rows.append(
                {
                    "eta":
                        float(eta),
                    "pathway":
                        pathway,
                    "factor":
                        factor,
                    "criterion":
                        criterion,
                    "median_SRE":
                        median_sre,
                    "T_sci_SRE":
                        threshold,
                    "pass_sci_SRE":
                        bool(
                            median_sre
                            >= threshold
                        ),
                }
            )

    return pd.DataFrame(rows)



def build_gate_summary(
    layer_a_agg: pd.DataFrame,
    reachability_agg: pd.DataFrame,
    boundary: pd.DataFrame,
    c8_c10_invariance: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for eta in ETA_LADDER:
        a = layer_a_agg.loc[
            layer_a_agg["eta"]
            == eta
        ]
        r = reachability_agg.loc[
            reachability_agg[
                "eta"
            ]
            == eta
        ]
        b = boundary.loc[
            boundary[
                "eta"
            ]
            == eta
        ]
        inv = c8_c10_invariance.loc[
            c8_c10_invariance[
                "eta"
            ]
            == eta
        ]

        if len(a) != 7:
            raise AssertionError(
                f"eta={eta}: expected 7 Layer-A criterion rows."
            )
        if len(r) != 12:
            raise AssertionError(
                f"eta={eta}: expected 12 reachability pathway rows."
            )
        if len(b) != 35:
            raise AssertionError(
                f"eta={eta}: expected 35 seed/criterion invariant rows."
            )
        if len(inv) != 5:
            raise AssertionError(
                f"eta={eta}: expected 5 C8-C10 invariance rows."
            )

        pass_num = bool(
            a[
                [
                    "all_seed_num_NS",
                    "all_seed_num_LRV",
                    "all_seed_num_NSV",
                ]
            ]
            .to_numpy(dtype=bool)
            .all()
        )

        pass_sci_layer_a = bool(
            a[
                [
                    "pass_sci_LRV",
                    "pass_sci_NSV",
                ]
            ]
            .to_numpy(dtype=bool)
            .all()
        )

        pass_reachability = bool(
            r[
                "pass_sci_SRE"
            ].all()
        )

        pass_boundary = bool(
            b[
                [
                    "lower_bound_ok",
                    "class_ceiling_ok",
                    "headroom_nonnegative_ok",
                    "derivative_floor_ok",
                    "structural_zero_ok",
                ]
            ]
            .to_numpy(dtype=bool)
            .all()
        )
        pass_c8_c10 = bool(
            inv[
                "C8_C10_unchanged"
            ].all()
        )
        pass_invariants = bool(
            pass_boundary
            and pass_c8_c10
        )

        rows.append(
            {
                "eta":
                    float(eta),
                "pass_numerical":
                    pass_num,
                "pass_scientific_layer_a":
                    pass_sci_layer_a,
                "pass_reachability":
                    pass_reachability,
                "pass_invariants":
                    pass_invariants,
                "all_frozen_gates":
                    bool(
                        pass_num
                        and pass_sci_layer_a
                        and pass_reachability
                        and pass_invariants
                    ),
                "failed_layer_a_criteria":
                    ",".join(
                        a.loc[
                            ~(
                                a[
                                    "pass_sci_LRV"
                                ]
                                & a[
                                    "pass_sci_NSV"
                                ]
                            ),
                            "criterion",
                        ]
                        .astype(str)
                        .tolist()
                    ),
                "failed_reachability_pathways":
                    ",".join(
                        r.loc[
                            ~r[
                                "pass_sci_SRE"
                            ],
                            "pathway",
                        ]
                        .astype(str)
                        .tolist()
                    ),
            }
        )

    return pd.DataFrame(rows)

def select_eta(
    gate_summary: pd.DataFrame,
) -> float | None:
    eligible = (
        gate_summary.loc[
            gate_summary[
                "all_frozen_gates"
            ]
        ]
        .sort_values(
            "eta"
        )
    )

    if eligible.empty:
        return None

    return float(
        eligible.iloc[
            0
        ][
            "eta"
        ]
    )


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


def run(
    output_dir: Path,
) -> dict[str, Any]:
    commit, branch = require_clean_git()

    d27_refs, d28_thresholds = (
        load_frozen_thresholds()
    )

    step1 = load_numbered_module(
        "v23_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = load_numbered_module(
        "v23_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )
    step3 = load_numbered_module(
        "v23_step3",
        ROOT / "src" / "03_generate_oracle_utility.py",
    )

    benchmark = d27.load_yaml(
        ROOT / "config" / "benchmark.yaml"
    )
    experiment = d27.load_yaml(
        ROOT / "config" / "experiment.yaml"
    )
    seeds_cfg = d27.load_yaml(
        ROOT / "config" / "seeds.yaml"
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
    ] = SIGMA_X

    oracle_spec = step3.load_oracle_spec(
        benchmark
    )

    profile_rows = []
    layer_a_rows = []
    reachability_rows = []
    layer_b_rows = []
    boundary_rows = []
    departure_rows = []
    c8_c10_rows = []
    dominance_rows = []

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

        contexts_est = (
            contexts.loc[
                contexts[
                    "partition"
                ].isin(
                    (
                        "fit",
                        "weight",
                    )
                )
            ]
            .copy()
            .sort_values(
                "context_number"
            )
            .reset_index(drop=True)
        )

        audit_est = (
            audit.loc[
                audit[
                    "context_number"
                ].isin(
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

        if len(
            contexts_est
        ) != 1000:
            raise AssertionError(
                "v2.3-F1 requires exactly 1000 FIT+WEIGHT contexts."
            )

        if (
            contexts_est[
                "partition"
            ]
            .eq("test")
            .any()
        ):
            raise AssertionError(
                "External TEST entered v2.3-F1 evaluation."
            )

        baseline, cap_params, _, _ = (
            step2.generate_master_technology_responses(
                contexts=contexts_est,
                replication_seed=seed,
                benchmark=benchmark0,
            )
        )

        baseline = (
            baseline
            .sort_values(
                [
                    "context_number",
                    "alternative_id",
                ]
            )
            .reset_index(drop=True)
        )

        opportunities = (
            step2.compute_opportunities(
                contexts_est,
                benchmark,
            )
        )

        profiles = all_headroom_profiles(
            seed,
            benchmark,
        )
        for criterion, profile in (
            profiles.items()
        ):
            active_ids = set(
                profile
            )
            for alt_id in ordered_alternative_ids(
                benchmark
            ):
                profile_rows.append(
                    {
                        "seed": seed,
                        "criterion":
                            criterion,
                        "alternative_id":
                            alt_id,
                        "active":
                            bool(
                                alt_id
                                in active_ids
                            ),
                        "c":
                            (
                                float(
                                    profile[
                                        alt_id
                                    ]
                                )
                                if alt_id
                                in active_ids
                                else np.nan
                            ),
                    }
                )

        # eta=0 is descriptive reference only.
        for eta in (
            (ETA_REFERENCE,)
            + ETA_LADDER
        ):
            candidate = (
                build_candidate_responses(
                    baseline=baseline,
                    opportunities=
                        opportunities,
                    capability_parameters=
                        cap_params,
                    benchmark=benchmark,
                    replication_seed=
                        seed,
                    eta=eta,
                )
            )

            layer_a_rows.extend(
                layer_a_for_candidate(
                    frame=candidate,
                    benchmark=benchmark,
                    seed=seed,
                    eta=eta,
                    d28_thresholds=
                        d28_thresholds,
                )
            )

            reachability_rows.extend(
                reachability_for_candidate(
                    contexts=contexts_est,
                    audit=audit_est,
                    base_opportunities=
                        opportunities,
                    capability_parameters=
                        cap_params,
                    benchmark=benchmark,
                    step2=step2,
                    seed=seed,
                    eta=eta,
                )
            )

            (
                boundary_part,
                departure_part,
                c8_c10_part,
            ) = boundary_diagnostics(
                frame=candidate,
                baseline=baseline,
                opportunities=opportunities,
                capability_parameters=
                    cap_params,
                benchmark=benchmark,
                seed=seed,
                eta=eta,
            )
            boundary_rows.extend(
                boundary_part
            )
            departure_rows.extend(
                departure_part
            )
            c8_c10_rows.append(
                c8_c10_part
            )

            oracle = (
                step3.compute_oracle_utility(
                    candidate,
                    oracle_spec=
                        oracle_spec,
                    lambda_value=
                        LAMBDA_VALUE,
                )
            )

            layer_b_rows.append(
                {
                    "seed": seed,
                    "eta":
                        float(eta),
                    **d27.modal_regret_summary(
                        oracle
                    ),
                }
            )

            dominance_rows.extend(
                dominance_diagnostics(
                    frame=candidate,
                    benchmark=benchmark,
                    seed=seed,
                    eta=eta,
                )
            )

    profiles_df = pd.DataFrame(
        profile_rows
    )
    layer_a = pd.DataFrame(
        layer_a_rows
    )
    reachability = pd.DataFrame(
        reachability_rows
    )
    layer_b = pd.DataFrame(
        layer_b_rows
    )
    boundary = pd.DataFrame(
        boundary_rows
    )
    departure = pd.DataFrame(
        departure_rows
    )
    c8_c10_invariance = pd.DataFrame(
        c8_c10_rows
    )
    dominance = pd.DataFrame(
        dominance_rows
    )

    layer_a_agg = aggregate_layer_a(
        layer_a,
        d27_refs,
    )
    reachability_agg = (
        aggregate_reachability(
            reachability,
            d27_refs,
        )
    )

    # Candidate selection excludes eta=0.
    gate_summary = build_gate_summary(
        layer_a_agg.loc[
            layer_a_agg[
                "eta"
            ].isin(
                ETA_LADDER
            )
        ].copy(),
        reachability_agg.loc[
            reachability_agg[
                "eta"
            ].isin(
                ETA_LADDER
            )
        ].copy(),
        boundary.loc[
            boundary[
                "eta"
            ].isin(
                ETA_LADDER
            )
        ].copy(),
        c8_c10_invariance.loc[
            c8_c10_invariance[
                "eta"
            ].isin(
                ETA_LADDER
            )
        ].copy(),
    )

    selected = select_eta(
        gate_summary
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    outputs = {
        "headroom_profiles.csv":
            profiles_df,
        "layer_a_per_seed.csv":
            layer_a,
        "layer_a_aggregated.csv":
            layer_a_agg,
        "reachability_per_seed.csv":
            reachability,
        "reachability_aggregated.csv":
            reachability_agg,
        "layer_b_diagnostics.csv":
            layer_b,
        "boundary_diagnostics.csv":
            boundary,
        "departure_diagnostics.csv":
            departure,
        "c8_c10_invariance.csv":
            c8_c10_invariance,
        "dominance_diagnostics.csv":
            dominance,
        "candidate_gate_summary.csv":
            gate_summary,
    }

    for name, frame in outputs.items():
        frame.to_csv(
            output_dir / name,
            index=False,
        )

    selection = {
        "selected_eta":
            selected,
        "selection_rule":
            "minimum frozen eta passing all numerical, Layer-A scientific, reachability, and invariant gates",
        "layer_b_used_for_selection":
            False,
        "eta_reference":
            ETA_REFERENCE,
        "eta_ladder":
            list(
                ETA_LADDER
            ),
        "candidate_family":
            "v2.3-F1 headroom-augmented response",
        "family_failed":
            bool(
                selected is None
            ),
    }
    write_json(
        output_dir
        / "selection.json",
        selection,
    )

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "design_seeds":
            list(
                DESIGN_SEEDS
            ),
        "rho": RHO,
        "sigma_x": SIGMA_X,
        "lambda": LAMBDA_VALUE,
        "headroom_namespace":
            HEADROOM_NAMESPACE,
        "tau":
            TAU,
        "eta_reference":
            ETA_REFERENCE,
        "eta_ladder":
            list(
                ETA_LADDER
            ),
        "external_test_used":
            False,
        "structural_validation_seeds_used":
            False,
        "primary_seeds_used":
            False,
        "production_generator_modified":
            False,
        "layer_b_used_for_selection":
            False,
        "d27_reference_file":
            str(
                D27_REFERENCES.relative_to(
                    ROOT
                )
            ),
        "d28_threshold_file":
            str(
                D28_THRESHOLDS.relative_to(
                    ROOT
                )
            ),
    }
    write_json(
        output_dir
        / "run_metadata.json",
        metadata,
    )

    summary_lines = [
        "v2.3-F1 HEADROOM-AUGMENTED CANDIDATE EVALUATION",
        f"git_commit: {commit}",
        f"design_seeds: {DESIGN_SEEDS}",
        f"rho: {RHO}",
        f"sigma_x: {SIGMA_X}",
        f"eta_ladder: {ETA_LADDER}",
        "external_TEST_used: False",
        "structural_validation_seeds_used: False",
        "primary_seeds_used: False",
        "layer_b_used_for_selection: False",
        "",
        "GATE SUMMARY",
    ]

    for row in gate_summary.itertuples(
        index=False
    ):
        summary_lines.append(
            "eta="
            f"{row.eta:.1f}; "
            f"num={row.pass_numerical}; "
            f"layerA={row.pass_scientific_layer_a}; "
            f"reach={row.pass_reachability}; "
            f"inv={row.pass_invariants}; "
            f"all={row.all_frozen_gates}; "
            f"failed_C={row.failed_layer_a_criteria or '-'}; "
            f"failed_pathways={row.failed_reachability_pathways or '-'}"
        )

    summary_lines.extend(
        [
            "",
            f"SELECTED_ETA: {selected}",
            (
                "V2_3_F1_FAILED: "
                f"{selected is None}"
            ),
        ]
    )

    (
        output_dir
        / "summary.txt"
    ).write_text(
        "\n".join(
            summary_lines
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        "\n".join(
            summary_lines
        )
    )
    print(
        f"WROTE: {output_dir}"
    )

    return {
        "selected_eta":
            selected,
        "selection":
            selection,
        "metadata":
            metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate version-frozen v2.3-F1 "
            "headroom-augmented candidate ladder."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "results"
            / "v2_3_f1_candidates"
        ),
    )
    args = parser.parse_args()
    run(
        args.output_dir
    )


if __name__ == "__main__":
    main()
