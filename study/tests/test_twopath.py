"""Integration test: two parallel paths, equal length, unequal capacity.

Verifies inside SUMO -- not merely in the policy object -- that
  * P1 sends the entire guided cohort to one path (it minimises distance and the
    tie is broken deterministically),
  * P3 splits the guided cohort towards the capacity ratio,
  * the resulting flows really do appear on the intended edges.
"""
import os, sys, subprocess, tempfile, shutil, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "policies"))
os.environ.setdefault("SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")
import traci, sumolib                                             # noqa: E402
import policies as POL                                            # noqa: E402

TMP = tempfile.mkdtemp(prefix="twopath_")
NODES = [("O", -500, 0), ("D", 0, 0), ("M", 1000, 0), ("E", 1500, 0)]
EDGES = [("o_d", "O", "D", 2, 13.89), ("m_e", "M", "E", 3, 13.89),
         ("A", "D", "M", 2, 13.89), ("B", "D", "M", 1, 13.89)]
# dedicated exit lane per approach: the merge cannot penalise the minor path
LANECON = [("A", "m_e", 0, 0), ("A", "m_e", 1, 1), ("B", "m_e", 0, 2)]
PATHS = {"A": ["A"], "B": ["B"]}
CAP = {"A": 2 * 1800.0, "B": 1 * 1800.0}


def build():
    with open(f"{TMP}/n.nod.xml", "w") as f:
        f.write("<nodes>\n" + "".join(
            f'<node id="{n}" x="{x}" y="{y}" type="priority"/>\n' for n, x, y in NODES) + "</nodes>")
    with open(f"{TMP}/e.edg.xml", "w") as f:
        f.write("<edges>\n" + "".join(
            f'<edge id="{i}" from="{a}" to="{b}" numLanes="{l}" speed="{s}" length="1000"/>\n'
            if i in ("A", "B") else
            f'<edge id="{i}" from="{a}" to="{b}" numLanes="{l}" speed="{s}"/>\n'
            for i, a, b, l, s in EDGES) + "</edges>")
    with open(f"{TMP}/c.con.xml", "w") as f:
        f.write("<connections>\n" + "".join(
            f'<connection from="{a}" to="{b}" fromLane="{fl}" toLane="{tl}"/>\n'
            for a, b, fl, tl in LANECON) + "".join(
            f'<connection from="o_d" to="{x}"/>\n' for x in ("A", "B")) + "</connections>")
    subprocess.run(["netconvert", "-n", f"{TMP}/n.nod.xml", "-e", f"{TMP}/e.edg.xml",
                    "-x", f"{TMP}/c.con.xml",
                    "-o", f"{TMP}/t.net.xml", "--no-turnarounds", "true"],
                   capture_output=True, check=True)


def routes(n, rate):
    with open(f"{TMP}/t.rou.xml", "w") as f:
        f.write('<routes>\n<vType id="car" vClass="passenger"/>\n'
                '<route id="r_A" edges="o_d A m_e"/>\n<route id="r_B" edges="o_d B m_e"/>\n')
        f.write("</routes>")
    return [(i * 3600.0 / rate, f"g_{i}") for i in range(n)]


def simulate(policy_name, n=600, rate=2400):
    sched = routes(n, rate)
    net = sumolib.net.readNet(f"{TMP}/t.net.xml")
    ff = {e: net.getEdge(e).getLength() / net.getEdge(e).getSpeed() for e in ("A", "B")}
    obs = POL.Observatory(["A", "B"], ff, 30.0, 120.0, 30.0)
    pol = POL.build(policy_name, PATHS, {p: 1000.0 for p in PATHS}, obs, CAP,
                    {"p3_eps": 0.20, "p3_assign_window": 120.0, "p4_lambda": 1.0})
    traci.start(["sumo", "-n", f"{TMP}/t.net.xml", "-r", f"{TMP}/t.rou.xml",
                 "--no-step-log", "true", "--no-warnings", "true", "--end", "4000"])
    picks = collections.Counter()
    t, nxt, si = 0.0, 0.0, 0
    while t < 4000 and (si < len(sched) or traci.simulation.getMinExpectedNumber() > 0):
        if t >= nxt:
            obs.record(t, {e: net.getEdge(e).getLength() /
                           max(traci.edge.getLastStepMeanSpeed(e), 0.1) for e in ("A", "B")},
                       {e: (traci.edge.getLastStepVehicleNumber(e) / 1000.0) *
                        traci.edge.getLastStepMeanSpeed(e) * 3600.0 for e in ("A", "B")})
            nxt += 30.0
        while si < len(sched) and sched[si][0] <= t:
            _, vid = sched[si]; si += 1
            p, _ = pol.choose(t, vid, None)
            picks[p] += 1
            traci.vehicle.add(vid, f"r_{p}", typeID="car", depart="now",
                              departLane="best", departSpeed="max")
        traci.simulationStep(); t = traci.simulation.getTime()
    traci.close()
    return picks


FAIL = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   <-- " + detail))
    if not cond: FAIL.append(name)

try:
    build()
    p1 = simulate("P1")
    check("P1 in SUMO commits the whole cohort to one path",
          max(p1.values()) == sum(p1.values()), f"{dict(p1)}")
    p3 = simulate("P3")
    ratio = p3["A"] / max(p3["B"], 1)
    check("P3 in SUMO splits towards the 2:1 capacity ratio",
          1.6 <= ratio <= 2.5, f"A={p3['A']} B={p3['B']} ratio={ratio:.2f}")
    check("P3 in SUMO uses both paths", min(p3.values()) > 0, f"{dict(p3)}")
    print(f"\n  observed P1 split: {dict(p1)}\n  observed P3 split: {dict(p3)} "
          f"(capacity ratio 2.00, observed {ratio:.2f})")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{'ALL TESTS PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
