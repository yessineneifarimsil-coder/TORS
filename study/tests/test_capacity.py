"""Capacity calibration and validation on the study network.

Each corridor is driven to saturation on its own and its discharge rate is
measured.  This does two things: it checks the network behaves like a
signalised network should, and it supplies the saturation flow used by the
dimensionless descriptors in the mechanistic model, so that v/c is a measured
quantity rather than a textbook constant asserted about this network.
"""
import json, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "..", "sim", "run.py")
CYCLE, YELLOW = 90.0, 4.0
LANES = {"C": 2, "N": 1, "S": 1}
SIGNALISED = {"C": True, "N": True, "S": False}

rows, sat = [], []
ALT_CHECK = []
print(f"{'corridor':9s}{'g/C':>6s}{'eff.green':>11s}{'lanes':>7s}"
      f"{'measured q':>12s}{'implied sat flow':>19s}")
for path in ("C", "N", "S"):
    for gc in (0.35, 0.50, 0.65):
        if not SIGNALISED[path] and gc != 0.50:
            continue
        out = subprocess.run(
            [sys.executable, RUN, "--policy", "P1", "--demand", "5400",
             "--penetration", "1.0", "--gc", str(gc), "--alt", "1",
             "--seed", "201", "--force", path, "--bg", "0"],
            capture_output=True, text=True,
            env={**os.environ, "SUMO_HOME": os.environ.get(
                "SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")})
        r = json.loads([l for l in out.stdout.splitlines() if l.startswith("{")][-1])
        eff = (gc * CYCLE - YELLOW) / CYCLE if SIGNALISED[path] else 1.0
        s_impl = r["throughput"] / (LANES[path] * eff)
        rows.append((path, gc, eff, r["throughput"], s_impl))
        sat.append(s_impl)
        print(f"{path:9s}{gc:6.2f}{eff:11.3f}{LANES[path]:7d}"
              f"{r['throughput']:12.0f}{s_impl:19.0f}")

# north corridor at two lanes: capacity must scale with lane count
out = subprocess.run(
    [sys.executable, RUN, "--policy", "P1", "--demand", "5400", "--penetration", "1.0",
     "--gc", "0.50", "--alt", "2", "--seed", "201", "--force", "N", "--bg", "0"],
    capture_output=True, text=True,
    env={**os.environ, "SUMO_HOME": os.environ.get(
        "SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")})
q_n2 = json.loads([l for l in out.stdout.splitlines() if l.startswith("{")][-1])["throughput"]
q_n1 = [q for (p, g, e, q, s) in rows if p == "N" and g == 0.50][0]
print(f"{'N (alt=2)':9s}{0.50:6.2f}{0.456:11.3f}{2:7d}{q_n2:12.0f}"
      f"{q_n2/(2*0.456):19.0f}")

FAIL = []
def check(n, c, d=""):
    print(("PASS  " if c else "FAIL  ") + n + ("" if c else "   <-- " + d))
    if not c: FAIL.append(n)

print()
per = {}
for p in ("C", "N"):
    v = [s for (q_p, g, e, q, s) in rows if q_p == p]
    per[p] = sum(v) / len(v)
    spread = (max(v) - min(v)) / per[p]
    check(f"corridor {p}: one saturation flow explains every green ratio (<3%)",
          spread < 0.03, f"spread={spread:.3f} values={[round(x) for x in v]}")
check("the two signalised corridors differ in saturation flow, as their "
      "different speed limits require", per["C"] > per["N"] * 1.05,
      f"C={per['C']:.0f} N={per['N']:.0f}")
check("north-corridor capacity scales with lane count (2 lanes ~ 2x 1 lane)",
      1.8 <= q_n2 / q_n1 <= 2.2, f"q(1 lane)={q_n1:.0f} q(2 lanes)={q_n2:.0f} "
      f"ratio={q_n2/q_n1:.2f}")
c35 = [q for (p, g, e, q, s) in rows if p == "C" and g == 0.35][0]
c65 = [q for (p, g, e, q, s) in rows if p == "C" and g == 0.65][0]
check("arterial capacity increases with green ratio", c65 > c35 * 1.4,
      f"q(0.35)={c35:.0f} q(0.65)={c65:.0f}")
q_s = [q for (p, g, e, q, s) in rows if p == "S"][0]
for p in ("C", "N"):
    check(f"corridor {p} saturation flow is physically plausible "
          f"(1400-2000 veh/h/lane)", 1400 <= per[p] <= 2000, f"{per[p]:.0f}")
check("uninterrupted bypass capacity is below queue-discharge saturation flow, "
      "as free-flow headways require", q_s < per["C"], f"S={q_s:.0f} C={per['C']:.0f}")
print(f"\n  CALIBRATED CAPACITY MODEL")
print(f"    arterial      s = {per['C']:.0f} veh/h/lane  (signalised, 50 km/h)")
print(f"    north street  s = {per['N']:.0f} veh/h/lane  (signalised, 40 km/h)")
print(f"    bypass        q = {q_s:.0f} veh/h/lane  (uninterrupted, 50 km/h)")
json.dump({"sat_flow_arterial_vphpl": per["C"], "sat_flow_north_vphpl": per["N"],
           "cap_bypass_vphpl": q_s, "cycle_s": CYCLE, "yellow_s": YELLOW,
           "north_2lane_throughput": q_n2,
           "measurements": [{"path": p, "gc": g, "eff_green": e,
                             "q": q, "s_implied": s} for p, g, e, q, s in rows]},
          open(os.path.join(HERE, "..", "results", "capacity_calibration.json"), "w"),
          indent=1)
print(f"\n{'ALL TESTS PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
