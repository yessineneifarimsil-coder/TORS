from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

STRUCTURAL_VALIDATION_SEEDS = (22001, 22002, 22003, 22004, 22005)
RESERVED_SEEDS = (30001, 30002, 30003, 30004, 30005)
PRIMARY_SEEDS = tuple(range(11001, 11031))

RHO = 0.4
SIGMA_X = 0.0
LAMBDA_VALUE = 0.5
SIGNED_PROFILE_NAMESPACE = 2010
DELTA = 0.05
CANDIDATE_ID = "d29_kernel"

CORRECTED_PROTOCOL = (
    ROOT / "config" / "corrected_production_eligibility_v1.json"
)
D29_REFERENCES = (
    ROOT / "results" / "d2_9_admissible_positive_control" / "references.json"
)
D28_THRESHOLDS = (
    ROOT / "results" / "v2_2_d2_8_numerical_null" / "thresholds.json"
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


v40 = load_numbered_module(
    "corrected_validation_v40",
    ROOT / "src" / "v4_0_f1_terminal_d29_kernel_evaluator.py",
)
d27 = v40.d27


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
            "CORRECTED STRUCTURAL VALIDATION REFUSES TO RUN FROM A DIRTY "
            "WORKING TREE.\nCommit or restore all changes before validation.\n"
            f"Current status:\n{status}"
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("rev-parse", "--abbrev-ref", "HEAD"),
    )


def load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = json.loads(
        CORRECTED_PROTOCOL.read_text(encoding="utf-8")
    )
    d29_refs = json.loads(
        D29_REFERENCES.read_text(encoding="utf-8")
    )
    d28_thresholds = json.loads(
        D28_THRESHOLDS.read_text(encoding="utf-8")
    )

    sv = protocol["structural_validation"]
    if sv["seeds"] != list(STRUCTURAL_VALIDATION_SEEDS):
        raise RuntimeError("Corrected protocol validation seeds drifted.")
    if sv["one_shot"] is not True:
        raise RuntimeError("Corrected protocol no longer requires one-shot validation.")
    if sv["parameter_tuning_allowed"] is not False:
        raise RuntimeError("Parameter tuning unexpectedly allowed.")
    if sv["d29_ratios_used_for_pass_fail"] is not False:
        raise RuntimeError("D2.9 ratios unexpectedly re-entered pass/fail.")
    if protocol["d29_role"]["binary_eligibility_gate"] is not False:
        raise RuntimeError("D2.9 binary eligibility unexpectedly re-enabled.")

    if float(sv["delta"]) != DELTA:
        raise RuntimeError("delta drifted from corrected protocol.")
    if int(sv["namespace"]) != SIGNED_PROFILE_NAMESPACE:
        raise RuntimeError("signed-profile namespace drifted.")
    if float(sv["rho"]) != RHO:
        raise RuntimeError("rho drifted.")
    if float(sv["sigma_x"]) != SIGMA_X:
        raise RuntimeError("sigma_x drifted.")
    if float(sv["lambda"]) != LAMBDA_VALUE:
        raise RuntimeError("lambda drifted.")

    return protocol, d29_refs, d28_thresholds


