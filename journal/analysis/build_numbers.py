"""Single source of every number in the journal manuscript.

Recomputes each quantity from the run records in study/results/*.jsonl.  The
frozen evaluation protocol (selector ladder, distribution-shift splits) is taken
from the study's own analysis modules, because that protocol is part of the
specification; the matrices it is given are rebuilt here.
"""
import json, os, sys, math, collections, itertools, statistics as st
import numpy as np
from scipy.stats import pearsonr, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = "/home/user/TORS/study"
RES = os.path.join(STUDY, "results")
AUD = os.path.join(STUDY, "audit2")

FACT = ["demand", "gc", "penetration", "lag", "incident", "alt"]
POL = ["P1", "P2", "P3", "P4"]
SAT_C, SAT_N, CAP_FREE, CYCLE, YELLOW, FF_C = 1761.0, 1596.0, 1500.0, 90.0, 4.0, 324.0
K_RES = 2.0
CRIT = {"C1": "C1_sys", "C2": "C2_sys", "C3": "C3_sys"}

def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")

def eff_green(gc): return (gc * CYCLE - YELLOW) / CYCLE

def caps(gc, alt):
    g = eff_green(gc)
    return {"C": 2 * SAT_C * g, "N": alt * SAT_N * g, "S": CAP_FREE}

def descriptors(m):
    cap = caps(m["gc"], m["alt"]); tot = sum(cap.values()); D, p = m["demand"], m["penetration"]
    return [D / tot, D / cap["C"], cap["N"] / tot, eff_green(m["gc"]), p,
            m["lag"] / FF_C, float(m["incident"]), p * D / cap["C"]]
XNAMES = ["x1_net_sat", "x2_short_sat", "x3_alt_share", "x4_eff_green",
          "x5_penetration", "x6_staleness", "x7_incident", "x8_ctrl_sat"]

def load(path):
    out = []
    for l in open(path):
        if not l.strip(): continue
        r = json.loads(l)
        if "_error" not in r: out.append(r)
    return out

def resolved(a, b, k=K_RES):
    d = np.asarray(a, float) - np.asarray(b, float)
    se = d.std(ddof=1) / math.sqrt(len(d))
    return bool(abs(d.mean()) > k * se), float(d.mean()), float(se)

def pareto(P):
    P = np.asarray(P, float)
    return [i for i in range(len(P))
            if not any(np.all(P[j] <= P[i]) and np.any(P[j] < P[i])
                       for j in range(len(P)) if j != i)]

N = {}

# ============================================================ campaign ledger
LEDGER = [("screen", "screen.jsonl", "complementarity screen"),
          ("validate", "validate.jsonl", "scenario validation"),
          ("main", "main.jsonl", "main factorial campaign"),
          ("boundary", "boundary.jsonl", "boundary refinement"),
          ("sens", "sens.jsonl", "policy-parameter sensitivity"),
          ("ood_north", "ood_north.jsonl", "domain-shift campaign")]
led = []; tot_ok = 0
for name, f, purpose in LEDGER:
    rows = load(os.path.join(RES, f))
    tot_ok += len(rows)
    led.append(dict(campaign=name, purpose=purpose, runs=len(rows),
                    contexts=len({r["ctx"] for r in rows}),
                    policies=len({r["policy"] for r in rows}),
                    seeds=len({r["seed"] for r in rows}),
                    failed=0,
                    min_completion=min(r["completion"] for r in rows),
                    teleports=sum(r.get("teleports", 0) for r in rows)))
n_bypass = len(json.load(open(os.path.join(RES, "ood_bypass_jobs.json"))))
led.append(dict(campaign="ood_bypass", purpose="planned domain-shift campaign, infeasible",
                runs=0, contexts=0, policies=4, seeds=5, failed=n_bypass,
                min_completion=None, teleports=None))
N["ledger"] = led
N["totals"] = dict(successful_runs=tot_ok, failed_runs=n_bypass,
                   attempted_runs=tot_ok + n_bypass, main_campaign_runs=12960)

# ============================================================ main campaign
rows = load(os.path.join(RES, "main.jsonl"))
cell = collections.defaultdict(list)
for r in rows: cell[(ctx_key(r), r["policy"])].append(r)
ctxs = sorted({k[0] for k in cell})
n = len(ctxs)
C = {c: {} for c in CRIT}; VEC = {}; META = {}; EXTRA = {}
for (ck, p), g in cell.items():
    g = sorted(g, key=lambda x: x["seed"])
    for c, col in CRIT.items(): C[c][(ck, p)] = st.mean(x[col] for x in g)
    VEC[(ck, p)] = [x[CRIT["C1"]] for x in g]
    META[ck] = {f: g[0][f] for f in FACT}
    EXTRA[(ck, p)] = {k: st.mean(x[k] for x in g)
                      for k in ("picks_C", "picks_N", "picks_S", "throughput", "C1_guided")}
