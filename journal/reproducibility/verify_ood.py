"""Re-run the frozen distribution-shift protocol on independently rebuilt matrices."""
import json, os, sys, math, collections, statistics as st
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.join(HERE,"..")
sys.path.insert(0,os.path.join(ROOT,"analysis"))
import warnings; warnings.filterwarnings("ignore")
import ood as O, policy_selectors as S
RES=os.path.join(ROOT,"results")
FACT=["demand","gc","penetration","lag","incident","alt"]; POL=["P1","P2","P3","P4"]
def ck(r): return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
                   f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")
SC,SN,CF,CY,YE,FF=1761.0,1596.0,1500.0,90.0,4.0,324.0
def desc(m):
    g=(m["gc"]*CY-YE)/CY; cap={"C":2*SC*g,"N":m["alt"]*SN*g,"S":CF}; tot=sum(cap.values())
    D,p=m["demand"],m["penetration"]
    return [D/tot,D/cap["C"],cap["N"]/tot,g,p,m["lag"]/FF,float(m["incident"]),p*D/cap["C"]]
def build(path):
    cell=collections.defaultdict(list)
    for l in open(path):
        r=json.loads(l)
        if "_error" in r: continue
        cell[(ck(r),r["policy"])].append(r)
    ctxs=sorted({k[0] for k in cell})
    X=np.zeros((len(ctxs),8)); C=np.zeros((len(ctxs),4)); noise=np.zeros(len(ctxs)); meta=[]
    for i,c in enumerate(ctxs):
        g0=cell[(c,"P1")][0]; m={f:g0[f] for f in FACT}
        X[i]=desc(m); meta.append(m); vecs={}
        for j,p in enumerate(POL):
            gg=sorted(cell[(c,p)],key=lambda x:x["seed"])
            C[i,j]=st.mean(x["C1_sys"] for x in gg); vecs[p]=[x["C1_sys"] for x in gg]
        best=POL[int(np.argmin(C[i]))]
        ses=[]
        for p in POL:
            if p==best: continue
            d=np.array(vecs[p])-np.array(vecs[best]); ses.append(d.std(ddof=1)/math.sqrt(len(d)))
        noise[i]=2.0*max(ses)
    return ctxs,X,C,noise,meta
ctxs,X,C,noise,meta=build(os.path.join(RES,"main.jsonl"))
res=O.all_splits(X,C,noise,meta)
nctx,nX,nC,nnoise,nmeta=build(os.path.join(RES,"ood_north.jsonl"))
res["O8_northcorridor"]=O.domain_split(X,C,noise,nX,nC,nnoise)

R=json.load(open(os.path.join(RES,"results.json"))); P=R["ood"]
print(f"{'split':20s}{'B0(mine)':>10s}{'B0(pub)':>10s}{'B4(mine)':>10s}{'B4(pub)':>10s}{'B5(mine)':>10s}{'B5(pub)':>10s}  {'abst':>6s} {'oos':>6s}")
bad=0
for k in sorted(res):
    r=res[k]; p=P.get(k)
    if not p: print(f"{k:20s}  NOT PUBLISHED"); continue
    row=[]
    for sel in ("B0_SBS","B4_GBDT","B5_selective"):
        a,b=r[sel]["mean_regret"],p[sel]["mean_regret"]; row+= [a,b]
        if abs(a-b)>1e-9: bad+=1
    print(f"{k:20s}"+"".join(f"{v:10.4f}" for v in row)+f"  {r['_abstain_rate']:6.3f} {r['_out_of_support_rate']:6.3f}"
          +("" if abs(row[0]-row[1])<1e-9 and abs(row[2]-row[3])<1e-9 and abs(row[4]-row[5])<1e-9 else "  <<< MISMATCH"))
print(f"\nmismatches: {bad}")
TOL=R["ood_summary"]["tolerance_s"]
print(f"\nclassification at tolerance {TOL} s (B4 vs B0):")
cl={}
for k in sorted(res):
    d=res[k]["B4_GBDT"]["mean_regret"]-res[k]["B0_SBS"]["mean_regret"]
    cl[k]="helps" if d<-TOL else ("harms" if d>TOL else "neutral")
    print(f"  {k:20s} B0 {res[k]['B0_SBS']['mean_regret']:7.4f}  B4 {res[k]['B4_GBDT']['mean_regret']:7.4f}  diff {d:+7.4f}  -> {cl[k]}  (published {R['ood_summary']['classification'][k]})")
print("\nB5 equals B0 on every split:", all(abs(res[k]["B5_selective"]["mean_regret"]-res[k]["B0_SBS"]["mean_regret"])<1e-12 for k in res))
json.dump({k:{s:res[k][s] for s in res[k] if not s.startswith("_")} | {s:res[k][s] for s in res[k] if s.startswith("_")}
           for k in res}, open(os.path.join(HERE,"verify_ood.json"),"w"), indent=1, default=str)
