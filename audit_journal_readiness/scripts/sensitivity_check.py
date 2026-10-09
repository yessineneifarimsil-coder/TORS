"""Recompute the frozen-parameter sensitivity directly from sens.jsonl + main.jsonl (paired)."""
import json, collections, statistics as st, math
R="/home/user/TORS/study/results/"
def key(r): return (r["demand"],float(r["gc"]),float(r["penetration"]),int(r["lag"]),int(r["incident"]),int(r["alt"]),r["seed"])
main={}; 
for l in open(R+"main.jsonl"):
    r=json.loads(l); main[(key(r),r["policy"])]=r["C1_sys"]
sens=collections.defaultdict(dict)
for l in open(R+"sens.jsonl"):
    r=json.loads(l)
    tag=("P3_eps",r.get("p3_eps")) if r["policy"]=="P3" else ("P4_lam",r.get("p4_lambda"))
    sens[tag][key(r)]=r["C1_sys"]
out={}
for tag,d in sorted(sens.items(),key=str):
    pol="P3" if tag[0]=="P3_eps" else "P4"
    diffs=[main[(k,pol)]-v for k,v in d.items()]          # positive = alternative parameter is faster
    ctxs=collections.defaultdict(list)
    for k,v in d.items(): ctxs[k[:6]].append(main[(k,pol)]-v)
    cm=[st.mean(x) for x in ctxs.values()]
    # also: would the alternative-parameter P3 still be SBS / beat frozen P3 vs other policies?
    out[f"{tag[0]}={tag[1]}"]=dict(n_runs=len(d),n_ctx=len(ctxs),mean_gain_vs_frozen=st.mean(diffs),
        frac_ctx_alt_better=sum(1 for x in cm if x>0)/len(cm), max_ctx_gain=max(cm), min_ctx_gain=min(cm))
json.dump(out,open("/home/user/TORS/audit_journal_readiness/outputs/sensitivity_check.json","w"),indent=1)
print(json.dumps(out,indent=1))
