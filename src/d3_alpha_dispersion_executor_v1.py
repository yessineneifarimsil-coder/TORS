from __future__ import annotations

import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL = ROOT / "config" / "d3_alpha_dispersion_protocol_v1.json"
PRODUCTION = ROOT / "config" / "production_response_generator_v1.json"
RETENTION_FREEZE = (
    ROOT / "results" / "production_generator_retention_resolution_v1"
    / "freeze_summary.json"
)
V22_ROBUSTNESS = ROOT / "config" / "secondary_v2_2_generator_robustness_v1.json"

CONTEXT_PATH = ROOT / "src" / "01_generate_contexts.py"
RESPONSE_PATH = ROOT / "src" / "02_generate_technology_responses.py"
D29_PATH = ROOT / "src" / "v4_0_f1_terminal_d29_kernel_evaluator.py"

OUTPUT_DIR = ROOT / "results" / "d3_alpha_dispersion_execution_v1"

CRITERIA = [f"C{i}" for i in range(1, 11)]
LOG3 = math.log(3.0)


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = git_output("status", "--porcelain")
    if status:
        raise RuntimeError(
            "D3 EXECUTION REFUSES TO RUN FROM A DIRTY TREE.\n" + status
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def q_transform(g: np.ndarray) -> np.ndarray:
    arr = np.asarray(g, dtype=float)
    if np.any(arr < -1e-12) or np.any(arr > 1.0 + 1e-12):
        raise AssertionError("D3 direction-adjusted g must remain in [0,1].")
    arr = np.clip(arr, 0.0, 1.0)
    return np.log1p(2.0 * arr) / LOG3


def q_mad(g: np.ndarray) -> float:
    q = q_transform(g)
    return float(np.mean(np.abs(q - float(np.mean(q)))))


def criterion_order(means: dict[str, float]) -> list[str]:
    # Descending mean q-MAD; criterion index is deterministic tie-breaker.
    return sorted(
        CRITERIA,
        key=lambda c: (-float(means[c]), int(c[1:])),
    )


def summarize_checkpoint(
    world_table: pd.DataFrame,
    W: int,
    epsilon: float,
) -> tuple[pd.DataFrame, list[str]]:
    sub = world_table.loc[world_table["world_index"] <= W].copy()
    if int(sub["world_index"].nunique()) != W:
        raise AssertionError(f"Checkpoint W={W} does not contain W worlds.")

    rows = []
    means: dict[str, float] = {}

    for criterion in CRITERIA:
        vals = sub.loc[
            sub["criterion"] == criterion, "q_mad"
        ].to_numpy(dtype=float)

        if len(vals) != W:
            raise AssertionError(
                f"{criterion}: expected {W} world q-MAD values, got {len(vals)}."
            )

        mean = float(np.mean(vals))
        sd = float(np.std(vals, ddof=1)) if W > 1 else float("nan")
        mcse = float(sd / math.sqrt(W)) if W > 1 else float("nan")
        rel_half = float(1.96 * mcse / (mean + epsilon)) if W > 1 else float("nan")

        means[criterion] = mean
        rows.append(
            {
                "W": W,
                "criterion": criterion,
                "mean_q_mad": mean,
                "sample_sd_world_q_mad": sd,
                "mcse": mcse,
                "relative_95pct_half_width": rel_half,
            }
        )

    return pd.DataFrame(rows), criterion_order(means)


def convergence_decision(
    world_table: pd.DataFrame,
    compare_pair: tuple[int, int],
    final_W: int,
    epsilon: float,
    target: float,
) -> dict[str, Any]:
    earlier_W, later_W = compare_pair
    earlier_summary, earlier_order = summarize_checkpoint(
        world_table, earlier_W, epsilon
    )
    final_summary, final_order = summarize_checkpoint(
        world_table, final_W, epsilon
    )

    precision_pass = bool(
        (
            final_summary["relative_95pct_half_width"].to_numpy(dtype=float)
            <= float(target)
        ).all()
    )
    order_stable = earlier_order == final_order

    return {
        "earlier_W": int(earlier_W),
        "final_W": int(final_W),
        "earlier_order": earlier_order,
        "final_order": final_order,
        "order_stable": bool(order_stable),
        "precision_pass": precision_pass,
        "all_pass": bool(order_stable and precision_pass),
        "final_summary": final_summary,
        "earlier_summary": earlier_summary,
    }


def derive_alpha_mappings(
    final_order: list[str],
    spectrum_descending: list[float],
) -> dict[str, dict[str, float]]:
    if len(final_order) != len(CRITERIA):
        raise ValueError("Final D3 order must contain all ten criteria.")
    if sorted(final_order, key=lambda c: int(c[1:])) != CRITERIA:
        raise ValueError("Final D3 order is not a permutation of C1..C10.")
    if len(spectrum_descending) != len(CRITERIA):
        raise ValueError("Alpha spectrum must have ten values.")

    aligned = {
        criterion: float(alpha)
        for criterion, alpha in zip(final_order, spectrum_descending)
    }
    anti = {
        criterion: float(alpha)
        for criterion, alpha in zip(reversed(final_order), spectrum_descending)
    }
    balanced = {criterion: 0.10 for criterion in CRITERIA}

    return {
        "balanced": balanced,
        "dispersion_aligned": aligned,
        "dispersion_anti_aligned": anti,
    }


def build_d3_contexts(
    world_seed: int,
    world_index: int,
    rho: float,
    n_contexts: int,
    benchmark: dict[str, Any],
    seeds: dict[str, Any],
    context_module,
) -> pd.DataFrame:
    factor_names = list(
        benchmark["context_generator"]["latent_factors"]
    )
    n_factors = len(factor_names)

    stream_namespace = int(
        seeds["context_generation"]["estimation_stream_namespace"]
    )

    z_shared, z_idio = context_module.generate_base_normals(
        replication_seed=int(world_seed),
        n_contexts=int(n_contexts),
        n_latent_factors=n_factors,
        stream_namespace=stream_namespace,
    )

    latent_normal = context_module.construct_correlated_normals(
        z_shared=z_shared,
        z_idiosyncratic=z_idio,
        rho=float(rho),
    )
    latent_uniform = context_module.transform_to_uniform(latent_normal)

    context_numbers = np.arange(1, n_contexts + 1, dtype=int)
    data: dict[str, Any] = {
        "context_id": [
            f"D3W{world_index:04d}_C{n:04d}"
            for n in context_numbers
        ],
        "context_number": context_numbers,
        "replication_seed": np.full(n_contexts, int(world_seed), dtype=np.int64),
        "rho": np.full(n_contexts, float(rho), dtype=float),
        "partition": np.full(n_contexts, "d3", dtype=object),
    }

    for j, factor in enumerate(factor_names):
        data[factor] = latent_uniform[:, j].astype(float)

    contexts = pd.DataFrame(data)

    if len(contexts) != n_contexts:
        raise AssertionError("D3 context count mismatch.")
    if not (contexts["partition"] == "d3").all():
        raise AssertionError("D3 contexts must not use FIT/WEIGHT/TEST roles.")

    return contexts


def evaluate_world(
    world_seed: int,
    world_index: int,
    rho: float,
    n_contexts: int,
    benchmark: dict[str, Any],
    seeds: dict[str, Any],
    context_module,
    response_module,
    d29_module,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contexts = build_d3_contexts(
        world_seed=world_seed,
        world_index=world_index,
        rho=rho,
        n_contexts=n_contexts,
        benchmark=benchmark,
        seeds=seeds,
        context_module=context_module,
    )

    d3_benchmark = copy.deepcopy(benchmark)
    d3_benchmark["technology_response"]["criterion_noise"]["sigma_x"] = 0.0

    (
        baseline,
        capability_parameters,
        _deployment_parameters,
        _response_audit,
    ) = response_module.generate_master_technology_responses(
        contexts=contexts,
        replication_seed=int(world_seed),
        benchmark=d3_benchmark,
    )

    opportunities = response_module.compute_opportunities(
        contexts=contexts,
        benchmark=d3_benchmark,
    )

    production = d29_module.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability_parameters,
        benchmark=d3_benchmark,
        replication_seed=int(world_seed),
    )

    expected_rows = n_contexts * int(
        d3_benchmark["dimensions"]["alternatives"]
    )
    if len(production) != expected_rows:
        raise AssertionError(
            f"D3 world {world_index}: expected {expected_rows} rows, "
            f"got {len(production)}."
        )

    if not (production["partition"] == "d3").all():
        raise AssertionError("D3 production rows inherited non-D3 partition labels.")

    rows: list[dict[str, Any]] = []
    for criterion in CRITERIA:
        g = production[f"g_{criterion}"].to_numpy(dtype=float)
        rows.append(
            {
                "world_index": int(world_index),
                "world_seed": int(world_seed),
                "criterion": criterion,
                "q_mad": q_mad(g),
                "n_observations": int(len(g)),
            }
        )

    world_audit = {
        "world_index": int(world_index),
        "world_seed": int(world_seed),
        "contexts": int(n_contexts),
        "rows": int(len(production)),
        "rho": float(rho),
        "sigma_x": 0.0,
        "partition_roles_used": False,
        "external_TEST_used": False,
        "primary_seed_used": False,
        "reserve_seed_used": False,
    }

    return rows, world_audit


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    commit, branch = require_clean_git()
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing D3 output: {output_dir}")

    protocol = load_json(PROTOCOL)
    production_cfg = load_json(PRODUCTION)
    retention = load_json(RETENTION_FREEZE)
    robustness = load_json(V22_ROBUSTNESS)

    if retention["resolution"] != "RETAIN_D29_KERNEL_UNDER_MINIMAL_INTERVENTION":
        raise AssertionError("Primary generator retention is not frozen.")
    if retention["retained_primary_candidate"] != "d29_kernel":
        raise AssertionError("Retained primary generator is not d29_kernel.")
    if robustness["D3_execution_allowed_after_this_protocol_is_frozen"] is not True:
        raise AssertionError("Secondary v2.2 robustness protocol does not release D3.")
    if production_cfg["candidate_id"] != "d29_kernel":
        raise AssertionError("Production generator config is not d29_kernel.")
    if production_cfg["d3_unblocked"] is not True:
        raise AssertionError("Production generator config does not unblock D3.")

    d = protocol["design_ensemble"]
    c = protocol["convergence"]
    e = protocol["dispersion_estimand"]

    assert d["master_seed_namespace"] == 74001
    assert d["contexts_per_world"] == 1000
    assert d["alternatives_per_context"] == 6
    assert d["observations_per_criterion_per_world"] == 6000
    assert d["rho"] == 0.4
    assert d["sigma_x"] == 0.0
    assert d["external_test_used"] is False
    assert d["primary_seeds_used"] is False
    assert d["protected_seed_collision_count"] == 0
    assert len(d["world_seeds"]) == 400
    assert len(set(d["world_seeds"])) == 400

    assert e["q_transform"] == "log(1+2g)/log(3)"
    assert e["within_world_statistic"] == (
        "mean absolute deviation from within-world mean q"
    )
    assert e["context_aggregation_before_qMAD"] is False
    assert e["criterion_minmax_before_qMAD"] is False

    context_module = load_module("d3_context_generator", CONTEXT_PATH)
    response_module = load_module("d3_response_generator", RESPONSE_PATH)
    d29_module = load_module("d3_d29_generator", D29_PATH)

    benchmark, _experiment, seeds = context_module.load_project_configuration()

    world_seeds = [int(x) for x in d["world_seeds"]]
    initial_W = int(d["initial_worlds"])
    max_W = int(d["total_worlds_frozen"])
    n_contexts = int(d["contexts_per_world"])
    rho = float(d["rho"])
    epsilon = float(c["epsilon"])
    target = float(c["relative_95pct_half_width_target"])

    protected = set(range(11001, 11031)) | set(range(30001, 30006))
    collisions = sorted(protected.intersection(world_seeds))
    if collisions:
        raise AssertionError(f"D3 world seeds collide with protected seeds: {collisions}")

    all_rows: list[dict[str, Any]] = []
    world_audits: list[dict[str, Any]] = []

    for idx in range(1, initial_W + 1):
        rows, audit = evaluate_world(
            world_seed=world_seeds[idx - 1],
            world_index=idx,
            rho=rho,
            n_contexts=n_contexts,
            benchmark=benchmark,
            seeds=seeds,
            context_module=context_module,
            response_module=response_module,
            d29_module=d29_module,
        )
        all_rows.extend(rows)
        world_audits.append(audit)

    world_table = pd.DataFrame(all_rows)

    initial_decision = convergence_decision(
        world_table=world_table,
        compare_pair=tuple(c["initial_order_compare"]),
        final_W=initial_W,
        epsilon=epsilon,
        target=target,
    )

    expanded = not initial_decision["all_pass"]

    if expanded:
        for idx in range(initial_W + 1, max_W + 1):
            rows, audit = evaluate_world(
                world_seed=world_seeds[idx - 1],
                world_index=idx,
                rho=rho,
                n_contexts=n_contexts,
                benchmark=benchmark,
                seeds=seeds,
                context_module=context_module,
                response_module=response_module,
                d29_module=d29_module,
            )
            all_rows.extend(rows)
            world_audits.append(audit)

        world_table = pd.DataFrame(all_rows)
        final_decision = convergence_decision(
            world_table=world_table,
            compare_pair=tuple(c["expanded_order_compare"]),
            final_W=max_W,
            epsilon=epsilon,
            target=target,
        )
    else:
        final_decision = initial_decision

    final_W = int(final_decision["final_W"])
    converged = bool(final_decision["all_pass"])

    checkpoint_frames = []
    checkpoints = [
        int(x) for x in c["initial_checkpoints"]
        if int(x) <= final_W
    ]
    if final_W > initial_W:
        checkpoints.extend(
            int(x) for x in c["expanded_checkpoints"]
            if int(x) <= final_W
        )

    checkpoint_orders: dict[str, list[str]] = {}
    for W in checkpoints:
        frame, order = summarize_checkpoint(world_table, W, epsilon)
        checkpoint_frames.append(frame)
        checkpoint_orders[str(W)] = order

    checkpoint_table = pd.concat(checkpoint_frames, ignore_index=True)

    if converged:
        mappings = derive_alpha_mappings(
            final_order=final_decision["final_order"],
            spectrum_descending=[
                float(x) for x in protocol["heterogeneous_spectrum_descending"]
            ],
        )
        status = "D3_CONVERGED_MAPPING_FROZEN_READY"
    else:
        mappings = None
        status = "D3_FAILED_PROTOCOL_AMENDMENT_REQUIRED"

    output_dir.mkdir(parents=True, exist_ok=False)
    world_table.to_csv(output_dir / "world_q_mad.csv", index=False)
    pd.DataFrame(world_audits).to_csv(
        output_dir / "world_audit.csv", index=False
    )
    checkpoint_table.to_csv(
        output_dir / "checkpoint_summary.csv", index=False
    )
    (output_dir / "checkpoint_orders.json").write_text(
        json.dumps(checkpoint_orders, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    mapping_payload = {
        "status": status,
        "converged": converged,
        "final_W": final_W,
        "final_order_descending_q_mad":
            final_decision["final_order"] if converged else None,
        "mappings": mappings,
        "primary_alpha_unchanged": protocol["primary_alpha"],
        "balanced_mapping_frozen": protocol["structures"]["balanced"],
        "mapping_defining_estimand": "superpopulation mean within-world q-MAD",
        "secondary_minmax_population_sd": {
            "configured_enabled": bool(
                protocol["secondary_diagnostics"]["minmax_population_sd"]["enabled"]
            ),
            "defines_mapping": False,
            "status": "NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC",
            "reason": (
                "Frozen artifacts name a historical min-max plus population-SD "
                "diagnostic but do not fully specify its exact normalization scope "
                "and implementation details. No formula was invented because it "
                "cannot define the D3 mapping."
            ),
        },
    }
    (output_dir / "alpha_mapping.json").write_text(
        json.dumps(mapping_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "status": status,
        "git_commit": commit,
        "git_branch": branch,
        "production_generator": "d29_kernel",
        "production_formula": "theta*o + 0.05*v*o*(1-o)",
        "signed_profile_namespace": 2010,
        "master_seed_namespace": 74001,
        "worlds_observed": final_W,
        "expanded_beyond_200": expanded,
        "converged": converged,
        "initial_order_stable_150_vs_200": bool(
            initial_decision["order_stable"]
        ),
        "initial_precision_pass_W200": bool(
            initial_decision["precision_pass"]
        ),
        "final_order_compare": [
            int(final_decision["earlier_W"]),
            int(final_decision["final_W"]),
        ],
        "final_order_stable": bool(final_decision["order_stable"]),
        "final_precision_pass": bool(final_decision["precision_pass"]),
        "final_order_descending_q_mad":
            final_decision["final_order"] if converged else None,
        "aligned_and_anti_mapping_formed": bool(converged),
        "primary_alpha_changed": False,
        "minmax_population_sd_used_for_mapping": False,
        "minmax_population_sd_status":
            "NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC",
        "new_seed_generation": False,
        "world_seed_replacement": False,
        "primary_11001_11030_used": False,
        "reserve_30001_30005_used": False,
        "external_TEST_used": False,
        "FIT_WEIGHT_partition_roles_used": False,
        "SHAP_used": False,
        "MCDM_used": False,
        "winner_identity_used": False,
        "v2_2_robustness_executed": False,
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "D3-B SUPERPOPULATION ALPHA-DISPERSION EXECUTION",
        f"git_commit: {commit}",
        "production_generator: d29_kernel",
        "master_seed_namespace: 74001",
        f"worlds_observed: {final_W}",
        f"expanded_beyond_200: {expanded}",
        f"initial_order_stable_150_vs_200: {initial_decision['order_stable']}",
        f"initial_precision_pass_W200: {initial_decision['precision_pass']}",
        f"final_order_compare: {final_decision['earlier_W']} vs {final_decision['final_W']}",
        f"final_order_stable: {final_decision['order_stable']}",
        f"final_precision_pass: {final_decision['precision_pass']}",
        f"converged: {converged}",
        f"status: {status}",
        f"final_order_descending_q_mad: {final_decision['final_order'] if converged else None}",
        f"aligned_and_anti_mapping_formed: {converged}",
        "primary_alpha_changed: False",
        "minmax_population_sd_used_for_mapping: False",
        "minmax_population_sd_status: NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC",
        "primary_11001_11030_used: False",
        "reserve_30001_30005_used: False",
        "external_TEST_used: False",
        "FIT_WEIGHT_partition_roles_used: False",
        "SHAP_used: False",
        "MCDM_used: False",
        "winner_identity_used: False",
        "v2_2_robustness_executed: False",
    ]
    (output_dir / "summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    print("WROTE:", output_dir)
    return summary


if __name__ == "__main__":
    run()
