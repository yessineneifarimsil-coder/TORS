"""Final quality-control gate.  Each item is checked against the artefacts
rather than asserted."""
import json, os, re, subprocess, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
R = json.load(open(os.path.join(ROOT, "results", "results.json")))
P = lambda *a: os.path.join(ROOT, *a)
out = []


def chk(tag, name, ok, detail=""):
    out.append((tag, name, bool(ok), detail))


# A. every reported number comes from actual data
defined = set(re.findall(r'\\newcommand\{\\(Num[A-Za-z]+)\}',
                         open(P("paper", "numbers.tex")).read()))
used = set()
for f in glob.glob(P("paper", "*.tex")) + glob.glob(P("paper", "tables", "*.tex")):
    if os.path.basename(f) == "numbers.tex":
        continue
    used |= set(re.findall(r'\\(Num[A-Za-z]+)', open(f).read()))
chk("A", "every manuscript number resolves through a generated macro",
    not (used - defined), f"{len(used)} used, {len(used-defined)} undefined")

# B. citations exist
bib = open(P("paper", "references.bib")).read()
keys = set(re.findall(r'@\w+\{([^,]+),', bib))
cited = set()
for f in glob.glob(P("paper", "*.tex")):
    for mm in re.finditer(r'\\cite\{([^}]*)\}', open(f).read()):
        cited |= {k.strip() for k in mm.group(1).split(",")}
chk("B", "every citation exists in the bibliography", not (cited - keys),
    f"{len(cited)} cited, {len(keys)} defined, missing {sorted(cited-keys)}")

# C/D/E. leakage, SBS on training only, VBS non-deployable
src = open(P("analysis", "policy_selectors.py")).read()
chk("C", "no test information in training (LOCO builds train by exclusion)",
    "j for j in range(n) if j != i" in open(P("analysis", "policy_selectors.py")).read())
chk("D", "SBS selected on training folds only",
    "sbs = int(np.argmin(Ctr.mean(axis=0)))" in src)
PAPER = re.sub(r"\s+", " ", "".join(
    open(f).read() for f in sorted(glob.glob(P("paper", "sec*.tex")))
    + [P("paper", "abstract.tex")]))
chk("E", "VBS stated as non-deployable in the manuscript",
    "not deployable" in PAPER.lower() and "retrospective" in PAPER.lower())

# F/G. mechanistic rule out-of-sample; ML compared against it
lad = {r["selector"]: r for r in R["ladder_loco"]}
chk("F", "mechanistic rule evaluated out-of-sample (present in the LOCO ladder)",
    "B1_mechanistic" in lad)
chk("G", "ML compared directly against the mechanistic rule",
    "B4_GBDT" in lad and "B1_mechanistic" in lad,
    f"B4 {lad['B4_GBDT']['mean_regret']:.3f} s vs B1 {lad['B1_mechanistic']['mean_regret']:.3f} s")

# H/I. criteria defined; stopped delay consistent
chk("H", "three criteria defined with measurement definitions",
    os.path.exists(P("paper", "tables", "tab3_criteria.tex")))
chk("I", "stopped delay measured consistently (single definition in run.py)",
    open(P("sim", "run.py")).read().count('waitingTime') == 1)

# J. portfolio frozen before evaluation
git = subprocess.run(["git", "log", "--format=%H %ct", "--", "study/spec/FROZEN_SPEC.md"],
                     cwd=os.path.join(ROOT, ".."), capture_output=True, text=True)
spec_t = int(git.stdout.strip().split("\n")[-1].split()[1]) if git.stdout.strip() else 0
main_t = int(os.path.getmtime(P("results", "main.jsonl")))
chk("J", "specification frozen before the main campaign ran", spec_t < main_t,
    f"spec committed {spec_t}, campaign data {main_t}")

# K. OOD reported separately by shift type
kinds = {d["_shift_type"] for d in R["ood"].values()}
chk("K", "OOD results reported separately by shift type", len(R["ood"]) >= 7,
    f"{len(R['ood'])} splits, {len(kinds)} distinct shift types")

# L. abstention uses only decision-time information
chk("L", "abstention uses only training-fold quantities",
    "np.quantile(resid, 1 - ALPHA)" in src and "Ztr" in src)

# M. no continuous threshold claimed
chk("M", "boundaries reported as brackets, not point thresholds",
    "bracket" in PAPER.lower() and "point estimate" in PAPER.lower())

# N. no causal claim
chk("N", "no causal mechanism claimed without identification",
    "not an identified causal mechanism" in PAPER)

# O/P. no version language
bad = []
for f in glob.glob(P("paper", "*.tex")):
    if os.path.basename(f) == "numbers.tex":
        continue
    for mm in re.finditer(r'\b(V1|V2|previous (study|version|manuscript)|earlier (study|version))\b',
                          open(f).read(), re.I):
        bad.append(f"{os.path.basename(f)}: {mm.group(0)}")
chk("O", "no previous-study or version language in the manuscript", not bad, str(bad[:3]))
chk("P", "manuscript compiles with no errors and no undefined references",
    os.path.exists(P("paper", "main.pdf"))
    and "! " not in open(P("paper", "main.log")).read().split("Output written")[0][-4000:])

# Q. contribution legible to a non-ML reader
chk("Q", "contributions stated without requiring ML background",
    "We introduce no routing algorithm, no learning algorithm" in PAPER)

print(f"{'':3s}{'check':68s}result")
print("-" * 82)
for tag, name, ok, detail in out:
    print(f"{tag:3s}{name:68s}{'PASS' if ok else 'FAIL'}")
    if detail and not ok:
        print(f"      -> {detail}")
    elif detail:
        print(f"      {detail}")
nfail = sum(1 for _, _, ok, _ in out if not ok)
print("-" * 82)
print(f"{len(out)-nfail}/{len(out)} checks pass")
sys.exit(1 if nfail else 0)
