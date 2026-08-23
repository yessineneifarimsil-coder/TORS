from __future__ import annotations

"""Frozen diagnostic RandomWeights and MajorityWinner references.

RandomWeights generates 200 Dirichlet(1,...,1) vectors from the replication-
specific frozen stream and accepts no condition arguments, enforcing reuse
across N, rho, c, and lambda. MajorityWinner estimates the modal deterministic
oracle winner on WEIGHT and emits a constant Top-1 prediction identity for the
fixed external TEST contexts. This module does not run MOORA, decision metrics,
model fitting, SHAP, or MCDM.
"""

from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np
import pandas as pd


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
ALTERNATIVE_IDS = tuple(f"A{i}" for i in range(1, 7))
ALTERNATIVES_PER_CONTEXT = 6
EPSILON = 1.0e-12

RANDOM_WEIGHT_MASTER_SEED = 81001
RANDOM_WEIGHT_DRAWS = 200
DIRICHLET_CONCENTRATION = np.ones(N_CRITERIA, dtype=float)

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_WEIGHT_ROWS = {25: 30, 50: 60, 100: 120, 250: 300, 1000: 1200}
EXPECTED_WEIGHT_CONTEXTS = {25: 5, 50: 10, 100: 20, 250: 50, 1000: 200}
EXPECTED_TEST_CONTEXTS = 200
EXPECTED_TEST_ROWS = EXPECTED_TEST_CONTEXTS * ALTERNATIVES_PER_CONTEXT
SORT_COLUMNS = ("context_number", "alternative_id")


@dataclass(frozen=True)
class RandomWeightReference:
    replication_seed: int
    weights: np.ndarray
    weights_sha256: str
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class MajorityWinnerReference:
    replication_seed: int
    n_contexts: int
    modal_winner_id: str
    modal_winner_count: int
    modal_winner_share: float
    distinct_oracle_winners: int
    normalized_winner_entropy: float
    winner_counts_by_alternative: dict[str, int]
    winner_by_weight_context_number: dict[int, str]
    diagnostics: dict[str, Any]


def generate_random_weight_reference(
    *,
    replication_seed: int,
) -> RandomWeightReference:
    """Generate the frozen 200 Dirichlet vectors for one replication seed."""
    seed = int(replication_seed)
    if seed < 0:
        raise ValueError("RandomWeights replication_seed must be nonnegative.")
    rng = np.random.default_rng(
        np.random.SeedSequence([seed, RANDOM_WEIGHT_MASTER_SEED])
    )
    weights = rng.dirichlet(DIRICHLET_CONCENTRATION, size=RANDOM_WEIGHT_DRAWS)
    if weights.shape != (RANDOM_WEIGHT_DRAWS, N_CRITERIA):
        raise AssertionError("Unexpected RandomWeights matrix shape.")
    if not np.isfinite(weights).all() or np.any(weights <= 0.0):
        raise FloatingPointError("RandomWeights contains invalid values.")
    if not np.allclose(weights.sum(axis=1), 1.0, atol=1.0e-12, rtol=0.0):
        raise FloatingPointError("RandomWeights rows do not sum to one.")

    canonical = np.asarray(weights, dtype="<f8", order="C")
    weights_sha256 = hashlib.sha256(canonical.tobytes(order="C")).hexdigest()
    weights.setflags(write=False)
    diagnostics: dict[str, Any] = {
        "method": "RandomWeights",
        "role": "diagnostic_lower_reference",
        "replication_seed": seed,
        "distribution": "Dirichlet",
        "concentration": [1.0] * N_CRITERIA,
        "draws": RANDOM_WEIGHT_DRAWS,
        "master_seed": RANDOM_WEIGHT_MASTER_SEED,
        "rng_seed_sequence": [seed, RANDOM_WEIGHT_MASTER_SEED],
        "reuse_same_200_vectors_across_N_rho_c_lambda_for_seed": True,
        "accepts_condition_arguments": False,
        "moora_executed": False,
        "decision_metrics_computed": False,
        "external_test_rows_used": 0,
        "oracle_utility_used": False,
        "target_Y_used": False,
        "model_fit_executed": False,
        "shap_used": False,
        "winner_inspected": False,
    }
    return RandomWeightReference(
        replication_seed=seed,
        weights=weights,
        weights_sha256=weights_sha256,
        diagnostics=diagnostics,
    )


