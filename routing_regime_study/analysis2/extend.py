"""Additional analyses. Every quantity is derived from analysis/runs.csv only.

The primary decision rule (two criteria, equal weights, fixed additive references) is
NOT modified: all headline regret / headroom numbers are the ones verified by verify.py.
Everything below is either (a) a decomposition of those numbers, or (b) an explicitly
labelled post-hoc analysis reported whatever its outcome.
"""
import json, statistics as st, itertools, math
import numpy as np
import core as K

T = K.ctx_means("time"); C = K.ctx_means("co2")
COST, aT, aC = K.scalarise(T, C, K.CTXS)
HB = {c: min(COST[c].values()) for c in K.CTXS}
O = {}

# =====================================================================
# 1. NOISE AND EFFECT SIZE  (paired seed replications)
# =====================================================================
ST_ = K.seed_means("time"); SC_ = K.seed_means("co2")
SCOST = {s: {c: {p: 0.5 * ST_[s][c][p] / aT + 0.5 * SC_[s][c][p] / aC for p in K.POL}
             for c in K.CTXS} for s in K.SEEDS}

def paired(c, p, q):
    d = [SCOST[s][c][p] - SCOST[s][c][q] for s in K.SEEDS]
    m = st.mean(d); se = st.stdev(d) / math.sqrt(len(d))
    return m, se, d

noise = {}
for c in K.CTXS:
    m, se, _ = paired(c, "SP", "DTT")
    noise[c] = dict(demand=K.META[c][0], restr=K.META[c][1], signal=K.META[c][2],
                    margin=m, se=se, resolved=abs(m) > 2 * se,
                    ratio=abs(m) / se if se > 0 else float("inf"))
O["noise_per_context"] = noise
O["noise_summary"] = {
    str(q): dict(
        n=sum(1 for c in K.CTXS if K.META[c][0] == q),
        resolved=sum(1 for c in K.CTXS if K.META[c][0] == q and noise[c]["resolved"]),
        median_abs_margin=st.median([abs(noise[c]["margin"]) for c in K.CTXS if K.META[c][0] == q]),
        median_se=st.median([noise[c]["se"] for c in K.CTXS if K.META[c][0] == q]),
        max_se=max(noise[c]["se"] for c in K.CTXS if K.META[c][0] == q))
    for q in K.DEMANDS}
O["noise_resolved_total"] = sum(1 for c in K.CTXS if noise[c]["resolved"])

# seed dispersion of the aggregate decision quantities
O["seed_level_headroom"] = {}
for s in K.SEEDS:
    hb = {c: min(SCOST[s][c].values()) for c in K.CTXS}
    O["seed_level_headroom"][s] = {p: st.mean(SCOST[s][c][p] - hb[c] for c in K.CTXS) for p in K.POL}
hm = [O["seed_level_headroom"][s]["DTT"] for s in K.SEEDS]
O["headroom_seed_mean"] = st.mean(hm)
O["headroom_seed_se"] = st.stdev(hm) / math.sqrt(3)

# =====================================================================
# 2. SELECTOR LADDER  (leave-one-context-out, refit per fold)
# =====================================================================
def loco_choice(fn):
    ch = {}
    for tr, te in K.loco_folds(K.CTXS):
        ch.update(fn(tr, te))
    return ch

def sbs_fold(tr, te):
    aT_, aC_ = (st.mean(T[c][p] for c in tr for p in K.POL), st.mean(C[c][p] for c in tr for p in K.POL))
    cst = {c: {p: 0.5 * T[c][p] / aT_ + 0.5 * C[c][p] / aC_ for p in K.POL} for c in tr}
    hb = {c: min(cst[c].values()) for c in tr}
    best = min(K.POL, key=lambda p: st.mean(cst[c][p] - hb[c] for c in tr))
    return {c: best for c in te}