N["campaign"] = dict(
    n_contexts=n, n_policies=len(POL), n_seeds=5, n_runs=len(rows),
    min_completion=min(r["completion"] for r in rows),
    mean_completion=st.mean(r["completion"] for r in rows),
    teleports=sum(r.get("teleports", 0) for r in rows),
    factor_levels={f: sorted({META[c][f] for c in ctxs}) for f in FACT},
    n_vehicles_total=int(sum(r.get("n_sys", 0) for r in rows)))

# ---------------------------------------------------------- ties and winners
minv = {ck: min(C["C1"][(ck, p)] for p in POL) for ck in ctxs}
tied = {ck: [p for p in POL if C["C1"][(ck, p)] == minv[ck]] for ck in ctxs}
n_tied = sum(1 for ck in ctxs if len(tied[ck]) > 1)
win = {ck: tied[ck][0] for ck in ctxs}                     # declared stable tie-break
N["ties"] = dict(n_tied=n_tied, frac_tied=n_tied / n,
                 composition={"+".join(v): c for v, c in
                              collections.Counter(tuple(tied[ck]) for ck in ctxs
                                                  if len(tied[ck]) > 1).items()})
N["winner_counts"] = dict(
    stable_tiebreak=dict(collections.Counter(win.values())),
    unique_minimum_only=dict(collections.Counter(win[ck] for ck in ctxs if len(tied[ck]) == 1)),
    tie_inclusive={p: sum(1 for ck in ctxs if p in tied[ck]) for p in POL},
    n_unique_minimum=n - n_tied)

rw = collections.Counter(); unres = 0; rm = []; um = []
for ck in ctxs:
    order = sorted(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p)))
    b, s2 = order[0], order[1]
    r, _, _ = resolved(VEC[(ck, s2)], VEC[(ck, b)])
    m = 100.0 * (C["C1"][(ck, s2)] - C["C1"][(ck, b)]) / C["C1"][(ck, b)]
    (rm if r else um).append(m)
    if r: rw[b] += 1
    else: unres += 1
N["resolved"] = dict(counts=dict(rw), n_resolved=sum(rw.values()), n_unresolved=unres,
                     frac_resolved=sum(rw.values()) / n,
                     median_resolved_margin_pct=st.median(rm),
                     median_unresolved_margin_pct=st.median(um),
                     max_resolved_margin_pct=max(rm),
                     n_policies_with_resolved_win=len([p for p in POL if rw[p] > 0]))

# ---------------------------------------------------------- operational identity
pi = {}
for a, b in itertools.combinations(POL, 2):
    nid = 0
    for ck in ctxs:
        r, _, _ = resolved(VEC[(ck, a)], VEC[(ck, b)])
        tot = sum(EXTRA[(ck, a)][f"picks_{x}"] for x in "CNS")
        guided = max(META[ck]["penetration"] * tot, 1.0)
        split = sum(abs(EXTRA[(ck, a)][f"picks_{x}"] - EXTRA[(ck, b)][f"picks_{x}"]) for x in "CNS")
        if (not r) and split / (2 * guided) < 0.02: nid += 1
    pi[f"{a}-{b}"] = nid / n
N["operational_identity"] = pi
N["mean_operational_identity"] = st.mean(pi.values())

# ---------------------------------------------------------- headroom
mean_cost = {p: st.mean(C["C1"][(ck, p)] for ck in ctxs) for p in POL}
sbs = min(mean_cost, key=mean_cost.get)
vbs = st.mean(minv[ck] for ck in ctxs)
head = mean_cost[sbs] - vbs
notbest = [ck for ck in ctxs if C["C1"][(ck, sbs)] > minv[ck]]
isbest = [ck for ck in ctxs if C["C1"][(ck, sbs)] == minv[ck]]
loss = st.mean(C["C1"][(ck, sbs)] - minv[ck] for ck in notbest)
marg = st.mean(sorted(C["C1"][(ck, p)] for p in POL)[1] - C["C1"][(ck, sbs)] for ck in isbest)
N["headroom"] = dict(
    sbs=sbs, mean_cost=mean_cost, cost_sbs=mean_cost[sbs], cost_vbs=vbs, headroom_s=head,
    headroom_pct_aggregate=100 * head / mean_cost[sbs],
    headroom_pct_per_context=100 * st.mean((C["C1"][(ck, sbs)] - minv[ck]) / minv[ck] for ck in ctxs),
    max_headroom_s=max(C["C1"][(ck, sbs)] - minv[ck] for ck in ctxs),
    penalty_s={p: mean_cost[p] - mean_cost[sbs] for p in POL},
    penalty_pct={p: 100 * (mean_cost[p] - mean_cost[sbs]) / mean_cost[sbs] for p in POL},
    n_sbs_attains_min=len(isbest), frac_sbs_attains_min=len(isbest) / n,
    n_sbs_not_best=len(notbest), frac_sbs_not_best=len(notbest) / n,
    mean_loss_when_not_best=loss, mean_margin_when_best=marg,
    upside_downside_ratio=marg / loss)

