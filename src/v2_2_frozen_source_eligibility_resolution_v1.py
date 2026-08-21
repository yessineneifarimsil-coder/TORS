from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL = ROOT / "config" / "v2_2_frozen_source_eligibility_resolution_v1.json"
V22_RESULTS = ROOT / "results" / "v2_2_d4_f1_candidates"
GATE = V22_RESULTS / "candidate_gate_summary.csv"
BOUNDARY = V22_RESULTS / "boundary_diagnostics.csv"

HISTORICAL_COMMIT = "37c8f31"
HISTORICAL_SOURCE_PATH = "src/v2_2_d4_f1_candidate_evaluator.py"

OUTPUT_DIR = ROOT / "results" / "v2_2_frozen_source_eligibility_resolution_v1"


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = git_output("status", "--porcelain")
    if status:
        raise RuntimeError(
            "v2.2 SOURCE-CONTRACT RESOLUTION REFUSES TO RUN FROM A DIRTY TREE.\n"
            + status
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def git_show(commit: str, path: str) -> str:
    return git_output("show", f"{commit}:{path}")


def bool_value(x: Any) -> bool:
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    return str(x).strip().lower() == "true"


def all_bool_true(frame: pd.DataFrame, columns: list[str]) -> bool:
    if frame.empty:
        return False
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"Missing required frozen column {column!r}.")
        if not bool(frame[column].map(bool_value).all()):
            return False
    return True


def function_node_and_source(source: str, function_name: str) -> tuple[ast.FunctionDef, str]:
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            end = getattr(node, "end_lineno", node.lineno)
            segment = "\n".join(lines[node.lineno - 1:end])
            return node, segment
    raise ValueError(f"Historical function {function_name!r} not found.")


def historical_source_contract(source: str) -> dict[str, Any]:
    build_node, build_source = function_node_and_source(
        source, "build_candidate_responses"
    )
    _, response_source = function_node_and_source(
        source, "candidate_response"
    )

    doc = ast.get_docstring(build_node) or ""
    doc_low = doc.lower()
    build_low = build_source.lower()
    response_low = response_source.lower()

    explicit_c8_c10_contract = (
        "c8-c10" in doc_low
        and "unchanged" in doc_low
    )

    baseline_copy_present = (
        "result = baseline.copy()" in build_low
        or "result=baseline.copy()" in build_low
    )
    c1_c7_loop_present = "for criterion in c1_c7" in build_low
    dynamic_response_write_present = (
        'f"g_{criterion}"' in build_source
        or "f'g_{criterion}'" in build_source
    )
    protected_literal_write_absent = not any(
        token in build_low
        for token in (
            '"g_c8"',
            "'g_c8'",
            '"g_c9"',
            "'g_c9'",
            '"g_c10"',
            "'g_c10'",
        )
    )

    c1_c7_only_response_overwrite = bool(
        baseline_copy_present
        and c1_c7_loop_present
        and dynamic_response_write_present
        and protected_literal_write_absent
    )

    structural_zero_explicit = bool(
        "capability_class == \"0\"" in build_source
        or "capability_class == '0'" in build_source
    ) and "np.zeros" in build_source

    no_clipping = not any(
        token in (build_low + "\n" + response_low)
        for token in (
            "np.clip(",
            ".clip(",
            "clip(",
        )
    )

    response_compact = "".join(response_source.split())
    endpoint_form_family_detected = (
        "theta_arr*o" in response_compact
        and "(1.0-o)" in response_compact
        and "kappa" in response_compact
    )

    source_contract_pass = bool(
        explicit_c8_c10_contract
        and c1_c7_only_response_overwrite
        and structural_zero_explicit
        and no_clipping
    )

    return {
        "historical_commit": HISTORICAL_COMMIT,
        "historical_source_path": HISTORICAL_SOURCE_PATH,
        "build_candidate_responses_docstring": doc,
        "explicit_C8_C10_unchanged_contract": explicit_c8_c10_contract,
        "baseline_copy_present": baseline_copy_present,
        "C1_C7_loop_present": c1_c7_loop_present,
        "dynamic_response_write_present": dynamic_response_write_present,
        "protected_C8_C10_literal_write_absent": protected_literal_write_absent,
        "C1_C7_only_response_overwrite": c1_c7_only_response_overwrite,
        "structural_zero_pathways_explicitly_zero": structural_zero_explicit,
        "no_clipping_used_to_create_admissibility": no_clipping,
        "endpoint_preserving_formula_pattern_detected_descriptive":
            endpoint_form_family_detected,
        "source_contract_pass": source_contract_pass,
    }


