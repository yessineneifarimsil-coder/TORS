from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL = ROOT / "config" / "historical_family_corrected_eligibility_readjudication_v1.json"
OUTPUT_DIR = ROOT / "results" / "historical_family_corrected_eligibility_readjudication_v1"

FAMILIES = {
    "v2.2": {
        "dir": ROOT / "results" / "v2_2_d4_f1_candidates",
        "parameter": "kappa",
        "has_c8_c10": False,
    },
    "v2.3": {
        "dir": ROOT / "results" / "v2_3_f1_candidates",
        "parameter": "eta",
        "has_c8_c10": True,
    },
    "v2.4": {
        "dir": ROOT / "results" / "v2_4_f1_candidates",
        "parameter": "eta",
        "has_c8_c10": True,
    },
    "v2.5": {
        "dir": ROOT / "results" / "v2_5_f1_candidates",
        "parameter": "eta",
        "has_c8_c10": True,
    },
    "v3.0": {
        "dir": ROOT / "results" / "v3_0_f1_candidates",
        "parameter": "p",
        "has_c8_c10": True,
    },
    "v3.1": {
        "dir": ROOT / "results" / "v3_1_f1_candidates",
        "parameter": "tau",
        "has_c8_c10": True,
    },
    "v4.0": {
        "dir": ROOT / "results" / "v4_0_f1_terminal_d29_kernel",
        "parameter": "candidate_id",
        "has_c8_c10": True,
    },
}

ALLOWED_STATUSES = (
    "VERIFIED_ELIGIBLE",
    "VERIFIED_INELIGIBLE",
    "INSUFFICIENT_FROZEN_EVIDENCE",
)


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
            "RE-ADJUDICATION REFUSES TO RUN FROM A DIRTY TREE.\n" + status
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def bool_series_all_true(frame: pd.DataFrame, columns: list[str]) -> bool:
    if not columns:
        raise ValueError("No boolean columns supplied.")
    vals = frame[columns].apply(
        lambda col: col.map(
            lambda x: x if isinstance(x, bool)
            else str(x).strip().lower() == "true"
        )
    )
    return bool(vals.to_numpy(dtype=bool).all())


def numeric_zero(frame: pd.DataFrame, column: str) -> bool:
    return bool(
        np.allclose(
            frame[column].to_numpy(dtype=float),
            0.0,
            atol=0.0,
            rtol=0.0,
        )
    )


def parameter_mask(frame: pd.DataFrame, parameter: str, value: Any) -> pd.Series:
    if parameter == "candidate_id":
        return frame[parameter].astype(str) == str(value)
    return np.isclose(
        frame[parameter].to_numpy(dtype=float),
        float(value),
        atol=1e-12,
        rtol=0.0,
    )


def historical_label(family: str, row: pd.Series) -> str:
    # Preserve the historical result; never reinterpret it as a corrected-rule label.
    return "FAILED_TERMINAL" if family == "v4.0" else "FAILED"


