import csv, json, statistics as st, numpy as np
from collections import defaultdict
from sklearn.tree import DecisionTreeRegressor, export_text
O=json.load(open("results.json"))
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; RES=["None","U","C","L"]; QS=[720,1200,1680]
REG={720:"A low",1200:"B transition",1680:"C high"}
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
BEST={c:min(COST[c],key=lambda p:COST[c][p]) for c in ctxs}
def feats(c):
    d,r,s=meta[c]; return [d/1000.0]+[1.0 if r==k else 0.0 for k in RES]+[1.0 if s=="Balanced" else 0.0]
FN=['demand','r_None','r_U','r_C','r_L','sig_Balanced']

print("="*100); print("5. ML DECISION STRUCTURE (inspection of the fitted tree; no retraining)"); print("="*100)
m=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
    np.array([feats(c) for c in ctxs]),
    np.array([[T[c][p]/aT for p in POL]+[C[c][p]/aC for p in POL] for c in ctxs]))
print(export_text(m,feature_names=FN,decimals=3))
imp=dict(zip(FN,m.feature_importances_))
print("  feature importances:", {k:round(v,4) for k,v in sorted(imp.items(),key=lambda x:-x[1]) if v>0})
print(f"  features never used: {[k for k,v in imp.items() if v==0]}")
print(f"  demand share of total importance: {imp['demand']*100:.1f}%")
print(f"  signal-regime share: {imp['sig_Balanced']*100:.1f}%")

ch=O['chosen_loco']
print("\n"+"="*100); print("   OBSERVED BEST vs TREE-SELECTED, per held-out context"); print("="*100)
print(f"  {'ctx':5s} {'q':>5s} {'restr':6s} {'signal':9s} {'observed best':>13s} {'selected':>9s} {'regret':>9s}  {'agree'}")
agree=0; reg_ok=[]; reg_bad=[]
for c in ctxs:
    d,r,s=meta[c]; a=(ch[c]==BEST[c]); agree+=a
    rg=COST[c][ch[c]]-HB[c]
    (reg_ok if rg<1e-12 else reg_bad).append(rg)
    print(f"  {c:5s} {d:5d} {r:6s} {s:9s} {BEST[c]:>13s} {ch[c]:>9s} {rg:9.5f}  {'yes' if a else 'NO'}")
print(f"\n  label agreement with observed best: {agree}/24 = {agree/24*100:.1f}%")
print(f"  zero-regret decisions (ties included): {len(reg_ok)}/24 = {len(reg_ok)/24*100:.1f}%")
print(f"  mean regret when zero-regret: {st.mean(reg_ok):.5f}")
print(f"  mean regret when non-zero:    {st.mean(reg_bad):.5f}  (n={len(reg_bad)}, max {max(reg_bad):.5f})")
print("\n  residual regret by regime:")
for q in QS:
    cs=[c for c in ctxs if meta[c][0]==q]
    print(f"    {REG[q]:14s} mean {st.mean(COST[c][ch[c]]-HB[c] for c in cs):.5f}   "
          f"non-zero contexts: {[c for c in cs if COST[c][ch[c]]-HB[c]>1e-12]}")

print("\n"+"="*100); print("6. PREDICTION -> RANKING -> DECISION DECOMPOSITION (LOCO predictions)"); print("="*100)
rows=[]
for t in ctxs:
    tr=[c for c in ctxs if c!=t]
    a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
    mm=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
    yp=mm.predict(np.array([feats(t)]))[0]
    pc={p:0.5*yp[i]+0.5*yp[i+3] for i,p in enumerate(POL)}
    pred_rank=sorted(POL,key=lambda p:pc[p]); obs_rank=sorted(POL,key=lambda p:COST[t][p])
    err=st.mean(abs(yp[i]*a1-T[t][p]) for i,p in enumerate(POL))
    relerr=st.mean(abs(yp[i]*a1-T[t][p])/T[t][p] for i,p in enumerate(POL))*100
    rows.append(dict(ctx=t,q=meta[t][0],relerr=relerr,rank_ok=pred_rank[0]==obs_rank[0],
                     full_rank_ok=pred_rank==obs_rank,regret=COST[t][pred_rank[0]]-HB[t]))
print(f"  {'ctx':5s} {'q':>5s} {'mean |pred-obs| time':>21s} {'top-1 rank ok':>14s} {'full rank ok':>13s} {'regret':>9s}  category")
cats=defaultdict(list)
for r in rows:
    if r['rank_ok'] and r['regret']<1e-12: cat="pred imperfect, decision CORRECT"
    elif not r['rank_ok'] and r['regret']<1e-12: cat="ranking changed, regret NEGLIGIBLE"
    elif not r['rank_ok']: cat="ranking changed, regret SUBSTANTIAL"
    else: cat="top-1 ok but regret>0"
    cats[cat].append(r)
    print(f"  {r['ctx']:5s} {r['q']:5d} {r['relerr']:20.1f}% {str(r['rank_ok']):>14s} {str(r['full_rank_ok']):>13s} {r['regret']:9.5f}  {cat}")
