"""Multi-criteria structure and the sensitivity battery. Source: analysis/runs.csv only."""
import json, statistics as st, math
import numpy as np
import core as K

T = K.ctx_means("time"); C = K.ctx_means("co2")
Q = K.ctx_means("stopped"); D = K.ctx_means("dist"); P95 = K.ctx_means("p95")
IN = K.ctx_means("innet")
COST, aT, aC = K.scalarise(T, C, K.CTXS)
HB2 = {c: min(COST[c], key=lambda p: COST[c][p]) for c in K.CTXS}
O = {}

# =====================================================================
# 3. MULTI-CRITERIA / PARETO STRUCTURE   (post hoc; primary rule unchanged)
#    third axis = network-wide stopped vehicle-time, pre-declared a DIAGNOSTIC
# =====================================================================
def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(
        sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))

cells = [(c, p) for c in K.CTXS for p in K.POL]
vt = [T[c][p] for c, p in cells]; vc = [C[c][p] for c, p in cells]
vq = [Q[c][p] for c, p in cells]; vd = [D[c][p] for c, p in cells]
O["criterion_correlation"] = dict(time_co2=corr(vt, vc), time_stopped=corr(vt, vq),
                                  co2_stopped=corr(vc, vq), time_dist=corr(vt, vd),
                                  co2_dist=corr(vc, vd))
# within-context (the correlation that matters for ranking policies)
wc = {k: [] for k in ("time_co2", "time_stopped", "co2_stopped")}
for c in K.CTXS:
    t = [T[c][p] for p in K.POL]; e = [C[c][p] for p in K.POL]; q = [Q[c][p] for p in K.POL]
    wc["time_co2"].append(corr(t, e)); wc["time_stopped"].append(corr(t, q))
    wc["co2_stopped"].append(corr(e, q))
O["criterion_correlation_within_context"] = {k: st.mean(v) for k, v in wc.items()}

def pareto(ctx, crits):
    """Non-dominated policies in `ctx` under the given criterion dicts (all minimised)."""
    nd = []
    for p in K.POL:
        dom = any(all(cr[ctx][o] <= cr[ctx][p] for cr in crits)
                  and any(cr[ctx][o] < cr[ctx][p] for cr in crits) for o in K.POL if o != p)
        if not dom:
            nd.append(p)
    return nd

O["pareto"] = {}
for name, crits in (("two_criterion", [T, C]), ("three_criterion", [T, C, Q])):
    sets = {c: pareto(c, crits) for c in K.CTXS}
    sizes = [len(sets[c]) for c in K.CTXS]
    O["pareto"][name] = dict(
        sets=sets, mean_size=st.mean(sizes),
        singleton=sum(1 for c in K.CTXS if len(sets[c]) == 1),
        n_nonsingleton=sum(1 for c in K.CTXS if len(sets[c]) > 1),
        by_demand={str(q): st.mean(len(sets[c]) for c in K.CTXS if K.META[c][0] == q) for q in K.DEMANDS},
        policy_appears={p: sum(1 for c in K.CTXS if p in sets[c]) for p in K.POL})
O["two_crit_winner_is_3d_pareto"] = sum(
    1 for c in K.CTXS if HB2[c] in O["pareto"]["three_criterion"]["sets"][c])

# three-criterion additive rule, equal weights, same fixed-reference scheme
aQ = st.mean(Q[c][p] for c in K.CTXS for p in K.POL)
cost3 = {c: {p: (T[c][p] / aT + C[c][p] / aC + Q[c][p] / aQ) / 3 for p in K.POL} for c in K.CTXS}
win3 = {c: min(cost3[c], key=lambda p: cost3[c][p]) for c in K.CTXS}
O["three_criterion_additive"] = dict(
    ref_stopped=aQ, winners=win3,
    agree_with_primary=sum(1 for c in K.CTXS if win3[c] == HB2[c]),
    disagree=[c for c in K.CTXS if win3[c] != HB2[c]],
    fixed_regret={p: st.mean(cost3[c][p] - min(cost3[c].values()) for c in K.CTXS) for p in K.POL})
# stopped vehicle-time on its own
winq = {c: min(K.POL, key=lambda p: Q[c][p]) for c in K.CTXS}
O["stopped_only_winner"] = dict(winners=winq,
                                agree_with_primary=sum(1 for c in K.CTXS if winq[c] == HB2[c]),
                                by_demand={str(q): [winq[c] for c in K.CTXS if K.META[c][0] == q]
                                           for q in K.DEMANDS})
O["stopped_means"] = {str(q): {p: st.mean(Q[c][p] for c in K.CTXS if K.META[c][0] == q)
                               for p in K.POL} for q in K.DEMANDS}
