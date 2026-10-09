"""Headroom (SBS->in-sample VBS) restricted to the 96 contexts of the sensitivity campaign,
so it can be compared like-for-like with the P3 eps=0.3 gain."""
import json, collections, statistics as st
R="/home/user/TORS/study/results/"
def ck(r): return (r["demand"],float(r["gc"]),float(r["penetration"]),int(r["lag"]),int(r["incident"]),int(r["alt"]))
sub={ck(json.loads(l)) for l in open(R+"sens.jsonl")}
cell=collections.defaultdict(list)
for l in open(R+"main.jsonl"):
    r=json.loads(l)
    if ck(r) in sub: cell[(ck(r),r["policy"])].append(r["C1_sys"])
ctx=sorted(sub); P=["P1","P2","P3","P4"]
C={c:{p:st.mean(cell[(c,p)]) for p in P} for c in ctx}
h=[C[c]["P3"]-min(C[c].values()) for c in ctx]
print(json.dumps(dict(n=len(ctx),headroom_mean=st.mean(h),P3_mean=st.mean(C[c]["P3"] for c in ctx)),indent=1))
