from __future__ import annotations

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

DEVELOPMENT_SEEDS = (29001, 29002, 29003, 29004, 29005)
RESERVED_SEEDS = (30001, 30002, 30003, 30004, 30005)
STRUCTURAL_VALIDATION_SEEDS = (22001, 22002, 22003, 22004, 22005)
V31_DEVELOPMENT_SEEDS = (27001, 27002, 27003, 27004, 27005)
V30_DEVELOPMENT_SEEDS = (23001, 23002, 23003, 23004, 23005)
D29_RESERVED_SEEDS = (26001, 26002, 26003, 26004, 26005)
LEGACY_RESERVED_SEEDS = (24001, 24002, 24003, 24004, 24005)
OLD_DEVELOPMENT_SEEDS = (21001, 21002, 21003, 21004, 21005)
PRIMARY_SEEDS = tuple(range(11001, 11031))

RHO = 0.4
SIGMA_X = 0.0
LAMBDA_VALUE = 0.5
SIGNED_PROFILE_NAMESPACE = 2010
DELTA = 0.05
CANDIDATE_ID = "d29_kernel"

C1_C7 = tuple(f"C{i}" for i in range(1, 8))
C8_C10 = ("C8", "C9", "C10")

D29_REFERENCES = (
    ROOT / "results" / "d2_9_admissible_positive_control" / "references.json"
)
D28_THRESHOLDS = (
    ROOT / "results" / "v2_2_d2_8_numerical_null" / "thresholds.json"
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


base = load_numbered_module(
    "v40_base_helpers",
    ROOT / "src" / "v3_1_f1_candidate_evaluator.py",
)
d27 = base.d27
d28 = base.d28


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
            "v4.0-F1 REFUSES TO RUN FROM A DIRTY WORKING TREE.\n"
            "Commit or restore all changes before candidate evaluation.\n"
            f"Current status:\n{status}"
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("rev-parse", "--abbrev-ref", "HEAD"),
    )


def load_frozen_thresholds() -> tuple[dict[str, Any], dict[str, Any]]:
    d29_refs = json.loads(D29_REFERENCES.read_text(encoding="utf-8"))
    d28_thresholds = json.loads(D28_THRESHOLDS.read_text(encoding="utf-8"))

    if d29_refs["layer_b"]["activated"] is not False:
        raise RuntimeError(
            "v4.0-F1 evaluator assumes D2.9 Layer-B non-activation."
        )
    if d29_refs["layer_b"]["T_R_sci"] is not None:
        raise RuntimeError(
            "Unexpected numeric T_R_sci in frozen D2.9 references."
        )
    return d29_refs, d28_thresholds


def ordered_alternative_ids(benchmark: dict[str, Any]) -> list[str]:
    return [alt_id for _, alt_id in d27.ordered_alternatives(benchmark)]


def criterion_number(criterion: str) -> int:
    if not criterion.startswith("C"):
        raise ValueError(criterion)
    return int(criterion[1:])


def signed_grid(m: int) -> np.ndarray:
    if m < 2:
        raise ValueError(
            "Signed profile grid requires at least two active alternatives."
        )
    return np.linspace(-1.0, 1.0, m, dtype=float)


def signed_profile(
    replication_seed: int,
    criterion: str,
    benchmark: dict[str, Any],
) -> dict[str, float]:
    """
    Frozen v4.0 profile: symmetric alternative-specific signed grid,
    permuted with SeedSequence([seed, 2010, criterion_number]).
    """
    active_ids = sorted(
        d27.active_alternative_ids(benchmark, criterion)
    )
    grid = signed_grid(len(active_ids))
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                int(replication_seed),
                SIGNED_PROFILE_NAMESPACE,
                criterion_number(criterion),
            ]
        )
    )
    permuted = rng.permutation(grid)
    return {
        alt_id: float(value)
        for alt_id, value in zip(active_ids, permuted)
    }


def all_signed_profiles(
    replication_seed: int,
    benchmark: dict[str, Any],
) -> dict[str, dict[str, float]]:
    return {
        criterion: signed_profile(
            replication_seed,
            criterion,
            benchmark,
        )
        for criterion in C1_C7
    }


