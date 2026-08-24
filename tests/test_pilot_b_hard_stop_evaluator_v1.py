from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src import pilot_b_hard_stop_evaluator_v1 as pilot


PROTOCOL = REPOSITORY_ROOT / "config" / "pilot_b_hard_stop_protocol_v1.json"


def make_inputs():
    structured = []
    for method in pilot.STRUCTURED_METHODS:
        for seed in pilot.DEVELOPMENT_SEEDS:
            structured.append({
                "method": method,
                "replication_seed": seed,
                "weights_defined": True,
                "equal_fallback_used": False,
                "test_contexts": 200,
                "kendall_defined_contexts": 200,
                "mean_kendall_tau_b": 0.72,
                "top1_accuracy": 0.78,
                "mean_normalized_oracle_regret": 0.04,
            })
    random = []
    for seed in pilot.DEVELOPMENT_SEEDS:
        for draw in range(1, 201):
            x = (draw - 1) / 199.0
            random.append({
                "replication_seed": seed,
                "random_draw_index": draw,
                "test_contexts": 200,
                "kendall_defined_contexts": 200,
                "mean_kendall_tau_b": 0.20 + 0.40 * x,
                "top1_accuracy": 0.25 + 0.40 * x,
                "mean_normalized_oracle_regret": 0.10 + 0.20 * x,
            })
    references = []
    for seed in pilot.DEVELOPMENT_SEEDS:
        references.extend([
            {
                "reference": "Equal", "replication_seed": seed,
                "test_contexts": 200, "kendall_defined_contexts": 200,
                "mean_kendall_tau_b": 0.45, "top1_accuracy": 0.50,
                "mean_normalized_oracle_regret": 0.17,
            },
            {
                "reference": "DirectXGBoost", "replication_seed": seed,
                "test_contexts": 200, "kendall_defined_contexts": 200,
                "mean_kendall_tau_b": 0.68, "top1_accuracy": 0.74,
                "mean_normalized_oracle_regret": 0.05,
            },
            {
                "reference": "MajorityWinner", "replication_seed": seed,
                "test_contexts": 200, "kendall_defined_contexts": 0,
                "mean_kendall_tau_b": None, "top1_accuracy": 0.42,
                "mean_normalized_oracle_regret": 0.19,
            },
        ])
    oracle = []
    modal = []
    for seed in pilot.DEVELOPMENT_SEEDS:
        for index, context in enumerate(range(1001, 1201)):
            oracle.append({
                "replication_seed": seed,
                "context_number": context,
                "oracle_selected_top1": pilot.ALTERNATIVE_IDS[index % 6],
            })
            modal.append({
                "replication_seed": seed,
                "context_number": context,
                "random_draws": 200,
                "modal_winner_id": pilot.ALTERNATIVE_IDS[(index + 1) % 6],
                "modal_count": 80,
                "modal_share": 0.40,
            })
    return {
        "structured_seed_metrics": pd.DataFrame(structured),
        "random_draw_metrics": pd.DataFrame(random),
        "reference_seed_metrics": pd.DataFrame(references),
        "oracle_winner_contexts": pd.DataFrame(oracle),
        "random_context_modal": pd.DataFrame(modal),
        "protocol_path": PROTOCOL,
    }


def evaluate(inputs=None):
    return pilot.evaluate_pilot_b_hard_stops(**(make_inputs() if inputs is None else inputs))


def test_frozen_constants_are_exact():
    assert pilot.DEVELOPMENT_SEEDS == (21001, 21002, 21003, 21004, 21005)
    assert pilot.STRUCTURED_METHODS == (
        "OracleAttribution", "SHAP", "PermutationImportance",
        "RidgePlus", "CRITIC", "Entropy",
    )
    assert pilot.RANDOM_KENDALL_MARGIN == 0.05
    assert pilot.RANDOM_REGRET_MARGIN == 0.01
    assert pilot.MODAL_TOP1_MARGIN == 0.02
    assert pilot.MODAL_REGRET_MARGIN == 0.01
    assert pilot.ORACLE_DOMINANCE_THRESHOLD == 0.90


def test_protocol_validation_passes_committed_frozen_file():
    p = pilot.validate_frozen_protocol(PROTOCOL)
    assert p["status"] == "FROZEN_PROSPECTIVELY_BEFORE_ANY_PILOT_B_RESULT"


