"""
One simulation run = one (context, policy, seed) triple.

The run is fully determined by its arguments.  Nothing is read from a previous
run, and nothing about the outcome of this run is visible to the policy while
it is being made.
"""
import os, sys, json, math, argparse, tempfile, shutil, subprocess
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "policies"))
os.environ.setdefault("SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")
import random                                           # noqa: E402
import traci, sumolib                                   # noqa: E402
import policies as POL                                  # noqa: E402
import demand as DEM                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.abspath(os.path.join(HERE, "..", "scenario"))

CYCLE, YELLOW = 90.0, 4.0
# Capacity model, MEASURED in tests/test_capacity.py rather than assumed.
# Queue-discharge saturation flow differs between the two signalised corridors
# because their speed limits differ; the uninterrupted bypass is governed by
# free-flow headways, which are longer than queue-discharge headways.
SAT_FLOW = {"c": 1761.0, "n": 1596.0}     # veh/h/lane, signalised discharge
CAP_FREE = 1500.0                          # veh/h/lane, uninterrupted
T_SAMPLE = 30.0                   # observation sampling interval, s
T_DEMAND = 1800.0                 # demand period, s
WARMUP, MEAS_END = 300.0, 1500.0  # measured cohort = intended departures in [300,1500)
T_MAX = 7200.0
CORRIDOR = {"C": ["c0", "c1", "c2", "c3", "c4"],
            "N": ["n0", "n1", "n2", "n3", "n4"],
            "S": ["s0", "s1", "s2"]}
ALL_CORR = [e for v in CORRIDOR.values() for e in v]


def is_corridor_lane(lane):
    e = lane.rsplit("_", 1)[0]
    return e in ALL_CORR


def set_signals(gc):
    """Impose the target green ratio on the eight signalised junctions.

    gc is the share of the cycle given to the through-corridor movement
    (arterial or north street); the cross street receives the remainder.  The
    cycle length and the 4 s yellow interval are held fixed, so gc changes the
    split of capacity between corridor and cross traffic and nothing else."""
    g_major = gc * CYCLE - YELLOW
    g_minor = CYCLE - 2 * YELLOW - g_major
    assert g_major > 5 and g_minor > 5, (g_major, g_minor)
    for tls in traci.trafficlight.getIDList():
        links = traci.trafficlight.getControlledLinks(tls)
        major = {i for i, l in enumerate(links) if l and is_corridor_lane(l[0][0])}
        logic = traci.trafficlight.getAllProgramLogics(tls)[0]
        for ph in logic.phases:
            st = ph.state
            has_major_green = any(st[i] in "Gg" for i in major)
            has_any_green = any(c in "Gg" for c in st)
            if "y" in st or "Y" in st:
                ph.duration = ph.minDur = ph.maxDur = YELLOW
            elif has_any_green:
                d = g_major if has_major_green else g_minor
                ph.duration = ph.minDur = ph.maxDur = d
        traci.trafficlight.setProgramLogic(tls, logic)
    return g_major, g_minor


INC_EDGES = {"arterial": ["c1", "c2", "c3"], "bypass": ["s1"], "north": ["n1", "n2", "n3"]}
INC_START = (600.0, 1200.0)
INC_DURS = (300.0, 600.0, 900.0)


def draw_incident(a):
    """Draw one capacity-reducing incident.

    A reliability-aware routing policy responds to travel-time RISK.  An
    incident that occurs at an identical time and place in every replication of
    a context is not a risk; it is a known event, and a policy that merely
    tracks the mean handles it as well as one that models dispersion.  The
    incident is therefore drawn -- location, onset and duration -- from a
    declared distribution, using a stream seeded by the run seed alone.

    Two consequences, both required:
      * within a context and seed the realisation is IDENTICAL across the four
        policies, so the paired comparison is preserved exactly;
      * across the five seeds of a context the realisation differs, so the
        context carries genuine travel-time dispersion that no policy can know
        in advance.
    Nothing about the realisation is visible to any policy; policies observe
    only the lagged link travel times the incident happens to produce."""
    if not a.incident:
        return None
    rng = random.Random(int(a.seed) * 7919 + 13)
    fam = INC_EDGES.get(a.inc_family, INC_EDGES["arterial"])
    return {"edge": rng.choice(fam),
            "start": rng.uniform(*INC_START),
            "dur": rng.choice(INC_DURS),
            "done": False}


def eff_green(gc):
    """Effective green ratio: the green interval only, excluding the yellow."""
    return (gc * CYCLE - YELLOW) / CYCLE


