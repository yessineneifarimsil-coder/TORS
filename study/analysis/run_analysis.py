"""Produce results.json: the single source of every number reported anywhere.

Nothing downstream -- no figure, no table, no sentence of the manuscript --
computes a number of its own.  All of them read this file.
"""
import json, sys, itertools, collections, warnings, os
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from scipy import stats
import common as K
import policy_selectors as S
import ood as OOD

HERE = os.path.dirname(os.path.abspath(__file__))
RESDIR = os.path.join(HERE, "..", "results")
R = {}
OUT = os.path.join(RESDIR, "results.json")


def jd(x):
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


# ---------------------------------------------------------------- 1. load
df, bad = K.load(os.path.join(RESDIR, "main.jsonl"))
R["campaign"] = dict(
    n_runs=len(df), n_failed=len(bad), n_contexts=int(df.ctx_key.nunique()),
    n_policies=int(df.policy.nunique()),
    seeds_per_cell=sorted(df.groupby(["ctx_key", "policy"]).size().unique().tolist()),
    factor_levels={f: sorted(df[f].unique().tolist()) for f in K.FACTORS})

# ------------------------------------------------------- 2. validity audit
need = max(R["campaign"]["seeds_per_cell"])
raw_min, raw_mean = float(df.completion.min()), float(df.completion.mean())
raw_tele = int(df.teleports.sum())
df, vrep = K.analysable(df, need_seeds=need)
R["validity"] = dict(
    min_completion=raw_min, mean_completion=raw_mean, total_teleports=raw_tele,
    rule="completion >= 0.98 and teleports == 0, declared in the frozen spec",
    completeness_rule=(f"a context is analysed only if all {len(K.POLICIES)} "
                       f"policies have {need} valid seeds"),
    n_contexts_analysed=int(df.ctx_key.nunique()), **vrep)
R["validity"]["excluded_contexts"] = vrep["excluded_contexts"][:50]

ct = K.context_table(df)
W = K.winners(ct)
PAR = K.pareto_by_context(ct)

# --------------------------------------- 3. confirmatory gate G1' (declared)
wr = W[W.resolved]
R["G1_confirmatory"] = dict(
    n_policies_with_resolved_win=int(wr.winner.nunique()),
    policies=sorted(wr.winner.unique().tolist()),
    threshold=3,
    passed=bool(wr.winner.nunique() >= 3),
    winner_counts_all=dict(collections.Counter(W.winner)),
    winner_counts_resolved=dict(collections.Counter(wr.winner)),
    n_contexts=int(len(W)),
    n_unresolved=int((~W.resolved).sum()),
    unresolved_margin_pct_median=float(np.median(
        [100 * r.margin / ct[ct.ctx_key == r.ctx_key].C1.min()
         for _, r in W[~W.resolved].iterrows()])) if (~W.resolved).any() else None,
    resolved_margin_pct_median=float(np.median(
        [100 * r.margin / ct[ct.ctx_key == r.ctx_key].C1.min()
         for _, r in wr.iterrows()])) if len(wr) else None,
    max_resolved_margin_pct=float(max(
        [100 * r.margin / ct[ct.ctx_key == r.ctx_key].C1.min()
         for _, r in wr.iterrows()])) if len(wr) else None)

# --------------------------------------------- 4. complementarity structure
pm = collections.Counter()
for _, r in PAR.iterrows():
    for p in r.pareto:
        pm[p] += 1
R["complementarity"] = dict(
    pareto_membership={p: int(pm[p]) for p in K.POLICIES},
    n_contexts=int(len(PAR)),
    pareto_size_distribution={int(k): int(v) for k, v in
                              collections.Counter(PAR.n_pareto).items()},
    frac_non_singleton_pareto=float((PAR.n_pareto > 1).mean()))

pair_ident, pair_gap = {}, {}
for a, b in itertools.combinations(K.POLICIES, 2):
    n_id, gaps = 0, []
    for ck, g in ct.groupby("ctx_key"):
        g = g.set_index("policy")
        res, d, _ = K.paired_resolved(g.loc[a, "vec"], g.loc[b, "vec"])
        gaps.append(d)
        tot = sum(g.loc[a, f"picks_{p}"] for p in "CNS")
        guided = max(g.loc[a, "penetration"] * tot, 1.0)
        split = sum(abs(g.loc[a, f"picks_{p}"] - g.loc[b, f"picks_{p}"]) for p in "CNS")
        if (not res) and split / (2 * guided) < 0.02:
            n_id += 1
    pair_ident[f"{a}-{b}"] = n_id / len(PAR)
    pair_gap[f"{a}-{b}"] = dict(mean=float(np.mean(gaps)),
                                median=float(np.median(gaps)),
                                p05=float(np.percentile(gaps, 5)),
                                p95=float(np.percentile(gaps, 95)))
R["complementarity"]["pairwise_identity"] = pair_ident
R["complementarity"]["pairwise_gap_seconds"] = pair_gap
R["complementarity"]["mean_pairwise_identity"] = float(np.mean(list(pair_ident.values())))

# winner-map dimensionality
stumps = {}
for f in K.FACTORS:
    acc = sum(collections.Counter(g.winner).most_common(1)[0][1]
              for _, g in W.groupby(f)) / len(W)
    stumps[f] = float(acc)
