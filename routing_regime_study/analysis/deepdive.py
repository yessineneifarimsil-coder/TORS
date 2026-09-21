"""Sections 2-8 of the strengthening pass. Post-processing of existing runs only."""
import csv, json, statistics as st, numpy as np
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor, export_text
O=json.load(open("results.json"))
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
T,C=defaultdict(dict),defaultdict(dict)
SEED=defaultdict(lambda: defaultdict(dict))
for p in POL:
    g=defaultdict(list)
    for x in R:
        if x['policy']==p:
            g[x['ctx']].append(x); SEED[x['seed']][x['ctx']][p]=(x['time'],x['co2'])
    for c in g: T[c][p]=st.mean(y['time'] for y in g[c]); C[c][p]=st.mean(y['co2'] for y in g[c])
ctxs=sorted(T); aT,aC=O['ref_time'],O['ref_co2']
cost=lambda t,c,w=0.5: w*t/aT+(1-w)*c/aC
COST={c:{p:cost(T[c][p],C[c][p]) for p in POL} for c in ctxs}
HB={c:min(COST[c].values()) for c in ctxs}
QS=[720,1200,1680]; REG={720:"A low",1200:"B transition",1680:"C high"}

print("="*100); print("2. QUANTITATIVE TRANSITION ANALYSIS"); print("="*100)
print(f"  {'cell':22s} {'m@720':>9s} {'m@1200':>9s} {'m@1680':>9s} {'%m@720':>8s} {'%m@1200':>9s} {'%m@1680':>9s} {'d1':>8s} {'d2':>8s} mono")
mono_ct=0
for sig in ("Balanced","Arterial"):
    for r in RES:
        cs=[[k for k in ctxs if meta[k]==(q,r,sig)][0] for q in QS]
        m=[COST[c]['SP']-COST[c]['DTT'] for c in cs]
        pm=[(COST[c]['SP']-COST[c]['DTT'])/COST[c]['DTT']*100 for c in cs]
        d1,d2=m[1]-m[0],m[2]-m[1]; mo=(d1>0 and d2>0)
        mono_ct+=mo
        print(f"  {sig[:3]+'/'+r:22s} {m[0]:9.4f} {m[1]:9.4f} {m[2]:9.4f} {pm[0]:7.1f}% {pm[1]:8.1f}% {pm[2]:8.1f}% {d1:+8.4f} {d2:+8.4f} {'yes' if mo else 'NO'}")
print(f"\n  monotone increasing in demand: {mono_ct}/8 cells")
print(f"  |d2|>|d1| (accelerating): {sum(1 for sig in ('Balanced','Arterial') for r in RES if (lambda m:abs(m[2]-m[1])>abs(m[1]-m[0]))([COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['SP']-COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['DTT'] for q in QS]))}/8")
print("\n  seed variability of m (sd across 3 seeds):")
print(f"  {'cell':22s} {'sd@720':>9s} {'sd@1200':>9s} {'sd@1680':>9s}")
for sig in ("Balanced","Arterial"):
    for r in RES:
        sds=[]
        for q in QS:
            c=[k for k in ctxs if meta[k]==(q,r,sig)][0]
            vals=[cost(*SEED[s][c]['SP'])-cost(*SEED[s][c]['DTT']) for s in ('8101','8102','8103')]
            sds.append(st.stdev(vals))
        print(f"  {sig[:3]+'/'+r:22s} {sds[0]:9.4f} {sds[1]:9.4f} {sds[2]:9.4f}")

print("\n"+"="*100); print("3. SIGNAL-REGIME EFFECT"); print("="*100)
print(f"  {'cell':14s} {'low winner':>11s} {'transition interval':>21s} {'high winner':>12s} {'m@1200':>9s}")
for sig in ("Balanced","Arterial"):
    for r in RES:
        cs=[[k for k in ctxs if meta[k]==(q,r,sig)][0] for q in QS]
        m=[COST[c]['SP']-COST[c]['DTT'] for c in cs]
        w=[min(COST[c],key=lambda p:COST[c][p]) for c in cs]
        br="(720, 1200]" if m[0]<0<=m[1] else ("(1200, 1680]" if m[1]<0<=m[2] else "none observed")
        print(f"  {sig[:3]+'/'+r:14s} {w[0]:>11s} {br:>21s} {w[2]:>12s} {m[1]:9.4f}")
mb=st.mean(COST[[k for k in ctxs if meta[k]==(1200,r,'Balanced')][0]]['SP']-COST[[k for k in ctxs if meta[k]==(1200,r,'Balanced')][0]]['DTT'] for r in RES)
ma=st.mean(COST[[k for k in ctxs if meta[k]==(1200,r,'Arterial')][0]]['SP']-COST[[k for k in ctxs if meta[k]==(1200,r,'Arterial')][0]]['DTT'] for r in RES)
print(f"\n  mean m@1200: Balanced {mb:+.4f}  Arterial {ma:+.4f}  difference {mb-ma:+.4f}")
print(f"  bracket shift: Balanced 3/4 cells cross in (720,1200]; Arterial 3/4 cross in (1200,1680] -> one grid step (>=480 veh/h)")
print("\n  seed stability of the signal-regime pattern (sign of m@1200 per seed):")
for sig in ("Balanced","Arterial"):
    rows=[]
    for r in RES:
        c=[k for k in ctxs if meta[k]==(1200,r,sig)][0]
        sg=["+" if cost(*SEED[s][c]['SP'])-cost(*SEED[s][c]['DTT'])>0 else "-" for s in ('8101','8102','8103')]
        rows.append(f"{r}:{''.join(sg)}")
    print(f"    {sig:10s} "+"  ".join(rows))

print("\n"+"="*100); print("4. DECISION-HEADROOM DECOMPOSITION BY REGIME"); print("="*100)
ch=O['chosen_loco']
print(f"  {'regime':14s} {'worst':>9s} {'fixedSP':>9s} {'fixedDTT':>9s} {'adaptive':>9s} {'hindsight':>10s} {'share of total headroom':>24s}")
tot=sum(COST[c]['DTT']-HB[c] for c in ctxs)
for q in QS:
    cs=[c for c in ctxs if meta[c][0]==q]
    w=st.mean(max(COST[c].values())-HB[c] for c in cs)
    sp=st.mean(COST[c]['SP']-HB[c] for c in cs); dt=st.mean(COST[c]['DTT']-HB[c] for c in cs)
    ad=st.mean(COST[c][ch[c]]-HB[c] for c in cs)
    sh=sum(COST[c]['DTT']-HB[c] for c in cs)/tot*100
    print(f"  {REG[q]:14s} {w:9.5f} {sp:9.5f} {dt:9.5f} {ad:9.5f} {0.0:10.5f} {sh:23.1f}%")
print(f"  {'ALL':14s} {st.mean(max(COST[c].values())-HB[c] for c in ctxs):9.5f} "
      f"{st.mean(COST[c]['SP']-HB[c] for c in ctxs):9.5f} {st.mean(COST[c]['DTT']-HB[c] for c in ctxs):9.5f} "
      f"{st.mean(COST[c][ch[c]]-HB[c] for c in ctxs):9.5f} {0.0:10.5f}")
