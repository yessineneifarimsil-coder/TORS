from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL = ROOT / "config" / "production_generator_retention_resolution_v1.json"
PRODUCTION = ROOT / "config" / "production_response_generator_v1.json"

HIST_FREEZE = (
    ROOT / "results" / "historical_family_corrected_eligibility_readjudication_v1"
    / "freeze_summary.json"
)
HIST_TABLE = (
    ROOT / "results" / "historical_family_corrected_eligibility_readjudication_v1"
    / "readjudication_table.csv"
)
V22_FREEZE = (
    ROOT / "results" / "v2_2_frozen_source_eligibility_resolution_v1"
    / "freeze_summary.json"
)

PREEXISTING_FREEZE_COMMIT = "bd56c2d"
PREEXISTING_CANDIDATE = "d29_kernel"
OUTPUT_DIR = ROOT / "results" / "production_generator_retention_resolution_v1"


def git_run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result


def git_output(*args: str) -> str:
    return git_run(*args).stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = git_output("status", "--porcelain")
    if status:
        raise RuntimeError(
            "RETENTION RESOLUTION REFUSES TO RUN FROM A DIRTY TREE.\n" + status
        )
    return (
        git_output("rev-parse", "HEAD"),
        git_output("branch", "--show-current"),
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bool_value(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() == "true"


def historical_production_spec() -> dict[str, Any]:
    raw = git_output(
        "show",
        f"{PREEXISTING_FREEZE_COMMIT}:config/production_response_generator_v1.json",
    )
    return json.loads(raw)


def commit_is_ancestor(commit: str) -> bool:
    result = git_run("merge-base", "--is-ancestor", commit, "HEAD", check=False)
    return result.returncode == 0


def verify_preexisting_production(
    current: dict[str, Any],
    historical: dict[str, Any],
) -> dict[str, Any]:
    keys = [
        "status",
        "candidate_id",
        "response_formula",
        "delta",
        "signed_profile_namespace",
        "corrected_structural_validation_passed",
        "response_generator_development_closed",
    ]

    comparisons = {}
    for key in keys:
        comparisons[key] = {
            "historical": historical.get(key),
            "current": current.get(key),
            "equal": historical.get(key) == current.get(key),
        }

    return {
        "historical_commit_is_ancestor": commit_is_ancestor(
            PREEXISTING_FREEZE_COMMIT
        ),
        "historical_candidate_is_d29_kernel":
            historical.get("candidate_id") == PREEXISTING_CANDIDATE,
        "current_candidate_is_d29_kernel":
            current.get("candidate_id") == PREEXISTING_CANDIDATE,
        "historical_status_frozen":
            historical.get("status") == "FROZEN_PRODUCTION_RESPONSE_GENERATOR",
        "current_status_frozen":
            current.get("status") == "FROZEN_PRODUCTION_RESPONSE_GENERATOR",
        "historical_corrected_validation_passed":
            bool(historical.get("corrected_structural_validation_passed")),
        "current_corrected_validation_passed":
            bool(current.get("corrected_structural_validation_passed")),
        "historical_development_closed":
            bool(historical.get("response_generator_development_closed")),
        "current_development_closed":
            bool(current.get("response_generator_development_closed")),
        "core_spec_comparisons": comparisons,
        "core_spec_unchanged": all(v["equal"] for v in comparisons.values()),
    }


def verify_corrected_eligibility(table: pd.DataFrame) -> dict[str, Any]:
    required = {
        "family",
        "parameter_name",
        "parameter_value",
        "corrected_eligible",
        "readjudication_status",
        "historical_status",
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(
            f"Historical eligibility table missing columns: {sorted(missing)}"
        )

    row = table.loc[
        (table["family"].astype(str) == "v4.0")
        & (table["parameter_value"].astype(str) == PREEXISTING_CANDIDATE)
    ]
    if len(row) != 1:
        raise AssertionError(
            f"Expected one v4.0/d29_kernel row, got {len(row)}."
        )

    r = row.iloc[0]
    return {
        "row_count": 1,
        "corrected_eligible": bool_value(r["corrected_eligible"]),
        "readjudication_status": str(r["readjudication_status"]),
        "historical_status": str(r["historical_status"]),
        "historical_failure_preserved":
            str(r["historical_status"]) == "FAILED_TERMINAL",
        "verified_eligible_status":
            str(r["readjudication_status"]) == "VERIFIED_ELIGIBLE",
    }


def verify_firewall_summaries(
    hist_freeze: dict[str, Any],
    v22_freeze: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "historical_readjudication_D3_worlds_used":
            hist_freeze.get("D3_worlds_used") is False,
        "historical_readjudication_reserve_used":
            hist_freeze.get("reserve_30001_30005_used") is False,
        "historical_readjudication_primary_used":
            hist_freeze.get("primary_11001_11030_used") is False,
        "historical_readjudication_external_TEST_used":
            hist_freeze.get("external_TEST_used") is False,
        "v22_resolution_D3_worlds_used":
            v22_freeze.get("D3_worlds_used") is False,
        "v22_resolution_reserve_used":
            v22_freeze.get("reserve_30001_30005_used") is False,
        "v22_resolution_primary_used":
            v22_freeze.get("primary_11001_11030_used") is False,
        "v22_resolution_external_TEST_used":
            v22_freeze.get("external_TEST_used") is False,
    }
    return {
        "checks": checks,
        "all_frozen_firewall_attestations_pass": all(checks.values()),
    }


def scan_for_d3_result_artifacts() -> list[str]:
    results_root = ROOT / "results"
    if not results_root.exists():
        return []
    hits = []
    for path in results_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix().lower()
        if "d3_alpha_dispersion" in rel:
            hits.append(path.relative_to(ROOT).as_posix())
    return sorted(hits)


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    commit, branch = require_clean_git()
    if branch != "protocol-production-generator-retention":
        raise RuntimeError(f"Unexpected branch {branch!r}.")
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output_dir}")

    protocol = load_json(PROTOCOL)
    current_prod = load_json(PRODUCTION)
    historical_prod = historical_production_spec()
    hist_freeze = load_json(HIST_FREEZE)
    v22_freeze = load_json(V22_FREEZE)
    hist_table = pd.read_csv(HIST_TABLE)

    assert protocol["eligible_universe_count"] == 54
    assert protocol["preexisting_production_candidate"] == PREEXISTING_CANDIDATE
    assert protocol["preexisting_production_freeze_commit"] == PREEXISTING_FREEZE_COMMIT
    assert protocol["retention_rule_name"] == "minimal_intervention_and_provenance_stability"
    assert protocol["D29_LRV_NSV_SRE_used_for_selection"] is False
    assert protocol["SHAP_used_for_selection"] is False
    assert protocol["MCDM_used_for_selection"] is False
    assert protocol["winner_identity_used_for_selection"] is False
    assert protocol["development_metric_ranking_used_for_selection"] is False
    assert protocol["new_simulation"] is False
    assert protocol["new_seed_use"] is False
    assert protocol["D3_execution_paused_during_resolution"] is True
    assert protocol["mandatory_secondary_robustness_protocol"] is True

    production_evidence = verify_preexisting_production(
        current_prod, historical_prod
    )
    eligibility_evidence = verify_corrected_eligibility(hist_table)
    firewall_evidence = verify_firewall_summaries(hist_freeze, v22_freeze)
    d3_result_artifacts = scan_for_d3_result_artifacts()

    universe_evidence = {
        "historical_readjudication_verified_eligible_count":
            hist_freeze.get("verified_eligible_count"),
        "supplemental_v22_verified_count":
            v22_freeze.get("v2_2_verified_eligible_by_source_contract_count"),
        "supplemental_selection_universe_count":
            v22_freeze.get("selection_eligible_universe_count_if_used"),
        "eligible_universe_54_confirmed": bool(
            hist_freeze.get("verified_eligible_count") == 44
            and v22_freeze.get(
                "v2_2_verified_eligible_by_source_contract_count"
            ) == 10
            and v22_freeze.get("selection_eligible_universe_count_if_used") == 54
        ),
    }

    retention_preconditions = {
        "preexisting_production_provenance_verified": bool(
            production_evidence["historical_commit_is_ancestor"]
            and production_evidence["historical_candidate_is_d29_kernel"]
            and production_evidence["current_candidate_is_d29_kernel"]
            and production_evidence["historical_status_frozen"]
            and production_evidence["current_status_frozen"]
            and production_evidence["historical_corrected_validation_passed"]
            and production_evidence["current_corrected_validation_passed"]
            and production_evidence["historical_development_closed"]
            and production_evidence["current_development_closed"]
            and production_evidence["core_spec_unchanged"]
        ),
        "preexisting_candidate_remains_corrected_eligible": bool(
            eligibility_evidence["corrected_eligible"]
            and eligibility_evidence["verified_eligible_status"]
            and eligibility_evidence["historical_failure_preserved"]
        ),
        "eligible_universe_54_confirmed":
            universe_evidence["eligible_universe_54_confirmed"],
        "frozen_firewall_attestations_pass":
            firewall_evidence["all_frozen_firewall_attestations_pass"],
        "no_D3_result_artifact_detected":
            len(d3_result_artifacts) == 0,
    }

    all_preconditions_pass = all(retention_preconditions.values())

    if all_preconditions_pass:
        resolution = "RETAIN_D29_KERNEL_UNDER_MINIMAL_INTERVENTION"
        retained_primary_candidate = PREEXISTING_CANDIDATE
    else:
        resolution = "RETENTION_PRECONDITIONS_FAILED"
        retained_primary_candidate = None

    output_dir.mkdir(parents=True, exist_ok=False)

    evidence_rows = []
    for key, value in retention_preconditions.items():
        evidence_rows.append(
            {
                "evidence_item": key,
                "pass": bool(value),
                "used_for_resolution": True,
            }
        )
    pd.DataFrame(evidence_rows).to_csv(
        output_dir / "retention_precondition_table.csv",
        index=False,
    )

    audit = {
        "status": "COMPLETED_PRODUCTION_GENERATOR_RETENTION_RESOLUTION",
        "git_commit": commit,
        "git_branch": branch,
        "eligible_universe_count": 54,
        "corrected_eligibility_nonunique": True,
        "preexisting_production_freeze_commit": PREEXISTING_FREEZE_COMMIT,
        "preexisting_production_candidate": PREEXISTING_CANDIDATE,
        "production_provenance_evidence": production_evidence,
        "corrected_eligibility_evidence": eligibility_evidence,
        "eligible_universe_evidence": universe_evidence,
        "firewall_evidence": firewall_evidence,
        "d3_result_artifacts_detected": d3_result_artifacts,
        "retention_preconditions": retention_preconditions,
        "all_retention_preconditions_pass": all_preconditions_pass,
        "resolution": resolution,
        "retained_primary_candidate": retained_primary_candidate,
        "retention_is_superiority_claim": False,
        "retention_is_uniqueness_claim": False,
        "retention_is_statistical_selection": False,
        "ranking_or_reoptimization_performed": False,
        "D29_LRV_NSV_SRE_used_for_selection": False,
        "SHAP_used_for_selection": False,
        "MCDM_used_for_selection": False,
        "winner_identity_used_for_selection": False,
        "development_metric_ranking_used_for_selection": False,
        "new_simulation": False,
        "new_seeds_used": False,
        "D3_worlds_used": False,
        "reserve_30001_30005_used": False,
        "primary_11001_11030_used": False,
        "external_TEST_used": False,
        "mandatory_secondary_v22_robustness_protocol": True,
        "D3_execution_paused_until_resolution_freeze": True,
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "POST-DEVELOPMENT PRODUCTION-GENERATOR RETENTION RESOLUTION",
        f"git_commit: {commit}",
        "eligible_universe_count: 54",
        "corrected_eligibility_nonunique: True",
        f"preexisting_production_freeze_commit: {PREEXISTING_FREEZE_COMMIT}",
        f"preexisting_production_candidate: {PREEXISTING_CANDIDATE}",
        f"preexisting_production_provenance_verified: {retention_preconditions['preexisting_production_provenance_verified']}",
        f"preexisting_candidate_remains_corrected_eligible: {retention_preconditions['preexisting_candidate_remains_corrected_eligible']}",
        f"eligible_universe_54_confirmed: {retention_preconditions['eligible_universe_54_confirmed']}",
        f"frozen_firewall_attestations_pass: {retention_preconditions['frozen_firewall_attestations_pass']}",
        f"no_D3_result_artifact_detected: {retention_preconditions['no_D3_result_artifact_detected']}",
        f"all_retention_preconditions_pass: {all_preconditions_pass}",
        f"resolution: {resolution}",
        f"retained_primary_candidate: {retained_primary_candidate}",
        "retention_is_superiority_claim: False",
        "retention_is_uniqueness_claim: False",
        "ranking_or_reoptimization_performed: False",
        "D29_LRV_NSV_SRE_used_for_selection: False",
        "SHAP_used_for_selection: False",
        "MCDM_used_for_selection: False",
        "winner_identity_used_for_selection: False",
        "new_simulation: False",
        "new_seeds_used: False",
        "D3_worlds_used: False",
        "mandatory_secondary_v22_robustness_protocol: True",
        "D3_execution_paused_until_resolution_freeze: True",
    ]
    (output_dir / "summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    print("WROTE:", output_dir)
    return audit


if __name__ == "__main__":
    run()
