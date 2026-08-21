from __future__ import annotations

"""Frozen Equal-weight comparator for the weighting/MCDM benchmark.

This module implements the prespecified deterministic Equal baseline:
0.1 for each of g_C1..g_C10. It does not inspect benchmark data, partitions,
seeds, outcomes, SHAP values, MCDM scores, or winner identities.
"""

from dataclasses import dataclass
from typing import Any


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
EQUAL_WEIGHT = 0.1


@dataclass(frozen=True)
class EqualWeightResult:
    weights_by_feature: dict[str, float]
    diagnostics: dict[str, Any]


def compute_equal_weights() -> EqualWeightResult:
    """Return the frozen ten-criterion Equal comparator."""
    weights = {feature: EQUAL_WEIGHT for feature in FEATURES}

    if set(weights) != set(FEATURES):
        raise AssertionError("Equal-weight feature mapping is incomplete.")
    if len(weights) != N_CRITERIA:
        raise AssertionError("Equal-weight vector must contain exactly ten criteria.")
    if any(value != EQUAL_WEIGHT for value in weights.values()):
        raise AssertionError("Equal-weight vector changed from the frozen value 0.1.")
    if abs(sum(weights.values()) - 1.0) > 1.0e-12:
        raise AssertionError("Equal weights do not sum to one.")

    diagnostics: dict[str, Any] = {
        "method": "Equal",
        "n_criteria": N_CRITERIA,
        "weight_per_criterion": EQUAL_WEIGHT,
        "data_used": False,
        "partition_used": None,
        "replication_seed_used": False,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "shap_used": False,
        "mcdm_executed": False,
        "winner_inspected": False,
        "fallback": False,
    }

    return EqualWeightResult(
        weights_by_feature=weights,
        diagnostics=diagnostics,
    )
