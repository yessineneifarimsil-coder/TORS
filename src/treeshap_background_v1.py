from __future__ import annotations

"""
Deterministic TreeSHAP background constructor for the frozen v1 protocol.

Scope
-----
This module implements ONLY the already-frozen background-row selection rule:

    complete N=1000 FIT alternative-context row identities
        -> canonical identity order
        -> SeedSequence([replication_seed, 83001])
        -> one random priority permutation
        -> filter to FIT rows available at nested N
        -> take first 100

It deliberately does NOT:
- fit XGBoost,
- import or execute SHAP,
- compute oracle-attribution fidelity,
- compute global SHAP weights,
- run MCDM,
- inspect winner identity,
- use external TEST for background construction,
- use primary/reserve seeds to choose the background size.

The canonical pre-permutation identity order is
(context_number, alternative_id), matching the repository's existing
identity-based CRN/XGBoost conventions. This is an implementation
disambiguation only; it does not reopen the frozen B_bg=100 choice.
"""

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml
import json


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

XGBOOST_CONFIG_PATH = CONFIG / "xgboost.yaml"
EXPERIMENT_CONFIG_PATH = CONFIG / "experiment.yaml"
SEEDS_CONFIG_PATH = CONFIG / "seeds.yaml"
PROTOCOL_PATH = CONFIG / "treeshap_background_protocol_v1.json"

FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
IDENTITY_COLUMNS = ("context_id", "context_number", "alternative_id")
CANONICAL_SORT_COLUMNS = ("context_number", "alternative_id")

EXPECTED_MASTER_CONTEXTS = 1200
EXPECTED_ESTIMATION_CONTEXTS = 1000
EXPECTED_TEST_CONTEXTS = 200
EXPECTED_ALTERNATIVES = 6

EXPECTED_MASTER_ROWS = EXPECTED_MASTER_CONTEXTS * EXPECTED_ALTERNATIVES
EXPECTED_FIT_CONTEXTS = 800
EXPECTED_WEIGHT_CONTEXTS = 200
EXPECTED_FIT_ROWS = EXPECTED_FIT_CONTEXTS * EXPECTED_ALTERNATIVES
EXPECTED_WEIGHT_ROWS = EXPECTED_WEIGHT_CONTEXTS * EXPECTED_ALTERNATIVES
EXPECTED_TEST_ROWS = EXPECTED_TEST_CONTEXTS * EXPECTED_ALTERNATIVES

FROZEN_BACKGROUND_SIZE = 100
FROZEN_NAMESPACE = 83001


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object.")
    return data


def load_configs() -> dict[str, dict[str, Any]]:
    return {
        "xgboost": load_yaml(XGBOOST_CONFIG_PATH),
        "experiment": load_yaml(EXPERIMENT_CONFIG_PATH),
        "seeds": load_yaml(SEEDS_CONFIG_PATH),
        "protocol": load_json(PROTOCOL_PATH),
    }