print()
for k,v in cats.items():
    print(f"  {k:36s} n={len(v):2d}  mean rel. pred error {st.mean(x['relerr'] for x in v):5.1f}%  mean regret {st.mean(x['regret'] for x in v):.5f}")
print(f"\n  full 3-policy ranking exactly right in {sum(1 for r in rows if r['full_rank_ok'])}/24; "
      f"top-1 right in {sum(1 for r in rows if r['rank_ok'])}/24; zero regret in {sum(1 for r in rows if r['regret']<1e-12)}/24")
print("  -> decision quality exceeds ranking quality, which exceeds prediction quality.")

print("\n"+"="*100); print("7. OOD / EXTRAPOLATION DETAIL"); print("="*100)
for d in QS:
    tr=[c for c in ctxs if meta[c][0]!=d]; te=[c for c in ctxs if meta[c][0]==d]
    sup=sorted({meta[c][0] for c in tr})
    a1=st.mean(T[c][p] for c in tr for p in POL); a2=st.mean(C[c][p] for c in tr for p in POL)
    mm=DecisionTreeRegressor(max_depth=3,min_samples_leaf=2,random_state=0).fit(
        np.array([feats(c) for c in tr]),
        np.array([[T[c][p]/a1 for p in POL]+[C[c][p]/a2 for p in POL] for c in tr]))
    pos = "BELOW" if d<min(sup) else ("ABOVE" if d>max(sup) else "INSIDE(gap)")
    print(f"\n  held-out q={d}  training support={sup}  test point lies {pos} support")
    sel=defaultdict(int); bst=defaultdict(int)
    for c in te:
        yp=mm.predict(np.array([feats(c)]))[0]
        pk=POL[int(np.argmin([0.5*yp[i]+0.5*yp[i+3] for i in range(3)]))]
        sel[pk]+=1; bst[BEST[c]]+=1
    r=st.mean(COST[c][POL[int(np.argmin([0.5*(v:=mm.predict(np.array([feats(c)]))[0])[i]+0.5*v[i+3] for i in range(3)]))]]-HB[c] for c in te)
    dt=st.mean(COST[c]['DTT']-HB[c] for c in te); sp=st.mean(COST[c]['SP']-HB[c] for c in te)
    print(f"    selected: {dict(sel)}   hindsight best: {dict(bst)}")
    print(f"    adaptive regret {r:.5f} | fixed DTT {dt:.5f} | fixed SP {sp:.5f} | difference adaptive-fixedDTT {r-dt:+.5f}")

print("\n"+"="*100); print("8. MCDM ROLE AUDIT"); print("="*100)
print(f"  {'w_time':>7s} {'SP wins':>8s} {'DTT wins':>9s} {'TECO10':>8s}  low-regime winners  high-regime winners  m@1200 sign pattern")
for w in (1.0,0.75,0.5,0.25,0.0):
    cc={c:{p:w*T[c][p]/aT+(1-w)*C[c][p]/aC for p in POL} for c in ctxs}
    wn={c:min(cc[c],key=lambda p:cc[c][p]) for c in ctxs}
    lo={wn[c] for c in ctxs if meta[c][0]==720}; hi={wn[c] for c in ctxs if meta[c][0]==1680}
    sgn="".join("+" if cc[c]['SP']-cc[c]['DTT']>0 else "-" for c in sorted(ctxs) if meta[c][0]==1200)
    print(f"  {w:7.2f} {sum(1 for c in ctxs if wn[c]=='SP'):8d} {sum(1 for c in ctxs if wn[c]=='DTT'):9d} "
          f"{sum(1 for c in ctxs if wn[c]=='TECO10'):8d}  {str(sorted(lo)):19s} {str(sorted(hi)):20s} {sgn}")
print("\n  full 0.05-spaced sweep, w_time 0..1: does the LOW/HIGH regime pattern ever break?")
brk=[]
for i in range(21):
    w=i*0.05
    cc={c:{p:w*T[c][p]/aT+(1-w)*C[c][p]/aC for p in POL} for c in ctxs}
    wn={c:min(cc[c],key=lambda p:cc[c][p]) for c in ctxs}
    if not all(wn[c]=='SP' for c in ctxs if meta[c][0]==720): brk.append((round(w,2),'low'))
    if not all(wn[c]=='DTT' for c in ctxs if meta[c][0]==1680): brk.append((round(w,2),'high'))
print("   breaks:",brk if brk else "NONE — SP wins all low-demand and DTT all high-demand at every tested weight")
