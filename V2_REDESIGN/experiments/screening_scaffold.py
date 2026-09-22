#!/usr/bin/env python3
"""
Complementarity screening analysis — V2 gate G1-G4.

Consumes a run table of COMPLETED SUMO runs and emits the gate report defined in
SCREENING_EXPERIMENT.md. Thresholds are hard-coded here on purpose: they were declared
before any run and must not be edited after seeing results.

There is deliberately NO synthetic-data path. Without a real run table this script
exits. A screening report can therefore only ever contain measured numbers.

Usage:
    python3 screening_scaffold.py --runs path/to/screening_runs.csv
"""
import argparse, csv, sys, math, statistics as st
from collections import defaultdict
from itertools import combinations

# --- pre-declared gate thresholds (see SCREENING_EXPERIMENT.md) ---------------
G1_MIN_WINNING_POLICIES   = 3      # of 4
G2_MIN_PARETO_FRACTION    = 0.25
G3_MAX_IDENTITY_FRACTION  = 0.50
NOISE_K                   = 1.0    # winner must beat runner-up by > NOISE_K * pooled SE
PARETO_CRITERIA           = ("sys_mean_tt", "p95_tt", "co2")
PRIMARY                   = "sys_mean_tt"

REQUIRED = ["context_id","policy","seed","sys_mean_tt","guided_mean_tt","bg_mean_tt",
            "p95_tt","sd_tt","max_util","stopped_time","co2","route_diversity",
            "oscillation_idx"]

def load(path):
    import os
    if not os.path.exists(path):
        sys.exit(f"ERROR: run table not found: {path}\n"
                 "The screen analyses COMPLETED simulation output only. There is no "
                 "synthetic-data path, by design: a screening report must never contain "
                 "a number that was not measured.")
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("ERROR: run table is empty. The screen requires completed simulation output.")
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        sys.exit(f"ERROR: run table is missing required columns: {missing}")
    for r in rows:
        for c in REQUIRED[3:]:
            r[c] = float(r[c])
    return rows

def cell_stats(rows):
    """(context, policy) -> {metric: (mean, se, n)} over seeds."""
    g = defaultdict(list)
    for r in rows:
        g[(r["context_id"], r["policy"])].append(r)
    out = {}
    for k, rs in g.items():
        if len(rs) < 2:
            sys.exit(f"ERROR: cell {k} has {len(rs)} seed(s); the screen needs >=2 to "
                     "estimate a noise floor (>=10 recommended).")
        d = {}
        for m in REQUIRED[3:]:
            v = [r[m] for r in rs]
            d[m] = (st.mean(v), st.stdev(v)/math.sqrt(len(v)), len(v))
        out[k] = d
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    a = ap.parse_args()
    rows = load(a.runs)
    cells = cell_stats(rows)
    ctxs = sorted({c for c, _ in cells})
    pols = sorted({p for _, p in cells})
    print(f"contexts {len(ctxs)} | policies {len(pols)} | runs {len(rows)}")

    # ---- per-context winner, with an explicit TIE verdict --------------------
    winners, ties = {}, []
    for c in ctxs:
        ranked = sorted(pols, key=lambda p: cells[(c, p)][PRIMARY][0])
        best, second = ranked[0], ranked[1]
        mb, sb, _ = cells[(c, best)][PRIMARY]
        ms, ss, _ = cells[(c, second)][PRIMARY]
        pooled = math.sqrt(sb**2 + ss**2)
        if (ms - mb) > NOISE_K * pooled:
            winners[c] = best
        else:
            winners[c] = "TIE"; ties.append(c)
    wins = {p: sum(1 for c in ctxs if winners[c] == p) for p in pols}
    print(f"\nwins: {wins}   ties: {len(ties)}/{len(ctxs)}")

    # ---- Pareto sets --------------------------------------------------------
    crit = [m for m in PARETO_CRITERIA if m in REQUIRED]
    nonsingleton = 0
    for c in ctxs:
        pts = {p: [cells[(c, p)][m][0] for m in crit] for p in pols}
        eff = [p for p in pols if not any(
            all(pts[q][i] <= pts[p][i] for i in range(len(crit))) and
            any(pts[q][i] <  pts[p][i] for i in range(len(crit))) for q in pols if q != p)]
        if len({tuple(round(v, 9) for v in pts[p]) for p in eff}) > 1:
            nonsingleton += 1
    pareto_frac = nonsingleton / len(ctxs)

    # ---- pairwise outcome identity (the V1 degeneracy diagnostic) -----------
    identity = {}
    for p, q in combinations(pols, 2):
        same = sum(1 for c in ctxs
                   if abs(cells[(c,p)][PRIMARY][0] - cells[(c,q)][PRIMARY][0])
                      <= NOISE_K * math.sqrt(cells[(c,p)][PRIMARY][1]**2 + cells[(c,q)][PRIMARY][1]**2))
        identity[(p, q)] = same / len(ctxs)
    worst_pair, worst_frac = max(identity.items(), key=lambda kv: kv[1])

    # ---- gates --------------------------------------------------------------
    g1 = sum(1 for p in pols if wins[p] > 0) >= G1_MIN_WINNING_POLICIES
    g2 = pareto_frac >= G2_MIN_PARETO_FRACTION
    g3 = worst_frac <= G3_MAX_IDENTITY_FRACTION
    print("\n--- GATES (thresholds declared before any run) ---")
    print(f"  G1 >={G1_MIN_WINNING_POLICIES} policies win a context : "
          f"{sum(1 for p in pols if wins[p] > 0)}  {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 non-singleton Pareto fraction    : {pareto_frac:.2f}  "
          f"(>= {G2_MIN_PARETO_FRACTION})  {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 worst pairwise identity          : {worst_frac:.2f} {worst_pair}  "
          f"(<= {G3_MAX_IDENTITY_FRACTION})  {'PASS' if g3 else 'FAIL'}")
    print("  G4 multi-factor winner map          : requires the factor table; "
          "evaluate with the frozen scenario file")
    print(f"\n  VERDICT: {'PROCEED (subject to G4)' if (g1 and g3) else 'STOP - portfolio degenerate'}")
    if not (g1 and g3):
        print("  Report the negative result. Do NOT retune the network to change this outcome.")

if __name__ == "__main__":
    main()