def validate_frozen_protocol(configs: Mapping[str, Mapping[str, Any]]) -> None:
    """Fail closed unless the committed TreeSHAP background contract is intact."""
    x = configs["xgboost"]
    e = configs["experiment"]
    s = configs["seeds"]
    p = configs["protocol"]

    tree = x["tree_shap"]
    bg = tree["background"]

    if tree["feature_perturbation"] != "interventional":
        raise ValueError("TreeSHAP feature perturbation must remain interventional.")
    if tree["model_output"] != "raw":
        raise ValueError("TreeSHAP model_output must remain raw.")
    if tree["explanation_partition"] != "weight":
        raise ValueError("TreeSHAP explanation partition must remain WEIGHT.")

    if bg["source_partition"] != "fit":
        raise ValueError("TreeSHAP background source must remain FIT.")
    if bg["selection"] != "random_without_replacement":
        raise ValueError("TreeSHAP background selection must remain without replacement.")
    if bg["calibrated"] is not True:
        raise ValueError("Frozen TreeSHAP background protocol is not marked calibrated.")
    if bg["calibration_mode"] != "prospective_fixed_choice_without_outcome_tuning":
        raise ValueError("Unexpected TreeSHAP background calibration mode.")
    if int(bg["frozen_target_size"]) != FROZEN_BACKGROUND_SIZE:
        raise ValueError("Frozen TreeSHAP background size must be 100.")
    if list(bg["candidate_sizes"]) != [25, 50, 75, 100]:
        raise ValueError("Unexpected TreeSHAP provenance/sensitivity sizes.")
    if bg["sensitivity_sizes_are_non_decision"] is not True:
        raise ValueError("Sensitivity sizes must remain non-decision.")
    if bg["candidate_set_status"] != "resolved_prospectively_before_background_results":
        raise ValueError("TreeSHAP candidate-set status is not frozen as expected.")

    feasibility = bg["feasibility"]
    if int(feasibility["fit_contexts_at_smallest_primary_sample"]) != 20:
        raise ValueError("Smallest-N FIT-context count must remain 20.")
    if int(feasibility["alternatives_per_context"]) != EXPECTED_ALTERNATIVES:
        raise ValueError("Alternatives per context must remain six.")
    if int(feasibility["available_fit_rows_at_smallest_primary_sample"]) != 120:
        raise ValueError("Smallest-N FIT-row availability must remain 120.")
    if feasibility["selection_unit"] != "alternative_context_row":
        raise ValueError("TreeSHAP background selection unit changed.")
    if feasibility["selection_without_replacement"] is not True:
        raise ValueError("TreeSHAP background must remain sampled without replacement.")
    if bg["if_target_exceeds_available_rows"]["rule"] != "raise_error":
        raise ValueError("TreeSHAP insufficient-row rule must remain raise_error.")

    rp = bg["row_priority"]
    if rp["seed_registry_key"] != "treeshap_background.row_priority_namespace":
        raise ValueError("Unexpected TreeSHAP background seed-registry key.")
    for key in ("reuse_priority_across_rho", "reuse_priority_across_c", "reuse_priority_across_lambda"):
        if rp[key] is not True:
            raise ValueError(f"TreeSHAP row-priority flag {key} must remain true.")
    for key in (
        "depends_on_feature_values",
        "depends_on_target_values",
        "depends_on_oracle_values",
        "depends_on_method_outcomes",
    ):
        if rp[key] is not False:
            raise ValueError(f"TreeSHAP row-priority flag {key} must remain false.")

    if int(s["treeshap_background"]["row_priority_namespace"]) != FROZEN_NAMESPACE:
        raise ValueError("TreeSHAP background namespace must remain 83001.")

    sample_sizes = [int(v) for v in e["factors"]["sample_size"]["values"]]
    if sample_sizes != [25, 50, 100, 250, 1000]:
        raise ValueError("Unexpected nested sample-size grid.")
    nested = e["partition"]["nested_assignment"]
    if int(nested["maximum_contexts"]) != EXPECTED_ESTIMATION_CONTEXTS:
        raise ValueError("Estimation master must remain 1000 contexts.")
    if int(nested["block_size"]) != 5:
        raise ValueError("Nested partition block size must remain five.")
    if list(nested["roles_per_block"]) != ["fit", "fit", "fit", "fit", "weight"]:
        raise ValueError("Nested FIT/WEIGHT block composition changed.")
    if nested["reuse_assignment_across_sample_sizes"] is not True:
        raise ValueError("Partition assignment must remain reused across sample sizes.")
    if e["partition"]["leakage_rules"]["test_used_for_shap_background"] is not False:
        raise ValueError("External TEST must remain forbidden for SHAP background.")

    if p["status"] != "FROZEN_BEFORE_ANY_TREESHAP_BACKGROUND_SIZE_RESULT":
        raise ValueError("TreeSHAP background protocol JSON status changed.")
    if int(p["resolution"]["frozen_background_size"]) != FROZEN_BACKGROUND_SIZE:
        raise ValueError("Protocol JSON frozen background size changed.")
    if p["resolution"]["sensitivity_sizes_can_change_primary_background_size"] is not False:
        raise ValueError("Sensitivity sizes must not change the primary background size.")
    if int(p["randomness"]["row_priority_namespace"]) != FROZEN_NAMESPACE:
        raise ValueError("Protocol JSON TreeSHAP namespace changed.")
    if any(value is not False for value in p["firewalls"].values()):
        raise ValueError("One or more TreeSHAP background firewalls are not false.")


