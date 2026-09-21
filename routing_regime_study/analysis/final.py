import csv, statistics as st, numpy as np, math
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
CT,CC=defaultdict(dict),defaultdict(dict)
for p in POL:
    g=defaultdict(list)
    for x in R:
        if x['policy']==p: g[x['ctx']].append(x)
    for c in g: CT[c][p]=st.mean(y['time'] for y in g[c]); CC[c][p]=st.mean(y['co2'] for y in g[c])
ctxs=sorted(CT)
def feats(c):
    d,r,s=meta[c]; return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
aT=st.mean(CT[c][p] for c in ctxs for p in POL); aC=st.mean(CC[c][p] for c in ctxs for p in POL)
cost={c:{p:0.5*CT[c][p]/aT+0.5*CC[c][p]/aC for p in POL} for c in ctxs}
hb={c:min(cost[c].values()) for c in ctxs}
# LOCO with prediction metrics
predT,predC,obsT,obsC,chosen={},{},{},{},{}
for t in ctxs:
    tr=[c for c in ctxs if c!=t]
    a1=st.mean(CT[c][p] for c in tr for p in POL); a2=st.mean(CC[c][p] for c in tr for p in POL)
    m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[CT[c][p]/a1 for p in POL]+[CC[c][p]/a2 for p in POL] for c in tr]))
    yp=m.predict(np.array([feats(t)]))[0]
    for i,p in enumerate(POL):
        predT[(t,p)]=yp[i]*a1; predC[(t,p)]=yp[i+3]*a2; obsT[(t,p)]=CT[t][p]; obsC[(t,p)]=CC[t][p]
    chosen[t]=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
k=list(predT)
maeT=st.mean(abs(predT[i]-obsT[i]) for i in k); rmseT=math.sqrt(st.mean((predT[i]-obsT[i])**2 for i in k))
maeC=st.mean(abs(predC[i]-obsC[i]) for i in k); rmseC=math.sqrt(st.mean((predC[i]-obsC[i])**2 for i in k))
print("="*92); print("FINAL HELD-OUT RESULT — CART policy selector, leave-one-context-out, 24 contexts"); print("="*92)
print(f"\nPREDICTION  time  MAE={maeT:7.2f} s   RMSE={rmseT:7.2f} s   (relative MAE {maeT/st.mean(obsT.values()):.1%})")
print(f"PREDICTION  CO2   MAE={maeC:7.2f} g   RMSE={rmseC:7.2f} g   (relative MAE {maeC/st.mean(obsC.values()):.1%})")
print("\nDECISION")
rows=[]
def row(lab,ch):
    reg=[cost[c][ch[c]]-hb[c] for c in ctxs]
    hits=sum(1 for c in ctxs if abs(cost[c][ch[c]]-hb[c])<1e-12)
    nb=sum(1 for c in ctxs if cost[c][ch[c]]<=hb[c]*1.01)
    rows.append((lab,st.mean(reg),max(reg),hits,nb))
for p in POL: row(f"fixed {p}",{c:p for c in ctxs})
row("CART adaptive (held-out)",chosen)
row("Hindsight Best-Policy",{c:min(cost[c],key=lambda q:cost[c][q]) for c in ctxs})
print(f"  {'method':28s} {'meanRegret':>11s} {'maxRegret':>10s} {'best-hits':>10s} {'near-best':>10s}")
for lab,mr,xr,h,nb in rows: print(f"  {lab:28s} {mr:11.5f} {xr:10.5f} {h:9d}/24 {nb:9d}/24")
dtt=[r for r in rows if r[0]=='fixed DTT'][0][1]; ad=[r for r in rows if 'CART' in r[0]][0][1]
print(f"\n  available headroom (fixed DTT -> hindsight) = {dtt:.5f}")
print(f"  adaptive gain captured                      = {(dtt-ad)/dtt*100:.1f}%   remaining regret = {ad:.5f}")
print("\n  per-context decisions (held-out):")
print(f"  {'ctx':5s} {'q':>5s} {'restr':6s} {'signal':9s} {'hindsight':10s} {'CART':8s} {'regret':>8s}")
for c in ctxs:
    d,r,s=meta[c]; best=min(cost[c],key=lambda q:cost[c][q])
    print(f"  {c:5s} {d:5d} {r:6s} {s:9s} {best:10s} {chosen[c]:8s} {cost[c][chosen[c]]-hb[c]:8.5f}"
          + ("" if chosen[c]==best else "   MISS"))
