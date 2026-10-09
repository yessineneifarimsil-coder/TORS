"""Independent noise-floor and decision-value analysis of the 648-context main campaign.

Reads study/results/main.jsonl only.  Re-runs the frozen LOCO ladder through the
study's own policy_selectors.loco() (unmodified) to obtain per-context choices,
then evaluates every comparison on held-out SEEDS so that selection noise and
evaluation noise are separated.  Writes only into audit_journal_readiness/outputs.
"""
import json, os, sys, math, collections, statistics as st, time
import numpy as np
OUT = "/home/user/TORS/audit_journal_readiness/outputs"; ROOT = "/home/user/TORS/study"
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import warnings; warnings.filterwarnings("ignore")

FACT = ["demand", "gc", "penetration", "lag", "incident", "alt"]; POL = ["P1", "P2", "P3", "P4"]
def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")
SAT_C, SAT_N, CAP_FREE, CYCLE, YELLOW, FF_C = 1761.0, 1596.0, 1500.0, 90.0, 4.0, 324.0
def desc(m):
    g = (m["gc"] * CYCLE - YELLOW) / CYCLE
    cap = {"C": 2 * SAT_C * g, "N": m["alt"] * SAT_N * g, "S": CAP_FREE}
    tot = sum(cap.values()); D, p = m["demand"], m["penetration"]
    return [D / tot, D / cap["C"], cap["N"] / tot, g, p, m["lag"] / FF_C, float(m["incident"]), p * D / cap["C"]]

rows = [json.loads(l) for l in open(os.path.join(ROOT, "results", "main.jsonl")) if l.strip()]
cell = collections.defaultdict(list)
for r in rows: cell[(ctx_key(r), r["policy"])].append(r)
ctxs = sorted({k[0] for k in cell}); n = len(ctxs)
SEEDS = sorted({r["seed"] for r in rows}); S_ = len(SEEDS)
Y = np.zeros((n, 4, S_))           # context x policy x seed, C1 system (s/veh)
X = np.zeros((n, 8)); meta = []
for i, ck in enumerate(ctxs):
    g0 = cell[(ck, "P1")][0]; m = {f: g0[f] for f in FACT}; meta.append(m); X[i] = desc(m)
    for j, p in enumerate(POL):
        bys = {r["seed"]: r["C1_sys"] for r in cell[(ck, p)]}
        Y[i, j] = [bys[s] for s in SEEDS]
C = Y.mean(axis=2)
O = {"n_contexts": n, "seeds": SEEDS}

# ---------------------------------------------------------------- choices
cache = os.path.join(OUT, "loco_choices.npz")
if os.path.exists(cache):
    z = np.load(cache); res = {k: z[k] for k in z.files if k not in ("abst", "supp")}
    abst, supp = z["abst"], z["supp"]
else:
    import policy_selectors as S
    noise = np.zeros(n)
    for i in range(n):
        b = int(np.argmin(C[i])); ses = []
        for j in range(4):
            if j == b: continue
            d = Y[i, j] - Y[i, b]; ses.append(d.std(ddof=1) / math.sqrt(S_))
        noise[i] = 2 * max(ses)
    t0 = time.time(); res, abst, supp = S.loco(X, C, noise)
    print(f"LOCO {time.time()-t0:.0f}s", flush=True)
    np.savez(cache, abst=abst, supp=supp, **res)

sbs = int(np.argmin(C.mean(axis=0)))
O["sbs"] = POL[sbs]
O["fixed_policy_mean_cost"] = {p: float(C[:, j].mean()) for j, p in enumerate(POL)}
O["wrong_fixed_penalty_vs_sbs"] = {p: float(C[:, j].mean() - C[:, sbs].mean()) for j, p in enumerate(POL)}

