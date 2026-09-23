"""
Build the AGB (Arterial-Grid-Bypass) scenario network.

Design rationale (frozen before any evaluation run):

The network must let four routing policies fail for *different* physical
reasons.  It therefore provides one origin-destination pair served by three
structurally different corridors between a common diverge (D) and a common
merge (M), crossed by four minor streets that carry independent background
demand through the same signals.

  C  central arterial : SHORTEST in distance, 2 lanes, 50 km/h, 4 signals.
                        Lowest free-flow cost, lowest capacity per unit demand.
  N  north street     : longer AND slower (40 km/h), n_alt lanes, 4 signals.
                        Only worth using once C is congested.
  S  south bypass     : longest, 1 lane, 50 km/h, NO signals.
                        Free-flow cost between C and N, unaffected by signal
                        timing, capacity-limited by its single lane.

Consequences that make the policies separable in principle:
  * a distance-minimising policy always loads C, so it must fail once C
    saturates;
  * a travel-time-minimising policy moves the whole guided cohort together,
    so with lag and high penetration it can overshoot onto whichever corridor
    was best one lag ago;
  * a load-balancing policy can only help if capacity is unevenly split, which
    is what n_alt controls;
  * a reliability-aware policy can only help if some corridor has high
    travel-time variance, which is what the incident provides.

None of this is assumed to occur.  Whether it occurs is measured in Phase D.
"""
import os, subprocess, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUMO_HOME = os.environ.get("SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")

# ----------------------------------------------------------------- geometry
KMH = 1000.0 / 3600.0
V_ACCESS, V_ART, V_NORTH, V_BYPASS, V_CROSS = 60*KMH, 50*KMH, 40*KMH, 50*KMH, 40*KMH
XS = [600, 1200, 1800, 2400]          # signal columns
Y_N, Y_XN, Y_XS = 400, 900, -600      # north corridor, north portal, south portal
Y_S = -900                            # bypass

NODES = [("W", -900, 0, "priority"), ("D", 0, 0, "priority"),
         ("M", 3000, 0, "priority"), ("E", 3900, 0, "priority"),
         ("S1", 600, Y_S, "priority"), ("S2", 2400, Y_S, "priority")]
for i, x in enumerate(XS, 1):
    NODES += [(f"J{i}", x, 0, "traffic_light"), (f"N{i}", x, Y_N, "traffic_light"),
              (f"XN{i}", x, Y_XN, "priority"), (f"XS{i}", x, Y_XS, "priority")]

def dist(a, b):
    pa = {n[0]: (n[1], n[2]) for n in NODES}[a]
    pb = {n[0]: (n[1], n[2]) for n in NODES}[b]
    return math.hypot(pb[0]-pa[0], pb[1]-pa[1])