O["stop_per_veh_means"] = {str(q): {p: st.mean(x["stop_per_veh"] for x in K.R
                                               if x["policy"] == p and x["demand"] == q)
                                    for p in K.POL} for q in K.DEMANDS}

# =====================================================================
# 4. SENSITIVITY BATTERY
# =====================================================================
def loco_regret(Tm, Cm, depth=3, leaf=2, w=0.5, use=("demand", "restr", "signal"),
                scoreT=None, scoreC=None):
    ch = {}
    for tr, te in K.loco_folds(K.CTXS):
        ch.update(K.fit_select(Tm, Cm, tr, te, depth=depth, leaf=leaf, w=w, use=use)[0])
    sT, sC = (scoreT or Tm), (scoreC or Cm)
    cst, _, _ = K.scalarise(sT, sC, K.CTXS, w=w)
    hb = {c: min(cst[c].values()) for c in K.CTXS}
    reg = st.mean(cst[c][ch[c]] - hb[c] for c in K.CTXS)
    fx = {p: st.mean(cst[c][p] - hb[c] for c in K.CTXS) for p in K.POL}
    bf = min(fx, key=lambda p: fx[p])
    return dict(regret=reg, best_fixed=bf, best_fixed_regret=fx[bf],
                captured=(fx[bf] - reg) / fx[bf] * 100 if fx[bf] > 0 else float("nan"),
                choices=ch, optimal=sum(1 for c in K.CTXS if cst[c][ch[c]] - hb[c] < 1e-12))

O["sens_tree"] = {}
for depth in (1, 2, 3, 4, None):
    for leaf in (1, 2, 3):
        r = loco_regret(T, C, depth=depth, leaf=leaf)
        O["sens_tree"][f"depth={depth},leaf={leaf}"] = {k: r[k] for k in
                                                        ("regret", "best_fixed", "best_fixed_regret", "captured", "optimal")}
caps = [v["captured"] for v in O["sens_tree"].values()]
O["sens_tree_range"] = [min(caps), max(caps)]
O["sens_tree_all_positive"] = all(c > 0 for c in caps)

O["sens_weight"] = {}
for w in (1.0, 0.75, 0.5, 0.25, 0.0):
    r = loco_regret(T, C, w=w)
    O["sens_weight"][str(w)] = {k: r[k] for k in ("regret", "best_fixed", "best_fixed_regret", "captured", "optimal")}
    O["sens_weight"][str(w)]["choices"] = r["choices"]
O["sens_weight_choices_identical"] = all(
    O["sens_weight"][str(w)]["choices"] == O["sens_weight"]["0.5"]["choices"] for w in (1.0, 0.75, 0.25, 0.0))
hw = {}
for w in (1.0, 0.75, 0.5, 0.25, 0.0):
    cc = {c: {p: w * T[c][p] / aT + (1 - w) * C[c][p] / aC for p in K.POL} for c in K.CTXS}
    hw[str(w)] = {c: min(cc[c], key=lambda p: cc[c][p]) for c in K.CTXS}
O["hindsight_winner_by_weight"] = hw
O["hindsight_winner_changes"] = sorted({c for w in hw for c in K.CTXS if hw[w][c] != hw["0.5"][c]})

O["sens_seed_block"] = {}
for held in K.SEEDS:
    tr_s = tuple(s for s in K.SEEDS if s != held)
    Ttr, Ctr = K.ctx_means("time", seeds=tr_s), K.ctx_means("co2", seeds=tr_s)
    Tte, Cte = K.ctx_means("time", seeds=(held,)), K.ctx_means("co2", seeds=(held,))
    r = loco_regret(Ttr, Ctr, scoreT=Tte, scoreC=Cte)
    O["sens_seed_block"][held] = {k: r[k] for k in ("regret", "best_fixed", "best_fixed_regret", "captured")}

# train-only scales used for scoring as well
regs, dtts = [], []
for tr, te in K.loco_folds(K.CTXS):
    a1 = st.mean(T[c][p] for c in tr for p in K.POL); a2 = st.mean(C[c][p] for c in tr for p in K.POL)
    ch, _ = K.fit_select(T, C, tr, te)
    for c in te:
        cst = {p: 0.5 * T[c][p] / a1 + 0.5 * C[c][p] / a2 for p in K.POL}
        hb = min(cst.values()); regs.append(cst[ch[c]] - hb); dtts.append(cst["DTT"] - hb)
O["sens_train_only_scaling"] = dict(regret=st.mean(regs), best_fixed_regret=st.mean(dtts),
                                    captured=(st.mean(dtts) - st.mean(regs)) / st.mean(dtts) * 100)