def class_ceiling(capability_class: str) -> float:
    return base.class_ceiling(capability_class)


def capability_lookup(
    capability_parameters: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    return d27.capability_lookup(capability_parameters)


def opportunity_lookup(
    opportunities: pd.DataFrame,
    criterion: str,
) -> dict[int, float]:
    return d27.opportunity_map(opportunities, criterion)


def candidate_response(
    theta: np.ndarray | float,
    opportunity: np.ndarray | float,
    v: np.ndarray | float,
) -> np.ndarray:
    """
    Frozen terminal D2.9-kernel response:
        g(o) = theta*o + DELTA*v*o*(1-o),
    with DELTA fixed at 0.05 and no clipping.
    """
    theta_arr = np.asarray(theta, dtype=float)
    o = np.asarray(opportunity, dtype=float)
    v_arr = np.asarray(v, dtype=float)

    if np.any(v_arr < -1.0 - EPS) or np.any(v_arr > 1.0 + EPS):
        raise ValueError("v must lie in [-1,1].")
    if np.any(theta_arr < DELTA - EPS):
        raise ValueError(
            "Active theta must satisfy theta>=DELTA=0.05 for admissibility."
        )

    return np.asarray(
        theta_arr * o + DELTA * v_arr * o * (1.0 - o),
        dtype=float,
    )


def candidate_response_derivative(
    theta: np.ndarray | float,
    opportunity: np.ndarray | float,
    v: np.ndarray | float,
) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=float)
    o = np.asarray(opportunity, dtype=float)
    v_arr = np.asarray(v, dtype=float)

    if np.any(v_arr < -1.0 - EPS) or np.any(v_arr > 1.0 + EPS):
        raise ValueError("v must lie in [-1,1].")

    return np.asarray(
        theta_arr + DELTA * v_arr * (1.0 - 2.0 * o),
        dtype=float,
    )


def build_candidate_responses(
    baseline: pd.DataFrame,
    opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    replication_seed: int,
) -> pd.DataFrame:
    """
    Overwrite only active C1-C7 systematic responses with the frozen v4.0
    D2.9 kernel. Structural-zero pathways remain exactly zero and C8-C10
    remain exactly unchanged.
    """
    result = baseline.copy()
    theta_map = capability_lookup(capability_parameters)
    profiles = all_signed_profiles(replication_seed, benchmark)

    protected = {
        f"g_{criterion}": baseline[f"g_{criterion}"].to_numpy(
            dtype=float,
            copy=True,
        )
        for criterion in C8_C10
    }

    for criterion in C1_C7:
        omap = opportunity_lookup(opportunities, criterion)
        profile = profiles[criterion]

        for _, alternative in benchmark["alternatives"].items():
            alt_id = str(alternative["id"])
            capability_class = str(alternative["capability"][criterion])
            mask = result["alternative_id"].astype(str) == alt_id
            context_numbers = result.loc[
                mask, "context_number"
            ].to_numpy(dtype=int)

            if capability_class == "0":
                values = np.zeros(len(context_numbers), dtype=float)
            else:
                theta = float(theta_map[(alt_id, criterion)])
                ceiling = class_ceiling(capability_class)
                if theta > ceiling + EPS:
                    raise AssertionError(
                        f"{criterion}/{alt_id}: theta={theta} exceeds ceiling={ceiling}."
                    )
                if theta < DELTA - EPS:
                    raise AssertionError(
                        f"{criterion}/{alt_id}: theta={theta} below DELTA={DELTA}."
                    )

                o = np.asarray(
                    [omap[int(n)] for n in context_numbers],
                    dtype=float,
                )
                v = float(profile[alt_id])
                values = candidate_response(theta, o, v)
                derivative = candidate_response_derivative(theta, o, v)

                if np.any(values < -EPS):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: negative v4.0 response."
                    )
                if np.any(values > ceiling + EPS):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: response exceeded class ceiling."
                    )
                if np.any(derivative < -EPS):
                    raise AssertionError(
                        f"{criterion}/{alt_id}: response lost monotonicity."
                    )

            result.loc[mask, f"g_{criterion}"] = values
            x_col = f"x_{criterion}"
            if x_col in result.columns:
                result.loc[mask, x_col] = values

    for col, expected in protected.items():
        if not np.array_equal(
            result[col].to_numpy(dtype=float),
            expected,
        ):
            raise AssertionError(f"{col} changed in v4.0.")

    return result


