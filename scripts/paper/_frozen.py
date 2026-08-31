"""Read-only access layer for the frozen scientific artefacts of the closed v1 study.

This module exists so that every manuscript-support script in ``scripts/paper``
reaches the frozen record through one audited path.

Scientific contract
-------------------
* Frozen artefacts are opened for reading only.
* ``PROTECTED_DIRS`` may never be written to by anything in ``scripts/paper``.
  ``guard_output_path`` enforces that at runtime.
* Nothing here recomputes, resamples, re-estimates, re-thresholds or reinterprets
  a scientific result. It loads what was frozen and hands it back unchanged.
"""

from __future__ import annotations

import json
import csv
import hashlib
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Directories holding the frozen scientific record. Writes here are refused.
PROTECTED_DIRS = ("results", "config", "docs", "src", "tests", "archives", "data")

#: The only directory tree that presentation scripts may write to.
OUTPUT_ROOT = REPO_ROOT / "outputs" / "paper"

PILOT_B = (
    REPO_ROOT
    / "results/pilot_b_reference_v1"
    / "pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json"
)
SELECTION_MAP = (
    REPO_ROOT
    / "results/pilot_b_fixed_weight_selection_diagnostic_v1"
    / "pilot_b_fixed_weight_selection_N250_c0p30_rho0p4_lambda0p5.json"
)
D29_LAYER_B_CSV = REPO_ROOT / "results/d29_layer_b_characterization_v1/seed_metrics.csv"
D29_LAYER_B_SUMMARY = REPO_ROOT / "results/d29_layer_b_characterization_v1/summary.json"
ORACLE_B100 = (
    REPO_ROOT
    / "results/oracle_b100_background_diagnostic_reference_v1"
    / "seed21001_N250_rho0p4_lambda0p5.json"
)
TREESHAP_DEV = (
    REPO_ROOT
    / "results/treeshap_reference_development_v1"
    / "seed21001_N250_c0p30_rho0p4_lambda0p5.json"
)
XGB_SELECTED = (
    REPO_ROOT / "results/xgboost_development_calibration_v1/selected_parameters.json"
)
D3_FREEZE = REPO_ROOT / "results/d3_alpha_dispersion_execution_v1/freeze_summary.json"
RETENTION_AUDIT = (
    REPO_ROOT / "results/production_generator_retention_resolution_v1/audit_summary.json"
)

#: Frozen records kept as markdown rather than machine-readable artefacts.
DOC_NUMERICAL_NULL = REPO_ROOT / "docs/v2_2_d2_8_numerical_null_results.md"
DOC_D27 = REPO_ROOT / "docs/v2_2_d2_7_calibration_results.md"
DOC_V21_AUDIT = REPO_ROOT / "docs/v2_1_structural_audit.md"
DOC_READJUDICATION = (
    REPO_ROOT / "docs/historical_family_corrected_eligibility_readjudication_v1_results.md"
)

PAPER_DIR = REPO_ROOT / "paper"
MAIN_TEX = PAPER_DIR / "IC_TORS26_SHAP_MCDM_conference_final_2026-08-29_v12.tex"
SUPP_TEX = PAPER_DIR / "IC_TORS26_SHAP_MCDM_conference_supplement_2026-08-29_v5.tex"

#: Canonical method ordering as stored in the frozen artefacts.
METHODS = [
    "OracleAttribution",
    "SHAP",
    "PermutationImportance",
    "RidgePlus",
    "CRITIC",
    "Entropy",
]

#: Worlds used by Pilot B. Each replication seed defines one benchmark world.
WORLDS = [21001, 21002, 21003, 21004, 21005]


class ProtectedWriteError(RuntimeError):
    """Raised when a presentation script attempts to write into the frozen record."""


def guard_output_path(path: os.PathLike | str) -> Path:
    """Return ``path`` if it is a legal output location, else refuse.

    Any path resolving inside a protected directory is rejected before the caller
    can open it for writing.
    """
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT)
    except ValueError:
        # Outside the repository entirely (a scratch dir); nothing frozen there.
        return resolved
    top = relative.parts[0] if relative.parts else ""
    if top in PROTECTED_DIRS:
        raise ProtectedWriteError(
            f"refusing to write into the frozen scientific record: {relative}"
        )
    return resolved


def open_output(path: os.PathLike | str, mode: str = "w", **kwargs):
    """Open ``path`` for writing after the protected-directory guard passes."""
    resolved = guard_output_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return open(resolved, mode, **kwargs)


def load_json(path: os.PathLike | str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: os.PathLike | str) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text(path: os.PathLike | str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def sha256_of(path: os.PathLike | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def truncated_digest(path: os.PathLike | str, head: int = 8, tail: int = 8) -> str:
    """Return the non-identifying ``head...tail`` digest form used in the supplement."""
    full = sha256_of(path)
    return f"{full[:head]}...{full[-tail:]}"


def pilot_b_assessments() -> dict[str, dict]:
    """Frozen per-method Pilot-B assessments, keyed by method name."""
    data = load_json(PILOT_B)
    return {
        entry["method"]: entry
        for entry in data["hard_stop_evaluation"]["structured_method_assessments"]
    }


def selection_summaries() -> dict[tuple[int, str], dict]:
    """Frozen post-closure per-(world, method) selection summaries."""
    data = load_json(SELECTION_MAP)
    return {
        (row["development_world"], row["method"]): row
        for row in data["per_world_method_summaries"]
    }
