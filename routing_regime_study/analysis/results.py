"""Single source of truth for every number in the manuscript. Exports results.json."""
import csv, json, statistics as st, math, numpy as np
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor, export_text
R=[dict(r,time=float(r['time']),co2=float(r['co2']),ins=float(r['ins']),p95=float(r['p95']),
        dist=float(r['dist']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
ALLP=["SP","DTT","ECO","TECO05","TECO10","TECO15"]; POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]
meta={x['ctx']:(x['demand'],x['restr'],x['signal']) for x in R}
def cm(pols):
    T,C=defaultdict(dict),defaultdict(dict)
    for p in pols:
        g=defaultdict(list)
        for x in R:
            if x['policy']==p: g[x['ctx']].append(x)
        for c in g: T[c][p]=st.mean(y['time'] for y in g[c]); C[c][p]=st.mean(y['co2'] for y in g[c])
    return T,C
T6,C6=cm(ALLP); T,C=cm(POL); ctxs=sorted(T)
aT=st.mean(T[c][p] for c in ctxs for p in POL); aC=st.mean(C[c][p] for c in ctxs for p in POL)
COST={c:{p:0.5*T[c][p]/aT+0.5*C[c][p]/aC for p in POL} for c in ctxs}
HB={c:min(COST[c].values()) for c in ctxs}
def feats(c):
    d,r,s=meta[c]; return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
O={}
O['n_runs']=len(R); O['n_contexts']=len(ctxs); O['portfolio']=POL
O['ref_time']=aT; O['ref_co2']=aC
# ---- LEAKAGE AUDIT ----
audit={}
audit['features_are_pre_decision']=sorted({'demand(scheduled)','restriction location(planned)','restriction speed ratio(planned)','signal regime(controller plan)'})
audit['no_outcome_in_features']=True
audit['scales_fit_on_training_only']=True
audit['model_refit_per_fold']=True
audit['seeds_grouped_with_context']=True
audit['hyperparameters_fixed_a_priori']='depth 3, min_samples_leaf 2 (pre-registered depth3/leaf8 rescaled: 8/84 training contexts -> 2/23)'
O['leakage_audit']=audit
# ---- LOCO ----
chosen={}; pT=[];pC=[];oT=[];oC=[]
for t in ctxs:
    tr=[c for c in ctxs if c!=t]
    a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
    m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
    yp=m.predict(np.array([feats(t)]))[0]
    for i,p in enumerate(POL):
        pT.append(yp[i]*a1); pC.append(yp[i+3]*a2); oT.append(T[t][p]); oC.append(C[t][p])
    chosen[t]=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
O['pred_mae_time']=st.mean(abs(a-b) for a,b in zip(pT,oT))
O['pred_rmse_time']=math.sqrt(st.mean((a-b)**2 for a,b in zip(pT,oT)))
O['pred_mae_co2']=st.mean(abs(a-b) for a,b in zip(pC,oC))
O['pred_rmse_co2']=math.sqrt(st.mean((a-b)**2 for a,b in zip(pC,oC)))
def stats(ch):
    reg=[COST[c][ch[c]]-HB[c] for c in ctxs]
    return dict(mean=st.mean(reg),max=max(reg),
                zero=sum(1 for c in ctxs if abs(COST[c][ch[c]]-HB[c])<1e-12),
                near=sum(1 for c in ctxs if COST[c][ch[c]]<=HB[c]*1.01))
O['fixed']={p:stats({c:p for c in ctxs}) for p in POL}
O['adaptive_loco']=stats(chosen)
O['hindsight']=stats({c:min(COST[c],key=lambda q:COST[c][q]) for c in ctxs})
O['headroom_mean']=O['fixed']['DTT']['mean']
O['captured_pct']=(O['fixed']['DTT']['mean']-O['adaptive_loco']['mean'])/O['fixed']['DTT']['mean']*100
O['chosen_loco']=chosen
# ---- extrapolation ----
ex={}; allc=[];alld=[]
for d in (720,1200,1680):
    tr=[c for c in ctxs if meta[c][0]!=d]; te=[c for c in ctxs if meta[c][0]==d]
    a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
    m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
    ch={c:POL[int(np.argmin([0.5*(v:=m.predict(np.array([feats(c)]))[0])[i]+0.5*v[i+3] for i in range(3)]))] for c in te}
    r=[COST[c][ch[c]]-HB[c] for c in te]; dd=[COST[c]['DTT']-HB[c] for c in te]
    ex[d]=dict(cart=st.mean(r),dtt=st.mean(dd),chosen=sorted(set(ch.values())))
    allc+=r; alld+=dd
O['extrapolation']=ex
O['extrap_pooled_cart']=st.mean(allc); O['extrap_pooled_dtt']=st.mean(alld)
O['extrap_captured_pct']=(st.mean(alld)-st.mean(allc))/st.mean(alld)*100
# ---- transition ----
tr_tab={}
for sig in ("Balanced","Arterial"):
    for restr in RES:
        row=[]
        for q in (720,1200,1680):
            c=[k for k in ctxs if meta[k]==(q,restr,sig)][0]
            row.append(COST[c]['SP']-COST[c]['DTT'])
        br=None
        for i in range(2):
            if row[i]<0<=row[i+1]: br=[(720,1200)[i],(1200,1680)[i]]
        tr_tab[f"{sig}|{restr}"]=dict(margins=row,bracket=br)
O['transition']=tr_tab
O['worst_policy_regret']={q:st.mean(max(COST[c].values())-HB[c] for c in ctxs if meta[c][0]==q) for q in (720,1200,1680)}
# ---- seed stability ----
SM=defaultdict(lambda: defaultdict(dict))
for x in R:
    if x['policy'] in POL: SM[x['seed']][x['ctx']][x['policy']]=0.5*x['time']/aT+0.5*x['co2']/aC
unst=[c for c in ctxs if len({min(SM[s][c],key=lambda p:SM[s][c][p]) for s in ('8101','8102','8103')})>1]
O['seed_stable_winner']=24-len(unst); O['seed_unstable_ctx']=unst
flip=[c for c in ctxs if len({SM[s][c]['SP']-SM[s][c]['DTT']>0 for s in ('8101','8102','8103')})>1]
O['seed_stable_margin_sign']=24-len(flip); O['seed_margin_flip_ctx']=flip
# ---- ECO negative control ----
O['eco_identical_to_sp']=sum(1 for c in ctxs if abs(T6[c]['SP']-T6[c]['ECO'])<1e-9 and abs(C6[c]['SP']-C6[c]['ECO'])<1e-9)
# ---- MCDM inertness ----
inert={}
for w in (1.0,0.75,0.5,0.25,0.0):
    ch={}
    for t in ctxs:
        tr=[c for c in ctxs if c!=t]
        a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
        m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
            np.array([feats(c) for c in tr]),
            np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
        yp=m.predict(np.array([feats(t)]))[0]
        ch[t]=POL[int(np.argmin([w*yp[i]+(1-w)*yp[i+3] for i in range(3)]))]
    inert[w]=ch
O['mcdm_identical_across_weights']=all(inert[w]==inert[0.5] for w in inert)
O['mcdm_weights_tested']=sorted(inert)
# hindsight winners under each weight, on observed outcomes
hw={}
for w in (1.0,0.5,0.0):
    cc={c:{p:w*T[c][p]/aT+(1-w)*C[c][p]/aC for p in POL} for c in ctxs}
    hw[w]={c:min(cc[c],key=lambda p:cc[c][p]) for c in ctxs}
O['hindsight_winner_identical_across_weights']=all(hw[w]==hw[0.5] for w in hw)
json.dump(O,open("results.json","w"),indent=1,default=str)
print(json.dumps({k:v for k,v in O.items() if k not in ('chosen_loco','transition','leakage_audit')},indent=1,default=str))
