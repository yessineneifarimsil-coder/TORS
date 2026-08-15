from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "03_generate_oracle_utility.py"

spec = importlib.util.spec_from_file_location("oracle_utility", MODULE_PATH)
oracle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)


EXPECTED_ALPHAS = {
    "C1": 0.11,
    "C2": 0.04,
    "C3": 0.05,
    "C4": 0.07,
    "C5": 0.10,
    "C6": 0.14,
    "C7": 0.12,
    "C8": 0.16,
    "C9": 0.08,
    "C10": 0.13,
}
EXPECTED_EDGES = {
    ("C1", "C2"),
    ("C3", "C7"),
    ("C4", "C5"),
    ("C6", "C10"),
    ("C8", "C9"),
}


def load_configs() -> tuple[dict, dict]:
    with (ROOT / "config" / "benchmark.yaml").open("r", encoding="utf-8") as handle:
        benchmark = yaml.safe_load(handle)
    with (ROOT / "config" / "experiment.yaml").open("r", encoding="utf-8") as handle:
        experiment = yaml.safe_load(handle)
    return benchmark, experiment


def toy_spec() -> oracle.OracleSpec:
    return oracle.OracleSpec(
        zeta=2.0,
        alphas=EXPECTED_ALPHAS.copy(),
        interactions=tuple(
            oracle.Interaction(left=a, right=b, beta=0.20, label=f"{a}_{b}")
            for a, b in sorted(EXPECTED_EDGES)
        ),
    )


def make_frame(n_contexts: int = 3, include_test: bool = False) -> pd.DataFrame:
    alternatives = ("ATSC", "TSP", "TIDM", "RMTI-DRG", "V2X-CS", "DSM")
    rows: list[dict[str, object]] = []

    total_contexts = n_contexts + (1 if include_test else 0)
    for context_number in range(1, total_contexts + 1):
        is_test = include_test and context_number == total_contexts
        partition = "test" if is_test else ("fit" if context_number % 2 else "weight")

        for alt_idx, alt in enumerate(alternatives):
            row: dict[str, object] = {
                "context_id": f"S21001_C{context_number:04d}",
                "context_number": context_number,
                "replication_seed": 21001,
                "rho": 0.4,
                "partition": partition,
                "alternative_id": f"A{alt_idx + 1}",
                "alternative_key": alt,
            }
            for j in range(1, 11):
                row[f"g_C{j}"] = min(0.95, 0.03 * j + 0.02 * alt_idx + 0.01 * context_number)
            rows.append(row)

    return pd.DataFrame(rows)


def test_current_config_matches_frozen_oracle_definition() -> None:
    benchmark, experiment = load_configs()
    spec_from_config = oracle.load_oracle_spec(benchmark)

    assert spec_from_config.zeta == pytest.approx(2.0)
    assert spec_from_config.alphas == EXPECTED_ALPHAS
    assert sum(spec_from_config.alphas.values()) == pytest.approx(1.0)
    assert {
        tuple(sorted((edge.left, edge.right))) for edge in spec_from_config.interactions
    } == {tuple(sorted(edge)) for edge in EXPECTED_EDGES}
    assert all(edge.beta == pytest.approx(0.20) for edge in spec_from_config.interactions)
    assert oracle.configured_lambdas(experiment) == (0.0, 0.5, 1.0)


def test_q_transform_endpoints_and_reference_midpoint() -> None:
    values = oracle.q_transform(np.array([0.0, 0.5, 1.0]), zeta=2.0)
    assert values[0] == pytest.approx(0.0)
    assert values[1] == pytest.approx(np.log(2.0) / np.log(3.0))
    assert values[2] == pytest.approx(1.0)


def test_q_transform_is_strictly_increasing() -> None:
    grid = np.linspace(0.0, 1.0, 1001)
    transformed = oracle.q_transform(grid, zeta=2.0)
    assert np.all(np.diff(transformed) > 0.0)


def test_q_transform_rejects_out_of_domain() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        oracle.q_transform(np.array([0.2, 1.2]), zeta=2.0)


def test_lambda_zero_removes_interaction_component_from_utility() -> None:
    frame = make_frame(n_contexts=2)
    result = oracle.compute_oracle_utility(
        frame,
        oracle_spec=toy_spec(),
        lambda_value=0.0,
    )
    np.testing.assert_allclose(
        result["U_star"].to_numpy(),
        result["oracle_main_component"].to_numpy(),
        rtol=0.0,
        atol=1e-14,
    )


def test_manual_oracle_reconstruction() -> None:
    frame = make_frame(n_contexts=1).iloc[[0]].reset_index(drop=True)
    spec_value = toy_spec()
    lam = 0.5
    result = oracle.compute_oracle_utility(
        frame,
        oracle_spec=spec_value,
        lambda_value=lam,
    )

    q = {
        criterion: float(
            oracle.q_transform(
                np.array([frame.loc[0, f"g_{criterion}"]]), spec_value.zeta
            )[0]
        )
        for criterion in oracle.CRITERIA
    }
    main = sum(spec_value.alphas[c] * q[c] for c in oracle.CRITERIA)
    interaction = sum(
        edge.beta * q[edge.left] * q[edge.right]
        for edge in spec_value.interactions
    )
    expected = (main + lam * interaction) / (1.0 + lam)

    assert result.loc[0, "oracle_main_component"] == pytest.approx(main)
    assert result.loc[0, "oracle_interaction_component"] == pytest.approx(interaction)
    assert result.loc[0, "U_star"] == pytest.approx(expected)


