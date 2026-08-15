"""
Unit tests for Step 2:
alternative-specific ITS criterion responses.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONTEXT_PATH = (
    PROJECT_ROOT
    / "src"
    / "01_generate_contexts.py"
)

RESPONSE_PATH = (
    PROJECT_ROOT
    / "src"
    / "02_generate_technology_responses.py"
)


def load_module(
    name: str,
    path: Path,
):
    """Dynamically import a numbered Python module."""

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to import {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    spec.loader.exec_module(
        module
    )

    return module


contexts_module = load_module(
    "contexts_module_for_response_tests",
    CONTEXT_PATH,
)

responses_module = load_module(
    "responses_module_for_tests",
    RESPONSE_PATH,
)

benchmark, experiment, seeds = (
    responses_module.load_project_configuration()
)

SEED = 21001

ALTERNATIVES = (
    responses_module.ordered_alternative_keys(
        benchmark
    )
)

CRITERIA = (
    responses_module.ordered_criterion_keys(
        benchmark
    )
)


def generate(
    rho: float = 0.4,
):
    """Generate full master contexts and responses."""

    contexts, _ = (
        contexts_module.generate_master_contexts(
            replication_seed=SEED,
            rho=rho,
            benchmark=benchmark,
            experiment=experiment,
            seeds=seeds,
        )
    )

    return (
        contexts,
        *responses_module.
        generate_master_technology_responses(
            contexts=contexts,
            replication_seed=SEED,
            benchmark=benchmark,
        ),
    )


def test_master_response_dimensions() -> None:
    """1200 contexts × 6 alternatives = 7200 rows."""

    contexts, responses, capability, deployment, audit = generate()

    assert len(contexts) == 1200
    assert len(responses) == 7200
    assert len(audit) == 7200

    assert len(capability) == 6 * 7
    assert len(deployment) == 6


def test_every_context_has_all_alternatives() -> None:
    """Each context must contain exactly six ITS alternatives."""

    _, responses, _, _, _ = generate()

    counts = (
        responses.groupby(
            "context_id"
        )["alternative_id"]
        .nunique()
    )

    assert (
        counts == 6
    ).all()


def test_all_raw_and_oriented_scores_in_unit_interval() -> None:
    """All x and g criterion values must be in [0,1]."""

    _, responses, _, _, _ = generate()

    for criterion in CRITERIA:

        assert responses[
            f"x_{criterion}"
        ].between(
            0.0,
            1.0,
            inclusive="both",
        ).all()

        assert responses[
            f"g_{criterion}"
        ].between(
            0.0,
            1.0,
            inclusive="both",
        ).all()


def test_direction_orientation() -> None:
    """C1-C9 unchanged; C10 converted to 1-burden."""

    _, responses, _, _, _ = generate()

    for criterion_number in range(
        1,
        10,
    ):

        criterion = f"C{criterion_number}"

        np.testing.assert_allclose(
            responses[
                f"x_{criterion}"
            ].to_numpy(),
            responses[
                f"g_{criterion}"
            ].to_numpy(),
            atol=0.0,
            rtol=0.0,
        )

    np.testing.assert_allclose(
        responses["g_C10"].to_numpy(),
        (
            1.0
            - responses["x_C10"].to_numpy()
        ),
        atol=1e-15,
        rtol=0.0,
    )


def test_generator_is_deterministic() -> None:
    """Same seed and rho must reproduce exactly."""

    _, responses_a, cap_a, dep_a, audit_a = (
        generate(
            rho=0.4
        )
    )

    _, responses_b, cap_b, dep_b, audit_b = (
        generate(
            rho=0.4
        )
    )

    pd.testing.assert_frame_equal(
        responses_a,
        responses_b,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        cap_a,
        cap_b,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        dep_a,
        dep_b,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        audit_a,
        audit_b,
        check_exact=True,
    )


def test_technology_parameters_reused_across_rho() -> None:
    """
    Capability and deployment parameters must not depend on rho.
    """

    _, _, cap_0, dep_0, _ = generate(
        rho=0.0
    )

    _, _, cap_8, dep_8, _ = generate(
        rho=0.8
    )

    pd.testing.assert_frame_equal(
        cap_0,
        cap_8,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        dep_0,
        dep_8,
        check_exact=True,
    )


def test_base_criterion_noise_reused_across_rho() -> None:
    """Criterion-noise base draws must be CRN across rho."""

    _, _, _, _, audit_0 = generate(
        rho=0.0
    )

    _, _, _, _, audit_8 = generate(
        rho=0.8
    )

    columns = [
        f"base_noise_C{i}"
        for i in range(
            1,
            11,
        )
    ]

    np.testing.assert_array_equal(
        audit_0[
            columns
        ].to_numpy(),
        audit_8[
            columns
        ].to_numpy(),
    )


@pytest.mark.parametrize(
    "n_contexts,expected_fit_rows,expected_weight_rows",
    [
        (25, 120, 30),
        (50, 240, 60),
        (100, 480, 120),
        (250, 1200, 300),
        (1000, 4800, 1200),
    ],
)
def test_nested_response_sizes(
    n_contexts: int,
    expected_fit_rows: int,
    expected_weight_rows: int,
) -> None:
    """Each condition contains N estimation contexts + 200 fixed TEST."""

    _, responses, _, _, audit = generate()
    subset, audit_subset = responses_module.extract_nested_responses(
        responses=responses,
        audit=audit,
        n_contexts=n_contexts,
    )

    assert len(subset) == (n_contexts + 200) * 6
    assert len(audit_subset) == (n_contexts + 200) * 6

    counts = subset["partition"].value_counts().to_dict()
    assert counts["fit"] == expected_fit_rows
    assert counts["weight"] == expected_weight_rows
    assert counts["test"] == 1200


def test_nested_estimation_responses_and_fixed_test_responses() -> None:
    """Estimation responses are nested and external TEST responses are fixed."""

    _, responses, _, _, audit = generate()
    sample_sizes = [25, 50, 100, 250, 1000]
    samples: dict[int, pd.DataFrame] = {}

    for n_contexts in sample_sizes:
        subset, _ = responses_module.extract_nested_responses(
            responses,
            audit,
            n_contexts,
        )
        samples[n_contexts] = subset

    reference_test = (
        samples[25].loc[samples[25]["partition"].eq("test")]
        .reset_index(drop=True)
    )
    assert len(reference_test) == 1200

    for n_contexts in sample_sizes:
        sample = samples[n_contexts]
        external_test = (
            sample.loc[sample["partition"].eq("test")]
            .reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(
            external_test,
            reference_test,
            check_exact=True,
        )

    for smaller, larger in zip(sample_sizes[:-1], sample_sizes[1:]):
        small_est = samples[smaller].loc[
            samples[smaller]["partition"].isin(["fit", "weight"])
        ].reset_index(drop=True)
        large_est = samples[larger].loc[
            samples[larger]["partition"].isin(["fit", "weight"])
        ].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            small_est,
            large_est.iloc[: smaller * 6].reset_index(drop=True),
            check_exact=True,
        )


def test_capability_amplitudes_respect_configured_bands() -> None:
    """0, I and D amplitudes must respect structural bands."""

    _, _, capability, _, _ = generate()

    for row in capability.itertuples(
        index=False
    ):

        if row.capability_class == "0":
            assert row.amplitude == 0.0

        elif row.capability_class == "I":
            assert (
                0.05
                <= row.amplitude
                <= 0.20
            )

        elif row.capability_class == "D":
            assert (
                0.20
                <= row.amplitude
                <= 0.40
            )

        else:
            pytest.fail(
                f"Unknown capability class "
                f"{row.capability_class}"
            )


def test_compound_deployment_draws_do_not_fill_class_gaps() -> None:
    """
    L-M and M-H must be mixture draws, not continuous draws
    through the class gap.
    """

    _, _, _, deployment, _ = generate()

    for row in deployment.itertuples(
        index=False
    ):

        compound_fields = [
            (
                row.readiness_class,
                row.readiness_requirement,
            ),
            (
                row.interoperability_class,
                row.interoperability_baseline,
            ),
            (
                row.burden_class,
                row.burden_baseline,
            ),
        ]

        for class_name, value in (
            compound_fields
        ):

            if class_name == "L-M":

                valid = (
                    0.25 <= value <= 0.40
                    or
                    0.45 <= value <= 0.60
                )

                assert valid

            elif class_name == "M-H":

                valid = (
                    0.45 <= value <= 0.60
                    or
                    0.65 <= value <= 0.80
                )

                assert valid


def test_c1_to_c7_formula_reconstruction() -> None:
    """Audit quantities must exactly reconstruct C1-C7."""

    _, responses, _, _, audit = generate()

    sigma_x = float(
        benchmark[
            "technology_response"
        ]["criterion_noise"]["sigma_x"]
    )

    gamma = float(
        benchmark[
            "technology_response"
        ]["response_exponent"][
            "reference_value"
        ]
    )

    for criterion_number in range(
        1,
        8,
    ):

        criterion = (
            f"C{criterion_number}"
        )

        reconstructed = np.clip(
            audit[
                f"amplitude_{criterion}"
            ].to_numpy()
            * (
                audit[
                    f"opportunity_{criterion}"
                ].to_numpy()
                ** gamma
            )
            + sigma_x
            * audit[
                f"base_noise_{criterion}"
            ].to_numpy(),
            0.0,
            1.0,
        )

        np.testing.assert_allclose(
            reconstructed,
            responses[
                f"x_{criterion}"
            ].to_numpy(),
            atol=1e-14,
            rtol=0.0,
        )


def test_c8_one_sided_shortfall_formula() -> None:
    """
    C8 must penalise only insufficient readiness.
    """

    contexts, responses, _, _, audit = generate()

    h_r_lookup = (
        contexts.set_index(
            "context_id"
        )["h_R"]
    )

    h_r = (
        responses[
            "context_id"
        ]
        .map(
            h_r_lookup
        )
        .to_numpy(
            dtype=float
        )
    )

    requirement = audit[
        "readiness_requirement"
    ].to_numpy()

    eta = audit[
        "eta_C8"
    ].to_numpy()

    reconstructed = np.clip(
        1.0
        - np.maximum(
            0.0,
            requirement - h_r,
        )
        + eta,
        0.0,
        1.0,
    )

    np.testing.assert_allclose(
        reconstructed,
        responses[
            "x_C8"
        ].to_numpy(),
        atol=1e-14,
        rtol=0.0,
    )

    no_shortfall = (
        h_r >= requirement
    )

    deterministic_component = (
        1.0
        - np.maximum(
            0.0,
            requirement - h_r,
        )
    )

    np.testing.assert_allclose(
        deterministic_component[
            no_shortfall
        ],
        1.0,
        atol=0.0,
        rtol=0.0,
    )


def test_c9_formula_reconstruction() -> None:
    """C9 must follow the configured readiness relationship."""

    contexts, responses, _, _, audit = generate()

    h_r_lookup = (
        contexts.set_index(
            "context_id"
        )["h_R"]
    )

    h_r = (
        responses[
            "context_id"
        ]
        .map(
            h_r_lookup
        )
        .to_numpy()
    )

    coefficient = float(
        benchmark[
            "technical_criteria"
        ]["C9"][
            "readiness_coefficient"
        ]
    )

    reconstructed = np.clip(
        audit[
            "interoperability_baseline"
        ].to_numpy()
        + coefficient * h_r
        + audit[
            "eta_C9"
        ].to_numpy(),
        0.0,
        1.0,
    )

    np.testing.assert_allclose(
        reconstructed,
        responses[
            "x_C9"
        ].to_numpy(),
        atol=1e-14,
        rtol=0.0,
    )


def test_c10_formula_reconstruction() -> None:
    """C10 raw burden must follow the specified formula."""

    contexts, responses, _, _, audit = generate()

    h_r_lookup = (
        contexts.set_index(
            "context_id"
        )["h_R"]
    )

    h_r = (
        responses[
            "context_id"
        ]
        .map(
            h_r_lookup
        )
        .to_numpy()
    )

    coefficient = float(
        benchmark[
            "technical_criteria"
        ]["C10"][
            "low_readiness_penalty"
        ]
    )

    reconstructed = np.clip(
        audit[
            "burden_baseline"
        ].to_numpy()
        + coefficient
        * (1.0 - h_r)
        * audit[
            "readiness_requirement"
        ].to_numpy()
        + audit[
            "eta_C10"
        ].to_numpy(),
        0.0,
        1.0,
    )

    np.testing.assert_allclose(
        reconstructed,
        responses[
            "x_C10"
        ].to_numpy(),
        atol=1e-14,
        rtol=0.0,
    )