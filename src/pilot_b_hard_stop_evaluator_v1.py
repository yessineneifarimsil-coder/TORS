from __future__ import annotations

"""Pure evaluator for the prospectively frozen Pilot-B hard-stop protocol.

The evaluator consumes already-computed, seed-level summaries and winner
identities.  It does not generate benchmark data, fit a model, estimate
weights, run SHAP/MCDM, inspect primary/reserve seeds, or write files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "pilot_b_hard_stop_protocol_v1.json"

DEVELOPMENT_SEEDS = (21001, 21002, 21003, 21004, 21005)
STRUCTURED_METHODS = (
    "OracleAttribution",
    "SHAP",
    "PermutationImportance",
    "RidgePlus",
    "CRITIC",
    "Entropy",
)
SCORED_REFERENCES = ("Equal", "DirectXGBoost")
TOP1_REFERENCE = "MajorityWinner"
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))

TEST_CONTEXTS_PER_SEED = 200
RANDOM_DRAWS_PER_SEED = 200
MINIMUM_KENDALL_CONTEXTS = 190
MINIMUM_ELIGIBLE_RANDOM_DRAWS = 190
CONSISTENT_SEEDS = 4
QUANTILE_METHOD = "linear"
NUMERICAL_TOLERANCE = 1.0e-12

RANDOM_KENDALL_MARGIN = 0.05
RANDOM_REGRET_MARGIN = 0.01
MODAL_TOP1_MARGIN = 0.02
MODAL_REGRET_MARGIN = 0.01
ORACLE_DOMINANCE_THRESHOLD = 0.90
RANDOM_CONTEXT_MODAL_SHARE_THRESHOLD = 0.95
RANDOM_CONTEXT_INVARIANT_FRACTION_THRESHOLD = 0.90
RANDOM_KENDALL_WIDTH_THRESHOLD = 0.05
RANDOM_TOP1_WIDTH_THRESHOLD = 0.02
RANDOM_REGRET_WIDTH_THRESHOLD = 0.01


@dataclass(frozen=True)
class PilotBHardStopResult:
    protocol_schema: str
    coverage_complete: bool
    coverage_reasons: tuple[str, ...]
    structured_method_assessments: tuple[dict[str, Any], ...]
    random_seed_summaries: tuple[dict[str, Any], ...]
    oracle_winner_summary: dict[str, Any]
    random_context_invariance_summary: dict[str, Any]
    gates: dict[str, bool]
    hard_stop: bool
    pilot_b_pass: bool


def _load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Pilot-B protocol must be a JSON object.")
    return value


def validate_frozen_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Fail closed if any prospectively frozen Pilot-B choice changed."""
    p = _load_protocol(path)
    if p.get("schema") != "pilot_b_hard_stop_protocol_v1":
        raise ValueError("Pilot-B protocol schema changed.")
    if p.get("status") != "FROZEN_PROSPECTIVELY_BEFORE_ANY_PILOT_B_RESULT":
        raise ValueError("Pilot-B protocol is not prospectively frozen.")
    s = p["scope"]
    if tuple(s["development_seeds"]) != DEVELOPMENT_SEEDS:
        raise ValueError("Pilot-B development seeds changed.")
    if s["reference_condition"] != {"N": 250, "c": 0.3, "rho": 0.4, "lambda": 0.5}:
        raise ValueError("Pilot-B reference condition changed.")
    if s["test_contexts_per_seed"] != TEST_CONTEXTS_PER_SEED:
        raise ValueError("Pilot-B TEST context count changed.")
    if s["random_weight_draws_per_seed"] != RANDOM_DRAWS_PER_SEED:
        raise ValueError("Pilot-B random-draw count changed.")
    if s["random_weight_master_seed"] != 81001:
        raise ValueError("Pilot-B RandomWeights namespace changed.")
    if s["primary_mcdm"] != "MOORA" or s["topsis_used_for_hard_stop"] is not False:
        raise ValueError("Pilot-B MCDM scope changed.")
    if s["primary_seeds_used"] is not False or s["reserve_seeds_used"] is not False:
        raise ValueError("Pilot-B seed firewall opened.")
    roles = p["method_roles"]
    if tuple(roles["structured_gate_methods"]) != STRUCTURED_METHODS:
        raise ValueError("Pilot-B structured method list changed.")
    c = p["coverage"]
    expected_coverage = (c["required_test_contexts_per_seed"], c["required_random_draws_per_seed"], c["minimum_kendall_defined_contexts_per_200"], c["minimum_eligible_random_draws_per_seed"])
    if expected_coverage != (200, 200, 190, 190):
        raise ValueError("Pilot-B coverage boundaries changed.")
    margins = p["practical_margins"]
    observed = (
        margins["random_separation"]["median_kendall_advantage_at_least"],
        margins["random_separation"]["median_mean_regret_advantage_at_least"],
        margins["modal_winner_escape"]["median_top1_advantage_at_least"],
        margins["modal_winner_escape"]["median_mean_regret_advantage_at_least"],
        margins["oracle_winner_dominance"]["pooled_modal_winner_share_at_least"],
        margins["random_context_top1_invariance"]["within_context_modal_share_at_least"],
        margins["random_context_top1_invariance"]["pooled_invariant_context_fraction_at_least"],
    )
    if observed != (0.05, 0.01, 0.02, 0.01, 0.90, 0.95, 0.90):
        raise ValueError("Pilot-B practical margins changed.")
    if p["overall_decision"]["hard_stop_logic"] != "OR_across_all_five_hard_stop_gates":
        raise ValueError("Pilot-B overall hard-stop logic changed.")
    if p["gates"]["random_equivalence_hard_stop"]["failure_to_reject_null_used_as_equivalence"] is not False:
        raise ValueError("Pilot-B incorrectly permits failure-to-reject equivalence.")
    return p