def aggregate_layer_a_diagnostics(
    layer_a: pd.DataFrame,
    d29_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for criterion in v40.C1_C7:
        sub = layer_a.loc[layer_a["criterion"] == criterion]
        if len(sub) != len(STRUCTURAL_VALIDATION_SEEDS):
            raise AssertionError(
                f"{criterion}: expected {len(STRUCTURAL_VALIDATION_SEEDS)} rows."
            )

        median_lrv = float(sub["LRV50"].median())
        median_nsv = float(sub["NSV_vector"].median())
        ref = d29_refs["layer_a"][criterion]
        t_lrv = float(ref["T_sci_LRV"])
        t_nsv = float(ref["T_sci_NSV_vector"])

        rows.append(
            {
                "criterion": criterion,
                "median_LRV50": median_lrv,
                "D29_reference_LRV": t_lrv,
                "LRV_to_D29_ratio": median_lrv / t_lrv,
                "median_NSV_vector": median_nsv,
                "D29_reference_NSV_vector": t_nsv,
                "NSV_to_D29_ratio": median_nsv / t_nsv,
                "D29_LRV_reference_met_descriptive":
                    bool(median_lrv >= t_lrv),
                "D29_NSV_reference_met_descriptive":
                    bool(median_nsv >= t_nsv),
                "all_seed_num_NS": bool(sub["pass_num_NS"].all()),
                "all_seed_num_LRV": bool(sub["pass_num_LRV"].all()),
                "all_seed_num_NSV": bool(sub["pass_num_NSV"].all()),
                "D29_used_for_pass_fail": False,
            }
        )
    return pd.DataFrame(rows)


def aggregate_reachability_diagnostics(
    reachability: pd.DataFrame,
    d29_refs: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for pathway, ref in sorted(d29_refs["reachability"].items()):
        sub = reachability.loc[
            reachability["pathway"] == pathway
        ]
        if len(sub) != len(STRUCTURAL_VALIDATION_SEEDS):
            raise AssertionError(
                f"{pathway}: expected {len(STRUCTURAL_VALIDATION_SEEDS)} rows."
            )

        median_sre = float(sub["SRE"].median())
        threshold = float(ref["T_sci_SRE"])
        factor, criterion = pathway.split("->", 1)

        rows.append(
            {
                "pathway": pathway,
                "factor": factor,
                "criterion": criterion,
                "median_SRE": median_sre,
                "D29_reference_SRE": threshold,
                "SRE_to_D29_ratio": median_sre / threshold,
                "D29_SRE_reference_met_descriptive":
                    bool(median_sre >= threshold),
                "D29_used_for_pass_fail": False,
            }
        )
    return pd.DataFrame(rows)


def corrected_gate_summary(
    layer_a_agg: pd.DataFrame,
    boundary: pd.DataFrame,
    c8_c10_invariance: pd.DataFrame,
) -> pd.DataFrame:
    if len(layer_a_agg) != 7:
        raise AssertionError("Expected seven Layer-A diagnostic rows.")
    if len(boundary) != 35:
        raise AssertionError("Expected 35 seed/criterion invariant rows.")
    if len(c8_c10_invariance) != 5:
        raise AssertionError("Expected five C8-C10 invariance rows.")

    pass_numerical = bool(
        layer_a_agg[
            [
                "all_seed_num_NS",
                "all_seed_num_LRV",
                "all_seed_num_NSV",
            ]
        ].to_numpy(dtype=bool).all()
    )

    invariant_cols = [
        "lower_bound_ok",
        "class_ceiling_ok",
        "theta_support_ok",
        "monotonicity_ok",
        "endpoint_zero_ok",
        "endpoint_theta_ok",
        "structural_zero_ok",
    ]
    pass_response_invariants = bool(
        boundary[invariant_cols].to_numpy(dtype=bool).all()
    )
    pass_c8_c10 = bool(
        c8_c10_invariance["C8_C10_unchanged"].all()
    )
    pass_invariants = bool(
        pass_response_invariants and pass_c8_c10
    )

    validation_passed = bool(
        pass_numerical and pass_invariants
    )

    return pd.DataFrame(
        [
            {
                "candidate_id": CANDIDATE_ID,
                "pass_D2_8_numerical_non_degeneracy":
                    pass_numerical,
                "pass_analytic_response_invariants":
                    pass_response_invariants,
                "pass_C8_C10_invariance":
                    pass_c8_c10,
                "pass_all_corrected_invariants":
                    pass_invariants,
                "D29_LRV_NSV_SRE_used_for_pass_fail":
                    False,
                "validation_passed":
                    validation_passed,
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
    protocol, d29_refs, d28_thresholds = load_frozen_inputs()

    step1 = load_numbered_module(
        "corrected_validation_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = load_numbered_module(
        "corrected_validation_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
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

    benchmark0 = copy.deepcopy(benchmark)
    benchmark0[
        "technology_response"
    ][
        "criterion_noise"
    ][
        "sigma_x"
    ] = SIGMA_X

    profile_rows = []
    layer_a_rows = []
    reachability_rows = []
    boundary_rows = []
    departure_rows = []
    c8_c10_rows = []

    for seed in STRUCTURAL_VALIDATION_SEEDS:
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
                "Corrected structural validation requires exactly "
                "1000 FIT+WEIGHT contexts."
            )
        if contexts_est["partition"].eq("test").any():
            raise AssertionError(
                "External TEST entered corrected structural validation."
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

        profiles = v40.all_signed_profiles(
            seed,
            benchmark,
        )
        for criterion, profile in profiles.items():
            active_ids = set(profile)
            for alt_id in v40.ordered_alternative_ids(benchmark):
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

        candidate = v40.build_candidate_responses(
            baseline=baseline,
            opportunities=opportunities,
            capability_parameters=cap_params,
            benchmark=benchmark,
            replication_seed=seed,
        )

        layer_a_rows.extend(
            v40.layer_a_for_candidate(
                frame=candidate,
                benchmark=benchmark,
                seed=seed,
                d28_thresholds=d28_thresholds,
            )
        )
        reachability_rows.extend(
            v40.reachability_for_candidate(
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
            v40.boundary_diagnostics(
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

    profiles_df = pd.DataFrame(profile_rows)
    layer_a = pd.DataFrame(layer_a_rows)
    reachability = pd.DataFrame(reachability_rows)
    boundary = pd.DataFrame(boundary_rows)
    departure = pd.DataFrame(departure_rows)
    c8_c10 = pd.DataFrame(c8_c10_rows)

    layer_a_agg = aggregate_layer_a_diagnostics(
        layer_a,
        d29_refs,
    )
    reachability_agg = aggregate_reachability_diagnostics(
        reachability,
        d29_refs,
    )
    gate = corrected_gate_summary(
        layer_a_agg,
        boundary,
        c8_c10,
    )

    validation_passed = bool(
        gate.iloc[0]["validation_passed"]
    )

    output_dir.mkdir(parents=True, exist_ok=False)

    outputs = {
        "signed_profiles.csv": profiles_df,
        "layer_a_per_seed.csv": layer_a,
        "layer_a_diagnostics.csv": layer_a_agg,
        "reachability_per_seed.csv": reachability,
        "reachability_diagnostics.csv": reachability_agg,
        "boundary_diagnostics.csv": boundary,
        "departure_diagnostics.csv": departure,
        "c8_c10_invariance.csv": c8_c10,
        "corrected_gate_summary.csv": gate,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / name, index=False)

    decision = {
        "candidate_id": CANDIDATE_ID,
        "validation_stage": "one-shot structural validation",
        "validation_passed": validation_passed,
        "production_generator_eligible_for_freeze":
            validation_passed,
        "response_formula": "theta*o + 0.05*v*o*(1-o)",
        "delta": DELTA,
        "signed_profile_namespace": SIGNED_PROFILE_NAMESPACE,
        "parameter_tuning": False,
        "fallback_candidate_selection": False,
        "D29_LRV_NSV_SRE_used_for_pass_fail": False,
        "D29_structural_diagnostics_reported": True,
    }
    write_json(output_dir / "decision.json", decision)

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "corrected_protocol_file":
            str(CORRECTED_PROTOCOL.relative_to(ROOT)),
        "structural_validation_seeds":
            list(STRUCTURAL_VALIDATION_SEEDS),
        "rho": RHO,
        "sigma_x": SIGMA_X,
        "lambda": LAMBDA_VALUE,
        "signed_profile_namespace":
            SIGNED_PROFILE_NAMESPACE,
        "delta": DELTA,
        "one_shot": True,
        "parameter_tuning_allowed": False,
        "D29_ratios_used_for_pass_fail": False,
        "external_test_used": False,
        "reserve_seeds_used": False,
        "primary_seeds_used": False,
        "reserve_seeds": list(RESERVED_SEEDS),
        "primary_seeds": list(PRIMARY_SEEDS),
        "production_generator_modified": False,
        "D29_reference_file":
            str(D29_REFERENCES.relative_to(ROOT)),
        "D28_threshold_file":
            str(D28_THRESHOLDS.relative_to(ROOT)),
    }
    write_json(output_dir / "run_metadata.json", metadata)

    row = gate.iloc[0]
    min_layer = float(
        min(
            layer_a_agg["LRV_to_D29_ratio"].min(),
            layer_a_agg["NSV_to_D29_ratio"].min(),
        )
    )
    min_sre = float(
        reachability_agg["SRE_to_D29_ratio"].min()
    )

    summary_lines = [
        "CORRECTED ONE-SHOT STRUCTURAL VALIDATION",
        f"git_commit: {commit}",
        f"structural_validation_seeds: {STRUCTURAL_VALIDATION_SEEDS}",
        f"candidate_id: {CANDIDATE_ID}",
        f"delta: {DELTA}",
        f"signed_profile_namespace: {SIGNED_PROFILE_NAMESPACE}",
        "parameter_tuning_allowed: False",
        "external_TEST_used: False",
        "reserve_seeds_used: False",
        "primary_seeds_used: False",
        "D29_LRV_NSV_SRE_used_for_pass_fail: False",
        "",
        "CORRECTED HARD GATES",
        (
            "D2.8_numerical="
            f"{bool(row.pass_D2_8_numerical_non_degeneracy)}; "
            "analytic_invariants="
            f"{bool(row.pass_analytic_response_invariants)}; "
            "C8_C10="
            f"{bool(row.pass_C8_C10_invariance)}; "
            "validation_passed="
            f"{bool(row.validation_passed)}"
        ),
        "",
        "DESCRIPTIVE D2.9-NORMALIZED STRUCTURAL DIAGNOSTICS",
        f"minimum_LayerA_ratio_to_D29: {min_layer:.9f}",
        f"minimum_SRE_ratio_to_D29: {min_sre:.9f}",
        "These ratios do not determine pass/fail.",
        "",
        f"VALIDATION_PASSED: {validation_passed}",
        (
            "PRODUCTION_GENERATOR_ELIGIBLE_FOR_FREEZE: "
            f"{validation_passed}"
        ),
    ]

    (output_dir / "summary.txt").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print("\n".join(summary_lines))
    print(f"WROTE: {output_dir}")

    return {
        "validation_passed": validation_passed,
        "decision": decision,
        "metadata": metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the corrected one-shot structural validation for the "
            "frozen v4.0 D2.9-kernel response generator."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "results"
            / "corrected_structural_validation_v1"
        ),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