def threshold_fold(tr, te):
    """Mechanistic demand-only rule: choose SP below a fitted demand threshold, DTT above."""
    aT_, aC_ = (st.mean(T[c][p] for c in tr for p in K.POL), st.mean(C[c][p] for c in tr for p in K.POL))
    cst = {c: {p: 0.5 * T[c][p] / aT_ + 0.5 * C[c][p] / aC_ for p in K.POL} for c in tr}
    hb = {c: min(cst[c].values()) for c in tr}
    cands = sorted({K.META[c][0] for c in tr}) + [10 ** 9]
    grid = [0] + [(a + b) / 2 for a, b in zip(cands, cands[1:])]
    best = min(grid, key=lambda t: st.mean(
        cst[c]["SP" if K.META[c][0] <= t else "DTT"] - hb[c] for c in tr))
    return {c: ("SP" if K.META[c][0] <= best else "DTT") for c in te}, best

def threshold_only(tr, te):
    return threshold_fold(tr, te)[0]

def signal_threshold_fold(tr, te):
    """Demand + signal regime: one fitted demand threshold per signal plan."""
    aT_, aC_ = (st.mean(T[c][p] for c in tr for p in K.POL), st.mean(C[c][p] for c in tr for p in K.POL))
    cst = {c: {p: 0.5 * T[c][p] / aT_ + 0.5 * C[c][p] / aC_ for p in K.POL} for c in tr}
    hb = {c: min(cst[c].values()) for c in tr}
    thr = {}
    for sig in ("Balanced", "Arterial"):
        sub = [c for c in tr if K.META[c][2] == sig]
        if not sub:
            thr[sig] = 0; continue
        cands = sorted({K.META[c][0] for c in sub}) + [10 ** 9]
        grid = [0] + [(a + b) / 2 for a, b in zip(cands, cands[1:])]
        thr[sig] = min(grid, key=lambda t: st.mean(
            cst[c]["SP" if K.META[c][0] <= t else "DTT"] - hb[c] for c in sub))
    return {c: ("SP" if K.META[c][0] <= thr[K.META[c][2]] else "DTT") for c in te}, thr

LADDER = {}
LADDER["R0_single_best_fixed"] = loco_choice(sbs_fold)
LADDER["R1_demand_threshold"] = loco_choice(threshold_only)
LADDER["R2_demand_signal_threshold"] = loco_choice(lambda tr, te: signal_threshold_fold(tr, te)[0])
LADDER["R3_tree_depth1"] = loco_choice(lambda tr, te: K.fit_select(T, C, tr, te, depth=1)[0])
LADDER["R4_tree_depth3"] = loco_choice(lambda tr, te: K.fit_select(T, C, tr, te, depth=3)[0])
LADDER["R5_hindsight"] = {c: min(COST[c], key=lambda p: COST[c][p]) for c in K.CTXS}

base = st.mean(COST[c]["DTT"] - HB[c] for c in K.CTXS)
O["ladder"] = {}
for k, ch in LADDER.items():
    s = K.regret_stats(COST, ch, K.CTXS)
    per_q = {str(q): st.mean(s["per_ctx"][c] for c in K.CTXS if K.META[c][0] == q) for q in K.DEMANDS}
    O["ladder"][k] = dict(mean=s["mean"], median=s["median"], max=s["max"], zero=s["zero"],
                          near=s["near"], captured_pct=(base - s["mean"]) / base * 100,
                          per_demand=per_q,
                          choices={c: ch[c] for c in K.CTXS})
# fitted thresholds actually selected across folds
O["threshold_values"] = sorted({threshold_fold(tr, te)[1] for tr, te in K.loco_folds(K.CTXS)})
sig_thr = [signal_threshold_fold(tr, te)[1] for tr, te in K.loco_folds(K.CTXS)]
O["signal_threshold_values"] = {s: sorted({d[s] for d in sig_thr}) for s in ("Balanced", "Arterial")}
O["sbs_fold_identity"] = sorted({v for ch in [LADDER["R0_single_best_fixed"]] for v in ch.values()})

# per-regime headroom decomposition (verifies the strengthening-report table)
O["regime_decomposition"] = {}
for q in K.DEMANDS:
    sub = [c for c in K.CTXS if K.META[c][0] == q]
    row = {p: st.mean(COST[c][p] - HB[c] for c in sub) for p in K.POL}
    row["worst"] = st.mean(max(COST[c].values()) - HB[c] for c in sub)
    row["adaptive"] = st.mean(COST[c][LADDER["R4_tree_depth3"][c]] - HB[c] for c in sub)
    row["share_of_total_headroom"] = row["DTT"] * len(sub) / (base * len(K.CTXS)) * 100
    O["regime_decomposition"][str(q)] = row

