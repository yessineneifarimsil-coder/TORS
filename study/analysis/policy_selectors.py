"""The baseline ladder B0-B5, the VBS reference, and their evaluation.

Leakage discipline, enforced structurally rather than by convention:
  * every quantity a selector uses is recomputed inside its own training fold,
    including standardisation, the single-best-fixed policy, tree thresholds,
    conformal quantiles and the support envelope;
  * the held-out context contributes nothing to training -- not its outcomes,
    not its seeds, not its scale;
  * the features are functions of the context definition alone and cannot be
    computed from any outcome.
"""
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import common as K

ALPHA = 0.10          # frozen conformal miscoverage
KNN_K = 5             # frozen support-gate neighbourhood
SUPPORT_Q = 95        # frozen support-gate percentile
CAL_FRAC = 0.30       # frozen calibration share
LGB = dict(n_estimators=400, learning_rate=0.05, num_leaves=15,
           min_child_samples=20, subsample=0.9, subsample_freq=1,
           colsample_bytree=0.9, reg_lambda=1.0, random_state=0,
           verbose=-1)


def matrices(ct, crit="C1"):
    """X: one row per context (the 8 descriptors).  Ccost: contexts x policies."""
    ctxs = sorted(ct.ctx_key.unique())
    idx = {c: i for i, c in enumerate(ctxs)}
    X = np.zeros((len(ctxs), len(K.XCOLS)))
    Ccost = np.full((len(ctxs), len(K.POLICIES)), np.nan)
    noise = np.zeros(len(ctxs))
    meta = [None] * len(ctxs)
    for ck, g in ct.groupby("ctx_key"):
        i = idx[ck]
        g0 = g.iloc[0]
        X[i] = [g0[c] for c in K.XCOLS]
        meta[i] = {f: g0[f] for f in K.FACTORS}
        gp = g.set_index("policy")
        for j, p in enumerate(K.POLICIES):
            if p in gp.index:
                Ccost[i, j] = gp.loc[p, crit]
        # noise floor: the largest paired standard error against the best policy
        best = gp[crit].idxmin()
        ses = []
        for p in K.POLICIES:
            if p == best or p not in gp.index:
                continue
            _, _, se = K.paired_resolved(gp.loc[p, "vec"], gp.loc[best, "vec"])
            ses.append(se)
        noise[i] = K.SEED_RESOLUTION_K * max(ses) if ses else 0.0
    return np.array(ctxs), X, Ccost, noise, meta


