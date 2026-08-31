#!/usr/bin/env python3
"""Compile both manuscripts in both build modes and audit the LaTeX logs.

For each of {main, supplement} x {anonymous review, identified camera-ready}:

* compile twice so cross-references and page counts settle;
* report undefined references, undefined citations, multiply-defined labels,
  missing files, overfull/underfull boxes and errors;
* report the final page count;
* run an anonymity audit on the review build's PDF text and on the source;
* run a stale-project-keyword scan.

Builds happen in a scratch directory under outputs/paper/build/. Nothing is
written into paper/ or into the frozen record.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402

#: Vocabulary that would reveal the authors in an anonymous build.
IDENTIFYING = [
    "Neifar", "Farhi", "Frikha", "Gustave Eiffel", "GRETTIA", "COSYS",
    "ISGIS", "Sfax", "OLID", "usf.tn", "yessine", "Marne-la-Vall",
    "Champs-sur-Marne", "@", "Acknowledgements", "CRediT",
]
#: '@' and a couple of others are too broad to test on raw source; PDF text only.
PDF_ONLY = {"@", "Acknowledgements", "CRediT"}

STALE = ["SUMO", "TraCI", "QMIX", "Max Pressure", "MaxPressure", "trained-policy",
         "trained policy", "policy checkpoint", "per-second", "route file",
         "traffic-signal controller", "CoCoSo", "reinforcement learning"]


@dataclass
class Build:
    label: str
    tex: Path
    anonymous: bool
    pages: int = 0
    errors: list[str] = field(default_factory=list)
    undefined_refs: list[str] = field(default_factory=list)
    undefined_cites: list[str] = field(default_factory=list)
    multiply_defined: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    overfull: list[str] = field(default_factory=list)
    underfull: list[str] = field(default_factory=list)
    identifying_hits: list[str] = field(default_factory=list)
    stale_hits: list[str] = field(default_factory=list)
    pdf: Path | None = None
    ok: bool = False


def run_latex(tex: Path, workdir: Path, anonymous: bool) -> tuple[str, int]:
    """Run pdflatex twice, returning the second log and the final return code."""
    jobname = tex.stem + ("" if anonymous else "-cameraready")
    if anonymous:
        target = str(tex.name)
    else:
        target = r"\def\CAMERAREADY{1}\input{%s}" % tex.stem
    log = ""
    rc = 0
    for _ in range(2):
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error=false",
             "-file-line-error", f"-jobname={jobname}", target],
            cwd=workdir, capture_output=True, text=True, timeout=300,
        )
        rc = proc.returncode
        logfile = workdir / f"{jobname}.log"
        if logfile.exists():
            log = logfile.read_text(encoding="utf-8", errors="replace")
    return log, rc


def parse_log(log: str, build: Build) -> None:
    build.pages = 0
    # pdflatex hard-wraps its log at ~79 columns, so "Output written on
    # <name>.pdf (14 pages, ...)" is routinely split mid-phrase. De-wrap first.
    dewrapped = log.replace("\n", "")
    m = re.findall(r"Output written on .*?\((\d+) pages?", dewrapped)
    if m:
        build.pages = int(m[-1])
    for line in log.splitlines():
        if re.match(r"^(?:.*?:\d+:|!)", line) and "Warning" not in line:
            build.errors.append(line.strip())
        if "Reference" in line and "undefined" in line:
            build.undefined_refs.append(line.strip())
        if "Citation" in line and "undefined" in line:
            build.undefined_cites.append(line.strip())
        if "multiply defined" in line or "multiply-defined" in line:
            build.multiply_defined.append(line.strip())
        if "File" in line and "not found" in line:
            build.missing_files.append(line.strip())
    build.overfull = re.findall(r"Overfull \\[hv]box \(([\d.]+pt) too \w+\)", log)
    build.underfull = re.findall(r"Underfull \\[hv]box \(badness (\d+)\)", log)


def pdf_text(pdf: Path) -> str:
    for tool in (["pdftotext", str(pdf), "-"], ):
        if shutil.which(tool[0]):
            proc = subprocess.run(tool, capture_output=True, text=True)
            if proc.returncode == 0:
                return proc.stdout
    return ""


def audit_anonymity(build: Build, source: str) -> None:
    if not build.anonymous:
        return
    body = re.sub(r"(?m)^\s*%.*$", "", source)
    # In the source, identifying strings may appear inside the \else branch of
    # the build switch. Strip those branches before scanning.
    stripped = re.sub(r"\\else.*?\\fi", "", body, flags=re.S)
    for term in IDENTIFYING:
        if term in PDF_ONLY:
            continue
        if term.lower() in stripped.lower():
            build.identifying_hits.append(f"source (outside \\else): {term!r}")
    text = pdf_text(build.pdf) if build.pdf and build.pdf.exists() else ""
    if text:
        for term in IDENTIFYING:
            if term.lower() in text.lower():
                build.identifying_hits.append(f"rendered PDF: {term!r}")
    else:
        build.identifying_hits.append(
            "NOTE: pdftotext unavailable; PDF text not scanned")


def audit_stale(build: Build, source: str) -> None:
    body = re.sub(r"(?m)^\s*%.*$", "", source)
    for term in STALE:
        if term.lower() in body.lower():
            build.stale_hits.append(f"source: {term!r}")
    text = pdf_text(build.pdf) if build.pdf and build.pdf.exists() else ""
    for term in STALE:
        if text and term.lower() in text.lower():
            build.stale_hits.append(f"rendered PDF: {term!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", type=Path, default=fz.OUTPUT_ROOT / "build")
    ap.add_argument("--pdfdir", type=Path, default=fz.OUTPUT_ROOT / "pdf")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if not shutil.which("pdflatex"):
        print("pdflatex not available; cannot run the LaTeX preflight.",
              file=sys.stderr)
        return 2

    workdir = Path(fz.guard_output_path(args.outdir))
    pdfdir = Path(fz.guard_output_path(args.pdfdir))
    workdir.mkdir(parents=True, exist_ok=True)
    pdfdir.mkdir(parents=True, exist_ok=True)

    # Stage sources and the generated figure into the scratch build directory.
    for tex in (fz.MAIN_TEX, fz.SUPP_TEX):
        shutil.copy2(tex, workdir / tex.name)
    figdir = fz.OUTPUT_ROOT / "figures"
    for fig in figdir.glob("decision_value_figure.*"):
        shutil.copy2(fig, workdir / fig.name)

    builds = [
        Build("main / anonymous review", fz.MAIN_TEX, True),
        Build("main / identified camera-ready", fz.MAIN_TEX, False),
        Build("supplement / anonymous review", fz.SUPP_TEX, True),
        Build("supplement / identified camera-ready", fz.SUPP_TEX, False),
    ]

    failed = False
    for b in builds:
        staged = workdir / b.tex.name
        log, rc = run_latex(staged, workdir, b.anonymous)
        parse_log(log, b)
        jobname = b.tex.stem + ("" if b.anonymous else "-cameraready")
        produced = workdir / f"{jobname}.pdf"
        if produced.exists():
            b.pdf = pdfdir / produced.name
            shutil.copy2(produced, b.pdf)
        source = fz.read_text(b.tex)
        audit_anonymity(b, source)
        audit_stale(b, source)
        b.ok = (b.pdf is not None and b.pages > 0 and not b.errors
                and not b.undefined_refs and not b.undefined_cites
                and not b.multiply_defined and not b.missing_files
                and not [h for h in b.identifying_hits if not h.startswith("NOTE")]
                and not b.stale_hits)
        if not b.ok:
            failed = True

    print("latex_preflight\n" + "=" * 62)
    for b in builds:
        status = "OK" if b.ok else "ISSUES"
        print(f"\n[{status}] {b.label}")
        print(f"   pages              : {b.pages}")
        print(f"   errors             : {len(b.errors)}")
        print(f"   undefined refs     : {len(b.undefined_refs)}")
        print(f"   undefined citations: {len(b.undefined_cites)}")
        print(f"   multiply-defined   : {len(b.multiply_defined)}")
        print(f"   missing files      : {len(b.missing_files)}")
        print(f"   overfull boxes     : {len(b.overfull)}"
              + (f"  (worst {max(b.overfull, key=lambda s: float(s[:-2]))})"
                 if b.overfull else ""))
        print(f"   underfull boxes    : {len(b.underfull)}")
        if b.anonymous:
            real = [h for h in b.identifying_hits if not h.startswith("NOTE")]
            print(f"   anonymity          : "
                  f"{'CLEAN' if not real else str(len(real)) + ' HIT(S)'}")
            for h in b.identifying_hits:
                print(f"      - {h}")
        print(f"   stale keywords     : "
              f"{'none' if not b.stale_hits else b.stale_hits}")
        for group, items in (("ERROR", b.errors), ("UNDEF REF", b.undefined_refs),
                             ("UNDEF CITE", b.undefined_cites),
                             ("MULTI LABEL", b.multiply_defined),
                             ("MISSING FILE", b.missing_files)):
            for item in items[:12]:
                print(f"      {group}: {item}")
        if b.pdf:
            print(f"   pdf                : {b.pdf.relative_to(fz.REPO_ROOT)}")

    if args.json:
        with fz.open_output(args.json) as handle:
            json.dump([{
                "label": b.label, "anonymous": b.anonymous, "pages": b.pages,
                "ok": b.ok, "errors": b.errors, "undefined_refs": b.undefined_refs,
                "undefined_citations": b.undefined_cites,
                "multiply_defined": b.multiply_defined,
                "missing_files": b.missing_files,
                "overfull_boxes": b.overfull, "underfull_boxes": b.underfull,
                "identifying_hits": b.identifying_hits, "stale_hits": b.stale_hits,
                "pdf": str(b.pdf.relative_to(fz.REPO_ROOT)) if b.pdf else None,
            } for b in builds], handle, indent=1)
        print(f"\nreport written to {args.json}")

    print("\n" + ("PREFLIGHT: ISSUES FOUND" if failed else "PREFLIGHT: ALL CLEAN"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
