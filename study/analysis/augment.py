"""Add the decision-value diagnostics to results.json.

These quantities are what distinguish 'the winner map is multi-policy' from
'exploiting the winner map is worth something'.  They are separate questions
and this study keeps them separate.
"""
import json, os, sys, warnings, collections
warnings.filterwarnings("ignore")
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K, policy_selectors as S

RES = os.path.join(HERE, "..", "results")
R = json.load(open(os.path.join(RES, "results.json")))
df, _ = K.load(os.path.join(RES, "main.jsonl"))
df, _ = K.analysable(df, need_seeds=max(R["campaign"]["seeds_per_cell"]))
ct = K.context_table(df)
per = ct.pivot_table(index="ctx_key", columns="policy", values="C1")
best = per.min(axis=1)
sbs = per.mean().idxmin()

# --- 1. cost of the fixed-policy choice itself
R["fixed_policy_choice"] = {
    "sbs": sbs,
    "mean_cost": {p: float(per[p].mean()) for p in K.POLICIES},
    "penalty_vs_sbs_s": {p: float(per[p].mean() - per[sbs].mean()) for p in K.POLICIES},
    "penalty_vs_sbs_pct": {p: float(100 * (per[p].mean() / per[sbs].mean() - 1))
                           for p in K.POLICIES},
    "worst_policy": per.mean().idxmax(),
    "worst_penalty_s": float(per.mean().max() - per[sbs].mean()),
    "worst_penalty_pct": float(100 * (per.mean().max() / per[sbs].mean() - 1)),
}

# --- 2. the asymmetry that makes the fixed policy near-dominant
loss = (per[sbs] - best)
margin = (per.drop(columns=sbs).min(axis=1) - per[sbs]).clip(lower=0)
R["asymmetry"] = {
    "sbs": sbs,
    "frac_contexts_sbs_not_best": float((loss > 0).mean()),
    "mean_loss_when_not_best_s": float(loss[loss > 0].mean()),
    "max_loss_s": float(loss.max()),
    "frac_contexts_sbs_best": float((margin > 0).mean()),
    "mean_margin_when_best_s": float(margin[margin > 0].mean()),
    "max_margin_s": float(margin.max()),
    "upside_downside_ratio": float(margin[margin > 0].mean() / loss[loss > 0].mean()),
}

# --- 3. is the headroom larger than the noise of the same comparison?
rows = []
for ck, g in ct.groupby("ctx_key"):
    g = g.set_index("policy"); b = g.C1.idxmin()
    if b == sbs:
        rows.append((0.0, 0.0, np.nan)); continue
    d = np.asarray(g.loc[sbs, "vec"], float) - np.asarray(g.loc[b, "vec"], float)
    rows.append((float(d.mean()), float(2 * d.std(ddof=1) / np.sqrt(len(d))),
                 float(d.std(ddof=1))))
hr = np.array([r[0] for r in rows]); nz = np.array([r[1] for r in rows])
sd = np.array([r[2] for r in rows])
nzm = hr > 0
eff = float(hr.mean()); sd_med = float(np.nanmedian(sd[nzm]))
R["resolvability"] = {
    "mean_headroom_s": eff,
    "n_contexts_sbs_not_best": int(nzm.sum()),
    "mean_headroom_where_nonzero_s": float(hr[nzm].mean()),
    "mean_noise_2se_where_nonzero_s": float(nz[nzm].mean()),
    "n_headroom_exceeds_own_noise": int((hr[nzm] > nz[nzm]).sum()),
    "frac_headroom_exceeds_own_noise": float((hr[nzm] > nz[nzm]).mean()),
    "median_sd_paired_difference_s": sd_med,
    "seeds_needed_for_mean_effect": int(np.ceil((2 * sd_med / eff) ** 2)),
    "runs_that_would_require": int(np.ceil((2 * sd_med / eff) ** 2)
                                   * len(per) * len(K.POLICIES)),
}

# --- 4. the mechanistic rule, and what its threshold means
ctxs, X, C, noise, meta = S.matrices(ct)
y = np.argmin(C, axis=1)
t2 = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, y)
f_i = int(t2.tree_.feature[0]); thr = float(t2.tree_.threshold[0])
col = X[:, f_i]
below, above = col[col <= thr], col[col > thr]
reg2 = float((C[np.arange(len(C)), t2.predict(X)] - C.min(axis=1)).mean())
sbs_i = K.POLICIES.index(sbs)
R["mechanistic_rule"] = {
    "root_feature": K.XCOLS[f_i],
    "root_threshold": thr,
    "bracket_low": float(below.max()), "bracket_high": float(above.min()),
    "rule_text": export_text(t2, feature_names=K.XCOLS),
    "in_sample_top1": float((t2.predict(X) == y).mean()),
    "in_sample_mean_regret_s": reg2,
    "in_sample_regret_of_fixed_sbs_s": float(
        (C[:, sbs_i] - C.min(axis=1)).mean()),
    "note": ("fitted on all contexts for exposition only; the evaluated "
             "version is refitted inside every leave-one-context-out fold"),
}

# --- 5. which policy minimises which criterion
spec = {}
for c in ("C1", "C2", "C3"):
    cc = collections.Counter(
        ct.groupby("ctx_key").apply(lambda g: g.set_index("policy")[c].idxmin()))
    spec[c] = {p: int(cc.get(p, 0)) for p in K.POLICIES}
R["criterion_specialisation"] = spec

json.dump(R, open(os.path.join(RES, "results.json"), "w"), indent=1, default=str)
print("augmented results.json with: fixed_policy_choice, asymmetry, "
      "resolvability, mechanistic_rule, criterion_specialisation")
for k in ("fixed_policy_choice", "asymmetry", "resolvability"):
    print(f"\n{k}:"); print(json.dumps(R[k], indent=1, default=str)[:600])
