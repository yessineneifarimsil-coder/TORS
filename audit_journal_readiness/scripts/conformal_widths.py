"""What actually sets the conformal gate's width?  Recompute the per-policy split-conformal
half-widths q_j for a sample of LOCO folds with the frozen fit_predict(), and compare them
with (a) the advantages available and (b) the manuscript's '20.90 s noise floor'."""
import sys, json, numpy as np, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/TORS/study/analysis"); sys.path.insert(0, "/home/user/TORS/audit_journal_readiness/scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("nf", "/home/user/TORS/audit_journal_readiness/scripts/noise_floor.py")
# rebuild X, C exactly as noise_floor.py does, without re-running LOCO
src = open(spec.origin).read().split("# ---------------------------------------------------------------- choices")[0]
ns = {}; exec(src, ns)
X, C, Y = ns["X"], ns["C"], ns["Y"]
import policy_selectors as S
n = len(X); rng = np.random.default_rng(1); folds = rng.choice(n, 24, replace=False)
qs, pos = [], []
for i in folds:
    tr = np.array([j for j in range(n) if j != i])
    out, ex = S.fit_predict(tr, np.array([i]), X, C)
    qs.append(ex["conformal_q"]); p = ex["B4_pred"][0]; pos.append(p.max())
qs = np.array(qs)
sbs = int(np.argmin(C.mean(axis=0)))
adv = C[:, [sbs]] - C
res = dict(folds_sampled=int(len(folds)),
           conformal_halfwidth_mean_by_policy={p: float(qs[:, j].mean()) for j, p in enumerate(["P1","P2","P3","P4"])},
           max_predicted_advantage_mean=float(np.mean(pos)),
           positive_true_advantage_mean_where_positive={p: float(adv[adv[:, j] > 1e-9, j].mean()) if (adv[:, j] > 1e-9).any() else 0.0 for j, p in enumerate(["P1","P2","P3","P4"])},
           true_advantage_p90_by_policy={p: float(np.quantile(adv[:, j], 0.9)) for j, p in enumerate(["P1","P2","P3","P4"])},
           seed_sd_of_SBS_mean_over_contexts=float((Y[:, sbs, :].std(axis=1, ddof=1) / np.sqrt(5)).mean()))
print(json.dumps(res, indent=1)); json.dump(res, open("outputs/conformal_widths.json", "w"), indent=1)