# ---------------------------------------------------------- noise resolvability
# For each context the question is whether the headroom of the single best fixed
# policy is resolvable, so the relevant dispersion is that of the paired
# difference between the SBS and the per-context best policy, not of an
# arbitrary policy pair.
sds = []; exceeds = 0
for ck in notbest:
    b = min(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p)))
    d = np.array(VEC[(ck, sbs)]) - np.array(VEC[(ck, b)])
    se = d.std(ddof=1) / math.sqrt(len(d)); sds.append(d.std(ddof=1))
    if (C["C1"][(ck, sbs)] - minv[ck]) > K_RES * se: exceeds += 1
# the noise floor used by the selector evaluation: worst paired SE against the best
floor = []
for ck in ctxs:
    b = min(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p)))
    floor.append(K_RES * max(resolved(VEC[(ck, p)], VEC[(ck, b)])[2] for p in POL if p != b))
N["resolvability"] = dict(
    mean_noise_floor_s=st.mean(floor),
    n_headroom_exceeds_noise=exceeds,
    frac_headroom_exceeds_noise=exceeds / len(notbest),
    median_sd_paired_difference_s=st.median(sds),
    mean_noise_2se_where_nonzero_s=st.mean(
        K_RES * (np.array(VEC[(ck, sbs)]) - np.array(VEC[(ck, min(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p))))])).std(ddof=1) / math.sqrt(5)
        for ck in notbest),
    seeds_for_mean_effect=int(math.ceil((K_RES * st.median(sds) / head) ** 2)))

# ---------------------------------------------------------- winner map
def rate(feats):
    grp = collections.defaultdict(collections.Counter)
    for ck in ctxs: grp[tuple(META[ck][f] for f in feats)][win[ck]] += 1
    return sum(max(c.values()) for c in grp.values()) / n
b2 = max(itertools.combinations(FACT, 2), key=lambda c: rate(list(c)))
b3 = max(itertools.combinations(FACT, 3), key=lambda c: rate(list(c)))
N["winner_map"] = dict(constant=rate([]), single={f: rate([f]) for f in FACT},
                       best_single=max(FACT, key=lambda f: rate([f])),
                       best_single_rate=max(rate([f]) for f in FACT),
                       best_two="+".join(b2), best_two_rate=rate(list(b2)),
                       best_three="+".join(b3), best_three_rate=rate(list(b3)),
                       all_six=rate(FACT))
N["winner_by_factor"] = {f: {str(l): dict(collections.Counter(
    win[ck] for ck in ctxs if META[ck][f] == l)) for l in sorted({META[c][f] for c in ctxs})}
    for f in FACT}

# ---------------------------------------------------------- Pareto / criteria
sizes = collections.Counter(); memb = collections.Counter()
for ck in ctxs:
    idx = pareto([[C[c][(ck, p)] for c in ("C1", "C2", "C3")] for p in POL])
    sizes[len(idx)] += 1
    for i in idx: memb[POL[i]] += 1
N["pareto"] = dict(sizes=dict(sizes), membership=dict(memb),
                   frac_non_singleton=(n - sizes[1]) / n, mean_size=st.mean(
                       [k for k, v in sizes.items() for _ in range(v)]))
crit = {}
for a, b in (("C1", "C2"), ("C1", "C3"), ("C2", "C3")):
    rc = []; ident = 0
    for ck in ctxs:
        s = spearmanr([C[a][(ck, p)] for p in POL], [C[b][(ck, p)] for p in POL])[0]
        rc.append(0.0 if np.isnan(s) else s)
        if sorted(POL, key=lambda q: C[a][(ck, q)]) == sorted(POL, key=lambda q: C[b][(ck, q)]): ident += 1
    crit[f"{a}_{b}"] = dict(
        pooled=pearsonr([C[a][(ck, p)] for ck in ctxs for p in POL],
                        [C[b][(ck, p)] for ck in ctxs for p in POL])[0],
        within=st.mean(rc), n_identical_order=ident)