def test_complete_separated_noninsensitive_fixture_passes():
    result = evaluate()
    assert result.coverage_complete is True
    assert result.coverage_reasons == ()
    assert result.gates == {
        "coverage_hard_stop": False,
        "random_equivalence_hard_stop": False,
        "modal_winner_effective_tie_hard_stop": False,
        "oracle_winner_dominance_hard_stop": False,
        "weight_insensitivity_hard_stop": False,
    }
    assert result.hard_stop is False
    assert result.pilot_b_pass is True


@pytest.mark.parametrize("column,value,reason", [
    ("weights_defined", False, "weight_vector_not_defined"),
    ("equal_fallback_used", True, "equal_fallback_used"),
    ("kendall_defined_contexts", 189, "fewer_than_190"),
])
def test_structured_coverage_failures_hard_stop(column, value, reason):
    inputs = make_inputs()
    frame = inputs["structured_seed_metrics"]
    frame.loc[frame["method"].eq("Entropy"), column] = value
    result = evaluate(inputs)
    assert result.gates["coverage_hard_stop"] is True
    assert any(reason in item for item in result.coverage_reasons)
    entropy = next(item for item in result.structured_method_assessments if item["method"] == "Entropy")
    assert entropy["eligible"] is False
    assert result.pilot_b_pass is False


def test_random_draw_coverage_requires_at_least_190_per_seed():
    inputs = make_inputs()
    frame = inputs["random_draw_metrics"]
    mask = frame["replication_seed"].eq(21001) & frame["random_draw_index"].le(11)
    frame.loc[mask, "kendall_defined_contexts"] = 189
    result = evaluate(inputs)
    assert result.gates["coverage_hard_stop"] is True
    assert "seed21001:fewer_than_190_eligible_random_draws" in result.coverage_reasons


def test_random_kendall_quantiles_use_only_eligible_draws():
    inputs = make_inputs()
    frame = inputs["random_draw_metrics"]
    mask = frame["replication_seed"].eq(21001) & frame["random_draw_index"].le(10)
    frame.loc[mask, "kendall_defined_contexts"] = 0
    frame.loc[mask, "mean_kendall_tau_b"] = np.nan
    result = evaluate(inputs)
    seed = next(row for row in result.random_seed_summaries if row["replication_seed"] == 21001)
    expected = frame.loc[
        frame["replication_seed"].eq(21001) & frame["random_draw_index"].gt(10),
        "mean_kendall_tau_b",
    ].median()
    assert seed["eligible_kendall_draws"] == 190
    assert seed["kendall_median"] == pytest.approx(expected)
    assert result.gates["coverage_hard_stop"] is False


def test_random_separation_needs_margin_and_four_positive_seeds():
    inputs = make_inputs()
    structured = inputs["structured_seed_metrics"]
    structured["mean_kendall_tau_b"] = 0.40
    structured["mean_normalized_oracle_regret"] = 0.20
    result = evaluate(inputs)
    assert result.gates["random_equivalence_hard_stop"] is True
    assert not any(item["separates_random"] for item in result.structured_method_assessments)


def test_exact_random_margin_with_four_positive_seeds_passes_clause():
    inputs = make_inputs()
    structured = inputs["structured_seed_metrics"]
    structured["mean_normalized_oracle_regret"] = 0.20
    structured["mean_kendall_tau_b"] = 0.45
    structured.loc[structured["replication_seed"].eq(21005), "mean_kendall_tau_b"] = 0.40
    result = evaluate(inputs)
    assessment = next(item for item in result.structured_method_assessments if item["method"] == "SHAP")
    assert assessment["random_kendall_median_advantage"] == pytest.approx(0.05)
    assert assessment["random_kendall_positive_seed_count"] == 4
    assert assessment["separates_random"] is True


def test_modal_escape_failure_hard_stops():
    inputs = make_inputs()
    structured = inputs["structured_seed_metrics"]
    structured["top1_accuracy"] = 0.42
    structured["mean_normalized_oracle_regret"] = 0.19
    result = evaluate(inputs)
    assert result.gates["modal_winner_effective_tie_hard_stop"] is True