def evaluate_family(family: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    folder = Path(spec["dir"])
    parameter = str(spec["parameter"])

    gate_path = folder / "candidate_gate_summary.csv"
    boundary_path = folder / "boundary_diagnostics.csv"
    c8_path = folder / "c8_c10_invariance.csv"

    if not gate_path.exists() or not boundary_path.exists():
        raise FileNotFoundError(f"Missing frozen artifacts for {family}.")

    gate = pd.read_csv(gate_path)
    boundary = pd.read_csv(boundary_path)

    if parameter not in gate.columns:
        raise ValueError(f"{family}: parameter {parameter!r} absent from gate summary.")
    if parameter not in boundary.columns:
        raise ValueError(f"{family}: parameter {parameter!r} absent from boundary diagnostics.")
    if "pass_numerical" not in gate.columns:
        raise ValueError(f"{family}: pass_numerical missing.")

    boundary_ok_cols = [c for c in boundary.columns if c.endswith("_ok")]
    if "structural_zero_ok" not in boundary_ok_cols:
        raise ValueError(f"{family}: structural_zero_ok missing from boundary diagnostics.")

    c8 = None
    if bool(spec["has_c8_c10"]):
        if not c8_path.exists():
            raise FileNotFoundError(f"{family}: expected frozen C8-C10 artifact missing.")
        c8 = pd.read_csv(c8_path)
        if parameter not in c8.columns:
            raise ValueError(f"{family}: parameter missing from C8-C10 artifact.")
        for col in ("C8_max_abs_diff", "C9_max_abs_diff", "C10_max_abs_diff", "C8_C10_unchanged"):
            if col not in c8.columns:
                raise ValueError(f"{family}: missing C8-C10 field {col}.")

    rows: list[dict[str, Any]] = []

    for _, grow in gate.iterrows():
        value = grow[parameter]
        bsub = boundary.loc[parameter_mask(boundary, parameter, value)].copy()
        if bsub.empty:
            raise AssertionError(f"{family}/{value}: no boundary diagnostics.")

        numerical = bool(
            grow["pass_numerical"]
            if isinstance(grow["pass_numerical"], (bool, np.bool_))
            else str(grow["pass_numerical"]).strip().lower() == "true"
        )
        invariant_gate = bool_series_all_true(bsub, boundary_ok_cols)
        structural_zero = bool_series_all_true(bsub, ["structural_zero_ok"])

        structural_zero_exact = None
        if "structural_zero_max_abs" in bsub.columns:
            structural_zero_exact = numeric_zero(bsub, "structural_zero_max_abs")
            structural_zero = bool(structural_zero and structural_zero_exact)

        c8_c10 = None
        c8_c10_exact = None
        evidence_complete = bool(spec["has_c8_c10"])

        if c8 is not None:
            csub = c8.loc[parameter_mask(c8, parameter, value)].copy()
            if csub.empty:
                raise AssertionError(f"{family}/{value}: no C8-C10 diagnostics.")
            c8_c10 = bool_series_all_true(csub, ["C8_C10_unchanged"])
            c8_c10_exact = bool(
                numeric_zero(csub, "C8_max_abs_diff")
                and numeric_zero(csub, "C9_max_abs_diff")
                and numeric_zero(csub, "C10_max_abs_diff")
            )
            c8_c10 = bool(c8_c10 and c8_c10_exact)

        if not evidence_complete:
            status = "INSUFFICIENT_FROZEN_EVIDENCE"
            corrected_eligible = None
            reason = "Frozen artifact set does not establish C8-C10 invariance."
        else:
            corrected_eligible = bool(
                numerical
                and invariant_gate
                and structural_zero
                and bool(c8_c10)
            )
            status = (
                "VERIFIED_ELIGIBLE"
                if corrected_eligible
                else "VERIFIED_INELIGIBLE"
            )
            failed = []
            if not numerical:
                failed.append("D2.8_numerical")
            if not invariant_gate:
                failed.append("analytic_boundary_invariants")
            if not structural_zero:
                failed.append("structural_zero_preservation")
            if not bool(c8_c10):
                failed.append("C8_C10_invariance")
            reason = "all corrected hard gates pass" if corrected_eligible else ",".join(failed)

        rows.append(
            {
                "family": family,
                "parameter_name": parameter,
                "parameter_value": str(value),
                "historical_status": historical_label(family, grow),
                "historical_all_frozen_gates": (
                    bool(grow["all_frozen_gates"])
                    if isinstance(grow.get("all_frozen_gates"), (bool, np.bool_))
                    else str(grow.get("all_frozen_gates", "")).strip().lower() == "true"
                ),
                "corrected_numerical_pass": numerical,
                "corrected_boundary_invariants_pass": invariant_gate,
                "corrected_structural_zero_pass": structural_zero,
                "corrected_C8_C10_pass": c8_c10,
                "frozen_evidence_complete": evidence_complete,
                "corrected_eligible": corrected_eligible,
                "readjudication_status": status,
                "reason": reason,
                "D29_LRV_NSV_SRE_used_for_binary_eligibility": False,
                "selection_or_ranking_performed": False,
            }
        )

    return rows


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    commit, branch = require_clean_git()
    if branch != "audit-corrected-family-eligibility":
        raise RuntimeError(f"Unexpected branch {branch!r}.")
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output_dir}")

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["D29_LRV_NSV_SRE_binary_gate"] is False
    assert protocol["selection_during_readjudication"] is False
    assert protocol["ranking_during_readjudication"] is False
    assert protocol["new_simulation"] is False
    assert protocol["new_seed_use"] is False
    assert protocol["D3_execution_paused"] is True

    rows: list[dict[str, Any]] = []
    for family, spec in FAMILIES.items():
        rows.extend(evaluate_family(family, spec))

    table = pd.DataFrame(rows)
    if table.empty:
        raise AssertionError("No historical points were re-adjudicated.")
    if not set(table["readjudication_status"]).issubset(ALLOWED_STATUSES):
        raise AssertionError("Unexpected re-adjudication status.")

    family_summary = (
        table.groupby(["family", "readjudication_status"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for status in ALLOWED_STATUSES:
        if status not in family_summary.columns:
            family_summary[status] = 0

    eligible = table.loc[table["readjudication_status"] == "VERIFIED_ELIGIBLE"].copy()
    ineligible = table.loc[table["readjudication_status"] == "VERIFIED_INELIGIBLE"].copy()
    insufficient = table.loc[
        table["readjudication_status"] == "INSUFFICIENT_FROZEN_EVIDENCE"
    ].copy()

    output_dir.mkdir(parents=True, exist_ok=False)
    table.to_csv(output_dir / "readjudication_table.csv", index=False)
    family_summary.to_csv(output_dir / "family_summary.csv", index=False)
    eligible.to_csv(output_dir / "verified_eligible_points.csv", index=False)
    ineligible.to_csv(output_dir / "verified_ineligible_points.csv", index=False)
    insufficient.to_csv(output_dir / "insufficient_evidence_points.csv", index=False)

    summary = {
        "status": "COMPLETED_NONSELECTIVE_CORRECTED_ELIGIBILITY_READJUDICATION",
        "git_commit": commit,
        "git_branch": branch,
        "total_historical_points": int(len(table)),
        "verified_eligible_count": int(len(eligible)),
        "verified_ineligible_count": int(len(ineligible)),
        "insufficient_frozen_evidence_count": int(len(insufficient)),
        "verified_eligible_families": sorted(eligible["family"].unique().tolist()),
        "families_with_insufficient_frozen_evidence": sorted(
            insufficient["family"].unique().tolist()
        ),
        "production_generator_selected": False,
        "selection_or_ranking_performed": False,
        "D29_LRV_NSV_SRE_used_for_binary_eligibility": False,
        "new_simulation": False,
        "new_seeds_used": False,
        "D3_worlds_used": False,
        "reserve_30001_30005_used": False,
        "primary_11001_11030_used": False,
        "external_TEST_used": False,
        "historical_statuses_modified": False,
        "multiple_verified_eligible_points": bool(len(eligible) > 1),
        "separate_selection_protocol_required": bool(len(eligible) > 1),
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "HISTORICAL FAMILY CORRECTED-ELIGIBILITY RE-ADJUDICATION",
        f"git_commit: {commit}",
        f"total_historical_points: {len(table)}",
        f"verified_eligible_count: {len(eligible)}",
        f"verified_ineligible_count: {len(ineligible)}",
        f"insufficient_frozen_evidence_count: {len(insufficient)}",
        f"verified_eligible_families: {summary['verified_eligible_families']}",
        f"families_with_insufficient_frozen_evidence: {summary['families_with_insufficient_frozen_evidence']}",
        "production_generator_selected: False",
        "selection_or_ranking_performed: False",
        "D29_LRV_NSV_SRE_used_for_binary_eligibility: False",
        "new_simulation: False",
        "new_seeds_used: False",
        "D3_worlds_used: False",
        "reserve_30001_30005_used: False",
        "primary_11001_11030_used: False",
        "external_TEST_used: False",
        f"separate_selection_protocol_required: {summary['separate_selection_protocol_required']}",
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
