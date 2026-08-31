#!/usr/bin/env python3
"""Build an anonymous reproducibility manifest for the closed v1 study.

The manifest states exactly what the reproducibility package contains, with a
content digest for every file, so a reviewer can confirm integrity without
learning who the authors are.

Anonymity
---------
By default the manifest is anonymous: no repository URL, no remote, no author
name, no email, and commit identifiers are omitted. Pass ``--identified`` to
include the git commit and branch for the camera-ready package.

Scientific contract
-------------------
Read-only over the frozen record; writes only under outputs/paper/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402

#: What the package contains, and what each part is for. Only directories that
#: actually exist are reported; nothing is promised that is not present.
SECTIONS = [
    ("Synthetic benchmark generator and pipeline", "src", "*.py"),
    ("Frozen configuration and protocol files", "config", "*"),
    ("Frozen protocol and result records", "docs", "*.md"),
    ("Frozen scientific result artefacts", "results", "**/*"),
    ("Software test suite", "tests", "*.py"),
    ("Manuscript sources", "paper", "*.tex"),
    ("Manuscript-support scripts (read-only)", "scripts/paper", "*.py"),
]

#: Named artefacts a reviewer is most likely to want to locate directly.
KEY_ARTEFACTS = {
    "Pilot-B confirmatory adequacy result": fz.PILOT_B,
    "Post-closure descriptive selection-map result": fz.SELECTION_MAP,
    "D29 decision-geometry characterization": fz.D29_LAYER_B_CSV,
    "Oracle B100 matched-background diagnostic": fz.ORACLE_B100,
    "Development TreeSHAP reference": fz.TREESHAP_DEV,
    "XGBoost calibration freeze": fz.XGB_SELECTED,
    "Frozen Pilot-B hard-stop protocol":
        fz.REPO_ROOT / "config/pilot_b_hard_stop_protocol_v1.json",
    "Frozen post-closure diagnostic protocol":
        fz.REPO_ROOT / "config/pilot_b_fixed_weight_selection_diagnostic_v1.json",
}


def git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=fz.REPO_ROOT,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def collect(section: str, root: str, pattern: str) -> dict:
    base = fz.REPO_ROOT / root
    if not base.exists():
        return {"section": section, "root": root, "present": False, "files": []}
    files = []
    for path in sorted(base.glob(pattern)):
        if not path.is_file() or ".git" in path.parts:
            continue
        files.append({
            "path": str(path.relative_to(fz.REPO_ROOT)),
            "bytes": path.stat().st_size,
            "sha256": fz.sha256_of(path),
        })
    return {"section": section, "root": root, "present": True,
            "file_count": len(files), "files": files}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--identified", action="store_true",
                    help="include git commit/branch (camera-ready package only)")
    ap.add_argument("--out", type=Path,
                    default=fz.OUTPUT_ROOT / "manifest/reproducibility_manifest.json")
    ap.add_argument("--md", type=Path,
                    default=fz.OUTPUT_ROOT / "manifest/reproducibility_manifest.md")
    args = ap.parse_args()

    sections = [collect(*s) for s in SECTIONS]
    total = sum(s.get("file_count", 0) for s in sections)

    manifest = {
        "manifest_schema": "xai_mcdm_v1_reproducibility_manifest",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anonymous": not args.identified,
        "study_state": {
            "pilot_b": "executed once against a prospectively frozen gate; FAILED",
            "stop_that_fired": "modal_winner_effective_tie_hard_stop",
            "primary_factorial_authorized": False,
            "primary_worlds_accessed": False,
            "reserve_worlds_accessed": False,
            "post_closure_layer": "descriptive, non-confirmatory; cannot reopen the gate",
        },
        "not_included": [
            "Generated benchmark worlds: regenerated deterministically from the "
            "frozen seeds and configurations rather than stored.",
            "Primary (11001-11030) and reserve (30001-30005) worlds: never accessed; "
            "no artefact exists.",
            "Primary factorial results: the gate barred execution; none exist.",
        ],
        "key_artefacts": {
            name: {"path": str(path.relative_to(fz.REPO_ROOT)),
                   "sha256": fz.sha256_of(path),
                   "truncated": fz.truncated_digest(path)}
            for name, path in KEY_ARTEFACTS.items() if path.exists()
        },
        "total_files": total,
        "sections": sections,
    }
    if args.identified:
        manifest["provenance"] = {"commit": git("rev-parse", "HEAD"),
                                  "branch": git("rev-parse", "--abbrev-ref", "HEAD")}
    else:
        manifest["provenance"] = {
            "note": "Repository identifiers are withheld for anonymous review. "
                    "The complete version-controlled provenance record accompanies "
                    "the public package after review."
        }

    with fz.open_output(args.out) as handle:
        json.dump(manifest, handle, indent=1)
    print(f"wrote {args.out.relative_to(fz.REPO_ROOT)}")

    lines = [
        "# Reproducibility manifest",
        "",
        f"Generated {manifest['generated_utc']} - "
        f"{'anonymous review' if manifest['anonymous'] else 'identified'} package.",
        "",
        "## Study state",
        "",
        "| Item | Value |", "|---|---|",
    ]
    for k, v in manifest["study_state"].items():
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Key artefacts", "",
              "| Artefact | Path | Truncated SHA-256 |", "|---|---|---|"]
    for name, info in manifest["key_artefacts"].items():
        lines.append(f"| {name} | `{info['path']}` | `{info['truncated']}` |")
    lines += ["", "## Contents", "", "| Section | Root | Files |", "|---|---|---|"]
    for s in sections:
        lines.append(f"| {s['section']} | `{s['root']}` | "
                     f"{s.get('file_count', 0) if s['present'] else 'absent'} |")
    lines += ["", f"Total files inventoried: **{total}**", "",
              "## Deliberately not included", ""]
    lines += [f"- {x}" for x in manifest["not_included"]]
    lines += ["", "## Provenance", ""]
    if args.identified:
        lines.append(f"- commit `{manifest['provenance']['commit']}`")
        lines.append(f"- branch `{manifest['provenance']['branch']}`")
    else:
        lines.append(f"- {manifest['provenance']['note']}")
    lines += ["", "## Reproducing the reported tables, figure and checks", "",
              "```bash",
              "python scripts/paper/verify_frozen_manuscript_numbers.py",
              "python scripts/paper/check_selection_map_consistency.py",
              "python scripts/paper/build_pilot_b_tables.py",
              "python scripts/paper/make_decision_value_figure.py",
              "python scripts/paper/manuscript_consistency_audit.py",
              "python scripts/paper/latex_preflight.py",
              "```", ""]
    with fz.open_output(args.md) as handle:
        handle.write("\n".join(lines))
    print(f"wrote {args.md.relative_to(fz.REPO_ROOT)}")
    print(f"inventoried {total} files across {len(sections)} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