def validate_master_rows(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
) -> None:
    """Validate a complete N=1000 estimation + fixed TEST alternative-row master."""
    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
    }
    missing = sorted(required - set(master_rows.columns))
    if missing:
        raise ValueError(f"Master row frame is missing required columns: {missing}.")

    if len(master_rows) != EXPECTED_MASTER_ROWS:
        raise ValueError(
            f"TreeSHAP background constructor requires exactly {EXPECTED_MASTER_ROWS} "
            f"master rows; found {len(master_rows)}."
        )

    if master_rows.duplicated(["context_number", "alternative_id"]).any():
        raise ValueError("Duplicate (context_number, alternative_id) identities detected.")
    if master_rows.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate (context_id, alternative_id) identities detected.")

    seeds = set(int(v) for v in master_rows["replication_seed"].unique())
    if seeds != {int(replication_seed)}:
        raise ValueError(
            f"Master rows must contain only replication seed {replication_seed}; "
            f"found {sorted(seeds)}."
        )

    context_map = master_rows[["context_number", "context_id", "partition"]].drop_duplicates()
    if context_map["context_number"].nunique() != EXPECTED_MASTER_CONTEXTS:
        raise ValueError("Master frame must contain exactly 1200 context numbers.")
    if context_map["context_id"].nunique() != EXPECTED_MASTER_CONTEXTS:
        raise ValueError("Master frame must contain exactly 1200 context IDs.")
    if context_map.duplicated(["context_number"]).any():
        raise ValueError("A context_number maps to multiple context IDs or partitions.")
    if context_map.duplicated(["context_id"]).any():
        raise ValueError("A context_id maps to multiple context numbers or partitions.")

    numbers = np.sort(context_map["context_number"].to_numpy(dtype=int))
    if not np.array_equal(numbers, np.arange(1, EXPECTED_MASTER_CONTEXTS + 1)):
        raise ValueError("Master context numbers must be exactly 1..1200.")

    counts = context_map["partition"].value_counts().to_dict()
    expected_context_counts = {
        "fit": EXPECTED_FIT_CONTEXTS,
        "weight": EXPECTED_WEIGHT_CONTEXTS,
        "test": EXPECTED_TEST_CONTEXTS,
    }
    actual_context_counts = {str(k): int(v) for k, v in counts.items()}
    if actual_context_counts != expected_context_counts:
        raise ValueError(
            f"Unexpected context partition counts: {actual_context_counts}; "
            f"expected {expected_context_counts}."
        )

    estimation = context_map.loc[context_map["context_number"].le(1000)]
    external = context_map.loc[context_map["context_number"].gt(1000)]
    if not estimation["partition"].isin(["fit", "weight"]).all():
        raise ValueError("Contexts 1..1000 must be FIT or WEIGHT only.")
    if not external["partition"].eq("test").all():
        raise ValueError("Contexts 1001..1200 must be external TEST only.")

    alt_counts = master_rows.groupby("context_number", sort=False)["alternative_id"].nunique()
    if not (alt_counts == EXPECTED_ALTERNATIVES).all():
        raise ValueError("Every context must contain exactly six alternatives.")

    alternative_sets = master_rows.groupby("context_number", sort=False)["alternative_id"].apply(
        lambda x: tuple(sorted(str(v) for v in x))
    )
    if alternative_sets.nunique() != 1:
        raise ValueError("Every context must contain the same six alternative IDs.")

    row_counts = master_rows["partition"].value_counts().to_dict()
    expected_row_counts = {
        "fit": EXPECTED_FIT_ROWS,
        "weight": EXPECTED_WEIGHT_ROWS,
        "test": EXPECTED_TEST_ROWS,
    }
    actual_row_counts = {str(k): int(v) for k, v in row_counts.items()}
    if actual_row_counts != expected_row_counts:
        raise ValueError(
            f"Unexpected row partition counts: {actual_row_counts}; "
            f"expected {expected_row_counts}."
        )


def canonical_fit_identities(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
) -> pd.DataFrame:
    """Return the complete 4800-row FIT identity table in canonical order."""
    validate_master_rows(master_rows, replication_seed=replication_seed)

    fit = master_rows.loc[
        master_rows["partition"].eq("fit"),
        list(IDENTITY_COLUMNS),
    ].copy()

    fit.sort_values(
        list(CANONICAL_SORT_COLUMNS),
        kind="stable",
        inplace=True,
    )
    fit.reset_index(drop=True, inplace=True)

    if len(fit) != EXPECTED_FIT_ROWS:
        raise AssertionError("Complete FIT identity table must contain exactly 4800 rows.")
    if fit["context_id"].nunique() != EXPECTED_FIT_CONTEXTS:
        raise AssertionError("Complete FIT identity table must contain exactly 800 contexts.")

    return fit


def build_priority_table(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
    namespace: int = FROZEN_NAMESPACE,
) -> pd.DataFrame:
    """Create the one frozen random priority ordering over all N=1000 FIT rows."""
    if int(namespace) != FROZEN_NAMESPACE:
        raise ValueError("TreeSHAP background namespace must be the frozen value 83001.")

    canonical = canonical_fit_identities(
        master_rows,
        replication_seed=replication_seed,
    )

    rng = np.random.default_rng(
        np.random.SeedSequence([int(replication_seed), int(namespace)])
    )
    permutation = rng.permutation(len(canonical))

    priority = canonical.iloc[permutation].copy().reset_index(drop=True)
    priority["background_priority_rank"] = np.arange(1, len(priority) + 1, dtype=int)

    if priority.duplicated(["context_number", "alternative_id"]).any():
        raise AssertionError("Priority permutation duplicated a FIT identity.")
    if set(priority["partition"].unique()) if "partition" in priority.columns else set():
        raise AssertionError("Identity-only priority table unexpectedly contains partition data.")

    return priority


