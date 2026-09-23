"""Shared analysis primitives.  Every number reported anywhere comes through here."""
import json, math, os
import numpy as np
import pandas as pd

FACTORS = ["demand", "gc", "penetration", "lag", "incident", "alt"]
POLICIES = ["P1", "P2", "P3", "P4"]
CRIT = {"C1": "C1_sys", "C2": "C2_sys", "C3": "C3_sys"}
PRIMARY = "C1_sys"                      # frozen primary decision cost
SEED_RESOLUTION_K = 2.0                 # frozen: |mean d| > K * SE(d)
SAT = {"c": 1761.0, "n": 1596.0}
CAP_FREE, CYCLE, YELLOW = 1500.0, 90.0, 4.0
FF_C = 324.0                            # free-flow path time on the arterial, s


def load(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    bad = [r for r in rows if "_error" in r]
    rows = [r for r in rows if "_error" not in r]
    df = pd.DataFrame(rows)
    df["ctx_key"] = [ctx_key(r) for _, r in df[FACTORS].iterrows()]
    return df, bad


def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")


def eff_green(gc):
    return (gc * CYCLE - YELLOW) / CYCLE


def capacities(gc, alt):
    g = eff_green(gc)
    return {"C": 2 * SAT["c"] * g, "N": alt * SAT["n"] * g, "S": CAP_FREE}


def descriptors(row):
    """The eight frozen mechanistic descriptors.  Functions of the context only;
    none of them can be computed from an outcome."""
    cap = capacities(row["gc"], row["alt"])
    tot = sum(cap.values())
    D, p = row["demand"], row["penetration"]
    return {
        "x1_net_sat": D / tot,
        "x2_short_sat": D / cap["C"],
        "x3_alt_share": cap["N"] / tot,
        "x4_eff_green": eff_green(row["gc"]),
        "x5_penetration": p,
        "x6_staleness": row["lag"] / FF_C,
        "x7_incident": float(row["incident"]),
        "x8_ctrl_sat": p * D / cap["C"],
    }
XCOLS = ["x1_net_sat", "x2_short_sat", "x3_alt_share", "x4_eff_green",
         "x5_penetration", "x6_staleness", "x7_incident", "x8_ctrl_sat"]


def context_table(df, crit=PRIMARY):
    """One row per (context, policy): seed mean, seed sd, and the seed vector.
    The seed vector is kept because every comparison in this study is paired."""
    out = []
    for (ck, pol), g in df.groupby(["ctx_key", "policy"]):
        g = g.sort_values("seed")
        rec = {"ctx_key": ck, "policy": pol, "n_seeds": len(g)}
        for f in FACTORS:
            rec[f] = g[f].iloc[0]
        for name, col in CRIT.items():
            rec[name] = g[col].mean()
            rec[name + "_sd"] = g[col].std(ddof=1) if len(g) > 1 else 0.0
        rec["seeds"] = list(g["seed"])
        rec["vec"] = list(g[crit])
        for extra in ("completion", "teleports", "picks_C", "picks_N", "picks_S",
                      "C1_corr", "C1_guided", "C3_guided", "throughput"):
            if extra in g:
                rec[extra] = g[extra].mean()
        rec.update(descriptors(rec))
        out.append(rec)
    return pd.DataFrame(out)


def paired_resolved(vec_a, vec_b, k=SEED_RESOLUTION_K):
    """Frozen resolution test on paired seed differences."""
    d = np.asarray(vec_a, float) - np.asarray(vec_b, float)
    if len(d) < 2:
        return False, float(d.mean()) if len(d) else 0.0, float("inf")
    se = d.std(ddof=1) / math.sqrt(len(d))
    return bool(abs(d.mean()) > k * se), float(d.mean()), float(se)


def winners(ct):
    """Per context: best policy on the primary cost, whether that win is
    resolved against the runner-up, and the full ranking."""
    rows = []
    for ck, g in ct.groupby("ctx_key"):
        g = g.set_index("policy")
        order = g["C1"].sort_values().index.tolist()
        if len(order) < 2:
            continue
        best, second = order[0], order[1]
        res, diff, se = paired_resolved(g.loc[second, "vec"], g.loc[best, "vec"])
        rec = {"ctx_key": ck, "winner": best, "runner_up": second,
               "margin": g.loc[second, "C1"] - g.loc[best, "C1"],
               "resolved": res, "margin_se": se, "order": order}
        for f in FACTORS:
            rec[f] = g[f].iloc[0]
        for p in POLICIES:
            if p in g.index:
                rec["C1_" + p] = g.loc[p, "C1"]
        rows.append(rec)
    return pd.DataFrame(rows)


def pareto_front(points):
    """Indices of non-dominated rows (all criteria minimised)."""
    P = np.asarray(points, float)
    keep = []
    for i in range(len(P)):
        dominated = False
        for j in range(len(P)):
            if i == j:
                continue
            if np.all(P[j] <= P[i]) and np.any(P[j] < P[i]):
                dominated = True
                break
        if not dominated:
            keep.append(i)
    return keep


def pareto_by_context(ct):
    rows = []
    for ck, g in ct.groupby("ctx_key"):
        g = g.reset_index(drop=True)
        idx = pareto_front(g[["C1", "C2", "C3"]].values)
        rows.append({"ctx_key": ck, "pareto": sorted(g.loc[idx, "policy"]),
                     "n_pareto": len(idx)})
    return pd.DataFrame(rows)


def regret_table(ct, crit="C1"):
    """R(s,a) = C(s,a) - min_b C(s,b), in the physical unit of the criterion."""
    out = []
    for ck, g in ct.groupby("ctx_key"):
        best = g[crit].min()
        for _, r in g.iterrows():
            out.append({"ctx_key": ck, "policy": r["policy"],
                        "regret": r[crit] - best, crit: r[crit]})
    return pd.DataFrame(out)


def fmt_pct(x):
    return f"{100*x:.1f}%"