@pytest.mark.parametrize("lambda_value", [0.0, 0.5, 1.0])
def test_oracle_utility_stays_in_unit_interval(lambda_value: float) -> None:
    rng = np.random.default_rng(1234)
    frame = make_frame(n_contexts=20)
    frame.loc[:, oracle.G_COLUMNS] = rng.uniform(0.0, 1.0, size=(len(frame), 10))

    result = oracle.compute_oracle_utility(
        frame,
        oracle_spec=toy_spec(),
        lambda_value=lambda_value,
    )
    assert result["U_star"].between(0.0, 1.0).all()


@pytest.mark.parametrize("lambda_value", [0.0, 0.5, 1.0])
def test_oracle_is_monotone_in_every_direction_adjusted_criterion(lambda_value: float) -> None:
    rng = np.random.default_rng(999)
    base = make_frame(n_contexts=1).iloc[[0]].reset_index(drop=True)
    base.loc[:, oracle.G_COLUMNS] = rng.uniform(0.1, 0.8, size=(1, 10))

    base_u = oracle.compute_oracle_utility(
        base,
        oracle_spec=toy_spec(),
        lambda_value=lambda_value,
    ).loc[0, "U_star"]

    for criterion in oracle.CRITERIA:
        improved = base.copy()
        column = f"g_{criterion}"
        improved.loc[0, column] = min(1.0, float(improved.loc[0, column]) + 0.10)
        improved_u = oracle.compute_oracle_utility(
            improved,
            oracle_spec=toy_spec(),
            lambda_value=lambda_value,
        ).loc[0, "U_star"]
        assert improved_u >= base_u - 1e-14


def test_all_zero_and_all_one_rows_hit_theoretical_utility_bounds() -> None:
    frame = make_frame(n_contexts=1).iloc[[0, 1]].reset_index(drop=True)
    frame.loc[0, oracle.G_COLUMNS] = 0.0
    frame.loc[1, oracle.G_COLUMNS] = 1.0

    for lam in (0.0, 0.5, 1.0):
        result = oracle.compute_oracle_utility(
            frame,
            oracle_spec=toy_spec(),
            lambda_value=lam,
        )
        assert result.loc[0, "U_star"] == pytest.approx(0.0)
        assert result.loc[1, "U_star"] == pytest.approx(1.0)


def test_partition_label_does_not_change_oracle_value() -> None:
    frame = make_frame(n_contexts=1).iloc[[0]].reset_index(drop=True)
    duplicate = frame.copy()
    duplicate["context_id"] = "S21001_C9999"
    duplicate["context_number"] = 9999
    duplicate["partition"] = "test"
    combined = pd.concat([frame, duplicate], ignore_index=True)

    result = oracle.compute_oracle_utility(
        combined,
        oracle_spec=toy_spec(),
        lambda_value=0.5,
    )
    assert result.loc[0, "U_star"] == pytest.approx(result.loc[1, "U_star"])


def test_development_scope_excludes_external_test_by_default() -> None:
    frame = make_frame(n_contexts=3, include_test=True)
    selected = oracle.select_development_scope(frame, include_external_test=False)

    assert not selected["partition"].eq("test").any()
    assert selected["context_id"].nunique() == 3
    assert len(selected) == 18


def test_external_test_can_be_transformed_without_entering_estimation_summary() -> None:
    frame = make_frame(n_contexts=3, include_test=True)
    selected = oracle.select_development_scope(frame, include_external_test=True)
    result = oracle.compute_oracle_utility(
        selected,
        oracle_spec=toy_spec(),
        lambda_value=0.5,
    )
    summary = oracle.estimation_summary(result)

    assert result["partition"].eq("test").any()
    assert summary["contexts"] == 3
    assert summary["rows"] == 18


def test_step3_output_contains_no_noisy_target_or_shap_columns() -> None:
    frame = make_frame(n_contexts=2)
    result = oracle.compute_oracle_utility(
        frame,
        oracle_spec=toy_spec(),
        lambda_value=0.5,
    )

    assert "U_star" in result.columns
    assert all(column in result.columns for column in oracle.Q_COLUMNS)
    forbidden = {"Y", "epsilon", "phi", "shap_value", "oracle_weight"}
    assert forbidden.isdisjoint(result.columns)


def test_validate_lambda_rejects_unconfigured_level() -> None:
    _, experiment = load_configs()
    with pytest.raises(ValueError, match="not one of the configured levels"):
        oracle.validate_lambda(0.25, experiment)