def _frame(value: pd.DataFrame | Iterable[Mapping[str, Any]], label: str) -> pd.DataFrame:
    result = value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame.from_records(value)
    if result.empty:
        raise ValueError(f"{label} must not be empty.")
    return result


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}.")


def _validate_seed(value: Any) -> int:
    seed = int(value)
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(f"Pilot B received non-development seed {seed}.")
    return seed


def _finite_unit_interval(value: Any, label: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0 or result > 1.0:
        raise ValueError(f"{label} must be finite and in [0,1].")
    return result


def _finite_kendall(value: Any, label: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < -1.0 or result > 1.0:
        raise ValueError(f"{label} must be finite and in [-1,1].")
    return result


def _prepare_structured(value: Any) -> pd.DataFrame:
    frame = _frame(value, "structured_seed_metrics")
    required = {
        "method", "replication_seed", "weights_defined", "equal_fallback_used",
        "test_contexts", "kendall_defined_contexts", "mean_kendall_tau_b",
        "top1_accuracy", "mean_normalized_oracle_regret",
    }
    _require_columns(frame, required, "structured_seed_metrics")
    frame = frame.loc[:, sorted(required)].copy()
    frame["method"] = frame["method"].astype(str)
    frame["replication_seed"] = frame["replication_seed"].map(_validate_seed)
    if frame.duplicated(["method", "replication_seed"]).any():
        raise ValueError("Duplicate structured method-seed row.")
    expected = {(method, seed) for method in STRUCTURED_METHODS for seed in DEVELOPMENT_SEEDS}
    observed = set(zip(frame["method"], frame["replication_seed"], strict=True))
    if observed != expected:
        raise ValueError("Structured method-seed grid is not exact.")
    frame["weights_defined"] = frame["weights_defined"].map(bool)
    frame["equal_fallback_used"] = frame["equal_fallback_used"].map(bool)
    frame["test_contexts"] = frame["test_contexts"].astype(int)
    frame["kendall_defined_contexts"] = frame["kendall_defined_contexts"].astype(int)
    if not frame["test_contexts"].eq(TEST_CONTEXTS_PER_SEED).all():
        raise ValueError("Every structured row must report 200 TEST contexts.")
    if ((frame["kendall_defined_contexts"] < 0) | (frame["kendall_defined_contexts"] > 200)).any():
        raise ValueError("Structured Kendall coverage escaped [0,200].")
    for column in ("top1_accuracy", "mean_normalized_oracle_regret"):
        frame[column] = [_finite_unit_interval(v, column) for v in frame[column]]
    for index, row in frame.iterrows():
        if int(row["kendall_defined_contexts"]) > 0:
            frame.at[index, "mean_kendall_tau_b"] = _finite_kendall(row["mean_kendall_tau_b"], "mean_kendall_tau_b")
        elif not pd.isna(row["mean_kendall_tau_b"]):
            raise ValueError("Undefined structured Kendall mean must be null.")
    return frame.sort_values(["method", "replication_seed"], kind="stable").reset_index(drop=True)


def _prepare_random(value: Any) -> pd.DataFrame:
    frame = _frame(value, "random_draw_metrics")
    required = {
        "replication_seed", "random_draw_index", "test_contexts",
        "kendall_defined_contexts", "mean_kendall_tau_b", "top1_accuracy",
        "mean_normalized_oracle_regret",
    }
    _require_columns(frame, required, "random_draw_metrics")
    frame = frame.loc[:, sorted(required)].copy()
    frame["replication_seed"] = frame["replication_seed"].map(_validate_seed)
    frame["random_draw_index"] = frame["random_draw_index"].astype(int)
    if frame.duplicated(["replication_seed", "random_draw_index"]).any():
        raise ValueError("Duplicate random seed-draw row.")
    expected = {(seed, draw) for seed in DEVELOPMENT_SEEDS for draw in range(1, 201)}
    observed = set(zip(frame["replication_seed"], frame["random_draw_index"], strict=True))
    if observed != expected:
        raise ValueError("Random seed-draw grid is not exact.")
    frame["test_contexts"] = frame["test_contexts"].astype(int)
    frame["kendall_defined_contexts"] = frame["kendall_defined_contexts"].astype(int)
    if not frame["test_contexts"].eq(200).all():
        raise ValueError("Every random draw must report 200 TEST contexts.")
    if ((frame["kendall_defined_contexts"] < 0) | (frame["kendall_defined_contexts"] > 200)).any():
        raise ValueError("Random Kendall coverage escaped [0,200].")
    for column in ("top1_accuracy", "mean_normalized_oracle_regret"):
        frame[column] = [_finite_unit_interval(v, column) for v in frame[column]]
    for index, row in frame.iterrows():
        if int(row["kendall_defined_contexts"]) > 0:
            frame.at[index, "mean_kendall_tau_b"] = _finite_kendall(row["mean_kendall_tau_b"], "mean_kendall_tau_b")
        elif not pd.isna(row["mean_kendall_tau_b"]):
            raise ValueError("Undefined random Kendall mean must be null.")
    return frame.sort_values(["replication_seed", "random_draw_index"], kind="stable").reset_index(drop=True)


def _prepare_references(value: Any) -> pd.DataFrame:
    frame = _frame(value, "reference_seed_metrics")
    required = {
        "reference", "replication_seed", "test_contexts", "kendall_defined_contexts",
        "mean_kendall_tau_b", "top1_accuracy", "mean_normalized_oracle_regret",
    }
    _require_columns(frame, required, "reference_seed_metrics")
    frame = frame.loc[:, sorted(required)].copy()
    frame["reference"] = frame["reference"].astype(str)
    frame["replication_seed"] = frame["replication_seed"].map(_validate_seed)
    expected = {(reference, seed) for reference in (*SCORED_REFERENCES, TOP1_REFERENCE) for seed in DEVELOPMENT_SEEDS}
    observed = set(zip(frame["reference"], frame["replication_seed"], strict=True))
    if observed != expected or frame.duplicated(["reference", "replication_seed"]).any():
        raise ValueError("Reported reference method-seed grid is not exact.")
    if not frame["test_contexts"].astype(int).eq(200).all():
        raise ValueError("Every reference must report 200 TEST contexts.")
    for column in ("top1_accuracy", "mean_normalized_oracle_regret"):
        frame[column] = [_finite_unit_interval(v, column) for v in frame[column]]
    for index, row in frame.iterrows():
        defined = int(row["kendall_defined_contexts"])
        reference = str(row["reference"])
        if reference == TOP1_REFERENCE:
            if defined != 0 or not pd.isna(row["mean_kendall_tau_b"]):
                raise ValueError("MajorityWinner must not invent Kendall ranks.")
        else:
            if not 0 <= defined <= 200:
                raise ValueError("Reference Kendall coverage escaped [0,200].")
            if defined:
                frame.at[index, "mean_kendall_tau_b"] = _finite_kendall(row["mean_kendall_tau_b"], "mean_kendall_tau_b")
    return frame.sort_values(["reference", "replication_seed"], kind="stable").reset_index(drop=True)


def _prepare_winner_contexts(value: Any, *, random_modal: bool) -> pd.DataFrame:
    label = "random_context_modal" if random_modal else "oracle_winner_contexts"
    frame = _frame(value, label)
    required = {"replication_seed", "context_number"}
    required |= ({"random_draws", "modal_winner_id", "modal_count", "modal_share"} if random_modal else {"oracle_selected_top1"})
    _require_columns(frame, required, label)
    frame = frame.loc[:, sorted(required)].copy()
    frame["replication_seed"] = frame["replication_seed"].map(_validate_seed)
    frame["context_number"] = frame["context_number"].astype(int)
    if frame.duplicated(["replication_seed", "context_number"]).any():
        raise ValueError(f"Duplicate {label} seed-context row.")
    counts = frame.groupby("replication_seed").size().to_dict()
    if counts != {seed: 200 for seed in DEVELOPMENT_SEEDS}:
        raise ValueError(f"{label} must contain 200 contexts per seed.")
    winner_column = "modal_winner_id" if random_modal else "oracle_selected_top1"
    if not set(frame[winner_column].astype(str)) <= set(ALTERNATIVE_IDS):
        raise ValueError(f"{label} contains an invalid alternative identity.")
    if random_modal:
        if not frame["random_draws"].astype(int).eq(200).all():
            raise ValueError("Random modal summaries must use all 200 draws.")
        modal_count = frame["modal_count"].astype(int)
        if ((modal_count < 0) | (modal_count > 200)).any():
            raise ValueError("Random modal count escaped [0,200].")
        computed = modal_count.to_numpy(dtype=float) / 200.0
        given = frame["modal_share"].to_numpy(dtype=float)
        if not np.allclose(computed, given, atol=1e-12, rtol=0.0):
            raise ValueError("Random modal share does not equal modal_count/200.")
    return frame.sort_values(["replication_seed", "context_number"], kind="stable").reset_index(drop=True)


def _quantiles(values: np.ndarray) -> tuple[float, float, float, float]:
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("Pilot-B quantiles require finite nonempty values.")
    p05, median, p95 = np.quantile(values, [0.05, 0.50, 0.95], method=QUANTILE_METHOD)
    return float(p05), float(median), float(p95), float(p95 - p05)


def evaluate_pilot_b_hard_stops(
    *,
    structured_seed_metrics: pd.DataFrame | Iterable[Mapping[str, Any]],
    random_draw_metrics: pd.DataFrame | Iterable[Mapping[str, Any]],
    reference_seed_metrics: pd.DataFrame | Iterable[Mapping[str, Any]],
    oracle_winner_contexts: pd.DataFrame | Iterable[Mapping[str, Any]],
    random_context_modal: pd.DataFrame | Iterable[Mapping[str, Any]],
    protocol_path: Path = PROTOCOL_PATH,
) -> PilotBHardStopResult:
    """Apply every frozen coverage, separation, dominance, and width gate."""
    p = validate_frozen_protocol(protocol_path)
    structured = _prepare_structured(structured_seed_metrics)
    random = _prepare_random(random_draw_metrics)
    references = _prepare_references(reference_seed_metrics)
    oracle_winners = _prepare_winner_contexts(oracle_winner_contexts, random_modal=False)
    random_modal = _prepare_winner_contexts(random_context_modal, random_modal=True)

    coverage_reasons: list[str] = []
    eligible_by_method: dict[str, bool] = {}
    for method in STRUCTURED_METHODS:
        rows = structured.loc[structured["method"].eq(method)]
        defined_all = bool(rows["weights_defined"].all())
        no_fallback = bool((~rows["equal_fallback_used"]).all())
        kendall_complete = bool(rows["kendall_defined_contexts"].ge(MINIMUM_KENDALL_CONTEXTS).all())
        eligible = defined_all and no_fallback and kendall_complete
        eligible_by_method[method] = eligible
        if not defined_all:
            coverage_reasons.append(f"{method}:weight_vector_not_defined_for_all_five_seeds")
        if not no_fallback:
            coverage_reasons.append(f"{method}:equal_fallback_used")
        if not kendall_complete:
            coverage_reasons.append(f"{method}:fewer_than_190_defined_kendall_contexts")

    random_summaries: list[dict[str, Any]] = []
    for seed in DEVELOPMENT_SEEDS:
        rows = random.loc[random["replication_seed"].eq(seed)]
        eligible = rows.loc[rows["kendall_defined_contexts"].ge(MINIMUM_KENDALL_CONTEXTS)]
        if len(eligible) < MINIMUM_ELIGIBLE_RANDOM_DRAWS:
            coverage_reasons.append(f"seed{seed}:fewer_than_190_eligible_random_draws")
        k05, k50, k95, kw = _quantiles(eligible["mean_kendall_tau_b"].to_numpy(dtype=float)) if len(eligible) else (None, None, None, None)
        t05, t50, t95, tw = _quantiles(rows["top1_accuracy"].to_numpy(dtype=float))
        r05, r50, r95, rw = _quantiles(rows["mean_normalized_oracle_regret"].to_numpy(dtype=float))
        random_summaries.append({
            "replication_seed": seed,
            "draws": int(len(rows)),
            "eligible_kendall_draws": int(len(eligible)),
            "kendall_p05": k05, "kendall_median": k50, "kendall_p95": k95, "kendall_width": kw,
            "top1_p05": t05, "top1_median": t50, "top1_p95": t95, "top1_width": tw,
            "regret_p05": r05, "regret_median": r50, "regret_p95": r95, "regret_width": rw,
        })
    random_summary_by_seed = {row["replication_seed"]: row for row in random_summaries}
    majority = references.loc[references["reference"].eq(TOP1_REFERENCE)].set_index("replication_seed")

    method_assessments: list[dict[str, Any]] = []
    separates_any = False
    escapes_any = False
    for method in STRUCTURED_METHODS:
        rows = structured.loc[structured["method"].eq(method)].set_index("replication_seed")
        random_k_adv = []
        random_r_adv = []
        modal_t_adv = []
        modal_r_adv = []
        for seed in DEVELOPMENT_SEEDS:
            random_k_adv.append(float(rows.loc[seed, "mean_kendall_tau_b"] - random_summary_by_seed[seed]["kendall_median"]))
            random_r_adv.append(float(random_summary_by_seed[seed]["regret_median"] - rows.loc[seed, "mean_normalized_oracle_regret"]))
            modal_t_adv.append(float(rows.loc[seed, "top1_accuracy"] - majority.loc[seed, "top1_accuracy"]))
            modal_r_adv.append(float(majority.loc[seed, "mean_normalized_oracle_regret"] - rows.loc[seed, "mean_normalized_oracle_regret"]))
        eligible = eligible_by_method[method]
        k_median = float(np.median(random_k_adv))
        r_median = float(np.median(random_r_adv))
        t_median = float(np.median(modal_t_adv))
        mr_median = float(np.median(modal_r_adv))
        k_positive = int(np.count_nonzero(np.asarray(random_k_adv) > 0.0))
        r_positive = int(np.count_nonzero(np.asarray(random_r_adv) > 0.0))
        t_positive = int(np.count_nonzero(np.asarray(modal_t_adv) > 0.0))
        mr_positive = int(np.count_nonzero(np.asarray(modal_r_adv) > 0.0))
        separates = bool(eligible and ((k_median >= RANDOM_KENDALL_MARGIN - NUMERICAL_TOLERANCE and k_positive >= CONSISTENT_SEEDS) or (r_median >= RANDOM_REGRET_MARGIN - NUMERICAL_TOLERANCE and r_positive >= CONSISTENT_SEEDS)))
        escapes = bool(eligible and ((t_median >= MODAL_TOP1_MARGIN - NUMERICAL_TOLERANCE and t_positive >= CONSISTENT_SEEDS) or (mr_median >= MODAL_REGRET_MARGIN - NUMERICAL_TOLERANCE and mr_positive >= CONSISTENT_SEEDS)))
        separates_any |= separates
        escapes_any |= escapes
        method_assessments.append({
            "method": method, "eligible": eligible,
            "random_kendall_advantages_by_seed": dict(zip(map(str, DEVELOPMENT_SEEDS), random_k_adv, strict=True)),
            "random_kendall_median_advantage": k_median, "random_kendall_positive_seed_count": k_positive,
            "random_regret_advantages_by_seed": dict(zip(map(str, DEVELOPMENT_SEEDS), random_r_adv, strict=True)),
            "random_regret_median_advantage": r_median, "random_regret_positive_seed_count": r_positive,
            "separates_random": separates,
            "modal_top1_advantages_by_seed": dict(zip(map(str, DEVELOPMENT_SEEDS), modal_t_adv, strict=True)),
            "modal_top1_median_advantage": t_median, "modal_top1_positive_seed_count": t_positive,
            "modal_regret_advantages_by_seed": dict(zip(map(str, DEVELOPMENT_SEEDS), modal_r_adv, strict=True)),
            "modal_regret_median_advantage": mr_median, "modal_regret_positive_seed_count": mr_positive,
            "escapes_majority_winner": escapes,
        })

    winner_counts = oracle_winners["oracle_selected_top1"].astype(str).value_counts().reindex(ALTERNATIVE_IDS, fill_value=0)
    modal_count = int(winner_counts.max())
    modal_id = min(winner_counts.index[winner_counts.eq(modal_count)].tolist())
    pooled_modal_share = float(modal_count / (len(DEVELOPMENT_SEEDS) * TEST_CONTEXTS_PER_SEED))
    oracle_summary = {
        "pooled_contexts": int(len(oracle_winners)),
        "winner_counts_by_alternative": {key: int(winner_counts[key]) for key in ALTERNATIVE_IDS},
        "pooled_modal_winner_id": modal_id,
        "pooled_modal_winner_count": modal_count,
        "pooled_modal_winner_share": pooled_modal_share,
    }

    invariant = random_modal["modal_share"].astype(float).ge(
        RANDOM_CONTEXT_MODAL_SHARE_THRESHOLD - NUMERICAL_TOLERANCE
    )
    invariant_count = int(invariant.sum())
    invariant_fraction = float(invariant.mean())
    width_seed_flags: dict[str, bool] = {}
    for row in random_summaries:
        flag = bool(
            row["eligible_kendall_draws"] >= MINIMUM_ELIGIBLE_RANDOM_DRAWS
            and row["kendall_width"] <= RANDOM_KENDALL_WIDTH_THRESHOLD + NUMERICAL_TOLERANCE
            and row["top1_width"] <= RANDOM_TOP1_WIDTH_THRESHOLD + NUMERICAL_TOLERANCE
            and row["regret_width"] <= RANDOM_REGRET_WIDTH_THRESHOLD + NUMERICAL_TOLERANCE
        )
        width_seed_flags[str(row["replication_seed"])] = flag
    width_seed_count = int(sum(width_seed_flags.values()))
    context_clause = invariant_fraction >= RANDOM_CONTEXT_INVARIANT_FRACTION_THRESHOLD - NUMERICAL_TOLERANCE
    width_clause = width_seed_count >= CONSISTENT_SEEDS
    invariance_summary = {
        "pooled_seed_contexts": int(len(random_modal)),
        "invariant_seed_contexts": invariant_count,
        "pooled_invariant_fraction": invariant_fraction,
        "within_context_modal_share_threshold": RANDOM_CONTEXT_MODAL_SHARE_THRESHOLD,
        "context_invariance_clause_met": bool(context_clause),
        "performance_width_seed_flags": width_seed_flags,
        "performance_width_seed_count": width_seed_count,
        "performance_width_clause_met": bool(width_clause),
    }

    gates = {
        "coverage_hard_stop": bool(coverage_reasons),
        "random_equivalence_hard_stop": not bool(separates_any),
        "modal_winner_effective_tie_hard_stop": not bool(escapes_any),
        "oracle_winner_dominance_hard_stop": pooled_modal_share >= ORACLE_DOMINANCE_THRESHOLD - NUMERICAL_TOLERANCE,
        "weight_insensitivity_hard_stop": bool(context_clause or width_clause),
    }
    hard_stop = any(gates.values())
    return PilotBHardStopResult(
        protocol_schema=str(p["schema"]),
        coverage_complete=not bool(coverage_reasons),
        coverage_reasons=tuple(coverage_reasons),
        structured_method_assessments=tuple(method_assessments),
        random_seed_summaries=tuple(random_summaries),
        oracle_winner_summary=oracle_summary,
        random_context_invariance_summary=invariance_summary,
        gates=gates,
        hard_stop=bool(hard_stop),
        pilot_b_pass=not bool(hard_stop),
    )
