from __future__ import annotations

"""One-shot D29 Layer-B decision-geometry characterization.

This implementation follows the committed
``config/d29_layer_b_characterization_v1.json`` contract. It characterizes the
already-retained D29 kernel descriptively on development seeds 21001--21005.
It cannot change generator retention and defines no pass/fail threshold.

Scientific reconstruction reuses the existing production pipeline:
contexts -> zero-noise baseline responses -> D29 responses -> noise-free oracle.
No Y, XGBoost, SHAP, weighting method, MCDM operator, primary seed, reserve seed,
or external TEST row contributes to the reported characterization.
"""

from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_PATH = ROOT / "config" / "d29_layer_b_characterization_v1.json"
BENCHMARK_PATH = ROOT / "config" / "benchmark.yaml"
EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"
SEEDS_PATH = ROOT / "config" / "seeds.yaml"

STEP1_PATH = ROOT / "src" / "01_generate_contexts.py"
STEP2_PATH = ROOT / "src" / "02_generate_technology_responses.py"
STEP3_PATH = ROOT / "src" / "03_generate_oracle_utility.py"
D29_PATH = ROOT / "src" / "v4_0_f1_terminal_d29_kernel_evaluator.py"
DECISION_PATH = ROOT / "src" / "decision_semantics_v1.py"

DEFAULT_OUTPUT_DIR = ROOT / "results" / "d29_layer_b_characterization_v1"

DEVELOPMENT_SEEDS = (21001, 21002, 21003, 21004, 21005)
PRIMARY_SEEDS = tuple(range(11001, 11031))
RESERVE_SEEDS = tuple(range(30001, 30006))
STRUCTURAL_VALIDATION_SEEDS = tuple(range(22001, 22006))