def matrix_for_active(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    criterion: str,
) -> tuple[list[str], np.ndarray]:
    return base.matrix_for_active(frame, benchmark, criterion)


def layer_a_for_candidate(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
    d28_thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for criterion in C1_C7:
        active_ids, values = matrix_for_active(
            frame,
            benchmark,
            criterion,
        )
        pair_metrics = d27.pairwise_lrv(
            frame,
            benchmark,
            criterion,
        )
        lrv_values = np.asarray(
            [float(row["lrv"]) for row in pair_metrics],
            dtype=float,
        )

        ns_value = d28.rank_one_energy(values)
        lrv50 = d27.quantile_linear(lrv_values, 0.5)
        lrv_max = float(lrv_values.max())
        nsv_vector = d27.nsv(values, "vector")

        rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                "criterion": criterion,
                "active_alternatives": len(active_ids),
                "NS": ns_value,
                "LRV50": lrv50,
                "LRV_max": lrv_max,
                "NSV_vector": nsv_vector,
                "pass_num_NS": bool(
                    ns_value > float(d28_thresholds["T_num_NS"])
                ),
                "pass_num_LRV": bool(
                    lrv50 > float(d28_thresholds["T_num_LRV"])
                ),
                "pass_num_NSV": bool(
                    nsv_vector
                    > float(d28_thresholds["T_num_NSV_vector"])
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
) -> tuple[list[int], list[str], np.ndarray]:
    theta_map = capability_lookup(capability_parameters)
    profile = signed_profile(replication_seed, criterion, benchmark)

    opp = opportunities[
        ["context_number", f"opportunity_{criterion}"]
    ].sort_values("context_number")
    context_numbers = opp["context_number"].to_numpy(dtype=int).tolist()
    o = opp[f"opportunity_{criterion}"].to_numpy(dtype=float)

    active_ids = d27.active_alternative_ids(benchmark, criterion)
    class_by_alt = {
        str(alternative["id"]):
            str(alternative["capability"][criterion])
        for _, alternative in benchmark["alternatives"].items()
    }

    values = []
    for alt_id in active_ids:
        theta = float(theta_map[(alt_id, criterion)])
        ceiling = class_ceiling(class_by_alt[alt_id])
        if theta > ceiling + EPS:
            raise AssertionError("theta exceeded class ceiling.")
        v = float(profile[alt_id])
        values.append(candidate_response(theta, o, v))

    return context_numbers, active_ids, np.column_stack(values)


def reachability_for_candidate(
    contexts: pd.DataFrame,
    audit: pd.DataFrame,
    base_opportunities: pd.DataFrame,
    capability_parameters: pd.DataFrame,
    benchmark: dict[str, Any],
    step2,
    seed: int,
) -> list[dict[str, Any]]:
    rows = []

    for factor, criterion in d27.declared_factor_criterion_pairs(benchmark):
        reflected_contexts = d27.reflected_contexts_for_factor(
            contexts=contexts,
            audit=audit,
            factor_name=factor,
            rho=RHO,
        )
        reflected_opportunities = step2.compute_opportunities(
            reflected_contexts,
            benchmark,
        )

        base_ids, base_alts, base_matrix = candidate_matrix_for_opportunity(
            criterion=criterion,
            opportunities=base_opportunities,
            capability_parameters=capability_parameters,
            benchmark=benchmark,
            replication_seed=seed,
        )
        int_ids, int_alts, int_matrix = candidate_matrix_for_opportunity(
            criterion=criterion,
            opportunities=reflected_opportunities,
            capability_parameters=capability_parameters,
            benchmark=benchmark,
            replication_seed=seed,
        )

        if base_ids != int_ids:
            raise AssertionError(
                "Context order changed under reachability intervention."
            )
        if base_alts != int_alts:
            raise AssertionError(
                "Alternative order changed under reachability intervention."
            )

        re_value = float(
            np.median(np.abs(int_matrix - base_matrix).reshape(-1))
        )
        base_iqr = d27.iqr_linear(base_matrix.reshape(-1))
        sre = re_value / (base_iqr + d27.EPS)

        rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                "factor": factor,
                "criterion": criterion,
                "pathway": f"{factor}->{criterion}",
                "active_alternatives": len(base_alts),
                "RE": re_value,
                "base_IQR": base_iqr,
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    theta_map = capability_lookup(capability_parameters)
    profiles = all_signed_profiles(seed, benchmark)

    boundary_rows = []
    departure_rows = []

    class_by_criterion_alt = {
        criterion: {
            str(alternative["id"]):
                str(alternative["capability"][criterion])
            for _, alternative in benchmark["alternatives"].items()
        }
        for criterion in C1_C7
    }

    ordered_contexts = sorted(
        frame["context_number"].astype(int).unique().tolist()
    )

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
        for _, alternative in benchmark["alternatives"].items():
            alt_id = str(alternative["id"])
            if str(alternative["capability"][criterion]) != "0":
                continue
            subset = frame.loc[
                frame["alternative_id"].astype(str) == alt_id,
                f"g_{criterion}",
            ].to_numpy(dtype=float)
            if len(subset):
                structural_zero_max = max(
                    structural_zero_max,
                    float(np.max(np.abs(subset))),
                )

        min_derivative = np.inf
        min_derivative_margin_vs_zero = np.inf
        max_ceiling_excess = -np.inf
        min_theta_minus_delta = np.inf
        endpoint_zero_error = 0.0
        endpoint_theta_error = 0.0

        omap = opportunity_lookup(opportunities, criterion)
        profile = profiles[criterion]

        for alt_id in active_ids:
            capability_class = class_by_criterion_alt[criterion][alt_id]
            ceiling = class_ceiling(capability_class)
            theta = float(theta_map[(alt_id, criterion)])
            v = float(profile[alt_id])
            min_theta_minus_delta = min(
                min_theta_minus_delta,
                theta - DELTA,
            )

            o = np.asarray(
                [omap[int(n)] for n in ordered_contexts],
                dtype=float,
            )
            derivative = candidate_response_derivative(theta, o, v)
            min_derivative = min(
                min_derivative,
                float(np.min(derivative)),
            )
            min_derivative_margin_vs_zero = min(
                min_derivative_margin_vs_zero,
                float(np.min(derivative)),
            )

            observed = frame.loc[
                frame["alternative_id"].astype(str) == alt_id,
                f"g_{criterion}",
            ].to_numpy(dtype=float)
            max_ceiling_excess = max(
                max_ceiling_excess,
                float(np.max(observed - ceiling)),
            )

            endpoint_zero_error = max(
                endpoint_zero_error,
                abs(float(candidate_response(theta, 0.0, v))),
            )
            endpoint_theta_error = max(
                endpoint_theta_error,
                abs(float(candidate_response(theta, 1.0, v)) - theta),
            )

        departure = np.abs(values - baseline_values)

        boundary_rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                "criterion": criterion,
                "min_active_g": float(values.min()),
                "max_active_g": float(values.max()),
                "min_theta_minus_delta": float(min_theta_minus_delta),
                "min_response_derivative": float(min_derivative),
                "min_derivative_margin_vs_zero":
                    float(min_derivative_margin_vs_zero),
                "max_class_ceiling_excess":
                    float(max_ceiling_excess),
                "endpoint_zero_max_abs_error":
                    float(endpoint_zero_error),
                "endpoint_theta_max_abs_error":
                    float(endpoint_theta_error),
                "structural_zero_max_abs":
                    structural_zero_max,
                "lower_bound_ok":
                    bool(values.min() >= -EPS),
                "class_ceiling_ok":
                    bool(max_ceiling_excess <= EPS),
                "theta_support_ok":
                    bool(min_theta_minus_delta >= -EPS),
                "monotonicity_ok":
                    bool(min_derivative >= -EPS),
                "endpoint_zero_ok":
                    bool(endpoint_zero_error <= EPS),
                "endpoint_theta_ok":
                    bool(endpoint_theta_error <= EPS),
                "structural_zero_ok":
                    bool(structural_zero_max == 0.0),
                "profile_min": float(min(profile.values())),
                "profile_max": float(max(profile.values())),
                "profile_mean": float(np.mean(list(profile.values()))),
            }
        )

        departure_rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                "criterion": criterion,
                "mean_abs_departure": float(np.mean(departure)),
                "median_abs_departure": float(np.median(departure)),
                "max_abs_departure": float(np.max(departure)),
            }
        )

    c8_c10_max = {}
    for criterion in C8_C10:
        col = f"g_{criterion}"
        diff = np.abs(
            frame[col].to_numpy(dtype=float)
            - baseline[col].to_numpy(dtype=float)
        )
        c8_c10_max[criterion] = float(np.max(diff))

    invariance = {
        "seed": seed,
        "candidate_id": CANDIDATE_ID,
        "C8_max_abs_diff": c8_c10_max["C8"],
        "C9_max_abs_diff": c8_c10_max["C9"],
        "C10_max_abs_diff": c8_c10_max["C10"],
        "C8_C10_unchanged": bool(
            all(value == 0.0 for value in c8_c10_max.values())
        ),
    }

    return boundary_rows, departure_rows, invariance


