from __future__ import annotations

"""
Historical v2.1 structural-characterization tests.

These tests intentionally characterize the structural property documented at
Git checkpoint 893a727. They are NOT acceptance criteria for a future v2.2
generator.

When the technology-response architecture is deliberately redesigned under a
new protocol version, this file must be reviewed and either retired or replaced
by the corresponding v2.2 scientific-invariant tests.

The tests do not assert accidental winner identities, modal shares, or exact
Pilot-A outcomes. They test only the structural C1-C7 normalization collapse
identified before the v2.2 redesign.
"""

import copy
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SEED = 21001
RHO = 0.4
EPS = 1.0e-12

C1_C7 = tuple(f"C{i}" for i in range(1, 8))
C8_C10 = ("C8", "C9", "C10")

# Numerical characterization tolerance, NOT a substantive adequacy threshold.
# The independently reproduced maximum C1-C7 normalized SD at 893a727 was
# approximately 1.224e-9. A 1e-7 ceiling leaves cross-platform numerical
# headroom while remaining many orders above floating-point zero.
NUMERICAL_COLLAPSE_TOL = 1.0e-7

# Used only to establish that C8-C10 are not subject to the same complete
# numerical collapse. This is not a future minimum-signal requirement.
NONZERO_SIGNAL_FLOOR = 1.0e-6


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
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"Expected mapping in {path}")
    return data


@pytest.fixture(scope="module")
def sigma0_estimation_responses():
    """Generate the historical v2.1 seed-21001/rho-.4 world in memory."""

    step1 = _load_numbered_module(
        "swfc_v21_characterization_step1",
        ROOT / "src" / "01_generate_contexts.py",
    )
    step2 = _load_numbered_module(
        "swfc_v21_characterization_step2",
        ROOT / "src" / "02_generate_technology_responses.py",
    )

    benchmark = _load_yaml(ROOT / "config" / "benchmark.yaml")
    experiment = _load_yaml(ROOT / "config" / "experiment.yaml")
    seeds = _load_yaml(ROOT / "config" / "seeds.yaml")

    # Historical v2.1 response exponent is part of the separability diagnosis.
    assert (
        float(
            benchmark["technology_response"]["response_exponent"][
                "reference_value"
            ]
        )
        == 1.0
    )

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

    # Official historical development scope.
    assert estimation["context_number"].nunique() == 1000
    assert len(estimation) == 6000
    assert set(estimation["partition"].unique()) <= {"fit", "weight"}
    assert not (estimation["partition"] == "test").any()

    return estimation


def _criterion_matrix(responses, criterion: str) -> np.ndarray:
    """Return contexts x alternatives matrix in deterministic order."""

    pivot = (
        responses.pivot(
            index="context_number",
            columns="alternative_id",
            values=f"g_{criterion}",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    return pivot.to_numpy(dtype=float)


def _normalize(x: np.ndarray, method: str) -> np.ndarray:
    if method == "vector":
        denominator = np.sqrt(np.sum(x * x, axis=1, keepdims=True)) + EPS
        return x / denominator

    if method == "sum":
        denominator = np.sum(x, axis=1, keepdims=True) + EPS
        return x / denominator

    if method == "max":
        denominator = np.max(x, axis=1, keepdims=True) + EPS
        return x / denominator

    if method == "minmax":
        lower = np.min(x, axis=1, keepdims=True)
        upper = np.max(x, axis=1, keepdims=True)
        return (x - lower) / (upper - lower + EPS)

    raise ValueError(f"Unknown normalization method: {method}")


@pytest.mark.parametrize("method", ("vector", "sum", "max", "minmax"))
def test_v21_c1_c7_context_signal_collapses_after_normalization(
    sigma0_estimation_responses,
    method: str,
):
    """
    Historical v2.1 characterization.

    With criterion noise removed, each C1-C7 response is a fixed
    alternative-specific amplitude multiplied by a context-only factor.
    Homogeneous within-context normalizations therefore remove the systematic
    context factor up to numerical epsilon.
    """

    observed_max_sd = 0.0

    for criterion in C1_C7:
        x = _criterion_matrix(sigma0_estimation_responses, criterion)
        normalized = _normalize(x, method)

        across_context_sd = np.std(normalized, axis=0, ddof=0)
        observed_max_sd = max(
            observed_max_sd,
            float(np.max(across_context_sd)),
        )

    assert observed_max_sd < NUMERICAL_COLLAPSE_TOL, (
        f"Historical v2.1 C1-C7 collapse no longer reproduced for {method}: "
        f"max across-context normalized SD={observed_max_sd:.6e}, "
        f"expected < {NUMERICAL_COLLAPSE_TOL:.1e}. "
        "If this is an intentional v2.2 redesign, retire/replace this "
        "historical characterization test rather than weakening its tolerance."
    )


def test_v21_c8_c10_are_not_subject_to_same_complete_collapse(
    sigma0_estimation_responses,
):
    """
    C8-C10 use different committed response equations.

    This historical test distinguishes the C1-C7 separability pathology from
    a claim that every criterion in the benchmark is context-invariant.
    """

    per_criterion_max_sd: dict[str, float] = {}

    for criterion in C8_C10:
        x = _criterion_matrix(sigma0_estimation_responses, criterion)
        normalized = _normalize(x, "vector")
        per_criterion_max_sd[criterion] = float(
            np.max(np.std(normalized, axis=0, ddof=0))
        )

    assert all(
        value > NONZERO_SIGNAL_FLOOR
        for value in per_criterion_max_sd.values()
    ), (
        "Historical v2.1 C8-C10 non-collapse characterization changed: "
        f"{per_criterion_max_sd}. "
        f"Expected every max SD > {NONZERO_SIGNAL_FLOOR:.1e}."
    )


def test_v21_sigma0_c1_c7_upper_clipping_is_inactive(
    sigma0_estimation_responses,
):
    """
    Confirm that the reproduced collapse is not an artifact of upper clipping.

    Under the frozen v2.1 capability bands, the independently reproduced
    C1-C7 maximum is below 0.4 at sigma_x=0.
    """

    maxima = {
        criterion: float(
            sigma0_estimation_responses[f"g_{criterion}"].max()
        )
        for criterion in C1_C7
    }

    assert max(maxima.values()) < 0.4 + 1.0e-12, maxima