def test_oracle_winner_share_at_exact_boundary_hard_stops():
    inputs = make_inputs()
    oracle = inputs["oracle_winner_contexts"]
    oracle["oracle_selected_top1"] = "A1"
    oracle.loc[oracle.index[-100:], "oracle_selected_top1"] = "A2"
    result = evaluate(inputs)
    assert result.oracle_winner_summary["pooled_modal_winner_share"] == pytest.approx(0.90)
    assert result.gates["oracle_winner_dominance_hard_stop"] is True


def test_oracle_modal_tie_break_is_alternative_id_ascending():
    inputs = make_inputs()
    oracle = inputs["oracle_winner_contexts"]
    oracle.loc[oracle.index[:500], "oracle_selected_top1"] = "A2"
    oracle.loc[oracle.index[500:], "oracle_selected_top1"] = "A1"
    result = evaluate(inputs)
    assert result.oracle_winner_summary["pooled_modal_winner_id"] == "A1"


def test_context_invariance_at_exact_boundaries_hard_stops():
    inputs = make_inputs()
    modal = inputs["random_context_modal"]
    modal.loc[modal.index[:900], ["modal_count", "modal_share"]] = [190, 0.95]
    result = evaluate(inputs)
    assert result.random_context_invariance_summary["pooled_invariant_fraction"] == pytest.approx(0.90)
    assert result.gates["weight_insensitivity_hard_stop"] is True


def test_width_clause_requires_all_three_widths_in_four_seeds():
    inputs = make_inputs()
    random = inputs["random_draw_metrics"]
    for seed in pilot.DEVELOPMENT_SEEDS[:4]:
        mask = random["replication_seed"].eq(seed)
        random.loc[mask, "mean_kendall_tau_b"] = 0.4
        random.loc[mask, "top1_accuracy"] = 0.5
        random.loc[mask, "mean_normalized_oracle_regret"] = 0.2
    result = evaluate(inputs)
    assert result.random_context_invariance_summary["performance_width_seed_count"] == 4
    assert result.gates["weight_insensitivity_hard_stop"] is True


def test_only_three_narrow_seeds_do_not_trigger_width_clause():
    inputs = make_inputs()
    random = inputs["random_draw_metrics"]
    for seed in pilot.DEVELOPMENT_SEEDS[:3]:
        mask = random["replication_seed"].eq(seed)
        random.loc[mask, "mean_kendall_tau_b"] = 0.4
        random.loc[mask, "top1_accuracy"] = 0.5
        random.loc[mask, "mean_normalized_oracle_regret"] = 0.2
    result = evaluate(inputs)
    assert result.random_context_invariance_summary["performance_width_seed_count"] == 3
    assert result.gates["weight_insensitivity_hard_stop"] is False


def test_overall_rule_is_or_across_five_gates():
    inputs = make_inputs()
    inputs["oracle_winner_contexts"]["oracle_selected_top1"] = "A1"
    result = evaluate(inputs)
    assert sum(result.gates.values()) == 1
    assert result.hard_stop is True
    assert result.pilot_b_pass is False


def test_nondevelopment_seed_is_rejected():
    inputs = make_inputs()
    inputs["structured_seed_metrics"].loc[0, "replication_seed"] = 11001
    with pytest.raises(ValueError, match="non-development seed"):
        evaluate(inputs)


def test_missing_structured_grid_row_is_rejected():
    inputs = make_inputs()
    inputs["structured_seed_metrics"] = inputs["structured_seed_metrics"].iloc[1:].copy()
    with pytest.raises(ValueError, match="grid is not exact"):
        evaluate(inputs)


def test_missing_random_draw_is_rejected():
    inputs = make_inputs()
    inputs["random_draw_metrics"] = inputs["random_draw_metrics"].iloc[:-1].copy()
    with pytest.raises(ValueError, match="grid is not exact"):
        evaluate(inputs)


def test_majority_winner_cannot_contain_kendall_rank_metric():
    inputs = make_inputs()
    refs = inputs["reference_seed_metrics"]
    row = refs["reference"].eq("MajorityWinner")
    refs.loc[row, "kendall_defined_contexts"] = 200
    refs.loc[row, "mean_kendall_tau_b"] = 0.5
    with pytest.raises(ValueError, match="must not invent Kendall"):
        evaluate(inputs)


def test_random_modal_share_must_match_count():
    inputs = make_inputs()
    inputs["random_context_modal"].loc[0, "modal_share"] = 0.41
    with pytest.raises(ValueError, match="modal_count/200"):
        evaluate(inputs)