def dominance_diagnostics(
    frame: pd.DataFrame,
    benchmark: dict[str, Any],
    seed: int,
) -> list[dict[str, Any]]:
    alt_ids = ordered_alternative_ids(benchmark)
    context_ids = sorted(
        frame["context_number"].astype(int).unique().tolist()
    )
    counts: Counter[tuple[str, str]] = Counter()

    for context_number in context_ids:
        sub = frame.loc[
            frame["context_number"].astype(int) == context_number
        ].set_index("alternative_id")

        matrix = {
            alt: sub.loc[
                alt,
                [f"g_C{i}" for i in range(1, 11)],
            ].to_numpy(dtype=float)
            for alt in alt_ids
        }

        for a, b in permutations(alt_ids, 2):
            ga = matrix[a]
            gb = matrix[b]
            if np.all(ga >= gb - EPS) and np.any(ga > gb + EPS):
                counts[(a, b)] += 1

    denominator = len(context_ids)
    rows = []
    for a, b in permutations(alt_ids, 2):
        count = int(counts[(a, b)])
        rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                "dominant_alternative": a,
                "dominated_alternative": b,
                "contexts_dominated": count,
                "context_count": denominator,
                "dominance_share": float(count / denominator),
                "structural_dominance": bool(count == denominator),
            }
        )
    return rows


