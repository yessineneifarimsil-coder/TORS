from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "production_generator_retention_resolution_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("retention_resolution_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retention_resolver_targets_preexisting_freeze():
    m = _load()
    assert m.PREEXISTING_FREEZE_COMMIT == "bd56c2d"
    assert m.PREEXISTING_CANDIDATE == "d29_kernel"


def test_corrected_eligibility_verifier_requires_exact_v4_row():
    m = _load()
    table = pd.DataFrame(
        [
            {
                "family": "v4.0",
                "parameter_name": "candidate_id",
                "parameter_value": "d29_kernel",
                "corrected_eligible": True,
                "readjudication_status": "VERIFIED_ELIGIBLE",
                "historical_status": "FAILED_TERMINAL",
            }
        ]
    )
    out = m.verify_corrected_eligibility(table)
    assert out["corrected_eligible"] is True
    assert out["verified_eligible_status"] is True
    assert out["historical_failure_preserved"] is True


def test_firewall_summary_verifier_requires_all_false_usage_flags():
    m = _load()
    hist = {
        "D3_worlds_used": False,
        "reserve_30001_30005_used": False,
        "primary_11001_11030_used": False,
        "external_TEST_used": False,
    }
    v22 = dict(hist)
    out = m.verify_firewall_summaries(hist, v22)
    assert out["all_frozen_firewall_attestations_pass"] is True

    bad = dict(v22)
    bad["primary_11001_11030_used"] = True
    out_bad = m.verify_firewall_summaries(hist, bad)
    assert out_bad["all_frozen_firewall_attestations_pass"] is False


def test_resolver_contains_no_performance_ranking_path():
    text = PATH.read_text(encoding="utf-8")
    assert '"ranking_or_reoptimization_performed": False' in text
    assert '"D29_LRV_NSV_SRE_used_for_selection": False' in text
    assert '"SHAP_used_for_selection": False' in text
    assert '"MCDM_used_for_selection": False' in text
    assert '"winner_identity_used_for_selection": False' in text