def prepare_majority_weight_rows(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> pd.DataFrame:
    """Select exact nested WEIGHT oracle rows for MajorityWinner estimation."""
    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        "U_star",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"MajorityWinner input is missing columns: {missing}.")
    if rows.empty:
        raise ValueError("MajorityWinner input must not be empty.")

    nested = rows.loc[rows["context_number"].le(n)].copy()
    if nested.empty:
        raise ValueError("No nested estimation rows found for requested N.")
    unexpected = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected:
        raise ValueError(f"Unexpected nested partition labels: {unexpected}.")

    # WEIGHT-only winner-estimation firewall. FIT values are excluded before
    # oracle utility and seed validation. External TEST is beyond nested scope.
    selected = nested.loc[nested["partition"].eq("weight")].copy()
    if selected.empty:
        raise ValueError("No WEIGHT rows found for MajorityWinner estimation.")
    if selected["replication_seed"].isna().any():
        raise ValueError("WEIGHT replication_seed contains missing values.")
    seeds = set(selected["replication_seed"].astype(int).tolist())
    if seeds != {int(replication_seed)}:
        raise ValueError(
            f"MajorityWinner WEIGHT rows require replication_seed={replication_seed}; "
            f"found {sorted(seeds)}."
        )
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate WEIGHT context-alternative identity detected.")
    utility = selected["U_star"].to_numpy(dtype=float)
    if not np.isfinite(utility).all():
        raise ValueError("WEIGHT U_star contains non-finite values.")
    if np.any(utility < -EPSILON) or np.any(utility > 1.0 + EPSILON):
        raise ValueError("WEIGHT U_star escaped the theoretical [0,1] range.")

    selected.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)
    if len(selected) != EXPECTED_WEIGHT_ROWS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_WEIGHT_ROWS[n]} WEIGHT rows; found {len(selected)}."
        )
    if selected["context_number"].nunique() != EXPECTED_WEIGHT_CONTEXTS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_WEIGHT_CONTEXTS[n]} WEIGHT contexts; "
            f"found {selected['context_number'].nunique()}."
        )
    if selected.groupby("context_number")["context_id"].nunique().max() != 1:
        raise ValueError("A WEIGHT context number maps to multiple context IDs.")
    for context_number, group in selected.groupby("context_number", sort=False):
        alternatives = tuple(group["alternative_id"].astype(str).tolist())
        if alternatives != ALTERNATIVE_IDS:
            raise ValueError(
                f"WEIGHT context {context_number} must contain A1..A6 exactly once."
            )
    return selected


def _oracle_winner(group: pd.DataFrame) -> str:
    utility = group["U_star"].to_numpy(dtype=float)
    maximum = float(np.max(utility))
    tied = group.loc[maximum - utility <= EPSILON, "alternative_id"].astype(str)
    if tied.empty:
        raise AssertionError("Oracle top tie set is unexpectedly empty.")
    return min(tied.tolist())