best2 = 0.0
for f1, f2 in itertools.combinations(K.FACTORS, 2):
    acc = sum(collections.Counter(g.winner).most_common(1)[0][1]
              for _, g in W.groupby([f1, f2])) / len(W)
    best2 = max(best2, acc)
R["complementarity"]["winner_map"] = dict(
    constant_rule=float(collections.Counter(W.winner).most_common(1)[0][1] / len(W)),
    single_factor=stumps,
    best_single=float(max(stumps.values())),
    best_single_factor=max(stumps, key=stumps.get),
    best_two_factor=float(best2))

# winner by factor level (the regime map)
wmap = {}
for f in K.FACTORS:
    wmap[f] = {str(lvl): dict(collections.Counter(g.winner))
               for lvl, g in W.groupby(f)}
R["complementarity"]["winner_by_factor"] = wmap

# ------------------------------------------------- 5. multi-criteria audit
def within_ctx_rank_corr(a, b):
    v = []
    for ck, g in ct.groupby("ctx_key"):
        g = g.set_index("policy").loc[[p for p in K.POLICIES if p in g.policy.values]]
        if len(g) < 3:
            continue
        ra = stats.rankdata(g[a].values); rb = stats.rankdata(g[b].values)
        if np.std(ra) > 0 and np.std(rb) > 0:
            v.append(np.corrcoef(ra, rb)[0, 1])
    return float(np.mean(v)), int(sum(1 for x in v if x > 0.999)), len(v)

crit_audit = {}
for a, b in [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]:
    m, same, n = within_ctx_rank_corr(a, b)
    crit_audit[f"{a}_vs_{b}"] = dict(
        pooled_pearson=float(np.corrcoef(ct[a], ct[b])[0, 1]),
        mean_within_context_rank_corr=m,
        n_contexts_identical_ordering=same, n_contexts=n,
        frac_identical_ordering=same / n if n else None)
n_c2 = n_c3 = 0
for ck, g in ct.groupby("ctx_key"):
    g = g.set_index("policy")
    if g.C2.idxmin() != g.C1.idxmin():
        n_c2 += 1
    if g.C3.idxmin() != g.C1.idxmin():
        n_c3 += 1
crit_audit["best_on_C2_differs_from_C1"] = dict(n=n_c2, frac=n_c2 / len(PAR))
crit_audit["best_on_C3_differs_from_C1"] = dict(n=n_c3, frac=n_c3 / len(PAR))
R["criteria"] = crit_audit

# ---------------------------------------- 6. selector ladder, LOCO on C1
ctxs, X, C, noise, meta = S.matrices(ct)
R["dataset"] = dict(n_contexts=int(len(ctxs)), n_features=len(K.XCOLS),
                    features=K.XCOLS,
                    mean_noise_floor_s=float(noise.mean()))
res, abst, supp = S.loco(X, C, noise)
lad = S.ladder(C, res, noise)
R["ladder_loco"] = json.loads(lad.to_json(orient="records"))
R["ladder_loco_abstention"] = dict(rate=float(abst.mean()),
                                   out_of_support_rate=float((~supp).mean()))
for k, ch in res.items():
    R.setdefault("top1_accuracy", {})[k] = float((ch == np.argmin(C, axis=1)).mean())

# headroom in physical units
sbs_idx = int(np.argmin(C.mean(axis=0)))
R["headroom"] = dict(
    global_sbs=K.POLICIES[sbs_idx],
    mean_cost_sbs_s=float(C[:, sbs_idx].mean()),
    mean_cost_vbs_s=float(C.min(axis=1).mean()),
    mean_headroom_s=float(C[:, sbs_idx].mean() - C.min(axis=1).mean()),
    mean_headroom_pct=float(((C[:, sbs_idx] - C.min(axis=1)) / C.min(axis=1)).mean() * 100),
    max_headroom_s=float((C[:, sbs_idx] - C.min(axis=1)).max()),
    frac_contexts_sbs_optimal=float((np.argmin(C, axis=1) == sbs_idx).mean()))

# -------------------------------------------------------- 7. OOD splits
R["ood"] = OOD.all_splits(X, C, noise, meta)

json.dump(R, open(OUT, "w"), indent=1, default=jd)   # checkpoint before optionals

# O8: incident on the bypass -- a corridor that carries no disruption in any
# training context.  Trained on the main campaign, tested on a separate one.
_p8 = os.path.join(RESDIR, "ood_bypass.jsonl")
try:
    if os.path.exists(_p8) and sum(1 for _ in open(_p8)) >= 200:
        d8, _ = K.load(_p8)
        d8, rep8 = K.analysable(d8, need_seeds=need)
        if d8.ctx_key.nunique() >= 10:
            ct8 = K.context_table(d8)
            _, X8, C8, n8, _m8 = S.matrices(ct8)
            R["ood"]["O8_bypass"] = OOD.domain_split(X, C, noise, X8, C8, n8)
            R["ood"]["O8_bypass"]["_excluded"] = rep8["n_incomplete_contexts"]
            R["ood"]["O8_bypass"]["_n_contexts"] = int(d8.ctx_key.nunique())
    else:
        R["ood_O8_status"] = "bypass-incident campaign not yet complete"
except Exception as e:
    R["ood_O8_status"] = f"bypass split skipped: {type(e).__name__}: {e}"

json.dump(R, open(OUT, "w"), indent=1, default=jd)
print(f"wrote {OUT} with {len(R)} top-level sections")
for k in R:
    print("  -", k)
