"""Distribution-shift evaluation.

Each split is reported on its own.  Pooling shifts of different kinds into one
average would hide the only thing the experiment can say about them, which is
that they behave differently.
"""
import numpy as np
import common as K
import policy_selectors as S

# Declared in the frozen specification, section 9.
SPLITS = [
    ("O1_demand_high",  "demand",       4200.0, "extrapolation",
     "held-out demand is above every demand seen in training"),
    ("O2_demand_low",   "demand",       1200.0, "extrapolation",
     "held-out demand is below every demand seen in training"),
    ("O3_demand_mid",   "demand",       2400.0, "interpolation",
     "held-out demand lies inside the training range: the control"),
    ("O4_lag_long",     "lag",           300.0, "extrapolation",
     "held-out information lag is longer than any seen in training"),
    ("O5_penetration",  "penetration",     0.8, "extrapolation",
     "held-out penetration is higher than any seen in training"),
    ("O6_green_high",   "gc",             0.65, "extrapolation",
     "held-out green ratio is higher than any seen in training"),
    ("O7_incident",     "incident",        1.0, "covariate + concept shift",
     "trained without any disruption, tested under disruption"),
]


def run_split(X, C, noise, meta, col, level):
    vals = np.array([m[col] for m in meta], float)
    te = np.where(np.isclose(vals, level))[0]
    tr = np.where(~np.isclose(vals, level))[0]
    if len(te) == 0 or len(tr) == 0:
        return None
    out, ex = S.fit_predict(tr, te, X, C)
    r = {}
    for k, ch in out.items():
        r[k] = S.evaluate(C[te], ch, noise[te])
    r["_n_test"], r["_n_train"] = int(len(te)), int(len(tr))
    r["_abstain_rate"] = float(ex["abstain"].mean())
    r["_out_of_support_rate"] = float((~ex["support_ok"]).mean())
    r["_sbs_policy"] = K.POLICIES[ex["sbs"]]
    # what abstention bought: regret of B4 on exactly the contexts B5 declined
    ab = ex["abstain"]
    if ab.any():
        b4 = S.evaluate(C[te][ab], out["B4_GBDT"][ab], noise[te][ab])
        b5 = S.evaluate(C[te][ab], out["B5_selective"][ab], noise[te][ab])
        r["_on_abstained"] = {"B4_mean_regret": b4["mean_regret"],
                              "B5_mean_regret": b5["mean_regret"],
                              "n": int(ab.sum())}
    if (~ab).any():
        r["_on_acted"] = {
            "B4_mean_regret": S.evaluate(C[te][~ab], out["B4_GBDT"][~ab],
                                         noise[te][~ab])["mean_regret"],
            "n": int((~ab).sum())}
    return r


def all_splits(X, C, noise, meta):
    res = {}
    for name, col, level, kind, why in SPLITS:
        r = run_split(X, C, noise, meta, col, level)
        if r is None:
            continue
        r["_shift_type"], r["_description"] = kind, why
        r["_held_out"] = f"{col} = {level}"
        res[name] = r
    return res


def domain_split(Xtr, Ctr, noisetr, Xte, Cte, noisete):
    """O8: incident on a corridor absent from every training context."""
    tr = np.arange(len(Xtr))
    Xall = np.vstack([Xtr, Xte]); Call = np.vstack([Ctr, Cte])
    te = np.arange(len(Xtr), len(Xall))
    out, ex = S.fit_predict(tr, te, Xall, Call)
    r = {k: S.evaluate(Cte, ch, noisete) for k, ch in out.items()}
    r.update(_n_test=int(len(te)), _n_train=int(len(tr)),
             _abstain_rate=float(ex["abstain"].mean()),
             _out_of_support_rate=float((~ex["support_ok"]).mean()),
             _sbs_policy=K.POLICIES[ex["sbs"]],
             _shift_type="domain shift",
             _held_out="incident located on the bypass corridor",
             _description=("the disruption occurs on a corridor that carries no "
                           "disruption in any training context"))
    ab = ex["abstain"]
    if ab.any():
        r["_on_abstained"] = {
            "B4_mean_regret": S.evaluate(Cte[ab], out["B4_GBDT"][ab],
                                         noisete[ab])["mean_regret"],
            "B5_mean_regret": S.evaluate(Cte[ab], out["B5_selective"][ab],
                                         noisete[ab])["mean_regret"],
            "n": int(ab.sum())}
    return r
