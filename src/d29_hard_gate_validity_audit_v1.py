from __future__ import annotations

import copy
import importlib.util
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

AUDIT_PROTOCOL = ROOT / "config" / "d29_hard_gate_validity_audit_v1.json"
D29_RESULTS = ROOT / "results" / "d2_9_admissible_positive_control"
D29_REFERENCES = D29_RESULTS / "references.json"
D29_LAYER = D29_RESULTS / "layer_a_summary.csv"
D29_REACH = D29_RESULTS / "reachability_summary.csv"

V40_RESULTS = ROOT / "results" / "v4_0_f1_terminal_d29_kernel"
V40_LAYER_AGG = V40_RESULTS / "layer_a_aggregated.csv"
V40_REACH_AGG = V40_RESULTS / "reachability_aggregated.csv"

OUTPUT_DIR = ROOT / "results" / "d29_hard_gate_validity_audit_v1"

AUDIT_SEEDS = (29001, 29002, 29003, 29004, 29005)
D29_SEEDS = (25001, 25002, 25003, 25004, 25005)
ROTATIONS = tuple(range(6))
RHO = 0.4
SIGMA_X = 0.0
DELTA = 0.05

SUPPORT_EQUIVALENT = ("C1", "C2", "C4", "C6", "C7")
SUPPORT_MISMATCH = ("C3", "C5")
C1_C7 = tuple(f"C{i}" for i in range(1, 8))


def load_module(name: str, path: Path):
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


