from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "04_generate_noisy_target.py"
ORACLE_PATH = ROOT / "src" / "03_generate_oracle_utility.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


noise = load_module("noise_step4_test", MODULE_PATH)
oracle = load_module("oracle_step3_test_for_noise", ORACLE_PATH)


def toy_experiment() -> dict:
    return {
        "factors": {
            "relative_target_noise": {"values": [0.10, 0.30, 0.60]},
            "interaction_strength": {"values": [0.0, 0.5, 1.0]},
        },
        "target_noise": {
            "base_distribution": "standard_normal",
            "signal_sd": {
                "source": "noise_free_1000_context_estimation_master_pool_for_condition",
                "exclude_external_test": True,
                "computed_before_sample_size_subsetting": True,
            },
            "common_random_numbers": {
                "reuse_standard_normal_noise_draw": True,
                "seed_registry_key": "target_noise.stream_namespace",
                "master_alternative_context_rows_per_seed": 7200,
                "assignment_key": ["context_number", "alternative_id"],
                "reuse_across_N": True,
                "reuse_across_rho": True,
                "reuse_across_lambda": True,
                "reuse_across_c": True,
            },
        },
    }


def toy_seeds() -> dict:
    return {"target_noise": {"stream_namespace": 3001}}


def make_master_identities() -> pd.DataFrame:
    rows = []
    for context_number in range(1, 1201):
        partition = "fit" if context_number <= 800 else (
            "weight" if context_number <= 1000 else "test"
        )
        for alt in range(1, 7):
            rows.append(
                {
                    "context_id": f"S21001_C{context_number:04d}",
                    "context_number": context_number,
                    "alternative_id": f"A{alt}",
                    "partition": partition,
                }
            )
    return pd.DataFrame(rows)


def make_oracle_master() -> pd.DataFrame:
    frame = make_master_identities()
    # Deterministic nonconstant U*; TEST distribution is intentionally different.
    x = np.linspace(0.1, 0.9, 6000)
    t = np.linspace(0.95, 0.99, 1200)
    frame["U_star"] = np.concatenate([x, t])
    return frame


def test_current_config_freezes_target_noise_namespace_3001() -> None:
    experiment = yaml.safe_load((ROOT / "config" / "experiment.yaml").read_text(encoding="utf-8"))
    seeds = yaml.safe_load((ROOT / "config" / "seeds.yaml").read_text(encoding="utf-8"))
    noise.validate_target_noise_protocol(experiment, seeds)
    assert noise.target_noise_namespace(seeds) == 3001


def test_configured_noise_levels_are_exact() -> None:
    assert noise.configured_noise_levels(toy_experiment()) == (0.10, 0.30, 0.60)


def test_unconfigured_noise_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="not one of the configured levels"):
        noise.validate_noise_level(0.2, toy_experiment())


def test_master_noise_draw_is_deterministic() -> None:
    ids = make_master_identities()
    a = noise.master_noise_table(ids, replication_seed=21001, namespace=3001)
    b = noise.master_noise_table(ids, replication_seed=21001, namespace=3001)
    np.testing.assert_array_equal(a["target_noise_e"], b["target_noise_e"])