RHO = 0.4
SIGMA_X = 0.0
LAMBDA_VALUE = 0.5
N_CONTEXTS = 1000
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
ESTIMATION_PARTITIONS = ("fit", "weight")
REGRET_RANGE_TOL = 1.0e-12
P95_METHOD = "linear"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}.")
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
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping in {path}.")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON mapping in {path}.")
    return payload


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = git_output("status", "--porcelain")
    if status:
        raise RuntimeError(
            "D29 Layer-B characterization refuses to run from a dirty worktree.\n"
            f"Current status:\n{status}"
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    if protocol["protocol_name"] != "d29_layer_b_characterization_v1":
        raise ValueError("Unexpected D29 Layer-B protocol identity.")
    if protocol["status"] != "freeze_before_characterization_execution":
        raise ValueError("D29 Layer-B protocol is not in frozen pre-execution state.")
    if protocol["retention_effect"] != "none":
        raise ValueError("D29 Layer-B characterization must not affect retention.")
    if protocol["can_change_d29_retention"] is not False:
        raise ValueError("Protocol unexpectedly permits D29 retention changes.")
    if protocol["can_change_corrected_eligible_set"] is not False:
        raise ValueError("Protocol unexpectedly permits eligible-set changes.")
    if protocol["can_create_new_generator_gate"] is not False:
        raise ValueError("Protocol unexpectedly permits a new generator gate.")
    if protocol["pass_fail_thresholds"] is not None:
        raise ValueError("D29 Layer-B characterization must have no pass/fail threshold.")

    if tuple(protocol["seeds"]["development"]) != DEVELOPMENT_SEEDS:
        raise ValueError("Development seed set changed from the frozen protocol.")
    if protocol["seeds"]["primary_allowed"] is not False:
        raise ValueError("Primary seeds are forbidden.")
    if protocol["seeds"]["reserve_allowed"] is not False:
        raise ValueError("Reserve seeds are forbidden.")
    if protocol["seeds"]["structural_validation_allowed"] is not False:
        raise ValueError("Structural-validation seeds are forbidden.")

    condition = protocol["condition"]
    expected = {
        "rho": RHO,
        "sigma_x": SIGMA_X,
        "lambda": LAMBDA_VALUE,
        "target_noise_used": False,
        "c": None,
        "N": N_CONTEXTS,
    }
    if condition != expected:
        raise ValueError(f"Frozen Layer-B condition changed: {condition!r}.")

    contexts = protocol["contexts"]
    if contexts["pool"] != "estimation_master_fit_plus_weight":
        raise ValueError("Unexpected Layer-B context pool.")
    if contexts["n_contexts_per_seed"] != N_CONTEXTS:
        raise ValueError("Layer-B must use exactly 1000 estimation contexts.")
    if contexts["external_test_used"] is not False:
        raise ValueError("External TEST is forbidden.")

    if protocol["normalized_regret"]["undefined_if_denominator_le"] != REGRET_RANGE_TOL:
        raise ValueError("Normalized-regret threshold changed.")
    if protocol["normalized_regret"]["epsilon_regularization"] is not False:
        raise ValueError("Normalized regret must not epsilon-regularize its denominator.")

    if protocol["execution"]["one_shot"] is not True:
        raise ValueError("Layer-B execution must remain one-shot.")
    if protocol["execution"]["result_overwrite_forbidden"] is not True:
        raise ValueError("Layer-B result overwrite must remain forbidden.")


def ordered_benchmark_alternative_ids(benchmark: Mapping[str, Any]) -> tuple[str, ...]:
    ids = tuple(
        str(alternative["id"])
        for _, alternative in benchmark["alternatives"].items()
    )
    if set(ids) != set(ALTERNATIVE_IDS) or len(ids) != len(ALTERNATIVE_IDS):
        raise ValueError(
            f"Benchmark alternatives must be exactly {ALTERNATIVE_IDS}; found {ids}."
        )
    return ALTERNATIVE_IDS


def _validated_oracle_frame(
    oracle_rows: pd.DataFrame,
    *,
    replication_seed: int,
) -> pd.DataFrame:
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        "U_star",
    }
    missing = sorted(required - set(oracle_rows.columns))
    if missing:
        raise ValueError(f"Oracle frame is missing columns: {missing}.")
    if oracle_rows.empty:
        raise ValueError("Oracle frame must not be empty.")

    frame = oracle_rows.copy()

    if frame["replication_seed"].isna().any():
        raise ValueError("replication_seed contains missing values.")
    seeds = set(frame["replication_seed"].astype(int).tolist())
    if seeds != {int(replication_seed)}:
        raise ValueError(
            f"Expected only replication_seed={replication_seed}; found {sorted(seeds)}."
        )

    if frame["partition"].eq("test").any():
        raise ValueError("External TEST row entered D29 Layer-B characterization.")
    if not set(frame["partition"]) <= set(ESTIMATION_PARTITIONS):
        raise ValueError("Unexpected partition in Layer-B oracle frame.")

    if frame["context_number"].min() < 1 or frame["context_number"].max() > N_CONTEXTS:
        raise ValueError("Layer-B context_number escaped the frozen 1..1000 scope.")
    if frame["context_number"].nunique() != N_CONTEXTS:
        raise ValueError("Layer-B requires exactly 1000 unique estimation contexts.")

    if frame.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate context-alternative oracle rows detected.")

    u = frame["U_star"].to_numpy(dtype=float)
    if not np.isfinite(u).all():
        raise ValueError("U_star contains non-finite values.")
    if np.any(u < -REGRET_RANGE_TOL) or np.any(u > 1.0 + REGRET_RANGE_TOL):
        raise ValueError("U_star escaped the theoretical [0,1] range.")

    grouped_ids = frame.groupby("context_number", sort=True)["alternative_id"].agg(
        lambda x: tuple(sorted(str(v) for v in x))
    )
    if len(grouped_ids) != N_CONTEXTS:
        raise AssertionError("Unexpected number of grouped contexts.")
    expected_sorted = tuple(sorted(ALTERNATIVE_IDS))
    if any(ids != expected_sorted for ids in grouped_ids):
        raise ValueError("Every Layer-B context must contain exactly A1..A6.")

    counts = frame.groupby("context_number", sort=True).size()
    if not (counts == len(ALTERNATIVE_IDS)).all():
        raise ValueError("Every Layer-B context must contain exactly six rows.")

    return frame.sort_values(
        ["context_number", "alternative_id"],
        kind="stable",
    ).reset_index(drop=True)


