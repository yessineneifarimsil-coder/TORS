from __future__ import annotations

"""
Historical v2.1 Layer-B/frontier and lower-boundary characterization tests.

These tests characterize properties reproduced at the historical v2.1
checkpoint before the v2.2 redesign. They are NOT v2.2 acceptance gates.

When the v2.2 generator/oracle geometry is deliberately changed, these tests
must be reviewed and retired/replaced rather than weakened to make the new
design pass.
"""

import copy
import importlib.util
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SEED = 21001
RHO = 0.4
LAMBDA = 0.5
EPS = 1.0e-12
C1_C7 = tuple(f"C{i}" for i in range(1, 8))


def _load_numbered_module(name: str, path: Path):
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


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(scope="module")
def historical_sigma0_world():
    step1 = _load_numbered_module(
        "swfc_v21_layerb_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = _load_numbered_module(
        "swfc_v21_layerb_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )
    step3 = _load_numbered_module(
        "swfc_v21_layerb_step3",
        ROOT / "src" / "03_generate_oracle_utility.py",
    )

    benchmark = _load_yaml(ROOT / "config" / "benchmark.yaml")
    experiment = _load_yaml(ROOT / "config" / "experiment.yaml")
    seeds = _load_yaml(ROOT / "config" / "seeds.yaml")

    contexts, _ = step1.generate_master_contexts(
        replication_seed=SEED,
        rho=RHO,
        benchmark=benchmark,
        experiment=experiment,
        seeds=seeds,
    )

    benchmark0 = copy.deepcopy(benchmark)
    benchmark0["technology_response"]["criterion_noise"]["sigma_x"] = 0.0

    responses, _, _, _ = step2.generate_master_technology_responses(
        contexts=contexts,
        replication_seed=SEED,
        benchmark=benchmark0,
    )

    estimation = responses.loc[
        responses["partition"].isin(("fit", "weight"))
    ].copy()

    assert estimation["context_number"].nunique() == 1000
    assert len(estimation) == 6000
    assert not (estimation["partition"] == "test").any()

    oracle_spec = step3.load_oracle_spec(benchmark)
    oracle = step3.compute_oracle_utility(
        estimation,
        oracle_spec=oracle_spec,
        lambda_value=LAMBDA,
    )

    return benchmark, estimation, oracle


def _oracle_matrix(oracle):
    pivot = (
        oracle.pivot(
            index="context_number",
            columns="alternative_id",
            values="U_star",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    return pivot.columns.tolist(), pivot.to_numpy(dtype=float)


def test_v21_noise_free_oracle_frontier_is_historically_concentrated(
    historical_sigma0_world,
):
    """
    Historical Layer-B characterization, not a future adequacy threshold.

    The v2.1 seed-21001/rho-.4 noise-free oracle had 19 orderings, two
    winners, and a modal winner in 962/1000 estimation contexts.
    """

    _, _, oracle = historical_sigma0_world
    alt_ids, U = _oracle_matrix(oracle)

    orders = []
    winners = []
    for row in U:
        order_idx = sorted(
            range(len(alt_ids)),
            key=lambda j: (-float(row[j]), str(alt_ids[j])),
        )
        order = tuple(alt_ids[j] for j in order_idx)
        orders.append(order)
        winners.append(order[0])

    counts = Counter(winners)
    modal_alt, modal_count = sorted(
        counts.items(),
        key=lambda kv: (-kv[1], str(kv[0])),
    )[0]

    assert len(set(orders)) == 19
    assert len(counts) == 2
    assert modal_count == 962
    assert modal_count / len(winners) == pytest.approx(0.962, abs=1e-12)

    # Deliberately do not assert the named modal alternative.
    assert modal_alt in alt_ids


def test_v21_constant_modal_baseline_has_historical_zero_p95_regret(
    historical_sigma0_world,
):
    """
    Characterize the historical trivial-baseline competitiveness.

    This is retired/replaced when v2.2 changes the decision geometry.
    """

    _, _, oracle = historical_sigma0_world
    alt_ids, U = _oracle_matrix(oracle)

    winners = [alt_ids[int(np.argmax(row))] for row in U]
    counts = Counter(winners)
    modal_alt, modal_count = sorted(
        counts.items(),
        key=lambda kv: (-kv[1], str(kv[0])),
    )[0]
    modal_index = alt_ids.index(modal_alt)

    u_max = U.max(axis=1)
    u_min = U.min(axis=1)
    chosen = U[:, modal_index]
    regret = (u_max - chosen) / (u_max - u_min + EPS)

    nonoptimal = np.asarray(winners, dtype=object) != modal_alt

    assert modal_count == 962
    assert int(nonoptimal.sum()) == 38
    assert float(np.median(regret)) == pytest.approx(0.0, abs=1e-15)
    assert float(np.quantile(regret, 0.95)) == pytest.approx(0.0, abs=1e-15)
    assert float(regret.mean()) == pytest.approx(0.00111064, abs=5e-9)


def test_v21_sigma0_c1_c7_lower_boundary_only_reflects_structural_zeros(
    historical_sigma0_world,
):
    """
    At sigma_x=0, active C1-C7 pathways remain strictly above zero.

    Exact zeros are confined to capability-class '0' pathways, so the
    reproduced normalization collapse is not caused by lower clipping of
    active deterministic responses.
    """

    benchmark, estimation, _ = historical_sigma0_world

    for alternative_key, alternative in benchmark["alternatives"].items():
        alt_id = alternative["id"]
        rows = estimation.loc[estimation["alternative_id"] == alt_id]

        for criterion in C1_C7:
            values = rows[f"g_{criterion}"].to_numpy(dtype=float)
            capability_class = alternative["capability"][criterion]

            if capability_class == "0":
                assert np.all(values == 0.0), (
                    alternative_key,
                    criterion,
                    values.min(),
                    values.max(),
                )
            else:
                assert np.all(values > 0.0), (
                    alternative_key,
                    criterion,
                    values.min(),
                    values.max(),
                )