def estimate_majority_winner(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> MajorityWinnerReference:
    """Estimate modal deterministic oracle winner on WEIGHT only."""
    selected = prepare_majority_weight_rows(
        rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )
    winner_by_context: dict[int, str] = {}
    for context_number, group in selected.groupby("context_number", sort=False):
        winner_by_context[int(context_number)] = _oracle_winner(group)

    counts = {alternative_id: 0 for alternative_id in ALTERNATIVE_IDS}
    for winner in winner_by_context.values():
        counts[winner] += 1
    modal_count = max(counts.values())
    modal_winner = min(
        alternative_id
        for alternative_id, count in counts.items()
        if count == modal_count
    )
    context_count = len(winner_by_context)
    modal_share = float(modal_count / context_count)
    probabilities = np.asarray(
        [counts[alternative_id] / context_count for alternative_id in ALTERNATIVE_IDS],
        dtype=float,
    )
    positive = probabilities > 0.0
    normalized_entropy = float(
        -np.sum(probabilities[positive] * np.log(probabilities[positive]))
        / np.log(ALTERNATIVES_PER_CONTEXT)
    )
    distinct = int(np.count_nonzero(np.asarray(list(counts.values()))))
    diagnostics: dict[str, Any] = {
        "method": "MajorityWinner",
        "role": "trivial_constant_top1_reference",
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "winner_estimation_partition": "weight",
        "weight_rows_used": int(len(selected)),
        "weight_contexts_used": context_count,
        "oracle_optimal_choice": "argmax_U_star",
        "oracle_score_tie_absolute_tolerance": EPSILON,
        "oracle_top1_tie_break": "alternative_id_ascending",
        "modal_count_tie_break": "alternative_id_ascending",
        "evaluate_on": "test",
        "primary_metric": "Top1Accuracy",
        "normalized_winner_entropy_denominator": "log_6",
        "test_oracle_utility_used_for_estimation": False,
        "test_target_Y_used_for_estimation": False,
        "fit_rows_used_for_estimation": 0,
        "model_fit_executed": False,
        "shap_used": False,
        "mcdm_executed": False,
        "decision_metrics_computed": False,
    }
    return MajorityWinnerReference(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        modal_winner_id=modal_winner,
        modal_winner_count=int(modal_count),
        modal_winner_share=modal_share,
        distinct_oracle_winners=distinct,
        normalized_winner_entropy=normalized_entropy,
        winner_counts_by_alternative=counts,
        winner_by_weight_context_number=winner_by_context,
        diagnostics=diagnostics,
    )


def build_majority_winner_test_predictions(
    rows: pd.DataFrame,
    *,
    reference: MajorityWinnerReference,
) -> pd.DataFrame:
    """Emit one constant predicted identity per fixed external TEST context.

    TEST U_star, Y, features, and outcomes are deliberately not read. Accuracy
    and all other decision metrics belong to the later frozen metrics stage.
    """
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"MajorityWinner TEST identities are missing columns: {missing}.")
    test = rows.loc[rows["partition"].eq("test"), list(required)].copy()
    if len(test) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"MajorityWinner requires {EXPECTED_TEST_ROWS} TEST rows; found {len(test)}."
        )
    if test["replication_seed"].isna().any():
        raise ValueError("TEST replication_seed contains missing values.")
    seeds = set(test["replication_seed"].astype(int).tolist())
    if seeds != {reference.replication_seed}:
        raise ValueError(
            "TEST identities do not match MajorityWinner replication seed."
        )
    if test.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate TEST context-alternative identity detected.")
    test.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    if test["context_number"].nunique() != EXPECTED_TEST_CONTEXTS:
        raise ValueError(
            f"MajorityWinner requires {EXPECTED_TEST_CONTEXTS} TEST contexts."
        )
    for context_number, group in test.groupby("context_number", sort=False):
        alternatives = tuple(group["alternative_id"].astype(str).tolist())
        if alternatives != ALTERNATIVE_IDS:
            raise ValueError(
                f"TEST context {context_number} must contain A1..A6 exactly once."
            )
        if group["context_id"].nunique() != 1:
            raise ValueError("A TEST context number maps to multiple context IDs.")

    contexts = test.drop_duplicates("context_number", keep="first").copy()
    result = contexts.loc[:, ["context_id", "context_number", "replication_seed"]]
    result["reference"] = "MajorityWinner"
    result["predicted_alternative_id"] = reference.modal_winner_id
    result.reset_index(drop=True, inplace=True)
    return result