# measurement boundary: in-network journey time (insertion delay excluded)
cin, _, _ = K.scalarise(IN, C, K.CTXS)
win_in = {c: min(cin[c], key=lambda p: cin[c][p]) for c in K.CTXS}
O["sens_measurement_boundary"] = dict(
    labels_changed=sum(1 for c in K.CTXS if win_in[c] != HB2[c]),
    headroom_innet=st.mean(cin[c]["DTT"] - min(cin[c].values()) for c in K.CTXS),
    headroom_journey=st.mean(COST[c]["DTT"] - min(COST[c].values()) for c in K.CTXS))
r = loco_regret(IN, C)
O["sens_measurement_boundary"].update(loco_regret=r["regret"], loco_captured=r["captured"])

# P95 substituted for the mean-time criterion
cp, _, _ = K.scalarise(P95, C, K.CTXS)
win_p = {c: min(cp[c], key=lambda p: cp[c][p]) for c in K.CTXS}
O["sens_p95"] = dict(labels_changed=sum(1 for c in K.CTXS if win_p[c] != HB2[c]),
                     changed_ctx=[c for c in K.CTXS if win_p[c] != HB2[c]])
# distance added as a third criterion
aD = st.mean(D[c][p] for c in K.CTXS for p in K.POL)
cd3 = {c: {p: (T[c][p] / aT + C[c][p] / aC + D[c][p] / aD) / 3 for p in K.POL} for c in K.CTXS}
win_d = {c: min(cd3[c], key=lambda p: cd3[c][p]) for c in K.CTXS}
O["sens_distance_criterion"] = dict(labels_changed=sum(1 for c in K.CTXS if win_d[c] != HB2[c]))
O["sens_three_criterion_labels_changed"] = sum(1 for c in K.CTXS if win3[c] != HB2[c])

json.dump(O, open("extend2.json", "w"), indent=1, default=str)

print("== CRITERION CORRELATION (72 context x policy cells) ==")
for k, v in O["criterion_correlation"].items():
    print(f"  {k:16s} {v:+.4f}")
print("  within-context (across the 3 policies):",
      {k: round(v, 4) for k, v in O["criterion_correlation_within_context"].items()})
print("\n== PARETO STRUCTURE ==")
for name in ("two_criterion", "three_criterion"):
    p = O["pareto"][name]
    print(f"  {name:16s} mean set size {p['mean_size']:.3f}  singleton {p['singleton']}/24  "
          f"by demand {[round(p['by_demand'][str(q)],3) for q in K.DEMANDS]}  appears {p['policy_appears']}")
print(f"  primary (two-criterion) winner is 3-criterion Pareto-optimal in "
      f"{O['two_crit_winner_is_3d_pareto']}/24 contexts")
t3 = O["three_criterion_additive"]
print(f"  equal-weight three-criterion additive winner agrees with the primary winner in "
      f"{t3['agree_with_primary']}/24  (differs: {t3['disagree']})")
print(f"  stopped-vehicle-time-only winner agrees in {O['stopped_only_winner']['agree_with_primary']}/24")
print(f"  network stopped vehicle-time by demand: "
      + "; ".join(f"q={q}: " + ", ".join(f"{p}={O['stopped_means'][str(q)][p]:.0f}" for p in K.POL) for q in K.DEMANDS))
print("\n== SENSITIVITY ==")
print(f"  tree depth/leaf captured range: {O['sens_tree_range'][0]:.1f}% .. {O['sens_tree_range'][1]:.1f}%  "
      f"all positive: {O['sens_tree_all_positive']}")
print("  weights:", {w: f"{v['captured']:.1f}%" for w, v in O["sens_weight"].items()})
print(f"  selector choices identical across weights: {O['sens_weight_choices_identical']}")
print(f"  hindsight winner changes at some weight in contexts: {O['hindsight_winner_changes']}")
print("  seed blocks:", {s: f"{v['captured']:.1f}%" for s, v in O["sens_seed_block"].items()})
print(f"  train-only scaling: {O['sens_train_only_scaling']['captured']:.1f}%")
b = O["sens_measurement_boundary"]
print(f"  measurement boundary: labels changed {b['labels_changed']}/24, headroom "
      f"{b['headroom_journey']:.5f} -> {b['headroom_innet']:.5f}, LOCO captured {b['loco_captured']:.1f}%")
print(f"  P95 instead of mean time: labels changed {O['sens_p95']['labels_changed']}/24 {O['sens_p95']['changed_ctx']}")
print(f"  distance as third criterion: labels changed {O['sens_distance_criterion']['labels_changed']}/24")
print(f"  stopped delay as third criterion: labels changed {O['sens_three_criterion_labels_changed']}/24")