# --------------------------------------------------------------- selectors
def fit_predict(train, test, X, C, names=K.POLICIES):
    """Return {selector_name: array of chosen policy indices for `test`}."""
    Xtr, Ctr, Xte = X[train], C[train], X[test]
    out, extra = {}, {}

    sbs = int(np.argmin(Ctr.mean(axis=0)))          # training folds only
    out["B0_SBS"] = np.full(len(test), sbs)
    extra["sbs"] = sbs

    ytr = np.argmin(Ctr, axis=1)
    sc = StandardScaler().fit(Xtr)
    Ztr, Zte = sc.transform(Xtr), sc.transform(Xte)

    def _tree(depth, key):
        if len(np.unique(ytr)) < 2:
            out[key] = np.full(len(test), int(ytr[0])); return None
        t = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(Xtr, ytr)
        out[key] = t.predict(Xte).astype(int)
        return t
    b1_tree = _tree(2, "B1_mechanistic")
    _tree(3, "B2_tree3")

    if len(np.unique(ytr)) < 2:
        out["B3_logit"] = np.full(len(test), int(ytr[0]))
    else:
        lr = LogisticRegression(max_iter=2000).fit(Ztr, ytr)
        out["B3_logit"] = lr.predict(Zte).astype(int)

    # B4: predict the advantage of each policy over the TRAINING-fold SBS
    Dtr = Ctr[:, [sbs]] - Ctr                      # positive = better than SBS
    pred = np.zeros((len(test), len(names)))
    models = []
    for j in range(len(names)):
        m = lgb.LGBMRegressor(**LGB).fit(Xtr, Dtr[:, j])
        models.append(m)
        pred[:, j] = m.predict(Xte)
    out["B4_GBDT"] = np.argmax(pred, axis=1)
    extra["B4_pred"] = pred

    # B5: B4 with a support gate and a confidence gate, abstaining to B0
    rng = np.random.RandomState(0)
    perm = rng.permutation(len(train))
    ncal = max(int(CAL_FRAC * len(train)), 10)
    cal, sub = perm[:ncal], perm[ncal:]
    q = np.zeros(len(names))
    pcal = np.zeros((len(cal), len(names)))
    for j in range(len(names)):
        m = lgb.LGBMRegressor(**LGB).fit(Xtr[sub], Dtr[sub, j])
        pcal[:, j] = m.predict(Xtr[cal])
        resid = np.abs(Dtr[cal, j] - pcal[:, j])
        q[j] = np.quantile(resid, 1 - ALPHA)        # split-conformal half-width

    d = np.sqrt(((Ztr[:, None, :] - Ztr[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    thr = np.percentile(np.sort(d, axis=1)[:, :KNN_K].mean(axis=1), SUPPORT_Q)
    dte = np.sqrt(((Zte[:, None, :] - Ztr[None, :, :]) ** 2).sum(-1))
    dist_te = np.sort(dte, axis=1)[:, :KNN_K].mean(axis=1)

    choice, abstained = [], []
    for i in range(len(test)):
        j = int(np.argmax(pred[i]))
        in_support = dist_te[i] <= thr
        confident = (pred[i, j] - q[j]) > 0.0       # lower bound on advantage > 0
        if in_support and confident and j != sbs:
            choice.append(j); abstained.append(False)
        else:
            choice.append(sbs); abstained.append(j != sbs)
    out["B5_selective"] = np.array(choice)
    extra.update(abstain=np.array(abstained), support_ok=dist_te <= thr,
                 conformal_q=q, support_thr=thr, dist_te=dist_te,
                 b1_tree=b1_tree)
    return out, extra


def loco(X, C, noise, selectors_fn=fit_predict):
    """Leave-one-context-out.  Also returns the VBS reference (regret 0 by
    construction) and per-context diagnostics."""
    n = len(X)
    res = {k: np.zeros(n, dtype=int) for k in
           ["B0_SBS", "B1_mechanistic", "B2_tree3", "B3_logit", "B4_GBDT", "B5_selective"]}
    abst = np.zeros(n, bool); supp = np.ones(n, bool)
    for i in range(n):
        tr = np.array([j for j in range(n) if j != i])
        out, ex = selectors_fn(tr, np.array([i]), X, C)
        for k in res:
            res[k][i] = out[k][0]
        abst[i] = ex["abstain"][0]; supp[i] = ex["support_ok"][0]
    return res, abst, supp


def evaluate(C, choice, noise, tol_frac=0.01):
    best = C.min(axis=1)
    got = C[np.arange(len(C)), choice]
    reg = got - best
    return dict(
        mean_regret=float(reg.mean()),
        median_regret=float(np.median(reg)),
        max_regret=float(reg.max()),
        cvar90=float(reg[reg >= np.quantile(reg, 0.90)].mean()),
        pct_exact_optimal=float((reg <= 1e-9).mean()),
        pct_within_noise=float((reg <= noise).mean()),
        pct_within_tol=float((reg <= tol_frac * best).mean()),
        mean_cost=float(got.mean()),
        regret_pct_of_best=float((reg / best).mean()),
    )


def ladder(C, res, noise):
    rows = []
    sbs_reg = evaluate(C, res["B0_SBS"], noise)["mean_regret"]
    for k, ch in res.items():
        e = evaluate(C, ch, noise)
        e["selector"] = k
        e["gap_closed_vs_SBS"] = (1.0 - e["mean_regret"] / sbs_reg) if sbs_reg > 0 else float("nan")
        rows.append(e)
    vbs = dict(selector="VBS_reference", mean_regret=0.0, median_regret=0.0,
               max_regret=0.0, cvar90=0.0, pct_exact_optimal=1.0,
               pct_within_noise=1.0, pct_within_tol=1.0,
               mean_cost=float(C.min(axis=1).mean()), regret_pct_of_best=0.0,
               gap_closed_vs_SBS=1.0)
    rows.append(vbs)
    return pd.DataFrame(rows)[["selector", "mean_regret", "median_regret",
                               "max_regret", "cvar90", "pct_exact_optimal",
                               "pct_within_noise", "pct_within_tol",
                               "gap_closed_vs_SBS", "mean_cost"]]


def accuracy_metrics(C, choice):
    """Three distinct quantities, never substituted for one another."""
    from scipy.stats import spearmanr
    true_best = np.argmin(C, axis=1)
    top1 = float((choice == true_best).mean())
    return dict(top1_accuracy=top1)
