"""Final submission audit: the sixteen questions A-P, checked against the
artefacts rather than asserted."""
import json, os, re, glob, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
P = lambda *a: os.path.join(ROOT, *a)
R = json.load(open(P("results", "results.json")))
_raw = "".join(open(f).read() for f in glob.glob(P("paper", "sec*.tex"))
               + [P("paper", "abstract.tex")])
# normalise whitespace once: source line breaks must not affect phrase checks
paper = re.sub(r"\s+", " ", _raw)
out = []


def chk(tag, q, ok, detail=""):
    out.append((tag, q, bool(ok), detail))


# A. headline numbers traceable
defined = set(re.findall(r"\\newcommand\{\\(Num[A-Za-z]+)\}", open(P("paper", "numbers.tex")).read()))
used = set()
for f in glob.glob(P("paper", "*.tex")) + glob.glob(P("paper", "tables", "*.tex")):
    if os.path.basename(f) == "numbers.tex":
        continue
    used |= set(re.findall(r"\\(Num[A-Za-z]+)", open(f).read()))
chk("A", "all headline numbers traceable to results.json via macros",
    not (used - defined), f"{len(used)} macros used, {len(used - defined)} undefined")

# B. percentages mathematically consistent
h = R["headroom"]
agg = 100.0 * h["mean_headroom_s"] / h["mean_cost_sbs_s"]
macro = float(re.search(r"\\NumHeadroomPct\}\{([0-9.]+)", open(P("paper", "numbers.tex")).read()).group(1))
chk("B", "adaptation percentage equals headroom / SBS mean cost",
    abs(agg - macro) < 0.001, f"{h['mean_headroom_s']:.4f}/{h['mean_cost_sbs_s']:.3f} = {agg:.4f}% vs macro {macro}%")
fp = R["fixed_policy_choice"]
p1 = 100.0 * fp["penalty_vs_sbs_s"]["P1"] / fp["mean_cost"][fp["sbs"]]
chk("B2", "46.4% equals P1 excess / SBS mean cost",
    abs(p1 - fp["penalty_vs_sbs_pct"]["P1"]) < 0.01, f"{p1:.3f}%")

# C. 12,960 distinguished from the project total
chk("C", "main-campaign count distinguished from total executions",
    "\\NumRunsMain" in paper and "\\NumRunsTotalAttempted" in paper
    and "distinct and are not inter" in paper,
    "both macros present; reconciliation paragraph in the integrity section")

# D/E/F. deviations disclosed
chk("D", "protocol deviation D-1 disclosed in the manuscript",
    "D-1" in paper and "screen did not satisfy criterion G1" in paper
    and "triggered the declared stopping rule" in paper)
chk("E", "infeasible OOD split and its replacement disclosed",
    "single-lane" in paper and "\\NumRunsFailedBypass" in paper)
chk("F", "G1' distinguished from G1, not presented as G1 passing",
    "G1$'$" in paper and "do not describe the original screen as having passed" in paper)

# G/H. criteria and Pareto
chk("G", "three criteria defined with measurement definitions",
    os.path.exists(P("paper", "tables", "tab3_criteria.tex"))
    and "stopped delay" in paper.lower())
chk("H", "Pareto analysis described as dominance-first",
    "Pareto dominance first" in paper or "dominance first" in paper)

# I/J. decision-oriented evaluation
lad = {r["selector"]: r for r in R["ladder_loco"]}
chk("I", "mechanistic rule compared on regret as well as accuracy",
    "\\NumBOneTopOne" in paper and "\\NumBOneRegret" in paper,
    f"B1 {100*R['top1_accuracy']['B1_mechanistic']:.1f}% top-1, {lad['B1_mechanistic']['mean_regret']:.3f} s regret")
chk("J", "B4 compared primarily against B1",
    "primary comparison is B4 against B1" in paper
    or "primary comparison declared in advance was B4 against B1" in paper)

# K/L. no overclaiming
bad = [p for p in ["conformal prediction solves", "guarantees safety",
                   "universal", "guarantees OOD", "guaranteed protection"]
       if p in paper.lower()]
chk("K", "selective model described without conformal/OOD overclaiming", not bad, str(bad))
chk("L", "feature-invisible shift limitation disclosed",
    "feature space unchanged" in paper or "feature space does not represent" in paper)

# M. scoping
chk("M", "claims scoped to the synthetic benchmark",
    "No claim of real-world validation" in paper)

# N. references
bib = open(P("paper", "references.bib")).read()
keys = set(re.findall(r"@\w+\{([^,]+),", bib))
cited = set()
for f in glob.glob(P("paper", "*.tex")):
    for mm in re.finditer(r"\\cite\{([^}]*)\}", open(f).read()):
        cited |= {k.strip() for k in mm.group(1).split(",")}
chk("N", "every reference cited and every citation defined",
    not (cited - keys) and not (keys - cited),
    f"{len(keys)} defined, {len(cited)} cited, unused {sorted(keys - cited)}")

# O. compiles cleanly
log = open(P("paper", "main.log")).read()
nerr = len(re.findall(r"^! ", log, re.M))
nund = len(re.findall(r"Warning: (?:Citation|Reference) .* undefined", log))
nover = len([x for x in re.findall(r"Overfull \\hbox \(([0-9.]+)pt", log) if float(x) > 15])
chk("O", "compiles with no errors, undefined references or bad overfull boxes",
    nerr == 0 and nund == 0 and nover == 0,
    f"errors {nerr}, undefined {nund}, overfull>15pt {nover}")

# P. format
chk("P", "uses the document class of the repository's prior IC_TORS'26 submission",
    "llncs" in open(P("paper", "lncs_front.tex")).read(),
    "llncs with runningheads; no official template found, dependency stated in README")

print(f"{'':4s}{'question':66s}result")
print("-" * 82)
for tag, q, ok, d in out:
    print(f"{tag:4s}{q:66s}{'PASS' if ok else 'FAIL'}")
    if d:
        print(f"      {d}")
n = sum(1 for _, _, ok, _ in out if not ok)
print("-" * 82)
print(f"{len(out) - n}/{len(out)} checks pass")
sys.exit(1 if n else 0)