def test_master_noise_assignment_is_input_order_invariant() -> None:
    ids = make_master_identities()
    shuffled = ids.sample(frac=1.0, random_state=123).reset_index(drop=True)
    a = noise.master_noise_table(ids, replication_seed=21001, namespace=3001)
    b = noise.master_noise_table(shuffled, replication_seed=21001, namespace=3001)
    a = a.sort_values(["context_number", "alternative_id"]).reset_index(drop=True)
    b = b.sort_values(["context_number", "alternative_id"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_different_replication_seed_changes_noise_master() -> None:
    ids = make_master_identities()
    a = noise.master_noise_table(ids, replication_seed=21001, namespace=3001)
    b = noise.master_noise_table(ids, replication_seed=21002, namespace=3001)
    assert not np.array_equal(a["target_noise_e"].to_numpy(), b["target_noise_e"].to_numpy())


def test_signal_sd_uses_estimation_rows_only() -> None:
    frame = make_oracle_master()
    observed = noise.compute_signal_sd(frame)
    expected = frame.iloc[:6000]["U_star"].to_numpy().std(ddof=0)
    assert observed == pytest.approx(expected, abs=1e-15)


def test_test_values_cannot_change_signal_sd() -> None:
    frame = make_oracle_master()
    first = noise.compute_signal_sd(frame)
    frame.loc[frame["partition"].eq("test"), "U_star"] = -9999.0
    second = noise.compute_signal_sd(frame)
    assert second == pytest.approx(first, abs=1e-15)


def test_add_relative_noise_matches_exact_equation() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    result = noise.add_relative_noise(frame, c=0.30, signal_sd=s_u, noise_table=table)
    expected = result["U_star"].to_numpy() + 0.30 * s_u * result["target_noise_e"].to_numpy()
    np.testing.assert_allclose(result["Y"], expected, atol=0.0, rtol=0.0)


def test_same_base_e_is_reused_across_c_levels() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    low = noise.add_relative_noise(frame, c=0.10, signal_sd=s_u, noise_table=table)
    high = noise.add_relative_noise(frame, c=0.60, signal_sd=s_u, noise_table=table)
    np.testing.assert_array_equal(low["target_noise_e"], high["target_noise_e"])
    np.testing.assert_allclose(
        high["target_noise"].to_numpy(),
        6.0 * low["target_noise"].to_numpy(),
        atol=1e-15,
        rtol=1e-15,
    )


def test_noisy_target_is_not_clipped() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    # Artificially large signal scale makes excursions outside [0,1] inevitable.
    result = noise.add_relative_noise(frame, c=0.60, signal_sd=5.0, noise_table=table)
    y = result["Y"].to_numpy()
    assert np.any(y < 0.0) or np.any(y > 1.0)


def test_development_summary_ignores_test_noise() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    result = noise.add_relative_noise(frame, c=0.30, signal_sd=s_u, noise_table=table)
    first = noise.development_noise_summary(result)
    result.loc[result["partition"].eq("test"), "Y"] = 1e9
    result.loc[result["partition"].eq("test"), "target_noise"] = 1e9
    second = noise.development_noise_summary(result)
    assert second == first


def test_realized_noise_ratio_tracks_base_e_sd_exactly() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    result = noise.add_relative_noise(frame, c=0.30, signal_sd=s_u, noise_table=table)
    summary = noise.development_noise_summary(result)
    assert summary["realized_noise_to_signal_sd_ratio"] == pytest.approx(
        0.30 * summary["base_e_sd"], abs=1e-15
    )


def test_signal_sd_is_invariant_to_c() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    a = noise.add_relative_noise(frame, c=0.10, signal_sd=s_u, noise_table=table)
    b = noise.add_relative_noise(frame, c=0.60, signal_sd=s_u, noise_table=table)
    assert a["signal_sd"].iloc[0] == b["signal_sd"].iloc[0] == s_u


def test_output_has_no_shap_or_mcdm_columns() -> None:
    frame = make_oracle_master()
    table = noise.master_noise_table(frame, replication_seed=21001, namespace=3001)
    s_u = noise.compute_signal_sd(frame)
    result = noise.add_relative_noise(frame, c=0.30, signal_sd=s_u, noise_table=table)
    lower = {column.lower() for column in result.columns}
    assert "y" in lower
    assert not any("shap" in column for column in lower)
    assert not any("mcdm" in column for column in lower)


def test_master_noise_table_has_standard_normal_shape_and_reasonable_moments() -> None:
    ids = make_master_identities()
    table = noise.master_noise_table(ids, replication_seed=21001, namespace=3001)
    e = table["target_noise_e"].to_numpy()
    assert len(e) == 7200
    assert abs(e.mean()) < 0.05
    assert 0.95 < e.std(ddof=0) < 1.05



def test_dynamic_oracle_loader_supports_dataclass_module() -> None:
    """The CLI loader must register Step 3 before executing @dataclass code."""
    loaded = noise.load_oracle_module()

    assert hasattr(loaded, "OracleSpec")
    assert loaded.__name__ == "oracle_step3"
    assert sys.modules["oracle_step3"] is loaded
