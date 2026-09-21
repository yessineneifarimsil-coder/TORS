import csv, statistics as st, numpy as np
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
print("E. DEMAND-EXTRAPOLATION STRESS TEST (hold out an entire demand level)")
print(f"{'held-out q':>12s} {'CARTreg':>9s} {'fixedDTT':>9s} {'fixedSP':>9s} {'hindsight':>9s}  chosen")
tot_c=[];tot_d=[]
for d in (720,1200,1680):
    tr=[c for c in ctxs if meta[c][0]!=d]; te=[c for c in ctxs if meta[c][0]==d]
    a1=st.mean(CT[c][p] for c in tr for p in POL); a2=st.mean(CC[c][p] for c in tr for p in POL)
    m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[CT[c][p]/a1 for p in POL]+[CC[c][p]/a2 for p in POL] for c in tr]))
    ch={}
    for c in te:
        yp=m.predict(np.array([feats(c)]))[0]
        ch[c]=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
    r=st.mean(cost[c][ch[c]]-hb[c] for c in te); dd=st.mean(cost[c]['DTT']-hb[c] for c in te)
    sp=st.mean(cost[c]['SP']-hb[c] for c in te)
    tot_c+= [cost[c][ch[c]]-hb[c] for c in te]; tot_d+=[cost[c]['DTT']-hb[c] for c in te]
    print(f"{d:12d} {r:9.5f} {dd:9.5f} {sp:9.5f} {0.0:9.5f}  {sorted(set(ch.values()))} "
          f"{'<-- WORSE than fixed DTT' if r>dd+1e-9 else ''}")
print(f"{'POOLED':>12s} {st.mean(tot_c):9.5f} {st.mean(tot_d):9.5f}")
print(f"  headroom captured under demand extrapolation = {(st.mean(tot_d)-st.mean(tot_c))/st.mean(tot_d)*100:+.1f}%")
