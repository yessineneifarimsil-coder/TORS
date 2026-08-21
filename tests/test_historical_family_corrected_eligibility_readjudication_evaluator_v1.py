from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "historical_family_corrected_eligibility_readjudication_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("readj_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_family_inventory_and_no_selection():
    m = _load()
    assert tuple(m.FAMILIES) == ("v2.2","v2.3","v2.4","v2.5","v3.0","v3.1","v4.0")
    assert set(m.ALLOWED_STATUSES) == {
        "VERIFIED_ELIGIBLE",
        "VERIFIED_INELIGIBLE",
        "INSUFFICIENT_FROZEN_EVIDENCE",
    }


def test_boolean_helper_requires_all_rows_and_all_columns():
    m = _load()
    f = pd.DataFrame(
        {
            "a_ok": [True, True],
            "b_ok": [True, True],
        }
    )
    assert m.bool_series_all_true(f, ["a_ok", "b_ok"]) is True
    f.loc[1, "b_ok"] = False
    assert m.bool_series_all_true(f, ["a_ok", "b_ok"]) is False


def test_v22_is_conservatively_missing_c8_c10_artifact_evidence():
    m = _load()
    assert m.FAMILIES["v2.2"]["has_c8_c10"] is False
    assert m.FAMILIES["v2.3"]["has_c8_c10"] is True
    assert m.FAMILIES["v4.0"]["has_c8_c10"] is True


def test_parameter_mask_handles_numeric_and_string_parameters():
    m = _load()
    numeric = pd.DataFrame({"tau": [0.1, 0.2, 0.3]})
    assert m.parameter_mask(numeric, "tau", 0.2).tolist() == [False, True, False]

    string = pd.DataFrame({"candidate_id": ["a", "d29_kernel"]})
    assert m.parameter_mask(string, "candidate_id", "d29_kernel").tolist() == [False, True]
