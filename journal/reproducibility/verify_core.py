"""Independent verification of the 648-context study.

Reads results/*.jsonl directly and rebuilds every load-bearing quantity with
code written here, then compares against results/results.json.  The frozen
protocol in analysis/policy_selectors.py is reused for the selector ladder,
because that protocol is part of the specification and must not be reinvented;
the matrices it is given are rebuilt here from the run records.
"""
import json, os, sys, math, collections, itertools, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "analysis"))
RES = os.path.join(ROOT, "results")

FACT = ["demand", "gc", "penetration", "lag", "incident", "alt"]
POL = ["P1", "P2", "P3", "P4"]
SAT_C, SAT_N, CAP_FREE, CYCLE, YELLOW, FF_C = 1761.0, 1596.0, 1500.0, 90.0, 4.0, 324.0
K_RES = 2.0

def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")

def eff_green(gc): return (gc * CYCLE - YELLOW) / CYCLE

def descriptors(m):
    g = eff_green(m["gc"])
    cap = {"C": 2 * SAT_C * g, "N": m["alt"] * SAT_N * g, "S": CAP_FREE}
    tot = sum(cap.values()); D, p = m["demand"], m["penetration"]
    return [D / tot, D / cap["C"], cap["N"] / tot, g, p, m["lag"] / FF_C,
            float(m["incident"]), p * D / cap["C"]]

def build(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    rows = [r for r in rows if "_error" not in r]
    cell = collections.defaultdict(list)
    for r in rows:
        cell[(ctx_key(r), r["policy"])].append(r)
    ctxs = sorted({k[0] for k in cell})
    C = {c: {} for c in ("C1", "C2", "C3")}; VEC = {}; META = {}
    for (ck, p), g in cell.items():
        g = sorted(g, key=lambda x: x["seed"])
        for c, col in (("C1", "C1_sys"), ("C2", "C2_sys"), ("C3", "C3_sys")):
            C[c][(ck, p)] = st.mean(x[col] for x in g)
        VEC[(ck, p)] = [x["C1_sys"] for x in g]
        META[ck] = {f: g[0][f] for f in FACT}
    return rows, ctxs, C, VEC, META

def resolved(a, b, k=K_RES):
    d = np.asarray(a, float) - np.asarray(b, float)
    se = d.std(ddof=1) / math.sqrt(len(d))
    return bool(abs(d.mean()) > k * se), float(d.mean()), float(se)

rows, ctxs, C, VEC, META = build(os.path.join(RES, "main.jsonl"))
R = json.load(open(os.path.join(RES, "results.json")))
n = len(ctxs)
OUT, CHECKS = {}, []

def chk(label, got, want, tol=1e-6):
    ok = (abs(got - want) <= tol) if isinstance(want, (int, float)) and not isinstance(want, bool) else got == want
    CHECKS.append((label, got, want, ok)); return ok

# ---------------------------------------------------------------- validity
comp = [r["completion"] for r in rows]; tel = sum(r.get("teleports", 0) for r in rows)
chk("n_runs", len(rows), R["campaign"]["n_runs"])
chk("n_contexts", n, R["campaign"]["n_contexts"])
chk("min_completion", min(comp), R["validity"]["min_completion"])
chk("total_teleports", tel, R["validity"]["total_teleports"])

# ---------------------------------------------------------------- ties
minv = {ck: min(C["C1"][(ck, p)] for p in POL) for ck in ctxs}
tied = {ck: [p for p in POL if C["C1"][(ck, p)] == minv[ck]] for ck in ctxs}
n_tied = sum(1 for ck in ctxs if len(tied[ck]) > 1)
OUT["ties"] = dict(n_contexts_with_tied_minimum=n_tied,
                   frac=n_tied / n,
                   composition={"+".join(v): sum(1 for c in ctxs if tied[c] == v)
                                for v in {tuple(tied[c]) for c in ctxs if len(tied[c]) > 1}
                                for v in [list(v)]})
# stable, declared tie-break: portfolio order
win = {ck: tied[ck][0] for ck in ctxs}
wc = collections.Counter(win.values())
OUT["winner_counts_stable_tiebreak"] = dict(wc)
OUT["winner_counts_unique_minimum_only"] = dict(
    collections.Counter(win[ck] for ck in ctxs if len(tied[ck]) == 1))
OUT["winner_counts_tie_inclusive"] = {p: sum(1 for ck in ctxs if p in tied[ck]) for p in POL}

# ---------------------------------------------------------------- resolved wins
rw = collections.Counter(); unres = 0; res_margin = []; unres_margin = []
for ck in ctxs:
    order = sorted(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p)))
    best, second = order[0], order[1]
    r, d, se = resolved(VEC[(ck, second)], VEC[(ck, best)])
    m = 100.0 * (C["C1"][(ck, second)] - C["C1"][(ck, best)]) / C["C1"][(ck, best)]
    if r: rw[best] += 1; res_margin.append(m)
    else: unres += 1; unres_margin.append(m)
