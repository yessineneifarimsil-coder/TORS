"""Decisive diagnostic 1: portfolio structure, headroom location, insertion-boundary sensitivity."""
import csv, statistics as st
from collections import defaultdict
R=[dict(r,time=float(r['time']),co2=float(r['co2']),ins=float(r['ins']),p95=float(r['p95']),
        dist=float(r['dist']),demand=int(r['demand']),stopped=float(r['stopped']),
        net_co2=float(r['net_co2']),bg_t=float(r['bg_t'])) for r in csv.DictReader(open("runs.csv"))]
for x in R: x['innet']=x['time']-x['ins']          # in-network time, excludes pre-insertion wait
POL=["SP","DTT","ECO","TECO05","TECO10","TECO15"]
def cmeans(key,pols=POL):
    m=defaultdict(dict)
    for p in pols:
        g=defaultdict(list)
        for x in R:
            if x['policy']==p: g[x['ctx']].append(x[key])
        for c in g: m[c][p]=st.mean(g[c])
    return m
T,C,I,P95=cmeans('time'),cmeans('co2'),cmeans('innet'),cmeans('p95')
ctxs=sorted(T)

print("="*78); print("1. PORTFOLIO DEGENERACY — outcome-identical policy pairs (24 contexts)"); print("="*78)
for a in range(len(POL)):
    for b in range(a+1,len(POL)):
        p,q=POL[a],POL[b]
        same=sum(1 for c in ctxs if abs(T[c][p]-T[c][q])<1e-9 and abs(C[c][p]-C[c][q])<1e-9)
        if same: print(f"   {p:7s} == {q:7s} in {same:2d}/24 contexts")
print("\n   distinct outcome points per context:",
      [len({(round(T[c][p],6),round(C[c][p],6)) for p in POL}) for c in ctxs])

print("\n"+"="*78); print("2. HEADROOM STRUCTURE (balanced additive cost, equal-mean reference)"); print("="*78)
for pols,label in [(POL,"all 6 settings"),(["SP","DTT","ECO","TECO10"],"core 4"),(["SP","DTT","TECO10"],"SP/DTT/TECO10")]:
    aT=st.mean(T[c][p] for c in ctxs for p in pols); aC=st.mean(C[c][p] for c in ctxs for p in pols)
    cost={c:{p:0.5*T[c][p]/aT+0.5*C[c][p]/aC for p in pols} for c in ctxs}
    win={c:min(cost[c],key=lambda p:cost[c][p]) for c in ctxs}
    hb={c:min(cost[c].values()) for c in ctxs}
    fixed={p:st.mean(cost[c][p]-hb[c] for c in ctxs) for p in pols}
    best=min(fixed,key=lambda p:fixed[p])
    nz=[c for c in ctxs if cost[c][best]-hb[c]>1e-9]
    print(f"\n   [{label}]  best fixed = {best}   mean regret = {fixed[best]:.5f}   "
          f"max = {max(cost[c][best]-hb[c] for c in ctxs):.5f}")
    print(f"      winner counts: { {p:sum(1 for c in ctxs if win[c]==p) for p in pols} }")
    print(f"      contexts where adaptive could beat {best}: {len(nz)}/24 -> {nz}")
    tot=sum(cost[c][best]-hb[c] for c in ctxs)
    top5=sorted(ctxs,key=lambda c:-(cost[c][best]-hb[c]))[:5]
    print(f"      top-5 contexts hold {sum(cost[c][best]-hb[c] for c in top5)/tot*100:.1f}% of all headroom")

print("\n"+"="*78); print("3. INSERTION-DELAY BOUNDARY — does it change the decision?"); print("="*78)
pols=["SP","DTT","ECO","TECO10"]
for key,lab,M in [('time','journey time (incl. insertion)',T),('innet','in-network time (excl. insertion)',I)]:
    aT=st.mean(M[c][p] for c in ctxs for p in pols); aC=st.mean(C[c][p] for c in ctxs for p in pols)
    cost={c:{p:0.5*M[c][p]/aT+0.5*C[c][p]/aC for p in pols} for c in ctxs}
    win={c:min(cost[c],key=lambda p:cost[c][p]) for c in ctxs}
    hb={c:min(cost[c].values()) for c in ctxs}
    fx={p:st.mean(cost[c][p]-hb[c] for c in ctxs) for p in pols}
    b=min(fx,key=lambda p:fx[p])
    print(f"   {lab:38s} winners={ {p:sum(1 for c in ctxs if win[c]==p) for p in pols} } "
          f"best fixed={b} meanregret={fx[b]:.5f}")
    globals()['W_'+key]=win
flips=[c for c in ctxs if W_time[c]!=W_innet[c]]
print(f"   -> winner FLIPS in {len(flips)}/24 contexts when insertion delay is excluded: {flips}")
print(f"   mean insertion share of journey time, by demand:")
for d in (720,1200,1680):
    g=[x for x in R if x['demand']==d]
    print(f"      q={d}: {st.mean(x['ins'] for x in g)/st.mean(x['time'] for x in g)*100:5.1f}%  "
          f"(SP {st.mean(x['ins'] for x in g if x['policy']=='SP'):7.1f}s vs DTT {st.mean(x['ins'] for x in g if x['policy']=='DTT'):7.1f}s)")
