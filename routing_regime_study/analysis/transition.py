"""Transition audit: localize the policy-switching boundary from the existing 432 runs."""
import csv, statistics as st
from collections import defaultdict
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
# context means (all seeds) and per-seed
CM=defaultdict(dict); SM=defaultdict(lambda: defaultdict(dict))
for x in R:
    if x['policy'] not in POL: continue
    SM[x['seed']][x['ctx']][x['policy']]=(x['time'],x['co2'])
for p in POL:
    g=defaultdict(list)
    for x in R:
        if x['policy']==p: g[x['ctx']].append(x)
    for c in g: CM[c][p]=(st.mean(y['time'] for y in g[c]), st.mean(y['co2'] for y in g[c]))
ctxs=sorted(CM)
aT=st.mean(CM[c][p][0] for c in ctxs for p in POL); aC=st.mean(CM[c][p][1] for c in ctxs for p in POL)
def cost(t,c): return 0.5*t/aT+0.5*c/aC
COST={c:{p:cost(*CM[c][p]) for p in POL} for c in ctxs}

print("="*100)
print("Q1/Q2/Q3  SWITCHING MARGIN  m = C(SP) - C(DTT).   m<0: SP preferred.  m>0: DTT preferred.")
print("="*100)
print(f"{'signal':10s} {'restr':6s} {'q=720':>12s} {'q=1200':>12s} {'q=1680':>12s}   bracket for sign change")
brackets=defaultdict(list)
for sig in ("Balanced","Arterial"):
    for restr in ("None","U","C","L"):
        row=[]
        for q in (720,1200,1680):
            c=[k for k in ctxs if meta[k]==(q,restr,sig)][0]
            row.append(COST[c]['SP']-COST[c]['DTT'])
        br=""
        for i in range(2):
            if row[i]<0<=row[i+1]: br=f"({(720,1200)[i]}, {(1200,1680)[i]}]"; brackets[sig].append(((720,1200)[i],(1200,1680)[i]))
        print(f"{sig:10s} {restr:6s} {row[0]:12.5f} {row[1]:12.5f} {row[2]:12.5f}   {br}")
print("\n  -> Balanced crossings all in:", sorted(set(brackets['Balanced'])))
print("  -> Arterial crossings all in:", sorted(set(brackets['Arterial'])))

print("\n"+"="*100); print("Q3  SIGNAL-REGIME EFFECT — winner at each demand level"); print("="*100)
for q in (720,1200,1680):
    for sig in ("Balanced","Arterial"):
        ws=[min(COST[c],key=lambda p:COST[c][p]) for c in ctxs if meta[c][0]==q and meta[c][2]==sig]
        marg=[COST[c]['SP']-COST[c]['DTT'] for c in ctxs if meta[c][0]==q and meta[c][2]==sig]
        print(f"   q={q:5d} {sig:9s} winners={str(ws):48s} mean margin={st.mean(marg):+.5f}")

print("\n"+"="*100); print("Q2  ABRUPT OR GRADUAL — margin trajectory per cell (normalised by |margin| at q=720)"); print("="*100)
for sig in ("Balanced","Arterial"):
    for restr in ("None","U","C","L"):
        row=[COST[[k for k in ctxs if meta[k]==(q,restr,sig)][0]]['SP']-COST[[k for k in ctxs if meta[k]==(q,restr,sig)][0]]['DTT'] for q in (720,1200,1680)]
        d1,d2=row[1]-row[0], row[2]-row[1]
        print(f"   {sig:9s} {restr:5s}  d(720->1200)={d1:+.5f}  d(1200->1680)={d2:+.5f}  "
              f"ratio={d2/d1 if d1 else float('nan'):6.2f}  {'CONVEX (accelerating)' if abs(d2)>abs(d1) else 'concave'}")

print("\n"+"="*100); print("Q4  PERFORMANCE GAP AROUND THE TRANSITION (regret of picking the wrong policy)"); print("="*100)
for q in (720,1200,1680):
    cs=[c for c in ctxs if meta[c][0]==q]
    hb={c:min(COST[c].values()) for c in cs}
    wr=st.mean(max(COST[c].values())-hb[c] for c in cs)
    sp=st.mean(COST[c]['SP']-hb[c] for c in cs); dt=st.mean(COST[c]['DTT']-hb[c] for c in cs)
    print(f"   q={q:5d}  worst-policy regret={wr:.5f}   fixed-SP regret={sp:.5f}   fixed-DTT regret={dt:.5f}")

print("\n"+"="*100); print("Q5  SEED STABILITY — winner per seed, per context"); print("="*100)
unstable=[]
for c in ctxs:
    ws=[]
    for s in ('8101','8102','8103'):
        cc={p:cost(*SM[s][c][p]) for p in POL}
        ws.append(min(cc,key=lambda p:cc[p]))
    agree=len(set(ws))==1
    if not agree: unstable.append((c,meta[c],ws))
print(f"   contexts with identical winner in all 3 seeds: {24-len(unstable)}/24")
for c,m,ws in unstable: print(f"     UNSTABLE {c} q={m[0]} {m[1]}/{m[2]}: {ws}")
print("\n   sign stability of the SP-DTT margin per seed:")
flip=0
for c in ctxs:
    sg=[]
    for s in ('8101','8102','8103'):
        cc={p:cost(*SM[s][c][p]) for p in POL}
        sg.append(cc['SP']-cc['DTT']>0)
    if len(set(sg))>1: flip+=1; print(f"     margin sign flips across seeds: {c} q={meta[c][0]} {meta[c][1]}/{meta[c][2]}")
print(f"   margin sign stable in {24-flip}/24 contexts")