OUT["resolved_wins"] = dict(rw); OUT["n_unresolved"] = unres
chk("resolved_P3", rw["P3"], R["G1_confirmatory"]["winner_counts_resolved"]["P3"])
chk("resolved_P4", rw["P4"], R["G1_confirmatory"]["winner_counts_resolved"]["P4"])
chk("resolved_P1", rw["P1"], R["G1_confirmatory"]["winner_counts_resolved"]["P1"])
chk("n_unresolved", unres, R["G1_confirmatory"]["n_unresolved"])
chk("resolved_margin_median", st.median(res_margin), R["G1_confirmatory"]["resolved_margin_pct_median"], 1e-9)
chk("unresolved_margin_median", st.median(unres_margin), R["G1_confirmatory"]["unresolved_margin_pct_median"], 1e-9)

# ---------------------------------------------------------------- headroom
mean_cost = {p: st.mean(C["C1"][(ck, p)] for ck in ctxs) for p in POL}
sbs = min(mean_cost, key=mean_cost.get)
vbs = st.mean(minv[ck] for ck in ctxs)
head = mean_cost[sbs] - vbs
OUT["headroom"] = dict(sbs=sbs, mean_cost=mean_cost, vbs=vbs, headroom_s=head,
                       headroom_pct_aggregate=100 * head / mean_cost[sbs],
                       headroom_pct_per_context=100 * st.mean(
                           (C["C1"][(ck, sbs)] - minv[ck]) / minv[ck] for ck in ctxs),
                       max_headroom_s=max(C["C1"][(ck, sbs)] - minv[ck] for ck in ctxs))
chk("sbs", sbs, R["headroom"]["global_sbs"])
chk("mean_cost_sbs", mean_cost[sbs], R["headroom"]["mean_cost_sbs_s"], 1e-9)
chk("mean_cost_vbs", vbs, R["headroom"]["mean_cost_vbs_s"], 1e-9)
chk("headroom_s", head, R["headroom"]["mean_headroom_s"], 1e-9)
chk("headroom_pct_per_context", OUT["headroom"]["headroom_pct_per_context"],
    R["headroom"]["mean_headroom_pct"], 1e-9)
chk("P1_penalty_s", mean_cost["P1"] - mean_cost[sbs], R["fixed_policy_choice"]["penalty_vs_sbs_s"]["P1"], 1e-8)
chk("P1_penalty_pct", 100 * (mean_cost["P1"] - mean_cost[sbs]) / mean_cost[sbs],
    R["fixed_policy_choice"]["penalty_vs_sbs_pct"]["P1"], 1e-8)

# ---------------------------------------------------------------- asymmetry
notbest = [ck for ck in ctxs if C["C1"][(ck, sbs)] > minv[ck]]
isbest = [ck for ck in ctxs if C["C1"][(ck, sbs)] == minv[ck]]
loss = st.mean(C["C1"][(ck, sbs)] - minv[ck] for ck in notbest)
marg = st.mean(sorted(C["C1"][(ck, p)] for p in POL)[1] - C["C1"][(ck, sbs)] for ck in isbest)
OUT["asymmetry"] = dict(n_sbs_not_best=len(notbest), frac_sbs_not_best=len(notbest) / n,
                        n_sbs_attains_min=len(isbest), frac_sbs_attains_min=len(isbest) / n,
                        mean_loss_when_not_best_s=loss, mean_margin_when_best_s=marg,
                        upside_downside_ratio=marg / loss)
chk("n_sbs_not_best", len(notbest), R["asymmetry"]["frac_contexts_sbs_not_best"] * n, 1e-6)
chk("mean_loss_when_not_best", loss, R["asymmetry"]["mean_loss_when_not_best_s"], 1e-9)

# ---------------------------------------------------------------- Pareto
def pf(P):
    P = np.asarray(P, float)
    return [i for i in range(len(P))
            if not any(np.all(P[j] <= P[i]) and np.any(P[j] < P[i])
                       for j in range(len(P)) if j != i)]