def characterize_oracle_rows(
    oracle_rows: pd.DataFrame,
    *,
    replication_seed: int,
    decision_module: Any,
) -> dict[str, Any]:
    """Compute the frozen per-seed Layer-B decision-geometry metrics."""
    frame = _validated_oracle_frame(
        oracle_rows,
        replication_seed=replication_seed,
    )

    ranking_signatures: list[tuple[float, ...]] = []
    winners: list[str] = []
    score_by_context: dict[int, dict[str, float]] = {}

    for context_number, group in frame.groupby("context_number", sort=True):
        indexed = group.set_index("alternative_id")
        scores = np.asarray(
            [float(indexed.loc[alt_id, "U_star"]) for alt_id in ALTERNATIVE_IDS],
            dtype=float,
        )

        ranks = decision_module.average_ranks_descending(scores, ALTERNATIVE_IDS)
        ranking_signatures.append(tuple(float(x) for x in ranks))

        winner = str(decision_module.deterministic_top1(scores, ALTERNATIVE_IDS))
        winners.append(winner)

        score_by_context[int(context_number)] = {
            alt_id: float(score)
            for alt_id, score in zip(ALTERNATIVE_IDS, scores, strict=True)
        }

    winner_counts = Counter(winners)
    maximum_frequency = max(winner_counts.values())
    modal_candidates = sorted(
        alt_id
        for alt_id, count in winner_counts.items()
        if count == maximum_frequency
    )
    modal_winner = modal_candidates[0]
    modal_share = maximum_frequency / float(N_CONTEXTS)

    regrets: list[float] = []
    undefined_count = 0
    for context_number in range(1, N_CONTEXTS + 1):
        score_map = score_by_context[context_number]
        scores = np.asarray([score_map[a] for a in ALTERNATIVE_IDS], dtype=float)
        maximum = float(np.max(scores))
        minimum = float(np.min(scores))
        denominator = maximum - minimum

        if denominator <= REGRET_RANGE_TOL:
            undefined_count += 1
            continue

        modal_score = float(score_map[modal_winner])
        regret = (maximum - modal_score) / denominator

        if regret < -REGRET_RANGE_TOL or regret > 1.0 + REGRET_RANGE_TOL:
            raise FloatingPointError(
                f"Normalized modal regret escaped [0,1]: {regret}."
            )
        regrets.append(float(np.clip(regret, 0.0, 1.0)))

    if regrets:
        regret_array = np.asarray(regrets, dtype=float)
        mean_regret = float(np.mean(regret_array))
        median_regret = float(np.median(regret_array))
        p95_regret = float(np.quantile(regret_array, 0.95, method=P95_METHOD))
    else:
        mean_regret = None
        median_regret = None
        p95_regret = None

    return {
        "replication_seed": int(replication_seed),
        "contexts": N_CONTEXTS,
        "alternatives_per_context": len(ALTERNATIVE_IDS),
        "distinct_complete_oracle_orderings": int(len(set(ranking_signatures))),
        "distinct_deterministic_oracle_winners": int(len(set(winners))),
        "modal_oracle_winner_id": modal_winner,
        "modal_oracle_winner_share": float(modal_share),
        "modal_baseline_mean_normalized_oracle_regret": mean_regret,
        "modal_baseline_median_normalized_oracle_regret": median_regret,
        "modal_baseline_p95_normalized_oracle_regret": p95_regret,
        "undefined_normalized_regret_context_count": int(undefined_count),
        "defined_normalized_regret_context_count": int(len(regrets)),
        "p95_quantile_method": P95_METHOD,
        "retention_effect": "none",
        "pass_fail_threshold": None,
    }


