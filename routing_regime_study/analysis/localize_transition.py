#!/usr/bin/env python3
"""
MINIMAL LOCALISING EXPERIMENT  --  NOT EXECUTED IN THIS SESSION.

Purpose
-------
Section 7 of the manuscript localises the routing-policy switching boundary.
The completed 432-run matrix brackets the reversal to intervals 480 veh/h wide:
    balanced signals -> crossing in (720, 1200]
    arterial signals -> crossing in (1200, 1680]   (3 of 4 restriction cells)
This script bisects both brackets by adding TWO demand levels: 960 and 1440 veh/h.

Design (minimum informative, NOT a factorial expansion)
------------------------------------------------------
    2 new demand levels x 4 restriction locations x 2 signal regimes
      x 3 policies (SP, DTT, TECO10) x 3 seeds (8101-8103)          = 144 runs
Expected wall time ~1.5 min at the throughput reported for the 432-run matrix.
A second bisection round (adding 840/1080 or 1320/1560 depending on the sign
observed at 960/1440) halves the remaining interval for a further 144 runs.

This characterises the switching regime. It does NOT add training data for the
selector, and no result in the manuscript depends on running it.

WHY IT WAS NOT RUN HERE
-----------------------
The SUMO network (.net.xml), route/demand manifests and .sumocfg files were not
present in the material supplied to this session -- only the compiled manuscript,
figures and the analysis workbook. Reconstructing the network from the workbook's
NETWORK sheet would yield a different simulator instance whose outputs could not
be spliced into the existing 432-run transition curve. Mixing two environments in
one curve would be invalid, so no simulation was run and none is reported.

TO RUN
------
    pip install eclipse-sumo            # or use the project's SUMO 1.25.0
    python3 localize_transition.py --project /path/to/reproducibility_package
Point --project at the directory holding the original net/route/config files.
Re-run the project's own observer/aggregation step afterwards so the new runs are
summarised exactly as the existing RAW_PERFORMANCE rows were.
"""
import argparse, itertools, os, subprocess, sys, csv

NEW_DEMANDS = [960, 1440]          # bisection of the two brackets
RESTRICTIONS = ["None", "U", "C", "L"]
SIGNALS      = ["Balanced", "Arterial"]
POLICIES     = ["SP", "DTT", "TECO10"]
SEEDS        = [8101, 8102, 8103]
SPEED_RATIO  = 0.35                # unchanged from the completed matrix
BG_PER_STREAM = 200                # unchanged

def plan():
    for q, r, s, p, seed in itertools.product(NEW_DEMANDS, RESTRICTIONS, SIGNALS, POLICIES, SEEDS):
        yield dict(demand=q, restriction=r, signal=s, policy=p, seed=seed,
                   run_id=f"T{q}_{r}_{s[:3]}_{p}_{seed}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True,
                    help="directory containing the original .net.xml / routes / .sumocfg")
    ap.add_argument("--out", default="transition_runs")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    runs = list(plan())
    print(f"planned runs: {len(runs)}  "
          f"({len(NEW_DEMANDS)} demands x {len(RESTRICTIONS)} restrictions x "
          f"{len(SIGNALS)} signals x {len(POLICIES)} policies x {len(SEEDS)} seeds)")

    net = os.path.join(a.project, "network.net.xml")
    if not os.path.exists(net):
        sys.exit(f"ERROR: {net} not found.\n"
                 "The original network/config files are required. This script "
                 "deliberately refuses to synthesise a substitute network, because "
                 "runs from a reconstructed network cannot be compared with the "
                 "existing 432 completed runs.")

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "run_manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0])); w.writeheader(); w.writerows(runs)
    if a.dry_run:
        print("dry run: manifest written, no simulation executed."); return

    for r in runs:
        cfg = os.path.join(a.out, r["run_id"] + ".sumocfg")
        # The project's own scenario generator builds the cfg for a given
        # (demand, restriction, signal, policy, seed); call it here.
        subprocess.run([sys.executable, os.path.join(a.project, "src", "build_scenario.py"),
                        "--demand", str(r["demand"]), "--restriction", r["restriction"],
                        "--signal", r["signal"], "--policy", r["policy"],
                        "--seed", str(r["seed"]), "--speed-ratio", str(SPEED_RATIO),
                        "--background", str(BG_PER_STREAM), "--out", cfg], check=True)
        subprocess.run(["sumo", "-c", cfg, "--no-step-log", "true"], check=True)
    print(f"done: {len(runs)} runs -> {a.out}")

if __name__ == "__main__":
    main()