d29 = load_module(
    "gate_audit_d29",
    ROOT / "src" / "d2_9_admissible_positive_control.py",
)
v40 = load_module(
    "gate_audit_v40",
    ROOT / "src" / "v4_0_f1_terminal_d29_kernel_evaluator.py",
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
            "D2.9 HARD-GATE VALIDITY AUDIT REFUSES TO RUN FROM A DIRTY TREE.\n"
            f"{status}"
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def load_protocol_and_refs() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = json.loads(AUDIT_PROTOCOL.read_text(encoding="utf-8"))
    refs = json.loads(D29_REFERENCES.read_text(encoding="utf-8"))

    assert protocol["analysis_A_matched_profile_ensemble"]["seeds"] == list(AUDIT_SEEDS)
    assert protocol["analysis_B_gate_calibration"]["d2_9_calibration_seeds"] == list(D29_SEEDS)
    assert protocol["analysis_B_gate_calibration"]["new_simulation"] is False
    assert protocol["new_seed_use"] is False
    assert protocol["d3_execution_paused_pending_audit"] is True
    assert protocol["d3_worlds_observed_before_audit"] is False
    assert protocol["reserve_30001_30005_blocked"] is True
    assert protocol["primary_blocked"] is True
    assert protocol["external_test_blocked"] is True

    return protocol, refs


def aggregate_six_rotation_layer(layer: pd.DataFrame) -> pd.DataFrame:
    required = {"seed", "rotation", "criterion", "lrv50", "nsv_vector"}
    if not required.issubset(layer.columns):
        raise ValueError(f"Missing Layer-A columns: {required - set(layer.columns)}")

    seed_med = (
        layer.groupby(["seed", "criterion"], as_index=False)
        .agg(
            seed_rotation_median_LRV50=("lrv50", "median"),
            seed_rotation_median_NSV=("nsv_vector", "median"),
        )
    )

    rows = []
    for criterion in C1_C7:
        sub = seed_med.loc[seed_med["criterion"] == criterion]
        if len(sub) != len(AUDIT_SEEDS):
            raise AssertionError(
                f"{criterion}: expected {len(AUDIT_SEEDS)} seed medians, got {len(sub)}."
            )
        rows.append(
            {
                "criterion": criterion,
                "six_rotation_median_LRV50": float(
                    sub["seed_rotation_median_LRV50"].median()
                ),
                "six_rotation_median_NSV_vector": float(
                    sub["seed_rotation_median_NSV"].median()
                ),
            }
        )
    return pd.DataFrame(rows)


def aggregate_six_rotation_reach(reach: pd.DataFrame) -> pd.DataFrame:
    required = {"seed", "rotation", "factor", "criterion", "sre"}
    if not required.issubset(reach.columns):
        raise ValueError(f"Missing reachability columns: {required - set(reach.columns)}")

    frame = reach.copy()
    frame["pathway"] = frame["factor"].astype(str) + "->" + frame["criterion"].astype(str)

    seed_med = (
        frame.groupby(["seed", "pathway"], as_index=False)
        .agg(seed_rotation_median_SRE=("sre", "median"))
    )

    rows = []
    for pathway in sorted(seed_med["pathway"].unique()):
        sub = seed_med.loc[seed_med["pathway"] == pathway]
        if len(sub) != len(AUDIT_SEEDS):
            raise AssertionError(
                f"{pathway}: expected {len(AUDIT_SEEDS)} seed medians, got {len(sub)}."
            )
        rows.append(
            {
                "pathway": pathway,
                "six_rotation_median_SRE": float(
                    sub["seed_rotation_median_SRE"].median()
                ),
            }
        )
    return pd.DataFrame(rows)


def shortfall_fraction_closed(single_ratio: float, matched_ratio: float) -> float:
    if single_ratio >= 1.0:
        return float("nan")
    denom = 1.0 - single_ratio
    if denom <= 0.0:
        return float("nan")
    return float((matched_ratio - single_ratio) / denom)


def build_analysis_a_comparisons(
    six_layer: pd.DataFrame,
    six_reach: pd.DataFrame,
    refs: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frozen_layer = pd.read_csv(V40_LAYER_AGG)
    frozen_reach = pd.read_csv(V40_REACH_AGG)

    layer_rows = []
    for criterion in C1_C7:
        old = frozen_layer.loc[frozen_layer["criterion"] == criterion]
        matched = six_layer.loc[six_layer["criterion"] == criterion]
        if len(old) != 1 or len(matched) != 1:
            raise AssertionError(f"Unexpected aggregate row count for {criterion}.")

        old = old.iloc[0]
        matched = matched.iloc[0]
        ref = refs["layer_a"][criterion]

        single_lrv = float(old["median_LRV50"])
        single_nsv = float(old["median_NSV_vector"])
        six_lrv = float(matched["six_rotation_median_LRV50"])
        six_nsv = float(matched["six_rotation_median_NSV_vector"])
        t_lrv = float(ref["T_sci_LRV"])
        t_nsv = float(ref["T_sci_NSV_vector"])

        single_lrv_ratio = single_lrv / t_lrv
        single_nsv_ratio = single_nsv / t_nsv
        six_lrv_ratio = six_lrv / t_lrv
        six_nsv_ratio = six_nsv / t_nsv

        layer_rows.append(
            {
                "criterion": criterion,
                "support_status": (
                    "support_equivalent"
                    if criterion in SUPPORT_EQUIVALENT
                    else "support_mismatch"
                ),
                "single_median_LRV50": single_lrv,
                "six_rotation_median_LRV50": six_lrv,
                "D29_reference_LRV": t_lrv,
                "single_LRV_ratio": single_lrv_ratio,
                "six_rotation_LRV_ratio": six_lrv_ratio,
                "LRV_ratio_shift": six_lrv_ratio - single_lrv_ratio,
                "LRV_fraction_original_shortfall_closed":
                    shortfall_fraction_closed(single_lrv_ratio, six_lrv_ratio),
                "single_LRV_pass": bool(single_lrv_ratio >= 1.0),
                "six_rotation_LRV_pass": bool(six_lrv_ratio >= 1.0),
                "single_median_NSV_vector": single_nsv,
                "six_rotation_median_NSV_vector": six_nsv,
                "D29_reference_NSV": t_nsv,
                "single_NSV_ratio": single_nsv_ratio,
                "six_rotation_NSV_ratio": six_nsv_ratio,
                "NSV_ratio_shift": six_nsv_ratio - single_nsv_ratio,
                "NSV_fraction_original_shortfall_closed":
                    shortfall_fraction_closed(single_nsv_ratio, six_nsv_ratio),
                "single_NSV_pass": bool(single_nsv_ratio >= 1.0),
                "six_rotation_NSV_pass": bool(six_nsv_ratio >= 1.0),
                "single_layerA_pass": bool(
                    single_lrv_ratio >= 1.0 and single_nsv_ratio >= 1.0
                ),
                "six_rotation_layerA_pass": bool(
                    six_lrv_ratio >= 1.0 and six_nsv_ratio >= 1.0
                ),
            }
        )

    reach_rows = []
    for pathway, ref in sorted(refs["reachability"].items()):
        old = frozen_reach.loc[frozen_reach["pathway"] == pathway]
        matched = six_reach.loc[six_reach["pathway"] == pathway]
        if len(old) != 1 or len(matched) != 1:
            raise AssertionError(f"Unexpected aggregate row count for {pathway}.")

        old = old.iloc[0]
        matched = matched.iloc[0]
        criterion = pathway.split("->", 1)[1]
        single = float(old["median_SRE"])
        six = float(matched["six_rotation_median_SRE"])
        threshold = float(ref["T_sci_SRE"])
        single_ratio = single / threshold
        six_ratio = six / threshold

        reach_rows.append(
            {
                "pathway": pathway,
                "criterion": criterion,
                "support_status": (
                    "support_equivalent"
                    if criterion in SUPPORT_EQUIVALENT
                    else "support_mismatch"
                ),
                "single_median_SRE": single,
                "six_rotation_median_SRE": six,
                "D29_reference_SRE": threshold,
                "single_SRE_ratio": single_ratio,
                "six_rotation_SRE_ratio": six_ratio,
                "SRE_ratio_shift": six_ratio - single_ratio,
                "SRE_fraction_original_shortfall_closed":
                    shortfall_fraction_closed(single_ratio, six_ratio),
                "single_SRE_pass": bool(single_ratio >= 1.0),
                "six_rotation_SRE_pass": bool(six_ratio >= 1.0),
            }
        )

    layer_cmp = pd.DataFrame(layer_rows)
    reach_cmp = pd.DataFrame(reach_rows)

    old_failed_support_equiv_layer = layer_cmp.loc[
        (layer_cmp["support_status"] == "support_equivalent")
        & (~layer_cmp["single_layerA_pass"]),
        "criterion",
    ].astype(str).tolist()

    unresolved_support_equiv_layer = layer_cmp.loc[
        (layer_cmp["support_status"] == "support_equivalent")
        & (~layer_cmp["single_layerA_pass"])
        & (~layer_cmp["six_rotation_layerA_pass"]),
        "criterion",
    ].astype(str).tolist()

    old_failed_support_equiv_reach = reach_cmp.loc[
        (reach_cmp["support_status"] == "support_equivalent")
        & (~reach_cmp["single_SRE_pass"]),
        "pathway",
    ].astype(str).tolist()

    unresolved_support_equiv_reach = reach_cmp.loc[
        (reach_cmp["support_status"] == "support_equivalent")
        & (~reach_cmp["single_SRE_pass"])
        & (~reach_cmp["six_rotation_SRE_pass"]),
        "pathway",
    ].astype(str).tolist()

    all_layer_pass = bool(layer_cmp["six_rotation_layerA_pass"].all())
    all_reach_pass = bool(reach_cmp["six_rotation_SRE_pass"].all())
    all_pass = bool(all_layer_pass and all_reach_pass)

    mismatch_fully_explains = bool(all_pass)
    mismatch_does_not_fully_explain = bool(
        len(unresolved_support_equiv_layer) > 0
        or len(unresolved_support_equiv_reach) > 0
    )

    conclusion = {
        "all_layerA_gates_pass_under_matched_six_rotation": all_layer_pass,
        "all_reachability_gates_pass_under_matched_six_rotation": all_reach_pass,
        "all_old_scientific_gates_pass_under_matched_six_rotation": all_pass,
        "profile_ensemble_mismatch_fully_explains_old_v4_failure":
            mismatch_fully_explains,
        "profile_ensemble_mismatch_does_not_fully_explain_old_v4_failure":
            mismatch_does_not_fully_explain,
        "old_failed_support_equivalent_layerA_criteria":
            old_failed_support_equiv_layer,
        "unresolved_support_equivalent_layerA_criteria":
            unresolved_support_equiv_layer,
        "old_failed_support_equivalent_reachability_pathways":
            old_failed_support_equiv_reach,
        "unresolved_support_equivalent_reachability_pathways":
            unresolved_support_equiv_reach,
        "support_mismatch_criteria": list(SUPPORT_MISMATCH),
        "no_arbitrary_magnitude_cutoff_used": True,
    }

    return layer_cmp, reach_cmp, conclusion


def matrix_from_layer(
    frame: pd.DataFrame,
    criterion: str,
    value_col: str,
) -> np.ndarray:
    arr = np.empty((len(D29_SEEDS), len(ROTATIONS)), dtype=float)
    for i, seed in enumerate(D29_SEEDS):
        for j, rotation in enumerate(ROTATIONS):
            sub = frame.loc[
                (frame["seed"] == seed)
                & (frame["rotation"] == rotation)
                & (frame["criterion"] == criterion),
                value_col,
            ]
            if len(sub) != 1:
                raise AssertionError(
                    f"Expected one D2.9 row for seed={seed}, rotation={rotation}, "
                    f"criterion={criterion}, value={value_col}; got {len(sub)}."
                )
            arr[i, j] = float(sub.iloc[0])
    return arr


def matrix_from_reach(
    frame: pd.DataFrame,
    pathway: str,
) -> np.ndarray:
    factor, criterion = pathway.split("->", 1)
    arr = np.empty((len(D29_SEEDS), len(ROTATIONS)), dtype=float)
    for i, seed in enumerate(D29_SEEDS):
        for j, rotation in enumerate(ROTATIONS):
            sub = frame.loc[
                (frame["seed"] == seed)
                & (frame["rotation"] == rotation)
                & (frame["factor"].astype(str) == factor)
                & (frame["criterion"].astype(str) == criterion),
                "sre",
            ]
            if len(sub) != 1:
                raise AssertionError(
                    f"Expected one D2.9 reach row for seed={seed}, rotation={rotation}, "
                    f"pathway={pathway}; got {len(sub)}."
                )
            arr[i, j] = float(sub.iloc[0])
    return arr


def exact_gate_calibration(
    d29_layer: pd.DataFrame,
    d29_reach: pd.DataFrame,
    refs: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    layer_metrics: list[tuple[str, str, np.ndarray, float]] = []
    for criterion in C1_C7:
        ref = refs["layer_a"][criterion]
        layer_metrics.append(
            (
                f"{criterion}:LRV50",
                "layerA",
                matrix_from_layer(d29_layer, criterion, "lrv50"),
                float(ref["T_sci_LRV"]),
            )
        )
        layer_metrics.append(
            (
                f"{criterion}:NSV_vector",
                "layerA",
                matrix_from_layer(d29_layer, criterion, "nsv_vector"),
                float(ref["T_sci_NSV_vector"]),
            )
        )

    reach_metrics: list[tuple[str, str, np.ndarray, float]] = []
    for pathway, ref in sorted(refs["reachability"].items()):
        reach_metrics.append(
            (
                f"{pathway}:SRE",
                "reachability",
                matrix_from_reach(d29_reach, pathway),
                float(ref["T_sci_SRE"]),
            )
        )

    metrics = layer_metrics + reach_metrics
    pass_counts = {name: 0 for name, _, _, _ in metrics}
    pseudo_rows = []

    seed_idx = np.arange(len(D29_SEEDS), dtype=int)

    layer_joint_count = 0
    reach_joint_count = 0
    overall_joint_count = 0

    total = 0
    min_ratios = []

    for combo in itertools.product(ROTATIONS, repeat=len(D29_SEEDS)):
        rotation_idx = np.asarray(combo, dtype=int)
        ratios = {}
        layer_pass = True
        reach_pass = True

        for name, family, values, threshold in metrics:
            selected = values[seed_idx, rotation_idx]
            candidate_value = float(np.median(selected))
            ratio = candidate_value / threshold
            ratios[name] = ratio
            passed = bool(ratio >= 1.0)
            if passed:
                pass_counts[name] += 1
            if family == "layerA" and not passed:
                layer_pass = False
            if family == "reachability" and not passed:
                reach_pass = False

        overall_pass = bool(layer_pass and reach_pass)
        layer_joint_count += int(layer_pass)
        reach_joint_count += int(reach_pass)
        overall_joint_count += int(overall_pass)

        min_ratio = float(min(ratios.values()))
        min_ratios.append(min_ratio)
        pseudo_rows.append(
            {
                "rotation_25001": combo[0],
                "rotation_25002": combo[1],
                "rotation_25003": combo[2],
                "rotation_25004": combo[3],
                "rotation_25005": combo[4],
                "min_normalized_ratio": min_ratio,
                "layerA_joint_pass": layer_pass,
                "reachability_joint_pass": reach_pass,
                "overall_joint_pass": overall_pass,
            }
        )
        total += 1

    expected = len(ROTATIONS) ** len(D29_SEEDS)
    if total != expected:
        raise AssertionError(f"Expected {expected} pseudo-candidates, got {total}.")

    rate_rows = []
    for name, family, _, _ in metrics:
        rate_rows.append(
            {
                "metric": name,
                "family": family,
                "pass_count": int(pass_counts[name]),
                "pseudo_candidate_count": total,
                "pass_proportion": float(pass_counts[name] / total),
            }
        )

    rates = pd.DataFrame(rate_rows)
    pseudo = pd.DataFrame(pseudo_rows)

    min_arr = np.asarray(min_ratios, dtype=float)
    q_probs = [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0]
    quantiles = {
        f"q{int(round(p * 100)):02d}": float(np.quantile(min_arr, p, method="linear"))
        for p in q_probs
    }

    joint = {
        "pseudo_candidate_count": total,
        "layerA_joint_pass_count": int(layer_joint_count),
        "layerA_joint_pass_proportion": float(layer_joint_count / total),
        "reachability_joint_pass_count": int(reach_joint_count),
        "reachability_joint_pass_proportion": float(reach_joint_count / total),
        "overall_joint_pass_count": int(overall_joint_count),
        "overall_joint_pass_proportion": float(overall_joint_count / total),
        "conditional_on_five_frozen_D29_worlds": True,
        "independent_type_I_error_estimate": False,
        "posthoc_acceptability_cutoff_used": False,
    }

    distribution = {
        "pseudo_candidate_count": total,
        "minimum_normalized_ratio_mean": float(min_arr.mean()),
        "minimum_normalized_ratio_sd_ddof0": float(min_arr.std(ddof=0)),
        "minimum_normalized_ratio_min": float(min_arr.min()),
        "minimum_normalized_ratio_max": float(min_arr.max()),
        "quantiles": quantiles,
    }

    return rates, pseudo, joint, distribution


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    commit, branch = require_clean_git()
    if branch != "audit-d29-gate-validity":
        raise RuntimeError(f"Unexpected branch {branch!r}.")
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing audit output: {output_dir}")

    protocol, refs = load_protocol_and_refs()

    step1 = load_module(
        "gate_audit_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = load_module(
        "gate_audit_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )

    benchmark = d29.load_yaml(ROOT / "config" / "benchmark.yaml")
    experiment = d29.load_yaml(ROOT / "config" / "experiment.yaml")
    seeds_cfg = d29.load_yaml(ROOT / "config" / "seeds.yaml")

    benchmark0 = copy.deepcopy(benchmark)
    benchmark0["technology_response"]["criterion_noise"]["sigma_x"] = SIGMA_X

    matched_layer_rows = []
    matched_reach_rows = []

    for seed in AUDIT_SEEDS:
        contexts, audit = step1.generate_master_contexts(
            replication_seed=seed,
            rho=RHO,
            benchmark=benchmark,
            experiment=experiment,
            seeds=seeds_cfg,
        )

        contexts_est = (
            contexts.loc[contexts["partition"].isin(("fit", "weight"))]
            .copy()
            .sort_values("context_number")
            .reset_index(drop=True)
        )
        audit_est = (
            audit.loc[audit["context_number"].isin(contexts_est["context_number"])]
            .copy()
            .sort_values("context_number")
            .reset_index(drop=True)
        )

        if len(contexts_est) != 1000:
            raise AssertionError("Analysis A requires exactly 1000 FIT+WEIGHT contexts.")
        if contexts_est["partition"].eq("test").any():
            raise AssertionError("External TEST entered Analysis A.")

        baseline, cap_params, _, _ = step2.generate_master_technology_responses(
            contexts=contexts_est,
            replication_seed=seed,
            benchmark=benchmark0,
        )
        baseline = (
            baseline.sort_values(["context_number", "alternative_id"])
            .reset_index(drop=True)
        )
        opportunities = step2.compute_opportunities(contexts_est, benchmark)

        for rotation in ROTATIONS:
            pc = d29.build_positive_control(
                baseline=baseline,
                opportunities=opportunities,
                capability_parameters=cap_params,
                benchmark=benchmark,
                rotation=rotation,
            )

            layer_rows, _ = d29.layer_a_metrics(
                pc=pc,
                benchmark=benchmark,
                seed=seed,
                rotation=rotation,
            )
            matched_layer_rows.extend(layer_rows)

            reach_rows = d29.reachability_metrics(
                contexts=contexts_est,
                audit=audit_est,
                base_opportunities=opportunities,
                capability_parameters=cap_params,
                benchmark=benchmark,
                step2=step2,
                seed=seed,
                rotation=rotation,
            )
            matched_reach_rows.extend(reach_rows)

    matched_layer = pd.DataFrame(matched_layer_rows)
    matched_reach = pd.DataFrame(matched_reach_rows)

    if len(matched_layer) != len(AUDIT_SEEDS) * 6 * 7:
        raise AssertionError(f"Unexpected matched Layer-A row count: {len(matched_layer)}")
    if len(matched_reach) != len(AUDIT_SEEDS) * 6 * len(refs["reachability"]):
        raise AssertionError(
            f"Unexpected matched reachability row count: {len(matched_reach)}"
        )

    six_layer = aggregate_six_rotation_layer(matched_layer)
    six_reach = aggregate_six_rotation_reach(matched_reach)

    layer_cmp, reach_cmp, analysis_a = build_analysis_a_comparisons(
        six_layer, six_reach, refs
    )

    d29_layer = pd.read_csv(D29_LAYER)
    d29_reach = pd.read_csv(D29_REACH)

    rates, pseudo, joint, distribution = exact_gate_calibration(
        d29_layer, d29_reach, refs
    )

    output_dir.mkdir(parents=True, exist_ok=False)

    matched_layer.to_csv(output_dir / "analysis_A_six_rotation_layer_per_seed_rotation.csv", index=False)
    matched_reach.to_csv(output_dir / "analysis_A_six_rotation_reach_per_seed_rotation.csv", index=False)
    six_layer.to_csv(output_dir / "analysis_A_six_rotation_layer_aggregated.csv", index=False)
    six_reach.to_csv(output_dir / "analysis_A_six_rotation_reach_aggregated.csv", index=False)
    layer_cmp.to_csv(output_dir / "analysis_A_layer_comparison.csv", index=False)
    reach_cmp.to_csv(output_dir / "analysis_A_reach_comparison.csv", index=False)
    rates.to_csv(output_dir / "analysis_B_metric_pass_rates.csv", index=False)
    pseudo.to_csv(output_dir / "analysis_B_pseudo_candidate_joint_results.csv", index=False)

    (output_dir / "analysis_A_conclusion.json").write_text(
        json.dumps(analysis_a, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "analysis_B_joint_summary.json").write_text(
        json.dumps(joint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "analysis_B_min_ratio_distribution.json").write_text(
        json.dumps(distribution, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "audit_protocol_file": str(AUDIT_PROTOCOL.relative_to(ROOT)),
        "analysis_A_seeds": list(AUDIT_SEEDS),
        "analysis_B_D29_seeds": list(D29_SEEDS),
        "rotations": list(ROTATIONS),
        "pseudo_candidate_count": 6 ** 5,
        "new_seeds_used": False,
        "D3_worlds_used": False,
        "reserve_30001_30005_used": False,
        "primary_11001_11030_used": False,
        "external_TEST_used": False,
        "response_formula_changed": False,
        "delta_changed": False,
        "thresholds_changed": False,
        "SHAP_or_MCDM_or_winner_outcomes_used": False,
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = [
        "POST-v4 D2.9 HARD-GATE VALIDITY AUDIT",
        f"git_commit: {commit}",
        f"analysis_A_seeds: {AUDIT_SEEDS}",
        f"analysis_B_pseudo_candidates: {joint['pseudo_candidate_count']}",
        "new_seeds_used: False",
        "D3_worlds_used: False",
        "reserve_30001_30005_used: False",
        "primary_11001_11030_used: False",
        "external_TEST_used: False",
        "",
        "ANALYSIS A — MATCHED SIX-ROTATION PROFILE ENSEMBLE",
        (
            "all_layerA_pass="
            f"{analysis_a['all_layerA_gates_pass_under_matched_six_rotation']}; "
            "all_reachability_pass="
            f"{analysis_a['all_reachability_gates_pass_under_matched_six_rotation']}; "
            "all_scientific_gates_pass="
            f"{analysis_a['all_old_scientific_gates_pass_under_matched_six_rotation']}"
        ),
        (
            "mismatch_fully_explains_old_v4_failure="
            f"{analysis_a['profile_ensemble_mismatch_fully_explains_old_v4_failure']}"
        ),
        (
            "mismatch_does_not_fully_explain_old_v4_failure="
            f"{analysis_a['profile_ensemble_mismatch_does_not_fully_explain_old_v4_failure']}"
        ),
        (
            "unresolved_support_equivalent_layerA="
            f"{analysis_a['unresolved_support_equivalent_layerA_criteria']}"
        ),
        (
            "unresolved_support_equivalent_reachability="
            f"{analysis_a['unresolved_support_equivalent_reachability_pathways']}"
        ),
        "",
        "ANALYSIS B — CONDITIONAL COMBINATORIAL OLD-GATE CALIBRATION",
        f"layerA_joint_pass_proportion={joint['layerA_joint_pass_proportion']:.9f}",
        f"reachability_joint_pass_proportion={joint['reachability_joint_pass_proportion']:.9f}",
        f"overall_joint_pass_proportion={joint['overall_joint_pass_proportion']:.9f}",
        (
            "median_min_normalized_ratio="
            f"{distribution['quantiles']['q50']:.9f}"
        ),
        "",
        "No post-hoc acceptable-pass-rate cutoff is applied.",
        "Audit output is diagnostic and does not itself rewrite the production freeze.",
    ]
    (output_dir / "summary.txt").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )

    print("\n".join(summary))
    print(f"WROTE: {output_dir}")

    return {
        "analysis_A": analysis_a,
        "analysis_B_joint": joint,
        "analysis_B_distribution": distribution,
    }


if __name__ == "__main__":
    run()
