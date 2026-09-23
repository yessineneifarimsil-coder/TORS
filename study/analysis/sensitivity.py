"""Sensitivity: to the two frozen policy parameters, and to preference weights.

Answers two distinct questions that are often conflated:
  (a) does the RESULT depend on a parameter we had to choose?  (eps, lambda)
  (b) does the DECISION depend on the preference weights?      (profiles)
"""
import json, os, sys, collections, warnings
warnings.filterwarnings("ignore")
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K

RES = os.path.join(HERE, "..", "results")
# Declared in the frozen specification, section 4.
PROFILES = {"TIME": (0.70, 0.15, 0.15), "BALANCED": (0.40, 0.30, 0.30),
            "ENVIRONMENT": (0.20, 0.55, 0.25)}


def preference_sensitivity(ct):
    """Within each context, min-max normalise the three criteria and score each
    policy under the three declared profiles.  Report whether the preferred
    policy changes."""
    rows, changes = [], 0
    per_profile = collections.defaultdict(collections.Counter)
    agree_with_c1 = collections.Counter()
    for ck, g in ct.groupby("ctx_key"):
        g = g.set_index("policy")
        norm = {}
        for c in ("C1", "C2", "C3"):
            v = g[c].values.astype(float)
            rng = v.max() - v.min()
            norm[c] = (v - v.min()) / rng if rng > 0 else np.zeros_like(v)
        picks = {}
        for name, (w1, w2, w3) in PROFILES.items():
            sc = w1 * norm["C1"] + w2 * norm["C2"] + w3 * norm["C3"]
            p = g.index[int(np.argmin(sc))]
            picks[name] = p
            per_profile[name][p] += 1
        best_c1 = g["C1"].idxmin()
        for name, p in picks.items():
            if p == best_c1:
                agree_with_c1[name] += 1
        if len(set(picks.values())) > 1:
            changes += 1
        rows.append({"ctx_key": ck, **picks, "best_C1": best_c1})
    n = len(rows)
    return dict(
        n_contexts=n,
        frac_profile_changes_decision=changes / n,
        selection_by_profile={k: dict(v) for k, v in per_profile.items()},
        frac_profile_agrees_with_C1={k: agree_with_c1[k] / n for k in PROFILES},
        profiles={k: list(v) for k, v in PROFILES.items()})


def parameter_sensitivity():
    """P3 admissibility tolerance and P4 dispersion weight."""
    path = os.path.join(RES, "sens.jsonl")
    if not os.path.exists(path):
        return {"status": "sensitivity campaign not present"}
    sdf, _ = K.load(path)
    mdf, _ = K.load(os.path.join(RES, "main.jsonl"))
    out = {}
    for pol, col, base, alts in (("P3", "p3_eps", 0.20, [0.10, 0.30]),
                                 ("P4", "p4_lambda", 1.0, [0.5, 1.5])):
        keys = set(sdf[sdf.policy == pol].ctx_key.unique())
        ref = (mdf[(mdf.policy == pol) & (mdf.ctx_key.isin(keys))]
               .groupby("ctx_key")[K.PRIMARY].mean())
        rec = {}
        for a in alts:
            cur = (sdf[(sdf.policy == pol) & (np.isclose(sdf[col], a))]
                   .groupby("ctx_key")[K.PRIMARY].mean())
            common = ref.index.intersection(cur.index)
            d = (cur.loc[common] - ref.loc[common]).values
            rec[str(a)] = dict(
                n_contexts=int(len(common)),
                mean_change_s=float(np.mean(d)),
                median_change_s=float(np.median(d)),
                max_abs_change_s=float(np.max(np.abs(d))),
                mean_change_pct=float(np.mean(d / ref.loc[common].values) * 100))
        out[pol] = dict(parameter=col, frozen_value=base, alternatives=rec)
    return out


def winner_stability(ct, sens_path):
    """Does the identity of the best policy change when P3/P4 use a different
    parameter value?  This is the question that matters, not the cost change."""
    if not os.path.exists(sens_path):
        return {"status": "sensitivity campaign not present"}
    sdf, _ = K.load(sens_path)
    res = {}
    for pol, col, alts in (("P3", "p3_eps", [0.10, 0.30]),
                           ("P4", "p4_lambda", [0.5, 1.5])):
        for a in alts:
            sub = sdf[(sdf.policy == pol) & (np.isclose(sdf[col], a))]
            alt_cost = sub.groupby("ctx_key")[K.PRIMARY].mean()
            n_same = n_tot = 0
            for ck, g in ct.groupby("ctx_key"):
                if ck not in alt_cost.index:
                    continue
                g = g.set_index("policy")
                base_win = g["C1"].idxmin()
                costs = {p: g.loc[p, "C1"] for p in K.POLICIES if p in g.index}
                costs[pol] = float(alt_cost.loc[ck])
                n_tot += 1
                if min(costs, key=costs.get) == base_win:
                    n_same += 1
            res[f"{pol}_{col}={a}"] = dict(
                n_contexts=n_tot,
                frac_winner_unchanged=(n_same / n_tot) if n_tot else None)
    return res


if __name__ == "__main__":
    df, _ = K.load(os.path.join(RES, "main.jsonl"))
    R = json.load(open(os.path.join(RES, "results.json")))
    df, _ = K.analysable(df, need_seeds=R["validity"]["need_seeds"])
    ct = K.context_table(df)
    out = dict(preference=preference_sensitivity(ct),
               parameters=parameter_sensitivity(),
               winner_stability=winner_stability(
                   ct, os.path.join(RES, "sens.jsonl")))
    R["sensitivity"] = out
    json.dump(R, open(os.path.join(RES, "results.json"), "w"), indent=1,
              default=str)
    print(json.dumps(out, indent=1, default=str)[:2200])
