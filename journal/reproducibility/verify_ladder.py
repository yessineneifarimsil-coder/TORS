"""Re-run the frozen LOCO protocol on independently rebuilt matrices."""
import json, os, sys, math, collections, statistics as st, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import warnings; warnings.filterwarnings("ignore")
import policy_selectors as S
import common as K
RES = os.path.join(ROOT, "results")

FACT = ["demand", "gc", "penetration", "lag", "incident", "alt"]; POL = ["P1", "P2", "P3", "P4"]
def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")
SAT_C, SAT_N, CAP_FREE, CYCLE, YELLOW, FF_C = 1761.0, 1596.0, 1500.0, 90.0, 4.0, 324.0
def desc(m):
    g = (m["gc"] * CYCLE - YELLOW) / CYCLE
    cap = {"C": 2 * SAT_C * g, "N": m["alt"] * SAT_N * g, "S": CAP_FREE}
    tot = sum(cap.values()); D, p = m["demand"], m["penetration"]
    return [D / tot, D / cap["C"], cap["N"] / tot, g, p, m["lag"] / FF_C, float(m["incident"]), p * D / cap["C"]]

rows = [json.loads(l) for l in open(os.path.join(RES, "main.jsonl")) if l.strip()]
cell = collections.defaultdict(list)
for r in rows: cell[(ctx_key(r), r["policy"])].append(r)
ctxs = sorted({k[0] for k in cell})
X = np.zeros((len(ctxs), 8)); C = np.zeros((len(ctxs), 4)); noise = np.zeros(len(ctxs))
for i, ck in enumerate(ctxs):
    g0 = sorted(cell[(ck, "P1")], key=lambda x: x["seed"])[0]
    X[i] = desc({f: g0[f] for f in FACT})
    vecs = {}
    for j, p in enumerate(POL):
        gg = sorted(cell[(ck, p)], key=lambda x: x["seed"])
        C[i, j] = st.mean(x["C1_sys"] for x in gg); vecs[p] = [x["C1_sys"] for x in gg]
    best = POL[int(np.argmin(C[i]))]
    ses = []
    for p in POL:
        if p == best: continue
        d = np.array(vecs[p]) - np.array(vecs[best]); ses.append(d.std(ddof=1) / math.sqrt(len(d)))
    noise[i] = 2.0 * max(ses)
print(f"matrices rebuilt: X{X.shape} C{C.shape}; mean noise floor {noise.mean():.6f} s", flush=True)

t0 = time.time()
res, abst, supp = S.loco(X, C, noise)
print(f"LOCO finished in {time.time()-t0:.0f} s", flush=True)
lad = S.ladder(C, res, noise)
acc = {k: float((v == np.argmin(C, axis=1)).mean()) for k, v in res.items()}
out = dict(ladder=lad.to_dict("records"), top1=acc,
           abstention_rate=float(abst.mean()), out_of_support_rate=float((~supp).mean()),
           b5_equals_b0=bool((res["B5_selective"] == res["B0_SBS"]).all()),
           b4_deviates_from_sbs=int((res["B4_GBDT"] != res["B0_SBS"]).sum()),
           n_contexts=len(ctxs), mean_noise_floor=float(noise.mean()))
json.dump(out, open(os.path.join(HERE, "verify_ladder.json"), "w"), indent=1)

R = json.load(open(os.path.join(RES, "results.json")))
pub = {r["selector"]: r for r in R["ladder_loco"]}
print(f"\n{'selector':16s}{'mean(mine)':>12s}{'mean(pub)':>12s}{'max(mine)':>11s}{'max(pub)':>11s}{'gap(mine)':>11s}{'gap(pub)':>10s}")
bad = 0
for r in lad.to_dict("records"):
    k = r["selector"]; p = pub.get(k)
    if not p: continue
    ok = abs(r["mean_regret"] - p["mean_regret"]) < 1e-9
    bad += (not ok)
    print(f"{k:16s}{r['mean_regret']:12.6f}{p['mean_regret']:12.6f}{r['max_regret']:11.4f}{p['max_regret']:11.4f}"
          f"{r['gap_closed_vs_SBS']:11.4f}{p['gap_closed_vs_SBS']:10.4f}{'' if ok else '   <<< MISMATCH'}")
print(f"\ntop-1 (mine): {({k: round(v,6) for k,v in acc.items()})}")
print(f"top-1 (pub) : {({k: round(v,6) for k,v in R['top1_accuracy'].items()})}")
print(f"abstention {out['abstention_rate']:.6f} (pub {R['ladder_loco_abstention']['rate']:.6f}); "
      f"out-of-support {out['out_of_support_rate']:.6f} (pub {R['ladder_loco_abstention']['out_of_support_rate']:.6f})")
print(f"B5 identical to B0 in every context: {out['b5_equals_b0']}")
print(f"B4 deviates from the fixed policy in {out['b4_deviates_from_sbs']} of {len(ctxs)} contexts")
print(f"ladder mismatches: {bad}")