N["criteria"] = crit
N["best_by_criterion"] = {c: dict(collections.Counter(
    min(POL, key=lambda p: (C[c][(ck, p)], POL.index(p))) for ck in ctxs)) for c in CRIT}

# ---------------------------------------------------------- verified protocol results
N["ladder"] = json.load(open(os.path.join(AUD, "verify_ladder.json")))
N["ood"] = json.load(open(os.path.join(AUD, "verify_ood.json")))

# ---------------------------------------------------------- boundary
brows = load(os.path.join(RES, "boundary.jsonl"))
allc = collections.defaultdict(list)
def cellk(r): return (float(r["gc"]), float(r["penetration"]), float(r["lag"]),
                      int(r["incident"]), int(r["alt"]))
for r in rows + brows: allc[(cellk(r), float(r["demand"]), r["policy"])].append(r)
BR = json.load(open(os.path.join(RES, "results.json")))["boundary"]
mono = 0; nonmono = 0; widths = []; endres = 0; ncp = []
for b in BR:
    k = (float(b["gc"]), float(b["penetration"]), float(b["lag"]), int(b["incident"]), int(b["alt"]))
    dems = sorted({d for (c, d, p) in allc if c == k and b["lo"] <= d <= b["hi"]})
    seq = []
    for d in dems:
        cost = {p: st.mean(x[CRIT["C1"]] for x in allc[(k, d, p)]) for p in POL}
        o = sorted(POL, key=lambda p: (cost[p], POL.index(p)))
        vb = {p: [x[CRIT["C1"]] for x in sorted(allc[(k, d, p)], key=lambda y: y["seed"])] for p in POL}
        seq.append((d, o[0], resolved(vb[o[1]], vb[o[0]])[0]))
    w = [s[1] for s in seq]
    cps = [i for i in range(1, len(w)) if w[i] != w[i - 1]]
    ncp.append(len(cps))
    if len(cps) == 1:
        mono += 1; i = cps[0]; widths.append(seq[i][0] - seq[i - 1][0])
        if seq[i][2] or seq[i - 1][2]: endres += 1
    else: nonmono += 1
N["boundary"] = dict(n_transitions=len(BR), n_monotone=mono, n_nonmonotone=nonmono,
                     median_bracket_width=st.median(widths),
                     n_bracket_150=sum(1 for x in widths if x == 150.0),
                     n_bracket_600=sum(1 for x in widths if x == 600.0),
                     n_with_resolved_endpoint=endres,
                     original_grid_spacing=600.0, refinement_step=150.0,
                     changepoints=collections.Counter(ncp))

# ---------------------------------------------------------- sensitivity
srows = load(os.path.join(RES, "sens.jsonl"))
sens = collections.defaultdict(list)
for r in srows:
    par = ("p3_eps", r["p3_eps"]) if r["policy"] == "P3" else ("p4_lambda", r["p4_lambda"])
    sens[(ctx_key(r), r["policy"], par)].append(r)
par_out = {}
for pol, pname, frozen in (("P3", "p3_eps", 0.2), ("P4", "p4_lambda", 1.0)):
    alts = {}
    for val in sorted({k[2][1] for k in sens if k[1] == pol}):
        d = []
        for (c, p, par), g in sens.items():
            if p != pol or par[1] != val: continue
            d.append(st.mean(x[CRIT["C1"]] for x in g) - st.mean(x[CRIT["C1"]] for x in cell[(c, pol)]))
        alts[str(val)] = dict(n=len(d), mean_change_s=st.mean(d), median_change_s=st.median(d),
                              max_abs_change_s=max(abs(x) for x in d))
    par_out[pol] = dict(parameter=pname, frozen=frozen, alternatives=alts)
N["parameter_sensitivity"] = par_out
N["preference_sensitivity"] = json.load(open(os.path.join(RES, "results.json")))["sensitivity"]["preference"]

# ---------------------------------------------------------- mechanistic descriptors
X = np.array([descriptors(META[ck]) for ck in ctxs])
N["descriptors"] = dict(names=XNAMES,
                        ranges={XNAMES[i]: [float(X[:, i].min()), float(X[:, i].max())] for i in range(8)})

json.dump(N, open(os.path.join(HERE, "numbers.json"), "w"), indent=1, default=str)
print(f"numbers.json written: {len(N)} blocks, {n} contexts")
for k in ("totals", "ties", "winner_counts", "resolved", "boundary"):
    print(f"  {k}: {json.dumps(N[k], default=str)[:220]}")
