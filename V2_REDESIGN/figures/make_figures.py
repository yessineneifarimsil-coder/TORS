"""V2 design figures. Schematics only — no result is plotted, because none exists."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
INK,MUTED,FAINT="#2f3437","#6b7378","#9aa3ab"
BLUE,ORANGE,AQUA="#2a78d6","#eb6834","#1baf7a"
plt.rcParams.update({"font.family":"DejaVu Sans","pdf.fonttype":42})

def box(ax,x,y,w,h,t,fc="white",ec=INK,fs=7.4,tc=INK,lw=1.1,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc,ec=ec,lw=lw,zorder=2))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,color=tc,zorder=3,
            fontweight="bold" if bold else "normal",linespacing=1.45)

def arrow(ax,p,q,color=MUTED,lw=1.2,style="-|>"):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle=style,mutation_scale=9,color=color,lw=lw,
                                 shrinkA=2,shrinkB=2,zorder=1))

# ---------------- Figure: full V2 architecture ----------------
fig,ax=plt.subplots(figsize=(6.6,4.5)); ax.axis("off"); ax.set_xlim(0,1); ax.set_ylim(0,1)
ax.text(0.5,0.975,"V2 architecture — context-dependent routing-policy selection",
        ha="center",va="top",fontsize=9.4,color=INK,fontweight="bold")

box(ax,.03,.845,.30,.085,"TRAFFIC CONTEXT\ndesign variables only",fc="#eef3fa",ec=BLUE,tc=INK,bold=True)
box(ax,.37,.845,.26,.085,"POLICY PORTFOLIO\nP1 · P2 · P3 · P4",fc="#eef3fa",ec=BLUE,bold=True)
box(ax,.67,.845,.30,.085,"SUMO\nnetwork response",fc="#eef3fa",ec=BLUE,bold=True)
arrow(ax,(.33,.888),(.37,.888)); arrow(ax,(.63,.888),(.67,.888))

box(ax,.67,.715,.30,.075,"OUTCOMES\nsystem TT · P95 · CO₂")
arrow(ax,(.82,.845),(.82,.79))
box(ax,.36,.715,.28,.075,"DECISION LAYER\nPareto → system objective")
arrow(ax,(.67,.752),(.64,.752))
box(ax,.03,.715,.30,.075,"PER-CONTEXT BEST POLICY\nregret · headroom · VBS/SBS")
arrow(ax,(.36,.752),(.33,.752))

ax.plot([.02,.98],[.665,.665],color=FAINT,lw=.8,ls=(0,(4,3)))
ax.text(.02,.652,"above: measurement   ·   below: learned selection",fontsize=6.5,color=FAINT,va="top")

box(ax,.03,.50,.30,.095,"MECHANISTIC FEATURES\nsaturation · penetration\nlag ratio · capacity share",
    fc="#fdf1ec",ec=ORANGE)
arrow(ax,(.18,.715),(.18,.595))
box(ax,.37,.50,.26,.095,"GBDT ADVANTAGE MODEL\n"+r"$\Delta_a(x)=C_{\mathrm{SBS}}-C_a$",fc="#fdf1ec",ec=ORANGE,bold=True)
arrow(ax,(.33,.548),(.37,.548))
box(ax,.67,.50,.30,.095,"PREDICTED ADVANTAGE\nper policy, with interval",fc="#fdf1ec",ec=ORANGE)
arrow(ax,(.63,.548),(.67,.548))

box(ax,.67,.355,.30,.075,"GATE 1 — SUPPORT\nis x inside training support?",fc="#eaf6f1",ec=AQUA)
arrow(ax,(.82,.50),(.82,.43))
box(ax,.67,.235,.30,.075,"GATE 2 — CONFIDENCE\nlower bound on Δ > 0 ?",fc="#eaf6f1",ec=AQUA)
arrow(ax,(.82,.355),(.82,.31))

box(ax,.55,.085,.24,.085,"ACT\nselected policy",fc="white",ec=AQUA,bold=True)
box(ax,.83,.085,.155,.085,"ABSTAIN\nfixed policy",fc="white",ec=MUTED,tc=MUTED,bold=True)
arrow(ax,(.79,.235),(.70,.17),color=AQUA); arrow(ax,(.92,.235),(.92,.17),color=MUTED)
ax.text(.685,.205,"pass",fontsize=6.2,color=AQUA,ha="right")
ax.text(.935,.205,"fail",fontsize=6.2,color=MUTED,ha="left")

box(ax,.03,.085,.44,.14,"EVALUATION LADDER\nB0 best fixed → B1 mechanistic rule →\nB2/B3 ML → B4 GBDT → B5 selective\nreference: cross-fitted VBS (not deployable)",
    fc="#f6f7f8",ec=MUTED,fs=6.9,tc=INK)
arrow(ax,(.55,.128),(.47,.128),color=MUTED)
ax.text(.25,.055,"headline test: B4 vs B1",ha="center",fontsize=6.9,color=ORANGE,style="italic")
ax.text(.99,.012,"Schematic of the proposed design. No V2 result exists.",
        ha="right",fontsize=6.2,color=FAINT,style="italic")
fig.savefig("figures/v2_architecture.pdf",bbox_inches="tight",pad_inches=0.02); plt.close()

# ---------------- Figure: two decision levels ----------------
fig,ax=plt.subplots(figsize=(6.2,1.85)); ax.axis("off"); ax.set_xlim(0,1); ax.set_ylim(0,1)
box(ax,.02,.55,.22,.34,"Traffic context\nx",fc="#eef3fa",ec=BLUE,fs=8,bold=True)
box(ax,.30,.55,.26,.34,"Choose ONE\nrouting policy",fc="#fdf1ec",ec=ORANGE,fs=8,bold=True)
box(ax,.62,.55,.36,.34,"Policy assigns routes\nby its own objective",fc="#eaf6f1",ec=AQUA,fs=8,bold=True)
arrow(ax,(.24,.72),(.30,.72)); arrow(ax,(.56,.72),(.62,.72))
ax.text(.43,.46,"LEVEL 1 — what the model learns",ha="center",fontsize=7,color=ORANGE,fontweight="bold")
ax.text(.80,.46,"LEVEL 2 — not learned",ha="center",fontsize=7,color=AQUA,fontweight="bold")
ax.text(.02,.20,"The model selects the policy, not the individual route.",
        fontsize=7.6,color=INK)
ax.text(.02,.05,"Per-instance algorithm selection applied to route guidance — not route prediction, "
        "signal control, or RL.",fontsize=6.6,color=MUTED)
fig.savefig("figures/v2_two_levels.pdf",bbox_inches="tight",pad_inches=0.02); plt.close()

# ---------------- Figure: design variables vs outcomes ----------------
fig,ax=plt.subplots(figsize=(6.2,2.5)); ax.axis("off"); ax.set_xlim(0,1); ax.set_ylim(0,1)
ax.text(.24,.95,"DESIGN VARIABLES",ha="center",fontsize=8,color=BLUE,fontweight="bold")
ax.text(.24,.87,"settable / known before activation",ha="center",fontsize=6.4,color=MUTED)
ax.text(.76,.95,"MEASURED OUTCOMES",ha="center",fontsize=8,color=MUTED,fontweight="bold")
ax.text(.76,.87,"never used as features",ha="center",fontsize=6.4,color=MUTED)
L=["Demand per OD","Guidance penetration","Information lag Δ","Incident location · severity",
   "Alternative-capacity ratio","Signal green ratio g/C"]
R=["Realised saturation","Link flows · queues","Travel time · P95","Emissions",
   "Utilisation · spillback","Policy winner · regret"]
for i,(l,r) in enumerate(zip(L,R)):
    y=.74-i*.115
    box(ax,.02,y-.045,.44,.085,l,fc="#eef3fa",ec=BLUE,fs=7,lw=.9)
    box(ax,.54,y-.045,.44,.085,r,fc="#f6f7f8",ec=FAINT,fs=7,tc=MUTED,lw=.9)
ax.plot([.50,.50],[.03,.82],color=FAINT,lw=1.0,ls=(0,(4,3)))
ax.text(.50,.015,"congestion is an outcome, never a factor",ha="center",fontsize=6.6,
        color=ORANGE,style="italic")
fig.savefig("figures/v2_factors.pdf",bbox_inches="tight",pad_inches=0.02); plt.close()
print("wrote v2_architecture.pdf, v2_two_levels.pdf, v2_factors.pdf")
