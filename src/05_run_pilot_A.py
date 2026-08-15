from __future__ import annotations

"""
Pilot A: model-independent oracle / decision-geometry gate.

This module is development-only. It evaluates the five reserved development
seeds at the frozen reference condition:

    (N, c, rho, lambda) = (250, 0.30, 0.4, 0.5)

Pilot A deliberately uses:
- direction-adjusted criterion scores g_C1..g_C10,
- the validated noise-free oracle U_star from Step 3,
- the validated relative-noise construction from Step 4.

Pilot A deliberately does NOT use:
- external TEST contexts in any diagnostic or warning calculation,
- Oracle Shapley,
- XGBoost / TreeSHAP,
- global weighting methods,
- MOORA / TOPSIS,
- primary seeds.

The two pre-specified warning flags are descriptive investigation triggers,
not automatic rejection rules.
"""

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_PATH = ROOT / "config" / "benchmark.yaml"
DEFAULT_EXPERIMENT_PATH = ROOT / "config" / "experiment.yaml"
DEFAULT_SEEDS_PATH = ROOT / "config" / "seeds.yaml"
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "diagnostics" / "pilot_A"

ORACLE_MODULE_PATH = ROOT / "src" / "03_generate_oracle_utility.py"
NOISE_MODULE_PATH = ROOT / "src" / "04_generate_noisy_target.py"

CRITERIA = tuple(f"C{i}" for i in range(1, 11))
G_COLUMNS = tuple(f"g_{criterion}" for criterion in CRITERIA)
ESTIMATION_PARTITIONS = ("fit", "weight")
TEST_PARTITION = "test"
ALTERNATIVE_COUNT = 6
EPSILON_DEFAULT = 1.0e-12
NUMERICAL_TOL = 1.0e-12


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return data


