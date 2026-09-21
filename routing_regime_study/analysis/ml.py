"""Decisive diagnostic 2: held-out policy-selection evaluation on existing 432 runs.
No new simulation. No tuning on test. Reference scales fit on training contexts only."""
import csv, statistics as st, numpy as np
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor
R=[dict(r,time=float(r['time']),co2=float(r['co2']),ins=float(r['ins']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]          # portfolio chosen on evidence: ECO outcome-identical to SP in 21/24
CT=defaultdict(dict); CC=defaultdict(dict)
for p in POL:
    g=defaultdict(list)
    for x in R:
        if x['policy']==p: g[x['ctx']].append(x)
    for c in g:
        CT[c][p]=st.mean(y['time'] for y in g[c]); CC[c][p]=st.mean(y['co2'] for y in g[c])
ctxs=sorted(CT)
meta={}
for x in R: meta[x['ctx']]=(x['demand'],x['restr'],x['signal'])
RES=["None","U","C","L"]
def feats(c):
    d,r,s=meta[c]
    return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
X=np.array([feats(c) for c in ctxs])

def evaluate(folds, depth=3, leaf=2, name=""):
    """folds: list of (train_ctx, test_ctx). Returns per-context chosen policy."""
    chosen={}
    for tr,te in folds:
        aT=st.mean(CT[c][p] for c in tr for p in POL)      # TRAIN-ONLY reference scales
        aC=st.mean(CC[c][p] for c in tr for p in POL)
        Xtr=np.array([feats(c) for c in tr])
        Ytr=np.array([[CT[c][p]/aT for p in POL]+[CC[c][p]/aC for p in POL] for c in tr])
        m=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=0).fit(Xtr,Ytr)
        for c in te:
            yp=m.predict(np.array([feats(c)]))[0]
            cost=[0.5*yp[i]+0.5*yp[i+len(POL)] for i in range(len(POL))]
            chosen[c]=POL[int(np.argmin(cost))]
    return chosen

def score(chosen,label):
    aT=st.mean(CT[c][p] for c in ctxs for p in POL); aC=st.mean(CC[c][p] for c in ctxs for p in POL)
    cost={c:{p:0.5*CT[c][p]/aT+0.5*CC[c][p]/aC for p in POL} for c in ctxs}
    hb={c:min(cost[c].values()) for c in ctxs}
    reg=[cost[c][chosen[c]]-hb[c] for c in ctxs]
    dtt=[cost[c]['DTT']-hb[c] for c in ctxs]
    nb=sum(1 for c in ctxs if cost[c][chosen[c]]<=hb[c]*1.01)
    cap=(st.mean(dtt)-st.mean(reg))/st.mean(dtt)*100 if st.mean(dtt)>0 else 0
    hit=sum(1 for c in ctxs if abs(cost[c][chosen[c]]-hb[c])<1e-12)
    print(f"  {label:34s} meanReg={st.mean(reg):.5f}  maxReg={max(reg):.5f}  "
          f"best-policy hits={hit:2d}/24  near-best(1%)={nb:2d}/24  headroom captured={cap:+6.1f}%")
    return st.mean(reg)

aT=st.mean(CT[c][p] for c in ctxs for p in POL); aC=st.mean(CC[c][p] for c in ctxs for p in POL)
cost={c:{p:0.5*CT[c][p]/aT+0.5*CC[c][p]/aC for p in POL} for c in ctxs}
hb={c:min(cost[c].values()) for c in ctxs}
print("="*92); print("REFERENCE POINTS (full-data, descriptive)"); print("="*92)
for p in POL: score({c:p for c in ctxs}, f"fixed {p}")
score({c:min(cost[c],key=lambda q:cost[c][q]) for c in ctxs}, "Hindsight Best-Policy (not deployable)")
print(f"  {'AVAILABLE HEADROOM vs best fixed DTT':34s} mean={st.mean(cost[c]['DTT']-hb[c] for c in ctxs):.5f}  max={max(cost[c]['DTT']-hb[c] for c in ctxs):.5f}")

print("\n"+"="*92); print("HELD-OUT EVALUATIONS (model + scales refit per fold; test never seen)"); print("="*92)
loco=[([c for c in ctxs if c!=t],[t]) for t in ctxs]
score(evaluate(loco), "CART  leave-one-context-out")
lro=[]
for r in RES:
    te=[c for c in ctxs if meta[c][1]==r]; lro.append(([c for c in ctxs if c not in te],te))
score(evaluate(lro), "CART  leave-one-restriction-out")
lqo=[]
for d in (720,1200,1680):
    te=[c for c in ctxs if meta[c][0]==d]; lqo.append(([c for c in ctxs if c not in te],te))
score(evaluate(lqo), "CART  leave-one-DEMAND-out (extrap)")
half=([c for i,c in enumerate(ctxs) if i%2==0],[c for i,c in enumerate(ctxs) if i%2==1])
score(evaluate([half,(half[1],half[0])]), "CART  2-fold interleaved split")
print("\n  Interpretable rule learned on all 24 contexts (for inspection only):")
m=DecisionTreeRegressor(max_depth=2,min_samples_leaf=2,random_state=0).fit(
    X,np.array([[CT[c][p]/aT for p in POL]+[CC[c][p]/aC for p in POL] for c in ctxs]))
from sklearn.tree import export_text
print("   features: demand/1000, restr_None, restr_U, restr_C, restr_L, signal_Balanced")
print("   " + export_text(m,feature_names=['demand','rNone','rU','rC','rL','sigBal']).replace("\n","\n   ")[:600])