def capacities(net, gc):
    """Per-edge capacity.  An edge's capacity is set by its downstream control:
    an edge discharging into a signal is limited by lanes x saturation flow x
    effective green; an edge discharging into a free node is limited by
    free-flow headways."""
    cap, g = {}, eff_green(gc)
    for e in ALL_CORR:
        edge = net.getEdge(e)
        n = edge.getLaneNumber()
        if edge.getToNode().getType() == "traffic_light":
            cap[e] = n * SAT_FLOW[e[0]] * g
        else:
            cap[e] = n * CAP_FREE
    return cap


def corridor_capacity(net, gc):
    """Capacity of each corridor = its most restrictive edge."""
    cap = capacities(net, gc)
    return {p: min(cap[e] for e in v) for p, v in CORRIDOR.items()}


def run(a):
    net = sumolib.net.readNet(os.path.join(SCEN, f"agb_alt{a.alt}.net.xml"))
    tmp = tempfile.mkdtemp(prefix="agbrun_")
    try:
        rou = os.path.join(tmp, "d.rou.xml")
        meta = DEM.generate(rou, a.demand, a.penetration, a.seed, a.bg, T_DEMAND)
        trip = os.path.join(tmp, "tripinfo.xml")
        cmd = ["sumo", "-n", os.path.join(SCEN, f"agb_alt{a.alt}.net.xml"),
               "-r", rou, "--tripinfo-output", trip,
               "--tripinfo-output.write-unfinished", "true",
               "--device.emissions.probability", "1.0",
               "--time-to-teleport", "900", "--no-step-log", "true",
               "--no-warnings", "true", "--seed", str(a.seed),
               "--step-length", "1.0", "--end", str(T_MAX),
               "--eager-insert", "true", "--default.carfollowmodel", "Krauss"]
        traci.start(cmd, label=f"r{os.getpid()}")
        g_major, g_minor = set_signals(a.gc)
        cap = capacities(net, a.gc)
        ff = {e: net.getEdge(e).getLength() / net.getEdge(e).getSpeed() for e in ALL_CORR}
        obs = POL.Observatory(ALL_CORR, ff, a.lag, a.window, T_SAMPLE)
        pol = POL.build(a.policy, CORRIDOR, {p: sum(ff[e] for e in v)
                                             for p, v in CORRIDOR.items()},
                        obs, cap, {"p3_eps": a.p3_eps,
                                   "p3_assign_window": a.p3_assign_window,
                                   "p4_lambda": a.p4_lambda})
        lengths = {p: sum(net.getEdge(e).getLength() for e in v)
                   for p, v in CORRIDOR.items()}
        pol_dist = POL.P1Static(CORRIDOR, lengths)          # for P1 tie-break check

        inc = draw_incident(a)
        inc_lane = f"{inc['edge']}_0" if inc else None
        if inc and net.getEdge(inc["edge"]).getLaneNumber() < 2:
            # Closing the only lane of a corridor does not reduce its capacity,
            # it disconnects it.  Refuse rather than produce vehicles with no
            # valid route.
            raise ValueError(
                f"incident edge {inc['edge']} has "
                f"{net.getEdge(inc['edge']).getLaneNumber()} lane(s); a "
                f"capacity-reducing lane closure requires at least 2")
        inc_on = False
        picks = {"C": 0, "N": 0, "S": 0}
        uninformed = 0
        sched, si = meta["schedule"], 0
        t, next_sample = 0.0, 0.0
        while t < T_MAX:
            if inc and not inc_on and inc["done"] is False and t >= inc["start"]:
                traci.lane.setDisallowed(inc_lane, ["all"]); inc_on = True
            if inc and inc_on and t >= inc["start"] + inc["dur"]:
                traci.lane.setAllowed(inc_lane, ["passenger"])
                inc_on = False; inc["done"] = True
            if t >= next_sample:
                tt, fl = {}, {}
                for e in ALL_CORR:
                    L = net.getEdge(e).getLength()
                    v = traci.edge.getLastStepMeanSpeed(e)
                    n = traci.edge.getLastStepVehicleNumber(e)
                    tt[e] = L / max(v, 0.1)
                    fl[e] = (n / L) * v * 3600.0
                obs.record(t, tt, fl)
                next_sample += T_SAMPLE
            while si < len(sched) and sched[si][0] <= t:
                _, vid, hab = sched[si]; si += 1
                if a.force:
                    p = a.force
                elif vid.startswith("g_"):
                    p, info = pol.choose(t, vid, None)
                    if info.get("informed") is False:
                        uninformed += 1
                else:
                    p = hab
                picks[p] += 1
                traci.vehicle.add(vid, f"r_{p}", typeID="car", depart="now",
                                  departLane="best", departSpeed="max")
            traci.simulationStep()
            t = traci.simulation.getTime()
            if (si >= len(sched)
                    and traci.simulation.getMinExpectedNumber() == 0
                    and t > T_DEMAND + 60):
                break
        tele = traci.simulation.getStartingTeleportNumber()
        traci.close()
        res = parse(trip, meta, a)
        res.update(dict(picks_C=picks["C"], picks_N=picks["N"], picks_S=picks["S"],
                        uninformed=uninformed, g_major=g_major, g_minor=g_minor,
                        sim_end=t, teleports=tele,
                        inc_realised_edge=(inc["edge"] if inc else ""),
                        inc_realised_start=(inc["start"] if inc else -1.0),
                        inc_realised_dur=(inc["dur"] if inc else -1.0),
                        dist_shortest=pol_dist.fixed,
                        **{f"cap_{p}": v for p, v in
                           corridor_capacity(net, a.gc).items()}))
        return res
    finally:
        try:
            traci.close()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def parse(trip, meta, a):
    root = ET.parse(trip).getroot()
    thr_lo, thr_hi = 600.0, 1500.0
    thr = 0
    sys_n = sys_jt = sys_co2 = sys_stop = sys_dur = 0.0
    g_n = g_jt = g_co2 = g_stop = 0.0
    c_n = c_jt = c_co2 = c_stop = 0.0
    arrived = 0
    for ti in root.findall("tripinfo"):
        vid = ti.get("id")
        depart = float(ti.get("depart")); dd = float(ti.get("departDelay"))
        intended = depart - dd
        if not (WARMUP <= intended < MEAS_END):
            continue
        dur = float(ti.get("duration"))
        arr = ti.get("arrival")
        if arr is None or float(arr) < 0:
            continue                      # never completed: counted via completion rate
        arrived += 1
        wait = float(ti.get("waitingTime"))
        em = ti.find("emissions")
        co2 = float(em.get("CO2_abs")) / 1e6 if em is not None else 0.0   # mg -> kg
        jt = dur + dd
        sys_n += 1; sys_jt += jt; sys_co2 += co2; sys_stop += wait; sys_dur += dur
        if not vid.startswith("b_"):
            c_n += 1; c_jt += jt; c_co2 += co2; c_stop += wait
        if vid.startswith("g_"):
            g_n += 1; g_jt += jt; g_co2 += co2; g_stop += wait
    for ti in root.findall("tripinfo"):
        arr = ti.get("arrival")
        if ti.get("id").startswith("b_") or arr is None:
            continue
        if thr_lo <= float(arr) < thr_hi:
            thr += 1
    # denominator: everything generated inside the measurement window
    gen = 0
    for ti in root.findall("tripinfo"):
        d = float(ti.get("depart")) - float(ti.get("departDelay"))
        if WARMUP <= d < MEAS_END:
            gen += 1
    return dict(
        throughput=thr * 3600.0 / (thr_hi - thr_lo),
        n_sys=int(sys_n), n_guided=int(g_n), n_generated=gen,
        completion=(arrived / gen) if gen else 0.0,
        C1_sys=sys_jt / sys_n if sys_n else float("nan"),
        C2_sys=sys_co2,
        C3_sys=sys_stop,
        innet_sys=sys_dur / sys_n if sys_n else float("nan"),
        C1_guided=g_jt / g_n if g_n else float("nan"),
        C2_guided=g_co2, C3_guided=g_stop,
        n_corr=int(c_n),
        C1_corr=c_jt / c_n if c_n else float("nan"),
        C2_corr=c_co2, C3_corr=c_stop,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--policy", required=True, choices=["P1", "P2", "P3", "P4"])
    p.add_argument("--demand", type=float, required=True)
    p.add_argument("--gc", type=float, default=0.50)
    p.add_argument("--penetration", type=float, default=0.50)
    p.add_argument("--lag", type=float, default=60.0)
    p.add_argument("--window", type=float, default=120.0)
    p.add_argument("--alt", type=int, default=1, choices=[1, 2])
    p.add_argument("--incident", type=int, default=0)
    p.add_argument("--inc-family", default="arterial",
                   choices=["arterial", "bypass", "north"])
    p.add_argument("--bg", type=float, default=300.0)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--p3-eps", type=float, default=0.20)
    p.add_argument("--p3-assign-window", type=float, default=120.0)
    p.add_argument("--p4-lambda", type=float, default=1.0)
    p.add_argument("--ctx", default="")
    p.add_argument("--force", default="", choices=["", "C", "N", "S"],
                   help="capacity calibration only: send every corridor vehicle "
                        "on the named path, overriding the policy")
    a = p.parse_args()
    r = run(a)
    r.update(vars(a))
    print(json.dumps(r))


if __name__ == "__main__":
    main()