def load_module(name: str, path: Path):
    """Load a numbered source module safely, including @dataclass support."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def load_step_modules():
    oracle = load_module("pilot_A_oracle_step3", ORACLE_MODULE_PATH)
    noise = load_module("pilot_A_noise_step4", NOISE_MODULE_PATH)
    return oracle, noise


def frozen_pilot_A_config(
    experiment: Mapping[str, Any],
    seeds: Mapping[str, Any],
) -> dict[str, Any]:
    pilot = experiment["development"]["pilot_A"]
    scope = pilot["reference_scope"]

    expected = {
        "N": 250,
        "c": 0.30,
        "rho": 0.4,
        "lambda": 0.5,
        "development_seeds": 5,
        "contexts_per_seed": 250,
        "pooled_contexts": 1250,
    }
    for key, value in expected.items():
        observed = scope.get(key)
        if isinstance(value, float):
            if not np.isclose(float(observed), value, atol=NUMERICAL_TOL, rtol=0.0):
                raise ValueError(f"Pilot A {key} must be frozen at {value}, found {observed}.")
        elif int(observed) != int(value):
            raise ValueError(f"Pilot A {key} must be frozen at {value}, found {observed}.")

    if scope.get("use_estimation_contexts_only") is not True:
        raise ValueError("Pilot A must use estimation contexts only.")
    if scope.get("use_external_test") is not False:
        raise ValueError("Pilot A must exclude the external TEST pool.")

    winner = pilot["oracle_winner"]
    if winner.get("score") != "U_star":
        raise ValueError("Pilot A oracle winner must be defined from U_star.")
    if winner.get("rule") != "maximum_within_context":
        raise ValueError("Unexpected Pilot A oracle-winner rule.")
    if winner.get("tie_break") != "alternative_id_ascending":
        raise ValueError("Pilot A tie-break must be alternative_id_ascending.")
    if winner.get("record_tie_rate") is not True:
        raise ValueError("Pilot A must record the oracle-winner tie rate.")

    margin = pilot["decision_margin"]
    if margin.get("primary") != "top1_U_star_minus_top2_U_star":
        raise ValueError("Unexpected primary Pilot A decision margin.")
    if margin.get("secondary_normalized") != (
        "primary_divided_by_within_context_U_star_range_plus_epsilon"
    ):
        raise ValueError("Unexpected normalized Pilot A decision margin.")
    epsilon = float(margin["epsilon"])
    if epsilon <= 0.0:
        raise ValueError("Pilot A decision-margin epsilon must be positive.")

    signal = pilot["signal_sd"]
    if signal.get("source") != "complete_1000_context_estimation_master_pool":
        raise ValueError("Pilot A s_U must come from the complete N1000 estimation master.")
    if signal.get("exclude_external_test") is not True:
        raise ValueError("External TEST must be excluded from Pilot A s_U.")

    snr = pilot["realized_snr"]
    if snr.get("evaluation_scope") != "reference_N250_estimation_contexts_only":
        raise ValueError("Unexpected Pilot A realized-SNR scope.")

    pareto = pilot["structural_pareto"]
    if pareto.get("input") != "direction_adjusted_g":
        raise ValueError("Pilot A Pareto diagnostics must use direction-adjusted g.")
    if pareto.get("unit") != "context":
        raise ValueError("Pilot A Pareto diagnostics must operate within context.")
    if pareto.get("ordered_alternative_pairs") is not True:
        raise ValueError("Pilot A Pareto diagnostics require ordered alternative pairs.")

    warnings = pilot["warning_flags"]
    if not np.isclose(
        float(warnings.get("modal_winner_share_above")),
        0.60,
        atol=NUMERICAL_TOL,
        rtol=0.0,
    ):
        raise ValueError("Pilot A modal-winner warning threshold must remain 0.60.")
    if int(warnings.get("fewer_than_distinct_oracle_winners")) != 3:
        raise ValueError("Pilot A distinct-winner warning threshold must remain 3.")
    if warnings.get("evaluation_scope") != (
        "pooled_five_development_seeds_reference_contexts"
    ):
        raise ValueError("Pilot A warning flags must be evaluated on the pooled five seeds.")
    if pilot.get("warning_flags_are_automatic_rejection_rules") is not False:
        raise ValueError("Pilot A warning flags must not be automatic rejection rules.")

    development_seeds = tuple(int(value) for value in seeds["development"])
    if len(development_seeds) != 5:
        raise ValueError("Pilot A requires exactly five reserved development seeds.")
    if any(seed < 20000 or seed >= 30000 for seed in development_seeds):
        raise ValueError("Pilot A must use only the reserved development-seed family.")

    return {
        "N": int(scope["N"]),
        "c": float(scope["c"]),
        "rho": float(scope["rho"]),
        "lambda": float(scope["lambda"]),
        "development_seeds": development_seeds,
        "pooled_contexts": int(scope["pooled_contexts"]),
        "epsilon": epsilon,
        "modal_warning": float(warnings["modal_winner_share_above"]),
        "distinct_warning": int(warnings["fewer_than_distinct_oracle_winners"]),
    }


def response_path(data_dir: Path, seed: int, rho: float) -> Path:
    rho_tag = f"{rho:.2f}".replace(".", "p")
    return data_dir / f"technology_responses_seed{seed}_N1000_rho{rho_tag}.csv"


def select_reference_scope(
    frame: pd.DataFrame,
    *,
    n_contexts: int,
) -> pd.DataFrame:
    required = {
        "context_id",
        "context_number",
        "alternative_id",
        "partition",
        *G_COLUMNS,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Pilot A input is missing columns: {missing}")

    selected = frame.loc[
        frame["partition"].isin(ESTIMATION_PARTITIONS)
        & (frame["context_number"].astype(int) <= int(n_contexts))
    ].copy()

    if selected["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leaked into Pilot A.")
    if selected["context_id"].nunique() != int(n_contexts):
        raise ValueError(
            f"Pilot A requires exactly {n_contexts} reference contexts per seed; "
            f"found {selected['context_id'].nunique()}."
        )
    expected_rows = int(n_contexts) * ALTERNATIVE_COUNT
    if len(selected) != expected_rows:
        raise ValueError(
            f"Pilot A requires {expected_rows} alternative-context rows per seed; "
            f"found {len(selected)}."
        )
    counts = selected.groupby("context_id", sort=False)["alternative_id"].nunique()
    if not (counts == ALTERNATIVE_COUNT).all():
        raise ValueError("Every Pilot A context must contain exactly six alternatives.")
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate context-alternative rows in Pilot A reference scope.")
    return selected


def criterion_geometry(
    frame: pd.DataFrame,
    *,
    seed_label: str,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for criterion, column in zip(CRITERIA, G_COLUMNS):
        values = frame[column].to_numpy(dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{column} contains non-finite values.")
        if np.any(values < -NUMERICAL_TOL) or np.any(values > 1.0 + NUMERICAL_TOL):
            raise ValueError(f"{column} lies outside [0,1].")
        rows.append(
            {
                "seed_scope": seed_label,
                "criterion": criterion,
                "rows": int(len(values)),
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=0)),
                "variance": float(values.var(ddof=0)),
                "min": float(values.min()),
                "q05": float(np.quantile(values, 0.05)),
                "median": float(np.median(values)),
                "q95": float(np.quantile(values, 0.95)),
                "max": float(values.max()),
                "exact_zero_rate": float(np.mean(values == 0.0)),
                "exact_one_rate": float(np.mean(values == 1.0)),
            }
        )
    return pd.DataFrame(rows)


def context_decisions(
    frame: pd.DataFrame,
    *,
    epsilon: float,
) -> pd.DataFrame:
    required = {"context_id", "alternative_id", "U_star"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Decision diagnostics missing columns: {missing}")

    records: list[dict[str, float | int | str | bool]] = []

    for context_id, group in frame.groupby("context_id", sort=True):
        if len(group) != ALTERNATIVE_COUNT:
            raise ValueError(f"Context {context_id} does not contain six alternatives.")
        values = group["U_star"].to_numpy(dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Context {context_id} contains non-finite U_star.")

        ranked = group.sort_values(
            ["U_star", "alternative_id"],
            ascending=[False, True],
            kind="mergesort",
        )
        top = ranked.iloc[0]
        second = ranked.iloc[1]

        u_max = float(values.max())
        u_min = float(values.min())
        margin = float(top["U_star"] - second["U_star"])
        normalized = float(margin / (u_max - u_min + float(epsilon)))
        tie_count = int(np.sum(values == u_max))

        records.append(
            {
                "context_id": str(context_id),
                "winner": str(top["alternative_id"]),
                "winner_U_star": float(top["U_star"]),
                "second_U_star": float(second["U_star"]),
                "decision_margin": margin,
                "normalized_decision_margin": normalized,
                "within_context_U_star_range": float(u_max - u_min),
                "top_tie": bool(tie_count > 1),
                "top_tie_count": tie_count,
            }
        )

    return pd.DataFrame(records)


def normalized_winner_entropy(winners: Sequence[str]) -> float:
    if len(winners) == 0:
        raise ValueError("Winner entropy requires at least one context.")
    counts = pd.Series(list(winners), dtype="object").value_counts()
    probabilities = counts.to_numpy(dtype=float) / float(len(winners))
    entropy = -float(np.sum(probabilities * np.log(probabilities)))
    return float(entropy / math.log(ALTERNATIVE_COUNT))


def winner_summary(
    decisions: pd.DataFrame,
    *,
    seed_label: str,
) -> dict[str, float | int | str]:
    if decisions.empty:
        raise ValueError("Winner summary requires non-empty decision diagnostics.")
    counts = decisions["winner"].value_counts()
    modal_count = int(counts.max())
    modal_winners = sorted(counts[counts == modal_count].index.astype(str).tolist())
    modal_winner = modal_winners[0]

    return {
        "seed_scope": seed_label,
        "contexts": int(len(decisions)),
        "distinct_winners": int(counts.size),
        "modal_winner": modal_winner,
        "modal_winner_share": float(modal_count / len(decisions)),
        "winner_entropy_normalized": normalized_winner_entropy(
            decisions["winner"].astype(str).tolist()
        ),
        "top_tie_rate": float(decisions["top_tie"].mean()),
    }


def margin_summary(
    decisions: pd.DataFrame,
    *,
    seed_label: str,
) -> dict[str, float | int | str]:
    margin = decisions["decision_margin"].to_numpy(dtype=float)
    normalized = decisions["normalized_decision_margin"].to_numpy(dtype=float)
    return {
        "seed_scope": seed_label,
        "contexts": int(len(decisions)),
        "margin_min": float(margin.min()),
        "margin_q05": float(np.quantile(margin, 0.05)),
        "margin_q25": float(np.quantile(margin, 0.25)),
        "margin_median": float(np.median(margin)),
        "margin_q75": float(np.quantile(margin, 0.75)),
        "margin_q95": float(np.quantile(margin, 0.95)),
        "margin_max": float(margin.max()),
        "normalized_margin_min": float(normalized.min()),
        "normalized_margin_q05": float(np.quantile(normalized, 0.05)),
        "normalized_margin_median": float(np.median(normalized)),
        "normalized_margin_q95": float(np.quantile(normalized, 0.95)),
        "normalized_margin_max": float(normalized.max()),
    }


def pareto_dominance(
    frame: pd.DataFrame,
    *,
    seed_label: str,
) -> pd.DataFrame:
    alternatives = sorted(frame["alternative_id"].astype(str).unique().tolist())
    if len(alternatives) != ALTERNATIVE_COUNT:
        raise ValueError("Pareto diagnostics require exactly six alternatives.")

    context_ids = sorted(frame["context_id"].astype(str).unique().tolist())
    dominated_counts = {(a, b): 0 for a in alternatives for b in alternatives if a != b}

    for context_id, group in frame.groupby("context_id", sort=True):
        matrix = group.set_index("alternative_id").loc[alternatives, G_COLUMNS].to_numpy(dtype=float)
        for i, left in enumerate(alternatives):
            for j, right in enumerate(alternatives):
                if i == j:
                    continue
                ge = bool(np.all(matrix[i] >= matrix[j]))
                gt = bool(np.any(matrix[i] > matrix[j]))
                if ge and gt:
                    dominated_counts[(left, right)] += 1

    rows = []
    denominator = float(len(context_ids))
    for (left, right), count in sorted(dominated_counts.items()):
        rows.append(
            {
                "seed_scope": seed_label,
                "dominant_alternative": left,
                "dominated_alternative": right,
                "contexts": int(len(context_ids)),
                "dominance_count": int(count),
                "dominance_rate": float(count / denominator),
            }
        )
    return pd.DataFrame(rows)


def reference_noise_summary(
    frame: pd.DataFrame,
    *,
    full_master_signal_sd: float,
    seed_label: str,
) -> dict[str, float | int | str]:
    if frame["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leaked into Pilot A SNR diagnostics.")

    u = frame["U_star"].to_numpy(dtype=float)
    noise = frame["target_noise"].to_numpy(dtype=float)
    e = frame["target_noise_e"].to_numpy(dtype=float)

    signal_sd_reference_N = float(u.std(ddof=0))
    realized_noise_sd = float(noise.std(ddof=0))
    realized_snr = (
        float((signal_sd_reference_N**2) / (realized_noise_sd**2))
        if realized_noise_sd > 0.0
        else float("inf")
    )

    return {
        "seed_scope": seed_label,
        "rows": int(len(frame)),
        "contexts": int(frame["context_id"].nunique()),
        "signal_sd_master_N1000": float(full_master_signal_sd),
        "signal_sd_reference_N250": signal_sd_reference_N,
        "imposed_noise_sd": float(frame["imposed_noise_sd"].iloc[0]),
        "realized_noise_sd_reference_N250": realized_noise_sd,
        "realized_noise_to_master_signal_sd_ratio": float(
            realized_noise_sd / full_master_signal_sd
        ),
        "realized_snr_variance_reference_N250": realized_snr,
        "base_e_mean_reference_N250": float(e.mean()),
        "base_e_sd_reference_N250": float(e.std(ddof=0)),
    }


def pooled_warning_flags(
    pooled_winner_summary: Mapping[str, Any],
    *,
    modal_warning: float,
    distinct_warning: int,
) -> dict[str, bool]:
    modal_share = float(pooled_winner_summary["modal_winner_share"])
    distinct = int(pooled_winner_summary["distinct_winners"])
    return {
        "modal_winner_share_warning": bool(modal_share > float(modal_warning)),
        "fewer_than_distinct_winners_warning": bool(distinct < int(distinct_warning)),
    }


def _prefix_seed_context(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    result = frame.copy()
    result["replication_seed"] = int(seed)
    result["context_id_original"] = result["context_id"].astype(str)
    result["context_id"] = (
        str(int(seed)) + ":" + result["context_id_original"].astype(str)
    )
    return result


def run_single_seed(
    *,
    seed: int,
    config: Mapping[str, Any],
    oracle,
    noise,
    benchmark: Mapping[str, Any],
    experiment: Mapping[str, Any],
    seeds_config: Mapping[str, Any],
    data_dir: Path,
) -> dict[str, Any]:
    source = response_path(data_dir, seed, float(config["rho"]))
    if not source.exists():
        raise FileNotFoundError(f"Pilot A response master not found: {source}")

    responses = pd.read_csv(source)
    oracle.validate_response_schema(responses)
    if len(responses) != noise.EXPECTED_MASTER_ROWS:
        raise ValueError(
            f"Pilot A requires a complete 7200-row master for seed {seed}; "
            f"found {len(responses)}."
        )

    oracle_spec = oracle.load_oracle_spec(benchmark)
    lam = oracle.validate_lambda(float(config["lambda"]), experiment)
    noise.validate_target_noise_protocol(experiment, seeds_config)
    c = noise.validate_noise_level(float(config["c"]), experiment)
    namespace = noise.target_noise_namespace(seeds_config)

    oracle_master = oracle.compute_oracle_utility(
        responses,
        oracle_spec=oracle_spec,
        lambda_value=lam,
    )
    signal_sd = noise.compute_signal_sd(oracle_master)
    noise_table = noise.master_noise_table(
        oracle_master,
        replication_seed=int(seed),
        namespace=int(namespace),
    )
    noisy_master = noise.add_relative_noise(
        oracle_master,
        c=c,
        signal_sd=signal_sd,
        noise_table=noise_table,
    )

    reference = select_reference_scope(
        noisy_master,
        n_contexts=int(config["N"]),
    )
    if reference["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leaked into Pilot A reference subset.")

    reference = _prefix_seed_context(reference, seed)
    decisions = context_decisions(reference, epsilon=float(config["epsilon"]))
    decisions["replication_seed"] = int(seed)

    label = str(int(seed))
    return {
        "reference": reference,
        "decisions": decisions,
        "criterion_geometry": criterion_geometry(reference, seed_label=label),
        "winner_summary": winner_summary(decisions, seed_label=label),
        "margin_summary": margin_summary(decisions, seed_label=label),
        "pareto": pareto_dominance(reference, seed_label=label),
        "noise_summary": reference_noise_summary(
            reference,
            full_master_signal_sd=signal_sd,
            seed_label=label,
        ),
    }


def run_pilot_A(
    *,
    benchmark_path: Path = DEFAULT_BENCHMARK_PATH,
    experiment_path: Path = DEFAULT_EXPERIMENT_PATH,
    seeds_path: Path = DEFAULT_SEEDS_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    save: bool = True,
) -> dict[str, Any]:
    benchmark = load_yaml(benchmark_path)
    experiment = load_yaml(experiment_path)
    seeds_config = load_yaml(seeds_path)
    config = frozen_pilot_A_config(experiment, seeds_config)
    oracle, noise = load_step_modules()

    per_seed = []
    for seed in config["development_seeds"]:
        per_seed.append(
            run_single_seed(
                seed=int(seed),
                config=config,
                oracle=oracle,
                noise=noise,
                benchmark=benchmark,
                experiment=experiment,
                seeds_config=seeds_config,
                data_dir=data_dir,
            )
        )

    pooled_reference = pd.concat(
        [result["reference"] for result in per_seed],
        ignore_index=True,
    )
    pooled_decisions = pd.concat(
        [result["decisions"] for result in per_seed],
        ignore_index=True,
    )

    if pooled_reference["partition"].eq(TEST_PARTITION).any():
        raise AssertionError("External TEST leaked into pooled Pilot A diagnostics.")
    if pooled_decisions["context_id"].nunique() != int(config["pooled_contexts"]):
        raise ValueError(
            "Pooled Pilot A context count does not match the frozen 1250-context scope."
        )
    expected_rows = int(config["pooled_contexts"]) * ALTERNATIVE_COUNT
    if len(pooled_reference) != expected_rows:
        raise ValueError(
            f"Pooled Pilot A requires {expected_rows} rows; found {len(pooled_reference)}."
        )

    pooled_winners = winner_summary(pooled_decisions, seed_label="pooled")
    warnings = pooled_warning_flags(
        pooled_winners,
        modal_warning=float(config["modal_warning"]),
        distinct_warning=int(config["distinct_warning"]),
    )

    pooled = {
        "criterion_geometry": criterion_geometry(
            pooled_reference,
            seed_label="pooled",
        ),
        "winner_summary": pooled_winners,
        "margin_summary": margin_summary(
            pooled_decisions,
            seed_label="pooled",
        ),
        "pareto": pareto_dominance(
            pooled_reference,
            seed_label="pooled",
        ),
    }

    per_seed_winner = pd.DataFrame(
        [result["winner_summary"] for result in per_seed]
    )
    per_seed_margin = pd.DataFrame(
        [result["margin_summary"] for result in per_seed]
    )
    per_seed_noise = pd.DataFrame(
        [result["noise_summary"] for result in per_seed]
    )
    per_seed_geometry = pd.concat(
        [result["criterion_geometry"] for result in per_seed],
        ignore_index=True,
    )
    per_seed_pareto = pd.concat(
        [result["pareto"] for result in per_seed],
        ignore_index=True,
    )

    manifest = {
        "pilot": "A",
        "model_independent": True,
        "reference_condition": {
            "N": int(config["N"]),
            "c": float(config["c"]),
            "rho": float(config["rho"]),
            "lambda": float(config["lambda"]),
        },
        "development_seeds": [int(value) for value in config["development_seeds"]],
        "contexts_per_seed": int(config["N"]),
        "pooled_contexts": int(config["pooled_contexts"]),
        "external_test_used_in_diagnostics": False,
        "oracle_shapley_used": False,
        "xgboost_used": False,
        "treeshap_used": False,
        "mcdm_used": False,
        "warning_flags_are_automatic_rejection_rules": False,
        "pooled_winner_summary": pooled_winners,
        "pooled_margin_summary": pooled["margin_summary"],
        "warning_flags": warnings,
    }

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        per_seed_geometry.to_csv(output_dir / "pilot_A_criterion_geometry_by_seed.csv", index=False)
        pooled["criterion_geometry"].to_csv(
            output_dir / "pilot_A_criterion_geometry_pooled.csv",
            index=False,
        )
        per_seed_winner.to_csv(output_dir / "pilot_A_winner_summary_by_seed.csv", index=False)
        pd.DataFrame([pooled_winners]).to_csv(
            output_dir / "pilot_A_winner_summary_pooled.csv",
            index=False,
        )
        per_seed_margin.to_csv(output_dir / "pilot_A_margin_summary_by_seed.csv", index=False)
        pd.DataFrame([pooled["margin_summary"]]).to_csv(
            output_dir / "pilot_A_margin_summary_pooled.csv",
            index=False,
        )
        per_seed_noise.to_csv(output_dir / "pilot_A_noise_summary_by_seed.csv", index=False)
        per_seed_pareto.to_csv(output_dir / "pilot_A_pareto_by_seed.csv", index=False)
        pooled["pareto"].to_csv(output_dir / "pilot_A_pareto_pooled.csv", index=False)
        pooled_decisions.to_csv(output_dir / "pilot_A_context_decisions.csv", index=False)
        with (output_dir / "pilot_A_manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)

    print("=" * 80)
    print("PILOT A — ORACLE / DECISION-GEOMETRY GATE")
    print("=" * 80)
    print(
        "Reference condition       : "
        f"N={config['N']}, c={config['c']:.2f}, "
        f"rho={config['rho']:.1f}, lambda={config['lambda']:.1f}"
    )
    print(
        "Development seeds        : "
        + ", ".join(str(value) for value in config["development_seeds"])
    )
    print(f"Contexts per seed         : {config['N']}")
    print(f"Pooled contexts           : {config['pooled_contexts']}")
    print("External TEST used        : False")
    print("Oracle Shapley            : NOT USED")
    print("XGBoost / TreeSHAP        : NOT USED")
    print("MCDM                      : NOT USED")
    print()
    print("Per-seed oracle geometry:")
    for _, row in per_seed_winner.iterrows():
        seed = row["seed_scope"]
        noise_row = per_seed_noise.loc[per_seed_noise["seed_scope"].eq(seed)].iloc[0]
        margin_row = per_seed_margin.loc[per_seed_margin["seed_scope"].eq(seed)].iloc[0]
        print(
            f"  seed {seed}: distinct={int(row['distinct_winners'])}, "
            f"modal={row['modal_winner']} ({row['modal_winner_share']:.3f}), "
            f"H={row['winner_entropy_normalized']:.3f}, "
            f"median_margin={margin_row['margin_median']:.6f}, "
            f"s_U={noise_row['signal_sd_master_N1000']:.6f}, "
            f"SNR_N250={noise_row['realized_snr_variance_reference_N250']:.3f}"
        )

    print()
    print("Pooled five-seed geometry:")
    print(f"  distinct winners        : {pooled_winners['distinct_winners']}")
    print(
        "  modal winner/share     : "
        f"{pooled_winners['modal_winner']} / {pooled_winners['modal_winner_share']:.6f}"
    )
    print(
        "  normalized entropy     : "
        f"{pooled_winners['winner_entropy_normalized']:.6f}"
    )
    print(f"  top-tie rate           : {pooled_winners['top_tie_rate']:.6f}")
    print(
        "  margin median [q05,q95]: "
        f"{pooled['margin_summary']['margin_median']:.6f} "
        f"[{pooled['margin_summary']['margin_q05']:.6f}, "
        f"{pooled['margin_summary']['margin_q95']:.6f}]"
    )

    pooled_pareto = pooled["pareto"].sort_values(
        ["dominance_rate", "dominant_alternative", "dominated_alternative"],
        ascending=[False, True, True],
    )
    max_pareto = pooled_pareto.iloc[0]
    print(
        "  max ordered Pareto rate: "
        f"{max_pareto['dominant_alternative']} > "
        f"{max_pareto['dominated_alternative']} = "
        f"{max_pareto['dominance_rate']:.6f}"
    )
    print()
    print("Pre-specified warning flags (pooled 1250 contexts):")
    print(
        "  modal share > 0.60     : "
        f"{warnings['modal_winner_share_warning']}"
    )
    print(
        "  distinct winners < 3   : "
        f"{warnings['fewer_than_distinct_winners_warning']}"
    )
    print("Automatic rejection      : False")
    if save:
        print(f"Diagnostics output       : {output_dir}")
    print("=" * 80)

    return {
        "config": config,
        "manifest": manifest,
        "per_seed_winner": per_seed_winner,
        "per_seed_margin": per_seed_margin,
        "per_seed_noise": per_seed_noise,
        "per_seed_geometry": per_seed_geometry,
        "per_seed_pareto": per_seed_pareto,
        "pooled_reference": pooled_reference,
        "pooled_decisions": pooled_decisions,
        "pooled": pooled,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run development-only Pilot A oracle/geometry diagnostics."
    )
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT_PATH)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pilot_A(
        benchmark_path=args.benchmark,
        experiment_path=args.experiment,
        seeds_path=args.seeds,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