# physical outcome of the selector versus the fixed policy
sel = LADDER["R4_tree_depth3"]
O["physical"] = dict(
    sel_time=st.mean(T[c][sel[c]] for c in K.CTXS), sel_co2=st.mean(C[c][sel[c]] for c in K.CTXS),
    dtt_time=st.mean(T[c]["DTT"] for c in K.CTXS), dtt_co2=st.mean(C[c]["DTT"] for c in K.CTXS),
    sp_time=st.mean(T[c]["SP"] for c in K.CTXS), sp_co2=st.mean(C[c]["SP"] for c in K.CTXS),
    hb_time=st.mean(T[c][LADDER["R5_hindsight"][c]] for c in K.CTXS),
    hb_co2=st.mean(C[c][LADDER["R5_hindsight"][c]] for c in K.CTXS))
O["physical"]["d_time"] = O["physical"]["dtt_time"] - O["physical"]["sel_time"]
O["physical"]["d_co2"] = O["physical"]["dtt_co2"] - O["physical"]["sel_co2"]
O["physical"]["d_time_pct"] = O["physical"]["d_time"] / O["physical"]["dtt_time"] * 100
O["physical"]["d_co2_pct"] = O["physical"]["d_co2"] / O["physical"]["dtt_co2"] * 100

json.dump(O, open("extend.json", "w"), indent=1, default=str)
print("== NOISE AND EFFECT SIZE ==")
for q in K.DEMANDS:
    n = O["noise_summary"][str(q)]
    print(f"  q={q:5d}  resolved {n['resolved']}/{n['n']}  median|margin|={n['median_abs_margin']:.4f}  "
          f"median SE={n['median_se']:.4f}  max SE={n['max_se']:.4f}")
print(f"  resolved overall: {O['noise_resolved_total']}/24")
print(f"  headroom across seed blocks: {O['headroom_seed_mean']:.5f} +/- {O['headroom_seed_se']:.5f} (SE of 3)")
print("\n== SELECTOR LADDER (LOCO) ==")
print(f"  {'rule':30s}{'mean':>9s}{'median':>9s}{'max':>9s}{'opt':>6s}{'captured':>10s}"
      + "".join(f"{('q=%d'%q):>9s}" for q in K.DEMANDS))
for k, v in O["ladder"].items():
    print(f"  {k:30s}{v['mean']:9.5f}{v['median']:9.5f}{v['max']:9.5f}{v['zero']:5d}/24{v['captured_pct']:9.1f}%"
          + "".join(f"{v['per_demand'][str(q)]:9.5f}" for q in K.DEMANDS))
print(f"\n  fitted demand thresholds (demand-only rule): {O['threshold_values']}")
print(f"  fitted thresholds by signal plan: {O['signal_threshold_values']}")
print(f"  single-best-fixed identity across folds: {O['sbs_fold_identity']}")
print("\n== REGIME DECOMPOSITION ==")
print(f"  {'q':>6s}{'worst':>10s}{'SP':>10s}{'DTT':>10s}{'TECO10':>10s}{'adaptive':>10s}{'share':>9s}")
for q in K.DEMANDS:
    r = O["regime_decomposition"][str(q)]
    print(f"  {q:6d}{r['worst']:10.5f}{r['SP']:10.5f}{r['DTT']:10.5f}{r['TECO10']:10.5f}"
          f"{r['adaptive']:10.5f}{r['share_of_total_headroom']:8.1f}%")
p = O["physical"]
print(f"\n== PHYSICAL ==\n  selector {p['sel_time']:.2f} s / {p['sel_co2']:.2f} g   "
      f"fixed DTT {p['dtt_time']:.2f} s / {p['dtt_co2']:.2f} g   "
      f"diff {p['d_time']:.2f} s ({p['d_time_pct']:.2f}%) / {p['d_co2']:.2f} g ({p['d_co2_pct']:.2f}%)")
print(f"  hindsight {p['hb_time']:.2f} s / {p['hb_co2']:.2f} g ; fixed SP {p['sp_time']:.2f} s / {p['sp_co2']:.2f} g")