def summarize_seed_metrics(seed_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    if len(seed_rows) != len(DEVELOPMENT_SEEDS):
        raise ValueError("Cross-seed summary requires exactly five development-seed rows.")

    observed = tuple(sorted(int(row["replication_seed"]) for row in seed_rows))
    if observed != DEVELOPMENT_SEEDS:
        raise ValueError(f"Unexpected development seeds in summary: {observed}.")

    numeric_metrics = (
        "distinct_complete_oracle_orderings",
        "distinct_deterministic_oracle_winners",
        "modal_oracle_winner_share",
        "modal_baseline_mean_normalized_oracle_regret",
        "modal_baseline_median_normalized_oracle_regret",
        "modal_baseline_p95_normalized_oracle_regret",
        "undefined_normalized_regret_context_count",
    )

    summary: dict[str, Any] = {
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "n_seeds": len(DEVELOPMENT_SEEDS),
        "retention_effect": "none",
        "pass_fail_threshold": None,
        "winner_identity_used_for_optimization": False,
        "metrics": {},
    }

    for metric in numeric_metrics:
        values = [row[metric] for row in seed_rows]
        if any(value is None for value in values):
            summary["metrics"][metric] = {
                "median": None,
                "min": None,
                "max": None,
                "undefined_across_seed_summary": True,
            }
            continue

        arr = np.asarray(values, dtype=float)
        summary["metrics"][metric] = {
            "median": float(np.median(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "undefined_across_seed_summary": False,
        }

    return summary


def load_pipeline_modules() -> dict[str, Any]:
    return {
        "step1": load_module("d29_layer_b_step1", STEP1_PATH),
        "step2": load_module("d29_layer_b_step2", STEP2_PATH),
        "step3": load_module("d29_layer_b_step3", STEP3_PATH),
        "d29": load_module("d29_layer_b_d29", D29_PATH),
        "decision": load_module("d29_layer_b_decision", DECISION_PATH),
    }


def build_seed_oracle_rows(
    *,
    replication_seed: int,
    configs: Mapping[str, Mapping[str, Any]],
    modules: Mapping[str, Any],
) -> pd.DataFrame:
    """Reconstruct one D29 development world without target noise or TEST use."""
    if int(replication_seed) not in DEVELOPMENT_SEEDS:
        raise ValueError("Only frozen development seeds 21001--21005 are permitted.")
    if int(replication_seed) in PRIMARY_SEEDS + RESERVE_SEEDS + STRUCTURAL_VALIDATION_SEEDS:
        raise AssertionError("Forbidden seed family entered D29 Layer-B reconstruction.")

    benchmark = configs["benchmark"]
    experiment = configs["experiment"]
    seeds_cfg = configs["seeds"]

    if tuple(seeds_cfg["development"]) != DEVELOPMENT_SEEDS:
        raise ValueError("config/seeds.yaml development seed family changed.")

    step1 = modules["step1"]
    step2 = modules["step2"]
    step3 = modules["step3"]
    d29 = modules["d29"]

    ordered_benchmark_alternative_ids(benchmark)

    contexts, _context_audit = step1.generate_master_contexts(
        replication_seed=int(replication_seed),
        rho=RHO,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds_cfg,
    )

    # Restrict immediately to the frozen estimation pool before technology
    # responses are generated. External TEST contexts contribute no g or U*.
    contexts_est = contexts.loc[
        contexts["partition"].isin(ESTIMATION_PARTITIONS)
        & contexts["context_number"].between(1, N_CONTEXTS)
    ].copy()

    contexts_est.sort_values("context_number", kind="stable", inplace=True)
    contexts_est.reset_index(drop=True, inplace=True)

    if len(contexts_est) != N_CONTEXTS:
        raise AssertionError("Expected exactly 1000 FIT+WEIGHT contexts.")
    if contexts_est["context_id"].nunique() != N_CONTEXTS:
        raise AssertionError("Expected exactly 1000 unique estimation context IDs.")
    if contexts_est["partition"].eq("test").any():
        raise AssertionError("External TEST entered the estimation context pool.")

    benchmark_zero_noise = copy.deepcopy(benchmark)
    benchmark_zero_noise["technology_response"]["criterion_noise"]["sigma_x"] = SIGMA_X

    baseline, capability_parameters, _deployment_parameters, _response_audit = (
        step2.generate_master_technology_responses(
            contexts=contexts_est,
            replication_seed=int(replication_seed),
            benchmark=benchmark_zero_noise,
        )
    )
    if len(baseline) != N_CONTEXTS * len(ALTERNATIVE_IDS):
        raise AssertionError("Expected exactly 6000 baseline alternative-context rows.")
    if baseline["partition"].eq("test").any():
        raise AssertionError("External TEST entered baseline responses.")

    baseline = baseline.sort_values(
        ["context_number", "alternative_id"],
        kind="stable",
    ).reset_index(drop=True)

    opportunities = step2.compute_opportunities(
        contexts_est,
        benchmark,
    )

    d29_responses = d29.build_candidate_responses(
        baseline=baseline,
        opportunities=opportunities,
        capability_parameters=capability_parameters,
        benchmark=benchmark,
        replication_seed=int(replication_seed),
    )
    if len(d29_responses) != N_CONTEXTS * len(ALTERNATIVE_IDS):
        raise AssertionError("Expected exactly 6000 D29 response rows.")
    if d29_responses["partition"].eq("test").any():
        raise AssertionError("External TEST entered D29 responses.")

    oracle_spec = step3.load_oracle_spec(benchmark)
    oracle_rows = step3.compute_oracle_utility(
        d29_responses,
        oracle_spec=oracle_spec,
        lambda_value=LAMBDA_VALUE,
    )

    return _validated_oracle_frame(
        oracle_rows,
        replication_seed=int(replication_seed),
    )


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Execute the committed one-shot characterization and persist results."""
    commit, branch = require_clean_git()

    protocol = load_json(PROTOCOL_PATH)
    validate_protocol(protocol)

    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing D29 Layer-B result path: {output_dir}"
        )

    configs = {
        "benchmark": load_yaml(BENCHMARK_PATH),
        "experiment": load_yaml(EXPERIMENT_PATH),
        "seeds": load_yaml(SEEDS_PATH),
    }
    modules = load_pipeline_modules()

    seed_rows: list[dict[str, Any]] = []
    for replication_seed in DEVELOPMENT_SEEDS:
        oracle_rows = build_seed_oracle_rows(
            replication_seed=replication_seed,
            configs=configs,
            modules=modules,
        )
        seed_rows.append(
            characterize_oracle_rows(
                oracle_rows,
                replication_seed=replication_seed,
                decision_module=modules["decision"],
            )
        )

    summary = summarize_seed_metrics(seed_rows)

    provenance = {
        "protocol": "d29_layer_b_characterization_v1",
        "execution_git_commit": commit,
        "execution_branch": branch,
        "generator": "d29_kernel",
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "rho": RHO,
        "sigma_x": SIGMA_X,
        "lambda": LAMBDA_VALUE,
        "N": N_CONTEXTS,
        "context_pool": "FIT+WEIGHT",
        "external_TEST_used": False,
        "target_Y_used": False,
        "xgboost_used": False,
        "shap_used": False,
        "weighting_methods_used": False,
        "mcdm_executed": False,
        "primary_seeds_used": False,
        "reserve_seeds_used": False,
        "structural_validation_seeds_used": False,
        "preferred_winner_used_for_selection": False,
        "retention_effect": "none",
        "pass_fail_threshold": None,
        "p95_quantile_method": P95_METHOD,
    }

    # Create the result directory only after all five in-memory computations
    # have completed successfully, preventing partial one-shot artefacts.
    output_dir.mkdir(parents=True, exist_ok=False)

    seed_frame = pd.DataFrame(seed_rows).sort_values(
        "replication_seed",
        kind="stable",
    )
    seed_frame.to_csv(output_dir / "seed_metrics.csv", index=False)

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return {
        "seed_metrics": seed_rows,
        "summary": summary,
        "provenance": provenance,
        "output_dir": output_dir.as_posix(),
    }


if __name__ == "__main__":
    result = run()
    print("D29 LAYER-B CHARACTERIZATION V1")
    print("=" * 72)
    for row in result["seed_metrics"]:
        print(
            "seed={replication_seed} orderings={distinct_complete_oracle_orderings} "
            "winners={distinct_deterministic_oracle_winners} "
            "modal={modal_oracle_winner_id} share={modal_oracle_winner_share:.6f} "
            "mean_regret={modal_baseline_mean_normalized_oracle_regret} "
            "median_regret={modal_baseline_median_normalized_oracle_regret} "
            "p95_regret={modal_baseline_p95_normalized_oracle_regret} "
            "undefined={undefined_normalized_regret_context_count}".format(**row)
        )
    print("RESULTS_WRITTEN:", result["output_dir"])
    print("RETENTION_EFFECT: none")
    print("PASS_FAIL_THRESHOLD: None")
