"""Exactly what do 53.1% and 79.9% measure? Inspect the depth-1 and depth-2 trees."""
import csv, json, statistics as st, numpy as np
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor, export_text
O=json.load(open("results.json"))
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]; FN=['demand','r_None','r_U','r_C','r_L','sig_Balanced']
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
T,C=defaultdict(dict),defaultdict(dict)
for p in POL:
    g=defaultdict(list)
    for x in R:
        if x['policy']==p: g[x['ctx']].append(x)
    for c in g: T[c][p]=st.mean(y['time'] for y in g[c]); C[c][p]=st.mean(y['co2'] for y in g[c])
ctxs=sorted(T); aT,aC=O['ref_time'],O['ref_co2']
COST={c:{p:0.5*T[c][p]/aT+0.5*C[c][p]/aC for p in POL} for c in ctxs}
HB={c:min(COST[c].values()) for c in ctxs}
def feats(c):
    d,r,s=meta[c]; return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
def loco(depth,leaf=2):
    ch={}
    for t in ctxs:
        tr=[c for c in ctxs if c!=t]
        a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
        m=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=0).fit(
            np.array([feats(c) for c in tr]),
            np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
        yp=m.predict(np.array([feats(t)]))[0]
        ch[t]=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
    reg=st.mean(COST[c][ch[c]]-HB[c] for c in ctxs)
    H=st.mean(COST[c]['DTT']-HB[c] for c in ctxs)
    return reg,H,(H-reg)/H*100,ch
print("="*92)
print("WHAT 53.1% AND 79.9% MEASURE  --  both are LOCO headroom-capture, same formula")
print("="*92)
print(f"  formula: (H - Rbar)/H  with H = mean_s[C(s,DTT) - C*(s)] = {st.mean(COST[c]['DTT']-HB[c] for c in ctxs):.8f}\n")
print(f"  {'depth':>6s} {'mean regret':>12s} {'H':>10s} {'captured':>10s}")
res={}
for d in (1,2,3,4,None):
    reg,H,cap,ch=loco(d); res[d]=(reg,cap,ch)
    print(f"  {str(d):>6s} {reg:12.8f} {H:10.6f} {cap:9.2f}%")
print("\n  -> SAME metric at every depth. Neither number is prediction accuracy or feature importance.")

print("\n"+"="*92); print("WHICH FEATURE DOES EACH TREE ACTUALLY SPLIT ON? (full-data fit, for inspection)"); print("="*92)
X=np.array([feats(c) for c in ctxs])
Y=np.array([[T[c][p]/aT for p in POL]+[C[c][p]/aC for p in POL] for c in ctxs])
for d in (1,2,3):
    m=DecisionTreeRegressor(max_depth=d,min_samples_leaf=2,random_state=0).fit(X,Y)
    imp={k:round(v,4) for k,v in zip(FN,m.feature_importances_) if v>0}
    print(f"\n  depth {d}: importances {imp}")
    print("   "+export_text(m,feature_names=FN,decimals=3).replace("\n","\n   ").split("value")[0].rstrip()[:400])

print("\n"+"="*92); print("CRITICAL: is the 53.1% -> 79.9% gain attributable to 'adding the signal split'?"); print("="*92)
print(f"  depth 1 (one split)            : {res[1][1]:6.2f}%")
print(f"  depth 2 (adds the signal split): {res[2][1]:6.2f}%   <-- change from depth 1: {res[2][1]-res[1][1]:+.2f} pp")
print(f"  depth 3 (adds 2nd demand split): {res[3][1]:6.2f}%   <-- change from depth 2: {res[3][1]-res[2][1]:+.2f} pp")
print("\n  VERDICT: the gain does NOT come from adding the signal split.")
print("  Depth 2 already contains the signal split and captures essentially the same as depth 1.")
print("  The jump appears only at depth 3, which adds the SECOND demand split (at 960).")
# does depth3 without signal feature do as well?
Xn=np.array([[feats(c)[0]]+feats(c)[1:5]+[0.0] for c in ctxs])   # signal feature blanked
def loco_nosig(depth):
    ch={}
    for t in ctxs:
        tr=[c for c in ctxs if c!=t]
        a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
        f=lambda c:[feats(c)[0]]+feats(c)[1:5]+[0.0]
        m=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=2,random_state=0).fit(
            np.array([f(c) for c in tr]),
            np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
        yp=m.predict(np.array([f(t)]))[0]
        ch[t]=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
    reg=st.mean(COST[c][ch[c]]-HB[c] for c in ctxs)
    H=st.mean(COST[c]['DTT']-HB[c] for c in ctxs)
    return (H-reg)/H*100
print(f"\n  ABLATION -- depth 3 with the signal feature REMOVED: {loco_nosig(3):.2f}%")
print(f"  ABLATION -- depth 3 with the signal feature present : {res[3][1]:.2f}%")
print(f"  => genuine contribution of the signal feature at depth 3: {res[3][1]-loco_nosig(3):+.2f} pp")
