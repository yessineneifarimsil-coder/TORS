"""
The four routing policies.

All four choose, for one vehicle at its moment of insertion, one element of a
finite candidate path catalogue.  For the main origin-destination pair of the
AGB network the catalogue is not an approximation: because every junction
permits straight-through movements only, the set of loopless paths from the
origin portal to the destination portal is exactly {C, N, S}.  There is
therefore no k-shortest-path generation heuristic to justify, and no path is
omitted.

Information available to a policy at time t
------------------------------------------
Every policy that uses traffic state reads it from one shared observation
buffer.  The buffer stores, for each sample instant t_k (every T_SAMPLE
seconds), the instantaneous travel time of every corridor edge.  A policy
acting at time t may read only samples with t_k <= t - LAG, and only the most
recent WINDOW seconds of those.  Before any admissible sample exists the
policy falls back to free-flow travel times.  This is the only channel through
which traffic state reaches a routing decision; no policy sees the future, and
no policy sees any realised outcome of the run it is part of.
"""
import math
from collections import deque, defaultdict

FREE_FLOW = "free-flow fallback"


class Observatory:
    """Lagged, windowed observation of edge travel times."""

    def __init__(self, edges, ff_tt, lag, window, sample_dt):
        self.edges = list(edges)
        self.ff = dict(ff_tt)                 # edge -> free-flow travel time (s)
        self.lag, self.window, self.dt = lag, window, sample_dt
        self.buf = deque()                    # (t, {edge: tt})
        self.flow = deque()                   # (t, {edge: veh/h})

    def record(self, t, tt_map, flow_map):
        self.buf.append((t, dict(tt_map)))
        self.flow.append((t, dict(flow_map)))
        cutoff = t - (self.lag + self.window) - 2 * self.dt
        while self.buf and self.buf[0][0] < cutoff:
            self.buf.popleft()
        while self.flow and self.flow[0][0] < cutoff:
            self.flow.popleft()

    def _visible(self, t, buf):
        hi, lo = t - self.lag, t - self.lag - self.window
        return [m for (tk, m) in buf if lo <= tk <= hi]

    def path_series(self, t, paths):
        """Per-path travel-time series over the visible window.

        Summing edge travel times *within* each sample instant preserves the
        correlation between edges of the same path, so the dispersion used by
        the reliability-aware policy is a property of the path, not a sum of
        independent edge variances."""
        vis = self._visible(t, self.buf)
        out = {}
        for name, edges in paths.items():
            if not vis:
                out[name] = [sum(self.ff[e] for e in edges)]
            else:
                out[name] = [sum(m.get(e, self.ff[e]) for e in edges) for m in vis]
        return out, bool(vis)

    def edge_flow(self, t):
        vis = self._visible(t, self.flow)
        if not vis:
            return {e: 0.0 for e in self.edges}
        return {e: sum(m.get(e, 0.0) for m in vis) / len(vis) for e in self.edges}


def _mean(x):
    return sum(x) / len(x)


def _sd(x):
    if len(x) < 2:
        return 0.0
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


class Policy:
    name = "base"

    def choose(self, t, vid, ctx):
        raise NotImplementedError


class P1Static(Policy):
    """Minimise path distance.  Uses no traffic state at all: the zero-
    information reference.  Tie-break: shortest free-flow time, then the
    lexicographically first path name."""
    name = "P1"

    def __init__(self, paths, lengths):
        self.paths, self.len = paths, lengths
        self.fixed = min(sorted(paths), key=lambda p: self.len[p])

    def choose(self, t, vid, ctx):
        return self.fixed, {}


class P2Reactive(Policy):
    """Minimise the mean observed path travel time over the visible window.

    Reactive, not predictive: it extrapolates nothing.  The estimate it acts on
    is LAG seconds old, which is the mechanism by which a large guided cohort
    can be sent, together, to a corridor that was best one lag ago."""
    name = "P2"

    def __init__(self, paths, obs):
        self.paths, self.obs = paths, obs

    def choose(self, t, vid, ctx):
        series, seen = self.obs.path_series(t, self.paths)
        mu = {p: _mean(s) for p, s in series.items()}
        best = min(sorted(self.paths), key=lambda p: (mu[p],))
        return best, {"mu": mu, "informed": seen}


class P3LoadBalance(Policy):
    """Capacity-aware load balancing over travel-time-admissible paths.

    Follows the flow-balanced k-shortest-path family: restrict to paths whose
    estimated travel time is within a declared tolerance of the best, then send
    the vehicle to whichever of those loads its most-utilised link least.

    Link utilisation combines what the policy can measure (lagged flow) with
    what it already knows it has caused (its own recent assignments that have
    not yet cleared the link).  Both are available at decision time."""
    name = "P3"

    def __init__(self, paths, obs, capacity, eps, assign_window):
        self.paths, self.obs, self.cap = paths, obs, capacity
        if not (1.0 <= assign_window <= 3600.0):
            raise ValueError(
                "assign_window must lie in [1, 3600] s: it converts a count of "
                "recent assignments into a rate, and degenerates outside that range")
        self.eps, self.aw = eps, assign_window
        self.assigned = deque()               # (t, path)

    def _own_rate(self, t):
        while self.assigned and self.assigned[0][0] < t - self.aw:
            self.assigned.popleft()
        per = defaultdict(float)
        scale = 3600.0 / max(self.aw, 1.0)
        for _, p in self.assigned:
            for e in self.paths[p]:
                per[e] += scale
        return per

    def choose(self, t, vid, ctx):
        series, seen = self.obs.path_series(t, self.paths)
        mu = {p: _mean(s) for p, s in series.items()}
        best = min(mu.values())
        adm = sorted([p for p in self.paths if mu[p] <= (1.0 + self.eps) * best])
        if not adm:
            adm = sorted(self.paths)
        meas, own = self.obs.edge_flow(t), self._own_rate(t)
        util = {}
        for p in adm:
            util[p] = max((meas.get(e, 0.0) + own.get(e, 0.0)) / self.cap[e]
                          for e in self.paths[p] if self.cap.get(e, 0) > 0)
        pick = min(adm, key=lambda p: (round(util[p], 6), round(mu[p], 6), p))
        self.assigned.append((t, pick))
        return pick, {"admissible": adm, "util": util, "informed": seen}


class P4Reliability(Policy):
    """Minimise mu_p + lambda * sigma_p over the visible window.

    sigma_p is the dispersion of the *path* travel time across sample instants
    in the window, so it is an observed quantity and not a modelled one.  It is
    computed only from samples already visible at decision time."""
    name = "P4"

    def __init__(self, paths, obs, lam):
        self.paths, self.obs, self.lam = paths, obs, lam

    def choose(self, t, vid, ctx):
        series, seen = self.obs.path_series(t, self.paths)
        sc = {p: _mean(s) + self.lam * _sd(s) for p, s in series.items()}
        best = min(sorted(self.paths), key=lambda p: (sc[p],))
        return best, {"score": sc, "informed": seen}


def build(name, paths, lengths, obs, capacity, params):
    if name == "P1":
        return P1Static(paths, lengths)
    if name == "P2":
        return P2Reactive(paths, obs)
    if name == "P3":
        return P3LoadBalance(paths, obs, capacity, params["p3_eps"],
                             params["p3_assign_window"])
    if name == "P4":
        return P4Reliability(paths, obs, params["p4_lambda"])
    raise ValueError(name)
