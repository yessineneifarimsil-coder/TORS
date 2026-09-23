"""
Deterministic demand generation.

Common random numbers: the vehicle set of a context is a function of
(demand, penetration, seed) ONLY.  It does not depend on which policy is being
evaluated.  Two runs of the same context with different policies therefore face
the identical vehicles, identical intended departure times, identical guided /
unguided labelling and identical background traffic, so their difference is
attributable to routing and to nothing else.

Unguided main-corridor drivers are not re-routed by anything.  They follow a
habitual corridor drawn once from a frozen multinomial logit over free-flow
path times, with scale THETA fixed before any run.  This is what makes
penetration a meaningful factor: at penetration p, a fraction 1-p of the
corridor demand is inert with respect to the policy under test.
"""
import math, random

THETA = 0.02          # logit scale, 1/s -- FROZEN
PATHS = {
    "C": ["w_d", "c0", "c1", "c2", "c3", "c4", "m_e"],
    "N": ["w_d", "n0", "n1", "n2", "n3", "n4", "m_e"],
    "S": ["w_d", "s0", "s1", "s2", "m_e"],
}
FF = {"C": 324.0, "N": 399.8, "S": 393.3}      # free-flow path time, s


def habitual_shares():
    u = {p: math.exp(-THETA * FF[p]) for p in PATHS}
    z = sum(u.values())
    return {p: u[p] / z for p in PATHS}


def _arrivals(rng, rate_vph, t0, t1):
    """Exponential inter-arrival renewal process on [t0, t1)."""
    if rate_vph <= 0:
        return []
    out, t, mean_gap = [], t0, 3600.0 / rate_vph
    while True:
        t += rng.expovariate(1.0 / mean_gap)
        if t >= t1:
            return out
        out.append(t)


def generate(path_out, demand_vph, penetration, seed, bg_vph, t_demand,
             cross_pairs=((1, 2, 3, 4))):
    rng = random.Random(seed)
    shares = habitual_shares()
    names = sorted(PATHS)
    cum, acc = [], 0.0
    for n in names:
        acc += shares[n]
        cum.append((acc, n))

    veh = []
    # main corridor demand
    for t in _arrivals(rng, demand_vph, 0.0, t_demand):
        u_guide, u_hab = rng.random(), rng.random()
        guided = u_guide < penetration
        hab = next(n for c, n in cum if u_hab <= c)
        veh.append((t, "g" if guided else "h", hab))
    # background cross-street demand, both directions, four streets
    bg = []
    for i in cross_pairs:
        for d in ("n", "s"):
            for t in _arrivals(rng, bg_vph, 0.0, t_demand):
                bg.append((t, f"x{d}{i}"))

    veh.sort(key=lambda r: r[0])
    bg.sort(key=lambda r: r[0])
    # Main-corridor vehicles are NOT written to the route file.  They are injected
    # through TraCI at their scheduled departure time with the route the policy has
    # already chosen, so the routing decision precedes insertion and the vehicle is
    # placed in a lane appropriate to the corridor it will actually use.  Assigning
    # a route after departure would make lane position, and therefore the cost of
    # reaching an alternative corridor, depend on the order of events rather than on
    # the policy.
    schedule = [(t, f"{kind}_{k}", hab) for k, (t, kind, hab) in enumerate(veh)]

    with open(path_out, "w") as f:
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n')
        f.write('  <vType id="car" vClass="passenger" emissionClass="HBEFA3/PC_G_EU4" '
                'accel="2.6" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" '
                'maxSpeed="27.78" tau="1.0"/>\n')
        for p in names:
            f.write(f'  <route id="r_{p}" edges="{" ".join(PATHS[p])}"/>\n')
        for i in cross_pairs:
            f.write(f'  <route id="r_xn{i}" edges="xn{i}a xn{i}b xn{i}c"/>\n')
            f.write(f'  <route id="r_xs{i}" edges="xs{i}a xs{i}b xs{i}c"/>\n')
        for k, (t, stem) in enumerate(bg):
            f.write(f'  <vehicle id="b_{k}" type="car" route="r_{stem}" '
                    f'depart="{t:.2f}" departLane="best" departSpeed="max"/>\n')
        f.write('</routes>\n')

    return {"n_main": len(veh), "n_bg": len(bg), "schedule": schedule,
            "shares": shares}