# ---------------------------------------------------------------- A. in-sample headroom
h = C[:, sbs] - C.min(axis=1)
hs = np.sort(h)[::-1]; tot = h.sum()
O["A_insample_headroom"] = dict(
    mean=float(h.mean()), median=float(np.median(h)), n_positive=int((h > 1e-9).sum()),
    pct_of_sbs_mean_cost=float(h.mean() / C[:, sbs].mean() * 100),
    share_top1pct=float(hs[:max(1, n // 100)].sum() / tot), share_top5pct=float(hs[:n // 20].sum() / tot),
    share_top10pct=float(hs[:n // 10].sum() / tot),
    n_contexts_carrying_half=int(np.searchsorted(np.cumsum(hs), tot / 2) + 1),
    max=float(h.max()))

# ---------------------------------------------------------------- B. cross-fitted (honest) VBS headroom
# choose the per-context winner on 4 seeds, evaluate on the held-out 5th.
gain = np.zeros((n, S_))
for k in range(S_):
    tr = [s for s in range(S_) if s != k]
    a = np.argmin(Y[:, :, tr].mean(axis=2), axis=1)
    gain[:, k] = Y[:, sbs, k] - Y[np.arange(n), a, k]
per_seed = gain.mean(axis=0)
O["B_crossfit_vbs_headroom"] = dict(
    mean=float(gain.mean()), per_seed=[float(x) for x in per_seed],
    se_over_seeds=float(per_seed.std(ddof=1) / math.sqrt(S_)),
    note="positive = an oracle that picks the per-context winner from 4 seeds beats SBS on the 5th")

# ---------------------------------------------------------------- C. pure-noise null for the in-sample headroom
# Replace every policy's outcome by SBS's outcome on a DIFFERENT random permutation of the
# seed residuals?  Not defensible with 5 seeds.  Use instead the analytic expectation of the
# selection bias: headroom computed when all four policies are identical copies of SBS with
# independent noise of the observed paired-difference size.
rng = np.random.default_rng(0)
dsd = np.array([[np.std(Y[i, j] - Y[i, sbs], ddof=1) if j != sbs else 0 for j in range(4)] for i in range(n)])
null = []
for _ in range(200):
    eps = rng.standard_normal((n, 4)) * dsd / math.sqrt(S_)
    eps[:, sbs] = 0.0
    Cnull = C[:, [sbs]] + eps          # every policy has the SBS mean; only seed noise differs
    null.append(float((Cnull[:, sbs] - Cnull.min(axis=1)).mean()))
O["C_null_headroom_if_all_policies_equal"] = dict(mean=float(np.mean(null)), p95=float(np.quantile(null, 0.95)),
    note="headroom the in-sample VBS would report if policies were identical to SBS in truth "
         "and differed only by the observed paired seed noise")

# ---------------------------------------------------------------- D. realised selector gains, by held-out seed
def realised(choice):
    g = Y[:, sbs, :] - Y[np.arange(n), choice, :]        # n x seeds, positive = better than SBS
    ps = g.mean(axis=0)
    dev = choice != sbs
    return dict(mean_gain=float(g.mean()), per_seed=[float(x) for x in ps],
                se_over_seeds=float(ps.std(ddof=1) / math.sqrt(S_)),
                min_seed=float(ps.min()), n_deviate=int(dev.sum()),
                deviate_better_5seedmean=int((g[dev].mean(axis=1) > 0).sum()),
                deviate_worse_5seedmean=int((g[dev].mean(axis=1) < 0).sum()),
                deviate_sign_consistent_all_seeds=int(((g[dev] > 0).all(axis=1) | (g[dev] < 0).all(axis=1)).sum()))
O["D_realised_gain_vs_SBS"] = {k: realised(v) for k, v in res.items()}
b4 = res["B4_GBDT"]; g4 = (Y[:, sbs, :] - Y[np.arange(n), b4, :]).mean(axis=1)
gs = np.sort(g4)[::-1]
O["D_B4_concentration"] = dict(total=float(g4.sum() / n),
    top10_contexts_share=float(gs[:10].sum() / g4.sum()), top20_share=float(gs[:20].sum() / g4.sum()),
    sum_positive=float(g4[g4 > 0].sum() / n), sum_negative=float(g4[g4 < 0].sum() / n))
O["E_gate"] = dict(abstain_rate=float(abst.mean()), out_of_support=float((~supp).mean()),
    b5_equals_b0_all=bool((res["B5_selective"] == res["B0_SBS"]).all()),
    b4_deviates=int((b4 != sbs).sum()),
    abstains_exactly_where_b4_deviates=bool(((b4 != sbs) <= abst).all()))

# ---------------------------------------------------------------- F. how many seeds would resolve the headroom?
pd_sd = float(np.mean([np.std(Y[i, int(np.argmin(C[i]))] - Y[i, sbs], ddof=1) for i in range(n) if np.argmin(C[i]) != sbs]))
O["F_resolution"] = dict(mean_sd_paired_diff_best_vs_sbs=pd_sd)
json.dump(O, open(os.path.join(OUT, "noise_floor.json"), "w"), indent=1)
print(json.dumps(O, indent=1))