def resolve_v22_points(
    gate: pd.DataFrame,
    boundary: pd.DataFrame,
    source_contract: dict[str, Any],
) -> pd.DataFrame:
    required_gate = {"kappa", "pass_numerical"}
    missing = required_gate - set(gate.columns)
    if missing:
        raise ValueError(f"Missing v2.2 gate columns: {sorted(missing)}")

    required_boundary = {
        "kappa",
        "lower_bound_ok",
        "upper_bound_ok",
        "structural_zero_ok",
    }
    missing = required_boundary - set(boundary.columns)
    if missing:
        raise ValueError(f"Missing v2.2 boundary columns: {sorted(missing)}")

    kappas = sorted(gate["kappa"].astype(float).unique().tolist())
    if len(kappas) != 10:
        raise AssertionError(f"Expected ten frozen v2.2 kappas, got {kappas}.")

    rows: list[dict[str, Any]] = []

    for kappa in kappas:
        gsub = gate.loc[np.isclose(gate["kappa"].astype(float), kappa)]
        bsub = boundary.loc[np.isclose(boundary["kappa"].astype(float), kappa)]

        if len(gsub) != 1:
            raise AssertionError(
                f"kappa={kappa}: expected one candidate_gate_summary row, got {len(gsub)}."
            )
        if bsub.empty:
            raise AssertionError(f"kappa={kappa}: no boundary rows.")

        numerical = bool_value(gsub.iloc[0]["pass_numerical"])
        lower = all_bool_true(bsub, ["lower_bound_ok"])
        upper = all_bool_true(bsub, ["upper_bound_ok"])
        structural_zero = all_bool_true(bsub, ["structural_zero_ok"])

        if "structural_zero_max_abs" in bsub.columns:
            structural_zero_exact = bool(
                np.allclose(
                    bsub["structural_zero_max_abs"].to_numpy(dtype=float),
                    0.0,
                    atol=0.0,
                    rtol=0.0,
                )
            )
            structural_zero = bool(structural_zero and structural_zero_exact)
        else:
            structural_zero_exact = None

        source_ok = bool(source_contract["source_contract_pass"])
        corrected_eligible = bool(
            numerical
            and lower
            and upper
            and structural_zero
            and source_ok
        )

        if corrected_eligible:
            status = "VERIFIED_ELIGIBLE_BY_FROZEN_SOURCE_CONTRACT"
            reason = (
                "all corrected hard gates established including C8-C10 by "
                "contemporaneous frozen source contract"
            )
        else:
            status = "REMAINS_INSUFFICIENT_FROZEN_EVIDENCE"
            failures = []
            if not numerical:
                failures.append("D2.8_numerical")
            if not lower:
                failures.append("lower_bound")
            if not upper:
                failures.append("upper_bound")
            if not structural_zero:
                failures.append("structural_zero")
            if not source_ok:
                failures.append("historical_C8_C10_source_contract")
            reason = ",".join(failures) if failures else "unresolved"

        rows.append(
            {
                "family": "v2.2",
                "kappa": float(kappa),
                "historical_status": "FAILED",
                "corrected_numerical_pass": numerical,
                "corrected_lower_bound_pass": lower,
                "corrected_upper_bound_pass": upper,
                "corrected_structural_zero_pass": structural_zero,
                "structural_zero_exact_if_available": structural_zero_exact,
                "historical_C8_C10_source_contract_pass": source_ok,
                "corrected_eligible": corrected_eligible,
                "resolution_status": status,
                "reason": reason,
                "D29_LRV_NSV_SRE_used_for_binary_eligibility": False,
                "selection_or_ranking_performed": False,
            }
        )

    return pd.DataFrame(rows)


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    commit, branch = require_clean_git()
    if branch != "audit-v22-frozen-source-contract":
        raise RuntimeError(f"Unexpected branch {branch!r}.")
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output_dir}")

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["historical_family_freeze_commit"] == HISTORICAL_COMMIT
    assert protocol["historical_source_path"] == HISTORICAL_SOURCE_PATH
    assert protocol["source_must_be_read_from_historical_commit"] is True
    assert protocol["current_worktree_source_not_sufficient_by_itself"] is True
    assert protocol["D29_LRV_NSV_SRE_binary_gate"] is False
    assert protocol["selection_or_ranking_performed"] is False
    assert protocol["new_simulation"] is False
    assert protocol["new_seed_use"] is False
    assert protocol["D3_execution_paused"] is True

    historical_source = git_show(HISTORICAL_COMMIT, HISTORICAL_SOURCE_PATH)
    source_contract = historical_source_contract(historical_source)

    gate = pd.read_csv(GATE)
    boundary = pd.read_csv(BOUNDARY)
    table = resolve_v22_points(gate, boundary, source_contract)

    verified_count = int(table["corrected_eligible"].astype(bool).sum())
    unresolved_count = int(len(table) - verified_count)

    if verified_count == len(table):
        family_outcome = "V2_2_VERIFIED_ELIGIBLE_BY_FROZEN_SOURCE_CONTRACT"
    else:
        family_outcome = "V2_2_REMAINS_INSUFFICIENT_FROZEN_EVIDENCE"

    output_dir.mkdir(parents=True, exist_ok=False)
    table.to_csv(output_dir / "v2_2_point_resolution.csv", index=False)
    (output_dir / "historical_source_contract.json").write_text(
        json.dumps(source_contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "status": "COMPLETED_V2_2_FROZEN_SOURCE_ELIGIBILITY_RESOLUTION",
        "git_commit": commit,
        "git_branch": branch,
        "historical_family_freeze_commit": HISTORICAL_COMMIT,
        "historical_source_path": HISTORICAL_SOURCE_PATH,
        "historical_source_contract_pass": bool(source_contract["source_contract_pass"]),
        "v2_2_historical_point_count": int(len(table)),
        "v2_2_verified_eligible_by_source_contract_count": verified_count,
        "v2_2_unresolved_count": unresolved_count,
        "family_outcome": family_outcome,
        "prior_frozen_verified_eligible_count": 44,
        "supplemental_verified_v2_2_count": verified_count,
        "selection_eligible_universe_count_if_used": int(44 + verified_count),
        "prior_44_10_freeze_rewritten": False,
        "historical_failure_labels_modified": False,
        "production_generator_selected": False,
        "selection_or_ranking_performed": False,
        "D29_LRV_NSV_SRE_used_for_binary_eligibility": False,
        "new_simulation": False,
        "new_seeds_used": False,
        "D3_worlds_used": False,
        "reserve_30001_30005_used": False,
        "primary_11001_11030_used": False,
        "external_TEST_used": False,
        "D3_execution_paused": True,
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "v2.2 FROZEN-SOURCE ELIGIBILITY EVIDENCE RESOLUTION",
        f"git_commit: {commit}",
        f"historical_family_freeze_commit: {HISTORICAL_COMMIT}",
        f"historical_source_contract_pass: {source_contract['source_contract_pass']}",
        f"explicit_C8_C10_unchanged_contract: {source_contract['explicit_C8_C10_unchanged_contract']}",
        f"C1_C7_only_response_overwrite: {source_contract['C1_C7_only_response_overwrite']}",
        f"structural_zero_pathways_explicitly_zero: {source_contract['structural_zero_pathways_explicitly_zero']}",
        f"no_clipping_used_to_create_admissibility: {source_contract['no_clipping_used_to_create_admissibility']}",
        f"v2_2_historical_point_count: {len(table)}",
        f"v2_2_verified_eligible_by_source_contract_count: {verified_count}",
        f"v2_2_unresolved_count: {unresolved_count}",
        f"family_outcome: {family_outcome}",
        f"selection_eligible_universe_count_if_used: {44 + verified_count}",
        "prior_44_10_freeze_rewritten: False",
        "production_generator_selected: False",
        "selection_or_ranking_performed: False",
        "new_simulation: False",
        "new_seeds_used: False",
        "D3_worlds_used: False",
        "D3_execution_paused: True",
    ]
    (output_dir / "summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    print("WROTE:", output_dir)
    return summary


if __name__ == "__main__":
    run()
