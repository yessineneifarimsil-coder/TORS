"""Robustness battery: is the held-out gain real, or an artifact of settings/seeds/weights?"""
import csv, statistics as st, numpy as np, itertools
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor
R=[dict(r,time=float(r['time']),co2=float(r['co2']),ins=float(r['ins']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
def build(seeds):
    T,C=defaultdict(dict),defaultdict(dict)
    for p in POL:
        g=defaultdict(list)
        for x in R:
            if x['policy']==p and x['seed'] in seeds: g[x['ctx']].append(x)
        for c in g: T[c][p]=st.mean(y['time'] for y in g[c]); C[c][p]=st.mean(y['co2'] for y in g[c])
    return T,C
ALL={'8101','8102','8103'}
CT,CC=build(ALL); ctxs=sorted(CT)
def feats(c):
    d,r,s=meta[c]; return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
def run(T,C,folds,w,depth,leaf,scoreT=None,scoreC=None):
    scoreT=scoreT or T; scoreC=scoreC or C
    chosen={}
    for tr,te in folds:
        aT=st.mean(T[c][p] for c in tr for p in POL); aC=st.mean(C[c][p] for c in tr for p in POL)
        m=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=0).fit(
            np.array([feats(c) for c in tr]),
            np.array([[T[c][p]/aT for p in POL]+[C[c][p]/aC for p in POL] for c in tr]))
        for c in te:
            yp=m.predict(np.array([feats(c)]))[0]
            k=[w*yp[i]+(1-w)*yp[i+len(POL)] for i in range(len(POL))]
            chosen[c]=POL[int(np.argmin(k))]
    aT=st.mean(scoreT[c][p] for c in ctxs for p in POL); aC=st.mean(scoreC[c][p] for c in ctxs for p in POL)
    cost={c:{p:w*scoreT[c][p]/aT+(1-w)*scoreC[c][p]/aC for p in POL} for c in ctxs}
    hb={c:min(cost[c].values()) for c in ctxs}
    reg=st.mean(cost[c][chosen[c]]-hb[c] for c in ctxs)
    fx={p:st.mean(cost[c][p]-hb[c] for c in ctxs) for p in POL}
    bf=min(fx,key=lambda p:fx[p])
    cap=(fx[bf]-reg)/fx[bf]*100 if fx[bf]>0 else float('nan')
    return reg,fx[bf],bf,cap,chosen
loco=[([c for c in ctxs if c!=t],[t]) for t in ctxs]
lqo=[([c for c in ctxs if meta[c][0]!=d],[c for c in ctxs if meta[c][0]==d]) for d in (720,1200,1680)]

print("="*90); print("A. TREE HYPERPARAMETER SENSITIVITY (LOCO, balanced w=0.5)"); print("="*90)
for depth in (1,2,3,4,None):
    for leaf in (1,2,3):
        reg,bfr,bf,cap,_=run(CT,CC,loco,0.5,depth,leaf)
        print(f"   depth={str(depth):4s} leaf={leaf}  meanReg={reg:.5f}  vs fixed {bf}={bfr:.5f}  captured={cap:+6.1f}%")

print("\n"+"="*90); print("B. PREFERENCE-WEIGHT SENSITIVITY (LOCO, depth3 leaf2)"); print("="*90)
for w in (1.0,0.75,0.5,0.25,0.0):
    reg,bfr,bf,cap,ch=run(CT,CC,loco,w,3,2)
    hb_w=sum(1 for c in ctxs if ch[c]=='SP'),sum(1 for c in ctxs if ch[c]=='DTT'),sum(1 for c in ctxs if ch[c]=='TECO10')
    print(f"   w_time={w:.2f}  meanReg={reg:.5f}  vs fixed {bf}={bfr:.5f}  captured={cap:+6.1f}%  chosen SP/DTT/TECO10={hb_w}")

print("\n"+"="*90); print("C. SEED ROBUSTNESS — train on 2 seeds, evaluate against the held-out 3rd seed"); print("="*90)
for held in ('8101','8102','8103'):
    tr_s=ALL-{held}
    Ttr,Ctr=build(tr_s); Tte,Cte=build({held})
    reg,bfr,bf,cap,_=run(Ttr,Ctr,loco,0.5,3,2,scoreT=Tte,scoreC=Cte)
    print(f"   train seeds {sorted(tr_s)} -> scored on seed {held}:  meanReg={reg:.5f}  vs fixed {bf}={bfr:.5f}  captured={cap:+6.1f}%")

print("\n"+"="*90); print("D. SCORING-SCALE CHECK (train-only scales used for scoring too)"); print("="*90)
chosen={}; regs=[]; dtts=[]
for tr,te in loco:
    aT=st.mean(CT[c][p] for c in tr for p in POL); aC=st.mean(CC[c][p] for c in tr for p in POL)
    m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[CT[c][p]/aT for p in POL]+[CC[c][p]/aC for p in POL] for c in tr]))
    for c in te:
        yp=m.predict(np.array([feats(c)]))[0]
        k=[0.5*yp[i]+0.5*yp[i+len(POL)] for i in range(len(POL))]
        pick=POL[int(np.argmin(k))]
        cost={p:0.5*CT[c][p]/aT+0.5*CC[c][p]/aC for p in POL}
        hb=min(cost.values()); regs.append(cost[pick]-hb); dtts.append(cost['DTT']-hb)
print(f"   meanReg={st.mean(regs):.5f}  vs fixed DTT={st.mean(dtts):.5f}  captured={(st.mean(dtts)-st.mean(regs))/st.mean(dtts)*100:+.1f}%")

print("\n"+"="*90); print("E. DEMAND EXTRAPOLATION STRESS TEST (per fold)"); print("="*90)
for d in (720,1200,1680):
    f=[([c for c in ctxs if meta[c][0]!=d],[c for c in ctxs if meta[c][0]==d])]
    aT=st.mean(CT[c][p] for c in ctxs for p in POL); aC=st.mean(CC[c][p] for c in ctxs for p in POL)
    cost={c:{p:0.5*CT[c][p]/aT+0.5*CC[c][p]/aC for p in POL} for c in ctxs}
    _,_,_,_,ch=run(CT,CC,f,0.5,3,2)
    te=[c for c in ctxs if meta[c][0]==d]
    hb={c:min(cost[c].values()) for c in te}
    r=st.mean(cost[c][ch[c]]-hb[c] for c in te); dd=st.mean(cost[c]['DTT']-hb[c] for c in te)
    print(f"   hold out q={d}:  meanReg={r:.5f}  fixedDTT={dd:.5f}  chosen={sorted(set(ch[c] for c in te))}  "
          f"{'WORSE than fixed' if r>dd+1e-9 else 'better/equal'}")
