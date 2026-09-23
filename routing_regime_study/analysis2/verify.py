"""Reproduce every number in analysis/results.json from runs.csv. Any mismatch is reported."""
import json, statistics as st, math
import numpy as np
import core as K

OLD = json.load(open("/home/user/TORS/routing_regime_study/analysis/results.json"))
fails, checks = [], 0

def chk(name, got, want, tol=1e-9):
    global checks
    checks += 1
    ok = (abs(got - want) <= tol) if isinstance(want, (int, float)) and not isinstance(want, bool) else (got == want)
    if not ok:
        fails.append((name, got, want))
    return ok

T = K.ctx_means("time"); C = K.ctx_means("co2")
T6 = K.ctx_means("time", K.ALLP); C6 = K.ctx_means("co2", K.ALLP)
cost, aT, aC = K.scalarise(T, C, K.CTXS)

chk("n_runs", len(K.R), OLD["n_runs"]); chk("n_contexts", len(K.CTXS), OLD["n_contexts"])
chk("ref_time", aT, OLD["ref_time"]); chk("ref_co2", aC, OLD["ref_co2"])
for p in K.POL:
    s = K.regret_stats(cost, {c: p for c in K.CTXS}, K.CTXS)
    chk(f"fixed.{p}.mean", s["mean"], OLD["fixed"][p]["mean"])
    chk(f"fixed.{p}.max", s["max"], OLD["fixed"][p]["max"])
    chk(f"fixed.{p}.zero", s["zero"], OLD["fixed"][p]["zero"])
    chk(f"fixed.{p}.near", s["near"], OLD["fixed"][p]["near"])

# ---- LOCO selector -------------------------------------------------------
chosen, pT, pC, oT, oC = {}, [], [], [], []
for tr, te in K.loco_folds(K.CTXS):
    ch, m = K.fit_select(T, C, tr, te)
    chosen.update(ch)
    a1 = st.mean(T[c][p] for c in tr for p in K.POL); a2 = st.mean(C[c][p] for c in tr for p in K.POL)
    yp = m.predict(np.array([K.feats(te[0])]))[0]
    for i, p in enumerate(K.POL):
        pT.append(yp[i] * a1); pC.append(yp[i + 3] * a2); oT.append(T[te[0]][p]); oC.append(C[te[0]][p])
chk("pred_mae_time", st.mean(abs(a - b) for a, b in zip(pT, oT)), OLD["pred_mae_time"])
chk("pred_rmse_time", math.sqrt(st.mean((a - b) ** 2 for a, b in zip(pT, oT))), OLD["pred_rmse_time"])
chk("pred_mae_co2", st.mean(abs(a - b) for a, b in zip(pC, oC)), OLD["pred_mae_co2"])
chk("pred_rmse_co2", math.sqrt(st.mean((a - b) ** 2 for a, b in zip(pC, oC))), OLD["pred_rmse_co2"])
chk("chosen_loco", chosen, OLD["chosen_loco"])
s = K.regret_stats(cost, chosen, K.CTXS)
for k in ("mean", "max", "zero", "near"):
    chk(f"adaptive_loco.{k}", s[k], OLD["adaptive_loco"][k])
cap = (OLD["fixed"]["DTT"]["mean"] - s["mean"]) / OLD["fixed"]["DTT"]["mean"] * 100
chk("captured_pct", cap, OLD["captured_pct"])

# ---- extrapolation -------------------------------------------------------
allc, alld = [], []
for d in K.DEMANDS:
    tr = [c for c in K.CTXS if K.META[c][0] != d]; te = [c for c in K.CTXS if K.META[c][0] == d]
    ch, _ = K.fit_select(T, C, tr, te)
    hb = {c: min(cost[c].values()) for c in te}
    r = [cost[c][ch[c]] - hb[c] for c in te]; dd = [cost[c]["DTT"] - hb[c] for c in te]
    chk(f"extrap.{d}.cart", st.mean(r), OLD["extrapolation"][str(d)]["cart"])
    chk(f"extrap.{d}.dtt", st.mean(dd), OLD["extrapolation"][str(d)]["dtt"])
    chk(f"extrap.{d}.chosen", sorted(set(ch.values())), OLD["extrapolation"][str(d)]["chosen"])
    allc += r; alld += dd
chk("extrap_pooled_cart", st.mean(allc), OLD["extrap_pooled_cart"])
chk("extrap_pooled_dtt", st.mean(alld), OLD["extrap_pooled_dtt"])

# ---- transition ----------------------------------------------------------
for sig in ("Balanced", "Arterial"):
    for restr in K.RES:
        row = []
        for q in K.DEMANDS:
            c = [k for k in K.CTXS if K.META[k] == (q, restr, sig)][0]
            row.append(cost[c]["SP"] - cost[c]["DTT"])
        o = OLD["transition"][f"{sig}|{restr}"]
        for i in range(3):
            chk(f"margin.{sig}.{restr}.{K.DEMANDS[i]}", row[i], o["margins"][i])
        br = None
        for i in range(2):
            if row[i] < 0 <= row[i + 1]:
                br = [K.DEMANDS[i], K.DEMANDS[i + 1]]
        chk(f"bracket.{sig}.{restr}", br, o["bracket"])

for q in K.DEMANDS:
    chk(f"worst_policy_regret.{q}",
        st.mean(max(cost[c].values()) - min(cost[c].values()) for c in K.CTXS if K.META[c][0] == q),
        OLD["worst_policy_regret"][str(q)])

# ---- seed stability + ECO ------------------------------------------------
SM = K.seed_means("time"); SC = K.seed_means("co2")
sc = {s: {c: {p: 0.5 * SM[s][c][p] / aT + 0.5 * SC[s][c][p] / aC for p in K.POL} for c in K.CTXS} for s in K.SEEDS}
unst = [c for c in K.CTXS if len({min(sc[s][c], key=lambda p: sc[s][c][p]) for s in K.SEEDS}) > 1]
chk("seed_stable_winner", 24 - len(unst), OLD["seed_stable_winner"])
chk("seed_unstable_ctx", unst, OLD["seed_unstable_ctx"])
flip = [c for c in K.CTXS if len({sc[s][c]["SP"] - sc[s][c]["DTT"] > 0 for s in K.SEEDS}) > 1]
chk("seed_stable_margin_sign", 24 - len(flip), OLD["seed_stable_margin_sign"])
chk("seed_margin_flip_ctx", flip, OLD["seed_margin_flip_ctx"])
chk("eco_identical_to_sp",
    sum(1 for c in K.CTXS if abs(T6[c]["SP"] - T6[c]["ECO"]) < 1e-9 and abs(C6[c]["SP"] - C6[c]["ECO"]) < 1e-9),
    OLD["eco_identical_to_sp"])

print(f"verified {checks} quantities against analysis/results.json")
if fails:
    print(f"MISMATCHES ({len(fails)}):")
    for n, g, w in fails:
        print(f"  {n}: got {g!r} expected {w!r}")
else:
    print("ALL MATCH — every published number reproduces from runs.csv")
