"""Evaluate the four pre-declared screening gates.

The thresholds are read from the frozen specification and are not arguments.
The script reports whichever answer the data gives.
"""
import sys, json, itertools, collections
import numpy as np
import common as K

G1_MIN_WINNING = 3
G2_MIN_PARETO_FRACTION = 0.25
G3_MAX_IDENTITY = 0.50
G4_MAX_STUMP_ACC = 0.95

df, bad = K.load(sys.argv[1] if len(sys.argv) > 1 else "../results/screen.jsonl")
print(f"runs={len(df)}  failed={len(bad)}  contexts={df.ctx_key.nunique()}  "
      f"seeds/cell={df.groupby(['ctx_key','policy']).size().min()}-"
      f"{df.groupby(['ctx_key','policy']).size().max()}")
inval = df[(df.completion < 0.98) | (df.teleports > 0)]
print(f"invalid runs (completion<0.98 or teleports>0): {len(inval)}")
if len(inval):
    for _, r in inval.head(10).iterrows():
        print(f"    {r.ctx_key} {r.policy} seed={r.seed} compl={r.completion:.3f} "
              f"tele={r.teleports}")

ct = K.context_table(df)
W = K.winners(ct)
PAR = K.pareto_by_context(ct)
res = {}

# ---- G1 complementarity -------------------------------------------------
wr = W[W.resolved]
winners_resolved = sorted(wr.winner.unique())
g1 = len(winners_resolved) >= G1_MIN_WINNING
res["G1"] = dict(passed=bool(g1), n_policies_winning=len(winners_resolved),
                 policies=winners_resolved, threshold=G1_MIN_WINNING,
                 counts_all=dict(collections.Counter(W.winner)),
                 counts_resolved=dict(collections.Counter(wr.winner)),
                 n_unresolved=int((~W.resolved).sum()))
print(f"\nG1 complementarity: {len(winners_resolved)} policies win a context with a "
      f"resolved margin (need >= {G1_MIN_WINNING})")
print(f"   winners, all contexts      : {dict(collections.Counter(W.winner))}")
print(f"   winners, resolved margin   : {dict(collections.Counter(wr.winner))}")
print(f"   contexts with unresolved margin: {int((~W.resolved).sum())}/{len(W)}")

# ---- G2 criterion conflict ---------------------------------------------
frac = (PAR.n_pareto > 1).mean()
res["G2"] = dict(passed=bool(frac >= G2_MIN_PARETO_FRACTION), fraction=float(frac),
                 threshold=G2_MIN_PARETO_FRACTION,
                 size_distribution=dict(collections.Counter(PAR.n_pareto)))
print(f"\nG2 criterion conflict: {K.fmt_pct(frac)} of contexts have a non-singleton "
      f"Pareto set (need >= {K.fmt_pct(G2_MIN_PARETO_FRACTION)})")
print(f"   Pareto-set size distribution: {dict(collections.Counter(PAR.n_pareto))}")

# ---- G3 non-degeneracy --------------------------------------------------
ident = {}
for a, b in itertools.combinations(K.POLICIES, 2):
    n_ident = 0
    for ck, g in ct.groupby("ctx_key"):
        g = g.set_index("policy")
        if a not in g.index or b not in g.index:
            continue
        r, _, _ = K.paired_resolved(g.loc[a, "vec"], g.loc[b, "vec"])
        tot = sum(g.loc[a, f"picks_{p}"] for p in "CNS")
        guided = max(g.loc[a, "penetration"] * tot, 1.0)
        split = sum(abs(g.loc[a, f"picks_{p}"] - g.loc[b, f"picks_{p}"]) for p in "CNS")
        if (not r) and (split / (2 * guided) < 0.02):
            n_ident += 1
    ident[f"{a}-{b}"] = n_ident / ct.ctx_key.nunique()
mean_ident = float(np.mean(list(ident.values())))
res["G3"] = dict(passed=bool(mean_ident <= G3_MAX_IDENTITY), mean_identity=mean_ident,
                 threshold=G3_MAX_IDENTITY, by_pair=ident)
print(f"\nG3 non-degeneracy: mean pairwise outcome identity {K.fmt_pct(mean_ident)} "
      f"(need <= {K.fmt_pct(G3_MAX_IDENTITY)})")
for k, v in ident.items():
    print(f"   {k}: {K.fmt_pct(v)}")

# ---- G4 multi-factor structure -----------------------------------------
best_acc, best_f = 0.0, None
for f in K.FACTORS:
    acc = 0
    for lvl, g in W.groupby(f):
        acc += collections.Counter(g.winner).most_common(1)[0][1]
    acc /= len(W)
    if acc > best_acc:
        best_acc, best_f = acc, f
const_acc = collections.Counter(W.winner).most_common(1)[0][1] / len(W)
res["G4"] = dict(passed=bool(best_acc < G4_MAX_STUMP_ACC), best_single_factor=best_f,
                 best_stump_accuracy=float(best_acc),
                 constant_rule_accuracy=float(const_acc), threshold=G4_MAX_STUMP_ACC)
print(f"\nG4 multi-factor structure: best single-factor stump is '{best_f}' at "
      f"{K.fmt_pct(best_acc)} (must be < {K.fmt_pct(G4_MAX_STUMP_ACC)})")
print(f"   constant 'always the same policy' rule: {K.fmt_pct(const_acc)}")

# ---- verdict ------------------------------------------------------------
go = res["G1"]["passed"] and res["G3"]["passed"] and res["G4"]["passed"]
res["verdict"] = dict(GO=bool(go),
                      note=("G2 is diagnostic: it does not gate the study, it "
                            "determines what may be claimed about multi-criteria "
                            "structure and whether a standalone eco-routing policy "
                            "is admissible."))
print("\n" + "=" * 68)
for g in ("G1", "G2", "G3", "G4"):
    print(f"  {g}: {'PASS' if res[g]['passed'] else 'FAIL'}"
          + ("   (diagnostic, not a gate)" if g == "G2" else ""))
print(f"  VERDICT: {'GO' if go else 'STOP'}  (requires G1, G3, G4)")
print("=" * 68)
json.dump(res, open("../results/screen_gates.json", "w"), indent=1, default=str)