def select_background_rows(
    master_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    target_size: int = FROZEN_BACKGROUND_SIZE,
    namespace: int = FROZEN_NAMESPACE,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    """Select the frozen TreeSHAP background rows for one nested N.

    Selection depends only on FIT row identity and the frozen RNG namespace.
    Feature/target/oracle/method values play no role in membership.
    """
    if int(target_size) != FROZEN_BACKGROUND_SIZE:
        raise ValueError("Primary TreeSHAP background target_size is frozen at 100.")

    allowed_n = {25, 50, 100, 250, 1000}
    n = int(n_contexts)
    if n not in allowed_n:
        raise ValueError(f"N={n} is not a frozen sample-size level: {sorted(allowed_n)}.")

    priority = build_priority_table(
        master_rows,
        replication_seed=replication_seed,
        namespace=namespace,
    )

    eligible = priority.loc[priority["context_number"].le(n)].copy()
    expected_eligible = {
        25: 120,
        50: 240,
        100: 480,
        250: 1200,
        1000: 4800,
    }[n]
    if len(eligible) != expected_eligible:
        raise ValueError(
            f"N={n} must expose exactly {expected_eligible} FIT alternative-context rows; "
            f"found {len(eligible)}."
        )

    if len(eligible) < int(target_size):
        raise ValueError(
            f"Frozen TreeSHAP background size {target_size} exceeds the "
            f"{len(eligible)} eligible FIT rows at N={n}."
        )

    selected_ids = eligible.iloc[: int(target_size)].copy()

    keyed = master_rows.set_index(
        ["context_number", "alternative_id"],
        drop=False,
    )
    lookup_keys = list(
        selected_ids[["context_number", "alternative_id"]].itertuples(
            index=False,
            name=None,
        )
    )
    selected = keyed.loc[lookup_keys].reset_index(drop=True)

    # Preserve the priority rank explicitly for audit/reproducibility.
    selected["background_priority_rank"] = selected_ids[
        "background_priority_rank"
    ].to_numpy(dtype=int)

    if len(selected) != FROZEN_BACKGROUND_SIZE:
        raise AssertionError("TreeSHAP background must contain exactly 100 rows.")
    if selected.duplicated(["context_number", "alternative_id"]).any():
        raise AssertionError("Selected TreeSHAP background contains duplicate identities.")
    if set(selected["partition"].unique()) != {"fit"}:
        raise AssertionError("TreeSHAP background contains non-FIT rows.")
    if int(selected["context_number"].max()) > n:
        raise AssertionError("TreeSHAP background escaped the requested nested N.")

    # Identity sequence must match the filtered priority table exactly.
    selected_key_sequence = list(
        selected[["context_number", "alternative_id"]].itertuples(index=False, name=None)
    )
    expected_key_sequence = list(
        selected_ids[["context_number", "alternative_id"]].itertuples(index=False, name=None)
    )
    if selected_key_sequence != expected_key_sequence:
        raise AssertionError("Selected background identity order differs from frozen priority order.")

    audit: dict[str, float | int | bool] = {
        "replication_seed": int(replication_seed),
        "N": n,
        "namespace": int(namespace),
        "master_rows": int(len(master_rows)),
        "master_fit_rows": EXPECTED_FIT_ROWS,
        "eligible_fit_rows": int(len(eligible)),
        "background_rows": int(len(selected)),
        "background_to_fit_row_ratio": float(len(selected) / len(eligible)),
        "fit_only": True,
        "weight_rows_used": 0,
        "external_test_rows_used": 0,
        "selection_depends_on_feature_values": False,
        "selection_depends_on_target_values": False,
        "selection_depends_on_oracle_values": False,
        "selection_depends_on_method_outcomes": False,
    }
    return selected, audit


def background_feature_matrix(background_rows: pd.DataFrame) -> np.ndarray:
    """Return the 100x10 direction-adjusted feature matrix for TreeExplainer."""
    missing = [column for column in FEATURES if column not in background_rows.columns]
    if missing:
        raise ValueError(f"Background rows are missing model features: {missing}.")
    if len(background_rows) != FROZEN_BACKGROUND_SIZE:
        raise ValueError("Background feature matrix requires exactly 100 rows.")
    if "partition" not in background_rows.columns or not background_rows["partition"].eq("fit").all():
        raise ValueError("Background feature matrix may contain FIT rows only.")

    X = background_rows.loc[:, FEATURES].to_numpy(dtype=float)
    if X.shape != (FROZEN_BACKGROUND_SIZE, len(FEATURES)):
        raise AssertionError(f"Unexpected TreeSHAP background feature shape: {X.shape}.")
    if not np.isfinite(X).all():
        raise ValueError("TreeSHAP background features contain non-finite values.")
    return X