def build(n_alt, out):
    """n_alt = lanes on the north corridor (the alternative-capacity factor)."""
    E = []   # (id, from, to, lanes, speed, type)
    E.append(("w_d", "W", "D", 3, V_ACCESS, "access"))
    # 5 lanes with one dedicated lane per approach: the merge is conflict-free by
    # construction.  This is deliberate.  At an ordinary priority merge the minor
    # approaches must yield to the major stream, so an alternative corridor would
    # be penalised by junction priority rather than by its own capacity, and every
    # policy that uses an alternative would be charged for an artefact of the
    # destination node.  The portal represents a distributed destination zone, not
    # a single intersection, so removing the conflict is also the faithful model.
    E.append(("m_e", "M", "E", 5, V_ACCESS, "access"))
    # central arterial, eastbound only
    chain = ["D"] + [f"J{i}" for i in (1,2,3,4)] + ["M"]
    for k in range(5):
        E.append((f"c{k}", chain[k], chain[k+1], 2, V_ART, "arterial"))
    # north corridor, eastbound only
    chain = ["D"] + [f"N{i}" for i in (1,2,3,4)] + ["M"]
    for k in range(5):
        E.append((f"n{k}", chain[k], chain[k+1], n_alt, V_NORTH, "north"))
    # south bypass, eastbound only, unsignalised
    for k, (a, b) in enumerate([("D","S1"), ("S1","S2"), ("S2","M")]):
        E.append((f"s{k}", a, b, 1, V_BYPASS, "bypass"))
    # four two-way cross streets
    for i in (1,2,3,4):
        E.append((f"xn{i}a", f"XN{i}", f"N{i}", 1, V_CROSS, "cross"))
        E.append((f"xn{i}b", f"N{i}",  f"J{i}", 1, V_CROSS, "cross"))
        E.append((f"xn{i}c", f"J{i}",  f"XS{i}", 1, V_CROSS, "cross"))
        E.append((f"xs{i}a", f"XS{i}", f"J{i}", 1, V_CROSS, "cross"))
        E.append((f"xs{i}b", f"J{i}",  f"N{i}", 1, V_CROSS, "cross"))
        E.append((f"xs{i}c", f"N{i}",  f"XN{i}", 1, V_CROSS, "cross"))

    # explicit connections: straight-through only, so every signal is 2-phase
    C = [("w_d","c0"), ("w_d","n0"), ("w_d","s0"),
         ("s0","s1"), ("s1","s2")]
    # dedicated exit lanes: c4 -> 0,1 | n4 -> 2(,3) | s2 -> 4
    LC = [("c4","m_e",0,0), ("c4","m_e",1,1), ("s2","m_e",0,4), ("n4","m_e",0,2)]
    if n_alt == 2:
        LC.append(("n4","m_e",1,3))
    for k in range(4):
        C += [(f"c{k}", f"c{k+1}"), (f"n{k}", f"n{k+1}")]
    for i in (1,2,3,4):
        C += [(f"xn{i}a", f"xn{i}b"), (f"xn{i}b", f"xn{i}c"),
              (f"xs{i}a", f"xs{i}b"), (f"xs{i}b", f"xs{i}c")]

    nod = os.path.join(out, "agb.nod.xml"); edg = os.path.join(out, "agb.edg.xml")
    con = os.path.join(out, "agb.con.xml")
    with open(nod, "w") as f:
        f.write('<nodes>\n')
        for n, x, y, t in NODES:
            f.write(f'  <node id="{n}" x="{x}" y="{y}" type="{t}"/>\n')
        f.write('</nodes>\n')
    with open(edg, "w") as f:
        f.write('<edges>\n')
        for eid, a, b, lanes, spd, ty in E:
            f.write(f'  <edge id="{eid}" from="{a}" to="{b}" numLanes="{lanes}" '
                    f'speed="{spd:.4f}" type="{ty}" length="{dist(a,b):.2f}"/>\n')
        f.write('</edges>\n')
    with open(con, "w") as f:
        f.write('<connections>\n')
        for a, b in C:
            f.write(f'  <connection from="{a}" to="{b}"/>\n')
        for a, b, fl, tl in LC:
            f.write(f'  <connection from="{a}" to="{b}" fromLane="{fl}" toLane="{tl}"/>\n')
        f.write('</connections>\n')

    net = os.path.join(out, f"agb_alt{n_alt}.net.xml")
    cmd = ["netconvert", "-n", nod, "-e", edg, "-x", con, "-o", net,
           "--no-turnarounds", "true", "--tls.default-type", "static",
           "--tls.cycle.time", "90", "--tls.yellow.time", "4",
           "--junctions.corner-detail", "5", "--offset.disable-normalization", "true",
           # The only turning movements in this network are the corridor diverge at
           # D and the corridor merge at M; every other movement is straight through.
           # Those two nodes stand for a distributed origin and destination zone and
           # are drawn as straight lines between schematic node coordinates, which
           # understates the design radius of the real ramp.  Applying a turn-radius
           # speed limit to them would impose a capacity ceiling that belongs to the
           # drawing rather than to the corridor, so it is disabled.  Verified in
           # tests/test_capacity.py: with it disabled, each corridor's measured
           # discharge is set by its own lanes and green time.
           "--junctions.limit-turn-speed", "-1",
           "--no-internal-links", "false"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); print(r.stderr); sys.exit(1)
    warn = [l for l in r.stderr.splitlines() if "Warning" in l]
    print(f"built {os.path.basename(net)}  edges={len(E)} nodes={len(NODES)} "
          f"connections={len(C)+len(LC)} warnings={len(warn)}")
    for w in warn[:6]:
        print("   ", w)
    return net

if __name__ == "__main__":
    os.environ.setdefault("SUMO_HOME", SUMO_HOME)
    for n_alt in (1, 2):
        build(n_alt, HERE)
