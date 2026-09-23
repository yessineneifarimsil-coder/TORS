"""Shared definitions for the final analysis. Single source of every number.

Frozen decision protocol (unchanged from the completed study):
  portfolio        SP, DTT, TECO10          (ECO excluded by the route-order gate)
  criteria         mean journey time, mean tailpipe CO2   (equal weights)
  normalisation    fixed additive references = grand mean over 24 contexts x 3 policies
  unit of analysis context (3 paired seeds averaged after run-level aggregation)
Everything else in this module is derived from analysis/runs.csv and nothing else.
"""
import csv, math, statistics as st
from collections import defaultdict
import numpy as np
from sklearn.tree import DecisionTreeRegressor

CSV = "/home/user/TORS/routing_regime_study/analysis/runs.csv"
POL = ["SP", "DTT", "TECO10"]          # decision portfolio
ALLP = ["SP", "DTT", "ECO", "TECO05", "TECO10", "TECO15"]
RES = ["None", "U", "C", "L"]
SEEDS = ("8101", "8102", "8103")
DEMANDS = (720, 1200, 1680)
REGIME = {720: "low", 1200: "transition", 1680: "high"}

def load():
    R = []
    for r in csv.DictReader(open(CSV)):
        d = dict(r)
        for k in ("time", "co2", "dist", "p95", "ins", "bg_t", "bg_co2",
                  "net_co2", "stopped", "dflt", "n"):
            d[k] = float(r[k])
        d["demand"] = int(r["demand"])
        d["innet"] = d["time"] - d["ins"]                 # measurement-boundary variant
        d["stop_per_veh"] = d["stopped"] / d["n"]
        d["speed"] = (d["dist"] / 1000.0) / (d["innet"] / 3600.0)
        d["co2_per_km"] = d["co2"] / (d["dist"] / 1000.0)
        R.append(d)
    return R

R = load()
META = {x["ctx"]: (x["demand"], x["restr"], x["signal"]) for x in R}
CTXS = sorted(META)

def ctx_means(key, pols=POL, seeds=SEEDS, rows=R):
    """context -> policy -> mean of `key` over the given seeds."""
    g = defaultdict(lambda: defaultdict(list))
    for x in rows:
        if x["policy"] in pols and x["seed"] in seeds:
            g[x["ctx"]][x["policy"]].append(x[key])
    return {c: {p: st.mean(v) for p, v in d.items()} for c, d in g.items()}

def seed_means(key, pols=POL, rows=R):
    """seed -> context -> policy -> value (one run per cell)."""
    out = defaultdict(lambda: defaultdict(dict))
    for x in rows:
        if x["policy"] in pols:
            out[x["seed"]][x["ctx"]][x["policy"]] = x[key]
    return out

def scalarise(T, C, ctxs, w=0.5, aT=None, aC=None):
    """Fixed-reference additive cost. References default to the grand mean of `ctxs`."""
    if aT is None:
        aT = st.mean(T[c][p] for c in ctxs for p in POL)
    if aC is None:
        aC = st.mean(C[c][p] for c in ctxs for p in POL)
    cost = {c: {p: w * T[c][p] / aT + (1 - w) * C[c][p] / aC for p in POL} for c in ctxs}
    return cost, aT, aC

def regret_stats(cost, choice, ctxs):
    hb = {c: min(cost[c].values()) for c in ctxs}
    reg = [cost[c][choice[c]] - hb[c] for c in ctxs]
    return dict(mean=st.mean(reg), max=max(reg), median=st.median(reg),
                zero=sum(1 for c in ctxs if cost[c][choice[c]] - hb[c] < 1e-12),
                near=sum(1 for c in ctxs if cost[c][choice[c]] <= hb[c] * 1.01),
                per_ctx={c: cost[c][choice[c]] - hb[c] for c in ctxs})

def feats(c, use=("demand", "restr", "signal")):
    d, r, s = META[c]
    f = []
    if "demand" in use:
        f.append(d / 1000.0)
    if "restr" in use:
        f += [1.0 if r == k else 0.0 for k in RES]
    if "signal" in use:
        f.append(1.0 if s == "Balanced" else 0.0)
    return f

def fit_select(T, C, train, test, depth=3, leaf=2, w=0.5, use=("demand", "restr", "signal")):
    """Refit scales + tree on `train`, return the chosen policy for each context in `test`."""
    aT = st.mean(T[c][p] for c in train for p in POL)
    aC = st.mean(C[c][p] for c in train for p in POL)
    X = np.array([feats(c, use) for c in train])
    Y = np.array([[T[c][p] / aT for p in POL] + [C[c][p] / aC for p in POL] for c in train])
    m = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=0).fit(X, Y)
    out = {}
    for c in test:
        yp = m.predict(np.array([feats(c, use)]))[0]
        k = [w * yp[i] + (1 - w) * yp[i + len(POL)] for i in range(len(POL))]
        out[c] = POL[int(np.argmin(k))]
    return out, m

def loco_folds(ctxs):
    return [([c for c in ctxs if c != t], [t]) for t in ctxs]