def aggregate_layer_a(
    layer_a: pd.DataFrame,
    d29_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for criterion in C1_C7:
        sub = layer_a.loc[layer_a["criterion"] == criterion]
        if len(sub) != len(DEVELOPMENT_SEEDS):
            raise AssertionError(
                f"{criterion}: expected {len(DEVELOPMENT_SEEDS)} seed rows."
            )

        median_lrv = float(sub["LRV50"].median())
        median_nsv = float(sub["NSV_vector"].median())
        ref = d29_refs["layer_a"][criterion]

        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
                "criterion": criterion,
                "median_LRV50": median_lrv,
                "T_sci_LRV": float(ref["T_sci_LRV"]),
                "pass_sci_LRV":
                    bool(median_lrv >= float(ref["T_sci_LRV"])),
                "median_NSV_vector": median_nsv,
                "T_sci_NSV_vector":
                    float(ref["T_sci_NSV_vector"]),
                "pass_sci_NSV":
                    bool(
                        median_nsv
                        >= float(ref["T_sci_NSV_vector"])
                    ),
                "all_seed_num_NS":
                    bool(sub["pass_num_NS"].all()),
                "all_seed_num_LRV":
                    bool(sub["pass_num_LRV"].all()),
                "all_seed_num_NSV":
                    bool(sub["pass_num_NSV"].all()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_reachability(
    reachability: pd.DataFrame,
    d29_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for pathway, ref in sorted(d29_refs["reachability"].items()):
        sub = reachability.loc[
            reachability["pathway"] == pathway
        ]
        if len(sub) != len(DEVELOPMENT_SEEDS):
            raise AssertionError(
                f"{pathway}: expected {len(DEVELOPMENT_SEEDS)} seed rows."
            )

        median_sre = float(sub["SRE"].median())
        threshold = float(ref["T_sci_SRE"])
        factor, criterion = pathway.split("->", 1)

        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
                "pathway": pathway,
                "factor": factor,
                "criterion": criterion,
                "median_SRE": median_sre,
                "T_sci_SRE": threshold,
                "pass_sci_SRE": bool(median_sre >= threshold),
            }
        )
    return pd.DataFrame(rows)


def build_gate_summary(
    layer_a_agg: pd.DataFrame,
    reachability_agg: pd.DataFrame,
    boundary: pd.DataFrame,
    c8_c10_invariance: pd.DataFrame,
) -> pd.DataFrame:
    if len(layer_a_agg) != 7:
        raise AssertionError("Expected 7 Layer-A criterion rows.")
    if len(reachability_agg) != 12:
        raise AssertionError("Expected 12 reachability pathway rows.")
    if len(boundary) != 35:
        raise AssertionError("Expected 35 seed/criterion invariant rows.")
    if len(c8_c10_invariance) != 5:
        raise AssertionError("Expected 5 C8-C10 invariance rows.")

    pass_num = bool(
        layer_a_agg[
            [
                "all_seed_num_NS",
                "all_seed_num_LRV",
                "all_seed_num_NSV",
            ]
        ].to_numpy(dtype=bool).all()
    )
    pass_sci_layer_a = bool(
        layer_a_agg[
            ["pass_sci_LRV", "pass_sci_NSV"]
        ].to_numpy(dtype=bool).all()
    )
    pass_reachability = bool(
        reachability_agg["pass_sci_SRE"].all()
    )
    pass_boundary = bool(
        boundary[
            [
                "lower_bound_ok",
                "class_ceiling_ok",
                "theta_support_ok",
                "monotonicity_ok",
                "endpoint_zero_ok",
                "endpoint_theta_ok",
                "structural_zero_ok",
            ]
        ].to_numpy(dtype=bool).all()
    )
    pass_c8_c10 = bool(
        c8_c10_invariance["C8_C10_unchanged"].all()
    )
    pass_invariants = bool(pass_boundary and pass_c8_c10)

    return pd.DataFrame(
        [
            {
                "candidate_id": CANDIDATE_ID,
                "pass_numerical": pass_num,
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
                        layer_a_agg.loc[
                            ~(
                                layer_a_agg["pass_sci_LRV"]
                                & layer_a_agg["pass_sci_NSV"]
                            ),
                            "criterion",
                        ].astype(str).tolist()
                    ),
                "failed_reachability_pathways":
                    ",".join(
                        reachability_agg.loc[
                            ~reachability_agg["pass_sci_SRE"],
                            "pathway",
                        ].astype(str).tolist()
                    ),
            }
        ]
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(output_dir: Path) -> dict[str, Any]:
    commit, branch = require_clean_git()
    d29_refs, d28_thresholds = load_frozen_thresholds()

    step1 = load_numbered_module(
        "v40_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = load_numbered_module(
        "v40_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )
    step3 = load_numbered_module(
        "v40_step3",
        ROOT / "src" / "03_generate_oracle_utility.py",
    )

    benchmark = d27.load_yaml(ROOT / "config" / "benchmark.yaml")
    experiment = d27.load_yaml(ROOT / "config" / "experiment.yaml")
    seeds_cfg = d27.load_yaml(ROOT / "config" / "seeds.yaml")

    benchmark0 = copy.deepcopy(benchmark)
    benchmark0["technology_response"]["criterion_noise"]["sigma_x"] = SIGMA_X
    oracle_spec = step3.load_oracle_spec(benchmark)

    profile_rows = []
    layer_a_rows = []
    reachability_rows = []
    layer_b_rows = []
    boundary_rows = []
    departure_rows = []
    c8_c10_rows = []
    dominance_rows = []

    for seed in DEVELOPMENT_SEEDS:
        contexts, audit = step1.generate_master_contexts(
            replication_seed=seed,
            rho=RHO,
            benchmark=benchmark,
            experiment=experiment,
            seeds=seeds_cfg,
        )

        contexts_est = (
            contexts.loc[
                contexts["partition"].isin(("fit", "weight"))
            ]
            .copy()
            .sort_values("context_number")
            .reset_index(drop=True)
        )
        audit_est = (
            audit.loc[
                audit["context_number"].isin(
                    contexts_est["context_number"]
                )
            ]
            .copy()
            .sort_values("context_number")
            .reset_index(drop=True)
        )

        if len(contexts_est) != 1000:
            raise AssertionError(
                "v4.0-F1 requires exactly 1000 FIT+WEIGHT contexts."
            )
        if contexts_est["partition"].eq("test").any():
            raise AssertionError(
                "External TEST entered v4.0-F1 evaluation."
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
            .sort_values(["context_number", "alternative_id"])
            .reset_index(drop=True)
        )
        opportunities = step2.compute_opportunities(
            contexts_est,
            benchmark,
        )

        profiles = all_signed_profiles(seed, benchmark)
        for criterion, profile in profiles.items():
            active_ids = set(profile)
            for alt_id in ordered_alternative_ids(benchmark):
                profile_rows.append(
                    {
                        "seed": seed,
                        "criterion": criterion,
                        "alternative_id": alt_id,
                        "active": bool(alt_id in active_ids),
                        "v": (
                            float(profile[alt_id])
                            if alt_id in active_ids
                            else np.nan
                        ),
                    }
                )

        candidate = build_candidate_responses(
            baseline=baseline,
            opportunities=opportunities,
            capability_parameters=cap_params,
            benchmark=benchmark,
            replication_seed=seed,
        )

        layer_a_rows.extend(
            layer_a_for_candidate(
                frame=candidate,
                benchmark=benchmark,
                seed=seed,
                d28_thresholds=d28_thresholds,
            )
        )
        reachability_rows.extend(
            reachability_for_candidate(
                contexts=contexts_est,
                audit=audit_est,
                base_opportunities=opportunities,
                capability_parameters=cap_params,
                benchmark=benchmark,
                step2=step2,
                seed=seed,
            )
        )

        boundary_part, departure_part, c8_c10_part = (
            boundary_diagnostics(
                frame=candidate,
                baseline=baseline,
                opportunities=opportunities,
                capability_parameters=cap_params,
                benchmark=benchmark,
                seed=seed,
            )
        )
        boundary_rows.extend(boundary_part)
        departure_rows.extend(departure_part)
        c8_c10_rows.append(c8_c10_part)

        oracle = step3.compute_oracle_utility(
            candidate,
            oracle_spec=oracle_spec,
            lambda_value=LAMBDA_VALUE,
        )
        layer_b_rows.append(
            {
                "seed": seed,
                "candidate_id": CANDIDATE_ID,
                **d27.modal_regret_summary(oracle),
            }
        )
        dominance_rows.extend(
            dominance_diagnostics(
                frame=candidate,
                benchmark=benchmark,
                seed=seed,
            )
        )

    profiles_df = pd.DataFrame(profile_rows)
    layer_a = pd.DataFrame(layer_a_rows)
    reachability = pd.DataFrame(reachability_rows)
    layer_b = pd.DataFrame(layer_b_rows)
    boundary = pd.DataFrame(boundary_rows)
    departure = pd.DataFrame(departure_rows)
    c8_c10_invariance = pd.DataFrame(c8_c10_rows)
    dominance = pd.DataFrame(dominance_rows)

    layer_a_agg = aggregate_layer_a(layer_a, d29_refs)
    reachability_agg = aggregate_reachability(
        reachability,
        d29_refs,
    )
    gate_summary = build_gate_summary(
        layer_a_agg,
        reachability_agg,
        boundary,
        c8_c10_invariance,
    )

    candidate_passed = bool(
        gate_summary.iloc[0]["all_frozen_gates"]
    )

    output_dir.mkdir(parents=True, exist_ok=False)

    outputs = {
        "signed_profiles.csv": profiles_df,
        "layer_a_per_seed.csv": layer_a,
        "layer_a_aggregated.csv": layer_a_agg,
        "reachability_per_seed.csv": reachability,
        "reachability_aggregated.csv": reachability_agg,
        "layer_b_diagnostics.csv": layer_b,
        "boundary_diagnostics.csv": boundary,
        "departure_diagnostics.csv": departure,
        "c8_c10_invariance.csv": c8_c10_invariance,
        "dominance_diagnostics.csv": dominance,
        "candidate_gate_summary.csv": gate_summary,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / name, index=False)

    selection = {
        "candidate_id": CANDIDATE_ID,
        "candidate_passed": candidate_passed,
        "candidate_count": 1,
        "parameter_search": False,
        "delta": DELTA,
        "family": "v4.0-F1 terminal D2.9-kernel response",
        "family_failed": bool(not candidate_passed),
        "adjudication_rule": (
            "single candidate must pass frozen D2.8 numerical, "
            "D2.9 Layer-A, D2.9 reachability, and invariant gates"
        ),
        "layer_b_used_for_selection": False,
    }
    write_json(output_dir / "selection.json", selection)

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "rho": RHO,
        "sigma_x": SIGMA_X,
        "lambda": LAMBDA_VALUE,
        "signed_profile_namespace": SIGNED_PROFILE_NAMESPACE,
        "delta": DELTA,
        "candidate_count": 1,
        "parameter_search": False,
        "external_test_used": False,
        "structural_validation_seeds_used": False,
        "primary_seeds_used": False,
        "reserved_seeds_used": False,
        "v31_development_seeds_used": False,
        "v30_development_seeds_used": False,
        "d29_reserved_seeds_used": False,
        "legacy_reserved_seeds_used": False,
        "old_development_seeds_used": False,
        "reserved_seeds": list(RESERVED_SEEDS),
        "structural_validation_seeds":
            list(STRUCTURAL_VALIDATION_SEEDS),
        "primary_seeds": list(PRIMARY_SEEDS),
        "production_generator_modified": False,
        "layer_b_used_for_selection": False,
        "d29_reference_file":
            str(D29_REFERENCES.relative_to(ROOT)),
        "d28_threshold_file":
            str(D28_THRESHOLDS.relative_to(ROOT)),
    }
    write_json(output_dir / "run_metadata.json", metadata)

    row = gate_summary.iloc[0]
    summary_lines = [
        "v4.0-F1 TERMINAL D2.9-KERNEL CANDIDATE EVALUATION",
        f"git_commit: {commit}",
        f"development_seeds: {DEVELOPMENT_SEEDS}",
        f"rho: {RHO}",
        f"sigma_x: {SIGMA_X}",
        f"delta: {DELTA}",
        "candidate_count: 1",
        "parameter_search: False",
        "external_TEST_used: False",
        "structural_validation_seeds_used: False",
        "primary_seeds_used: False",
        "reserved_seeds_used: False",
        "layer_b_used_for_selection: False",
        "",
        "GATE SUMMARY",
        (
            f"candidate={CANDIDATE_ID}; "
            f"num={row.pass_numerical}; "
            f"layerA={row.pass_scientific_layer_a}; "
            f"reach={row.pass_reachability}; "
            f"inv={row.pass_invariants}; "
            f"all={row.all_frozen_gates}; "
            f"failed_C={row.failed_layer_a_criteria or '-'}; "
            f"failed_pathways={row.failed_reachability_pathways or '-'}"
        ),
        "",
        f"CANDIDATE_PASSED: {candidate_passed}",
        f"V4_0_F1_FAILED: {not candidate_passed}",
    ]

    (output_dir / "summary.txt").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print("\n".join(summary_lines))
    print(f"WROTE: {output_dir}")

    return {
        "candidate_passed": candidate_passed,
        "selection": selection,
        "metadata": metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen single-candidate v4.0-F1 "
            "terminal D2.9-kernel response."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "results"
            / "v4_0_f1_terminal_d29_kernel"
        ),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