sizes = collections.Counter(); memb = collections.Counter()
for ck in ctxs:
    idx = pf([[C[c][(ck, p)] for c in ("C1", "C2", "C3")] for p in POL])
    sizes[len(idx)] += 1
    for i in idx: memb[POL[i]] += 1
OUT["pareto"] = dict(sizes=dict(sizes), membership=dict(memb),
                     frac_non_singleton=(n - sizes[1]) / n)
chk("pareto_non_singleton", (n - sizes[1]) / n, R["complementarity"]["frac_non_singleton_pareto"], 1e-12)
for p in POL:
    chk(f"pareto_memb_{p}", memb[p], R["complementarity"]["pareto_membership"][p])

# ---------------------------------------------------------------- winner map
def rate(feats, labels):
    grp = collections.defaultdict(collections.Counter)
    for ck in ctxs: grp[tuple(META[ck][f] for f in feats)][labels[ck]] += 1
    return sum(max(c.values()) for c in grp.values()) / n
OUT["winner_map_stable"] = dict(
    constant=rate([], win),
    single={f: rate([f], win) for f in FACT},
    best_two=max(rate(list(c), win) for c in itertools.combinations(FACT, 2)),
    best_two_pair="+".join(max(itertools.combinations(FACT, 2), key=lambda c: rate(list(c), win))),
    best_three=max(rate(list(c), win) for c in itertools.combinations(FACT, 3)),
    all_six=rate(FACT, win))

# ---------------------------------------------------------------- criteria
from scipy.stats import spearmanr, pearsonr
crit = {}
for a, b in (("C1", "C2"), ("C1", "C3"), ("C2", "C3")):
    xa = [C[a][(ck, p)] for ck in ctxs for p in POL]
    xb = [C[b][(ck, p)] for ck in ctxs for p in POL]
    rc = []; ident = 0
    for ck in ctxs:
        s = spearmanr([C[a][(ck, p)] for p in POL], [C[b][(ck, p)] for p in POL])[0]
        rc.append(0.0 if np.isnan(s) else s)
        if sorted(POL, key=lambda q: C[a][(ck, q)]) == sorted(POL, key=lambda q: C[b][(ck, q)]):
            ident += 1
    crit[f"{a}_vs_{b}"] = dict(pooled_pearson=pearsonr(xa, xb)[0],
                               mean_within_context_rank_corr=st.mean(rc),
                               n_identical_ordering=ident)
OUT["criteria"] = crit
chk("C1C2_pooled", crit["C1_vs_C2"]["pooled_pearson"], R["criteria"]["C1_vs_C2"]["pooled_pearson"], 1e-9)
chk("C1C3_pooled", crit["C1_vs_C3"]["pooled_pearson"], R["criteria"]["C1_vs_C3"]["pooled_pearson"], 1e-9)
chk("C1C2_within", crit["C1_vs_C2"]["mean_within_context_rank_corr"],
    R["criteria"]["C1_vs_C2"]["mean_within_context_rank_corr"], 1e-9)

# ---------------------------------------------------------------- specialisation
OUT["best_by_criterion"] = {c: dict(collections.Counter(
    min(POL, key=lambda p: (C[c][(ck, p)], POL.index(p))) for ck in ctxs)) for c in ("C1", "C2", "C3")}

json.dump(OUT, open(os.path.join(HERE, "verify_core.json"), "w"), indent=1, default=str)

bad = [c for c in CHECKS if not c[3]]
print(f"core verification: {len(CHECKS)-len(bad)}/{len(CHECKS)} checks match results.json")
for lab, got, want, _ in bad:
    print(f"  MISMATCH {lab}: recomputed {got!r} vs published {want!r}")
print()
print(f"ties for the C1 minimum: {n_tied}/{n} contexts ({n_tied/n:.4f})")
print("  composition:", OUT["ties"]["composition"])
print("winner counts, stable portfolio-order tie-break:", OUT["winner_counts_stable_tiebreak"])
print("published winner_counts_all                   :", R["G1_confirmatory"]["winner_counts_all"])
print("SBS attains the minimum in", len(isbest), f"contexts ({len(isbest)/n:.6f})")
print("published frac_contexts_sbs_optimal           :", R["headroom"]["frac_contexts_sbs_optimal"])
print("published asymmetry.frac_contexts_sbs_best    :", R["asymmetry"]["frac_contexts_sbs_best"])
print("winner map (stable):", {k: (round(v, 4) if isinstance(v, float) else v)
                               for k, v in OUT["winner_map_stable"].items() if k != "single"})
print("published winner_map:", {k: round(v, 4) for k, v in R["complementarity"]["winner_map"].items()
                                if isinstance(v, float)})
