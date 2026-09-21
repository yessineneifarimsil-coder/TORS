import csv, json, statistics as st, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import defaultdict
OUT="paper/figures/"
SP_C,DTT_C,TEC_C="#2a78d6","#eb6834","#1baf7a"     # validated slots 1-3
INK,INK2,GRID="#0b0b0b","#52514e","#d9d8d4"
plt.rcParams.update({"font.size":8,"axes.edgecolor":INK2,"axes.labelcolor":INK,
 "xtick.color":INK2,"ytick.color":INK2,"text.color":INK,"axes.grid":True,
 "grid.color":GRID,"grid.linewidth":.6,"axes.axisbelow":True,"figure.dpi":200,
 "axes.spines.top":False,"axes.spines.right":False,"legend.frameon":False})
O=json.load(open("results.json"))
R=[dict(r,time=float(r['time']),co2=float(r['co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
POL=["SP","DTT","TECO10"]; COLS={"SP":SP_C,"DTT":DTT_C,"TECO10":TEC_C}
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
RES=["None","U","C","L"]; QS=[720,1200,1680]

# ================= FIGURE 1 : regime structure =================
fig,ax=plt.subplots(1,2,figsize=(7.1,2.75))
a=ax[0]
for sig,mk,ls in (("Balanced","o","-"),("Arterial","s","--")):
    for r in RES:
        y=[COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['SP']-COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['DTT'] for q in QS]
        a.plot(QS,y,ls,color=GRID,lw=.9,zorder=1)
    ym=[st.mean(COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['SP']-COST[[k for k in ctxs if meta[k]==(q,r,sig)][0]]['DTT'] for r in RES) for q in QS]
    a.plot(QS,ym,ls,marker=mk,color=SP_C if sig=="Balanced" else DTT_C,lw=2,ms=5,zorder=3,label=sig)
a.axhline(0,color=INK,lw=1.1,zorder=2)
a.axvspan(720,1200,color=SP_C,alpha=.07,zorder=0); a.axvspan(1200,1680,color=DTT_C,alpha=.07,zorder=0)
a.text(960,-0.30,"Balanced\ncrossing",ha="center",va="top",fontsize=6.8,color=SP_C)
a.text(1440,-0.30,"Arterial\ncrossing",ha="center",va="top",fontsize=6.8,color=DTT_C)
a.set_xticks(QS); a.set_xlabel("Primary demand (veh/h)")
a.set_ylabel("Switching margin  $C_{SP}-C_{DTT}$")
a.set_title("(a) Preference reverses with demand",fontsize=8.5,loc="left")
a.legend(loc="upper left",fontsize=7.5)
a.set_ylim(-0.62,1.20)
a.text(735,0.06,"SP preferred",fontsize=6.8,color=INK2,style="italic")
a.text(1265,-0.13,"DTT preferred",fontsize=6.8,color=INK2,style="italic")
b=ax[1]
cells=np.zeros((3,8)); labs=[]
for j,(r,sig) in enumerate([(r,s) for s in ("Balanced","Arterial") for r in RES]):
    labs.append(f"{r}\n{sig[:3]}")
    for i,q in enumerate(QS):
        c=[k for k in ctxs if meta[k]==(q,r,sig)][0]
        w=min(COST[c],key=lambda p:COST[c][p]); cells[i,j]=POL.index(w)
b.imshow(cells,cmap=matplotlib.colors.ListedColormap([SP_C,DTT_C,TEC_C]),aspect="auto",vmin=0,vmax=2)
for i in range(3):
    for j in range(8):
        b.text(j,i,POL[int(cells[i,j])],ha="center",va="center",fontsize=5.9,
               color="white",fontweight="bold")
b.set_xticks(range(8)); b.set_xticklabels(labs,fontsize=6.2)
b.set_yticks(range(3)); b.set_yticklabels(QS); b.set_ylabel("Primary demand (veh/h)")
b.set_xlabel("Restriction location / signal regime"); b.grid(False)
b.set_title("(b) Hindsight-best policy per context",fontsize=8.5,loc="left")
plt.tight_layout(); plt.savefig(OUT+"regime_structure.pdf",bbox_inches="tight"); plt.close()

# ================= FIGURE 2 : decision outcome =================
fig,ax=plt.subplots(1,2,figsize=(7.1,2.6))
a=ax[0]
meths=[("SP",O['fixed']['SP'],SP_C),("DTT",O['fixed']['DTT'],DTT_C),
       ("TECO10",O['fixed']['TECO10'],TEC_C),("adaptive\n(held-out)",O['adaptive_loco'],INK),
       ("hindsight\nbest",O['hindsight'],GRID)]
xs=np.arange(len(meths))
a.bar(xs-.19,[m[1]['mean'] for m in meths],.36,color=[m[2] for m in meths])
a.bar(xs+.19,[m[1]['max'] for m in meths],.36,color=[m[2] for m in meths],alpha=.40)
for i,m in enumerate(meths):
    a.text(i-.19,m[1]['mean']+.02,f"{m[1]['mean']:.3f}",ha="center",fontsize=6.3,color=INK)
a.set_xticks(xs); a.set_xlabel("fixed policies          selector      benchmark",fontsize=7)
a.set_xticklabels([m[0] for m in meths],fontsize=7)
a.set_ylim(0,1.30)
a.set_ylabel("Additive decision regret"); a.legend(handles=[Patch(facecolor=INK2,label="mean regret"),Patch(facecolor=INK2,alpha=.40,label="max regret")],fontsize=7.5,loc="upper center")
a.set_title(f"(a) Adaptive selection captures {O['captured_pct']:.1f}% of headroom",fontsize=8.5,loc="left")
b=ax[1]
ex=O['extrapolation']; q=[720,1200,1680]
xs=np.arange(3)
b.bar(xs-.19,[ex[str(k)]['cart'] for k in q],.36,color=INK,label="adaptive selector")
b.bar(xs+.19,[ex[str(k)]['dtt'] for k in q],.36,color=DTT_C,label="best fixed (DTT)")
for i,k in enumerate(q):
    b.text(i-.19,ex[str(k)]['cart']+.004,f"{ex[str(k)]['cart']:.3f}",ha="center",fontsize=6.3)
    b.text(i+.19,ex[str(k)]['dtt']+.004,f"{ex[str(k)]['dtt']:.3f}",ha="center",fontsize=6.3)
b.set_xticks(xs); b.set_xticklabels([f"{k}" for k in q])
b.set_xlabel("Held-out (unseen) demand regime, veh/h"); b.set_ylabel("Mean regret on held-out regime")
b.legend(fontsize=7.5,loc="upper left",bbox_to_anchor=(0,1.02))
b.set_ylim(0,0.20)
b.annotate("selector worse than\nthe fixed policy",xy=(2-.19,ex['1680']['cart']),xytext=(0.30,.112),
           fontsize=6.8,color=INK,ha="left",arrowprops=dict(arrowstyle="->",color=INK,lw=.9,
           connectionstyle="arc3,rad=-0.15"))
b.set_title("(b) Out-of-regime extrapolation fails",fontsize=8.5,loc="left")
plt.tight_layout(); plt.savefig(OUT+"decision_outcome.pdf",bbox_inches="tight"); plt.close()
print("figures written")
