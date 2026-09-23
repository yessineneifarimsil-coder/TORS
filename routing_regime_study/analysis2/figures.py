"""Publication figures sized for the LNCS text width (12.2 cm = 4.82 in), drawn 1:1.
Every plotted value comes from analysis/runs.csv via core.py."""
import json, math, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import numpy as np
import openpyxl
import core as K

OUT = "/home/user/TORS/routing_regime_study/final/figures"
WB = "/root/.claude/uploads/35501cb2-bbe1-5745-801e-da4fe3f5e9fd/554ddaf1-Routing_Strategy_Selection_Corrected.xlsx"
W = 4.82                                  # LNCS \textwidth in inches

# Okabe-Ito, colour-vision-deficiency safe; assigned in fixed order, never cycled
CLR = {"SP": "#0072B2", "DTT": "#D55E00", "TECO10": "#009E73"}
MRK = {"SP": "o", "DTT": "s", "TECO10": "^"}
INK, MUTED, FAINT, GRID = "#2f3437", "#6b7378", "#9aa3ab", "#dfe3e6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.size": 7.2, "axes.labelsize": 7.2, "axes.titlesize": 7.8,
    "xtick.labelsize": 6.7, "ytick.labelsize": 6.7, "legend.fontsize": 6.6,
    "axes.edgecolor": "#b9c0c5", "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.labelcolor": INK, "axes.titlecolor": INK,
    "xtick.major.size": 2.4, "ytick.major.size": 2.4,
    "grid.color": GRID, "grid.linewidth": 0.5,
    "legend.frameon": False, "figure.dpi": 200})

def tidy(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid, lw=0.5, color=GRID, zorder=0)
    ax.set_axisbelow(True)

T = K.ctx_means("time"); C = K.ctx_means("co2"); Q = K.ctx_means("stopped")
COST, aT, aC = K.scalarise(T, C, K.CTXS)
HBW = {c: min(COST[c], key=lambda p: COST[c][p]) for c in K.CTXS}
EX = json.load(open("extend.json")); EX2 = json.load(open("extend2.json"))
OLDR = json.load(open("/home/user/TORS/routing_regime_study/analysis/results.json"))
NOISE = EX["noise_per_context"]
CELLS = [(s, r) for r in K.RES for s in ("Balanced", "Arterial")]
RLAB = {"None": "none", "U": "upper", "C": "central", "L": "lower"}

def policy_map(ax, annotate_resolution=False, fs=5.6):
    for i, q in enumerate(K.DEMANDS):
        for j, (sig, restr) in enumerate(CELLS):
            c = [k for k in K.CTXS if K.META[k] == (q, restr, sig)][0]
            w = HBW[c]
            ax.add_patch(Rectangle((j, -i), 1, 1, facecolor=CLR[w], alpha=0.9,
                                   edgecolor="white", lw=1.0))
            ax.text(j + 0.5, -i + (0.58 if annotate_resolution and not NOISE[c]["resolved"] else 0.5),
                    {"SP": "SP", "DTT": "DTT", "TECO10": "TEC"}[w], ha="center", va="center",
                    fontsize=fs, color="white", fontweight="bold")
            if annotate_resolution and not NOISE[c]["resolved"]:
                ax.text(j + 0.5, -i + 0.24, "unresolved", ha="center", va="center",
                        fontsize=4.1, color="white", style="italic")
    ax.set_xlim(0, 8); ax.set_ylim(-2, 1); ax.set_aspect("equal")
    ax.set_yticks([0.5, -0.5, -1.5]); ax.set_yticklabels([str(q) for q in K.DEMANDS], fontsize=6.6)
    ax.set_xticks([j + 0.5 for j in range(8)]); ax.set_xticklabels(["B", "A"] * 4, fontsize=5.8)
    ax.tick_params(length=0, pad=1.4)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for r_i, restr in enumerate(K.RES):
        ax.text(2 * r_i + 1, -2.44, RLAB[restr], ha="center", va="top", fontsize=6.2, color=INK)
    ax.set_ylabel("demand (veh/h)", fontsize=6.8, labelpad=2)

# =====================================================================
# FIGURE 1 — network and experimental design
# =====================================================================
ws = openpyxl.load_workbook(WB, data_only=True)["NETWORK"]
links = []
for r in range(20, 70):
    v = ws.cell(r, 1).value
    if not v or v == "External link":
        continue
    links.append(dict(frm=ws.cell(r, 2).value, to=ws.cell(r, 3).value, lanes=int(ws.cell(r, 4).value)))
assert len(links) == 47, len(links)
COL = {0: 0.0, 1: 400.0, 2: 800.0, 3: 1200.0}
ROW = {"U": 300.0, "C": 0.0, "L": -300.0}
XR, O_X, D_X, NS_Y = 550.0, -300.0, 1560.0, 560.0
P = {f"{k}{c}": (COL[c], y) for c in COL for k, y in ROW.items()}
P.update({f"{k}R": (XR, ROW[k]) for k in "UCL"})
P.update({"O": (O_X, 0.0), "D": (D_X, 0.0), "N1": (COL[1], NS_Y), "N2": (COL[2], NS_Y),
          "S1": (COL[1], -NS_Y), "S2": (COL[2], -NS_Y)})
SIGNALS = [f"{k}{c}" for c in COL for k in "UCL"]
BGN = {"N1", "N2", "S1", "S2"}
RESTRICTED = {("U1", "UR"), ("C1", "CR"), ("L1", "LR")}
ACC = "#D55E00"

fig = plt.figure(figsize=(W, 2.52))
ax = fig.add_axes([0.02, 0.135, 0.96, 0.72]); ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-1020, 1800); ax.set_ylim(-740, 740)
LW = {1: 1.6, 2: 2.8, 3: 3.7}
drawn = set()
for l in links:
    key = frozenset((l["frm"], l["to"]))
    if key in drawn:
        continue
    drawn.add(key)
    a, b = l["frm"], l["to"]
    xy = ([P[a][0], P[b][0]], [P[a][1], P[b][1]])
    if (a, b) in RESTRICTED or (b, a) in RESTRICTED:
        ax.plot(*xy, color=ACC, lw=3.8, solid_capstyle="round", zorder=3)
    elif a in BGN or b in BGN:
        ax.plot(*xy, color="#a9b2b9", lw=1.2, ls=(0, (4.5, 2.4)), zorder=1)
    else:
        ax.plot(*xy, color=INK, lw=LW[l["lanes"]], solid_capstyle="round", zorder=2)
def brk(x, y, vert=False):
    for d in (-24, 24):
        for col, w in (("white", 2.8), (MUTED, 0.9)):
            if vert:
                ax.plot([x - 26, x + 26], [y + d - 18, y + d + 18], color=col, lw=w, zorder=5)
            else:
                ax.plot([x + d - 18, x + d + 18], [y - 26, y + 26], color=col, lw=w, zorder=5)
brk(-180, 0); brk(1400, 0)
for xx in (COL[1], COL[2]):
    brk(xx, 440, vert=True); brk(xx, -440, vert=True)
ax.scatter([P[n][0] for n in SIGNALS], [P[n][1] for n in SIGNALS], s=34, marker="s",
           facecolor="#1f2933", edgecolor="white", lw=0.8, zorder=7)
ax.scatter([P[f"{k}R"][0] for k in "UCL"], [P[f"{k}R"][1] for k in "UCL"], s=16, marker="o",
           facecolor="white", edgecolor=ACC, lw=1.2, zorder=8)
ax.scatter([P["O"][0], P["D"][0]], [0, 0], s=30, marker="o", facecolor=INK,
           edgecolor="white", lw=0.8, zorder=7)
ax.scatter([P[n][0] for n in BGN], [P[n][1] for n in BGN], s=16, marker="o",
           facecolor="white", edgecolor=FAINT, lw=1.0, zorder=7)
for c in COL:
    dx, ha = (40, "left") if c == 3 else (-40, "right")
    ax.text(COL[c] + dx, ROW["U"] + 26, f"U{c}", ha=ha, va="bottom", fontsize=5.8, color=INK)
    ax.text(COL[c] + dx, ROW["C"] + 26, f"C{c}", ha=ha, va="bottom", fontsize=5.8, color=INK)
    ax.text(COL[c] + dx, ROW["L"] - 30, f"L{c}", ha=ha, va="top", fontsize=5.8, color=INK)
for n, dy, va in (("N1", 38, "bottom"), ("N2", 38, "bottom"), ("S1", -38, "top"), ("S2", -38, "top")):
    ax.text(P[n][0], P[n][1] + dy, n, ha="center", va=va, fontsize=5.6, color=MUTED)
ax.text(P["O"][0], 36, "O", ha="center", va="bottom", fontsize=6.8, color=INK, fontweight="bold")
ax.text(P["D"][0], 36, "D", ha="center", va="bottom", fontsize=6.8, color=INK, fontweight="bold")
ax.text(O_X, -55, "source\n1500 m, 3 lanes", ha="center", va="top", fontsize=5.3, color=MUTED,
        linespacing=1.3)
ax.text(D_X, -55, "sink\n450 m, 3 lanes", ha="center", va="top", fontsize=5.3, color=MUTED,
        linespacing=1.3)
for k, name in (("U", "upper  40 km/h, 1 lane"), ("C", "central  50 km/h, 1 lane"),
                ("L", "lower  60 km/h, 2 lanes")):
    ax.text(-430, ROW[k] + 4, name, ha="right", va="center", fontsize=5.8, color=MUTED)
ax.legend([Line2D([], [], color=INK, lw=1.6), Line2D([], [], color=INK, lw=2.8),
           Line2D([], [], color=ACC, lw=3.8),
           Line2D([], [], color="#a9b2b9", lw=1.2, ls=(0, (4.5, 2.4))),
           Line2D([], [], marker="s", color="none", markerfacecolor="#1f2933",
                  markeredgecolor="white", markersize=4.8)],
          ["primary link, 1 lane", "primary link, 2 lanes", "restriction segment, 150 m",
           "background approach", "signalised junction"],
          loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3, columnspacing=1.2,
          handlelength=1.6, labelspacing=0.4, fontsize=5.7, handletextpad=0.5)
ax.set_title("Network: 12 signalised junctions, 47 links, 29 legal primary paths",
             loc="left", x=0.0, fontsize=7.8, fontweight="bold", pad=3)
fig.savefig(f"{OUT}/fig1_network.pdf", bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# =====================================================================
# FIGURE 2 — policy performance versus demand
# =====================================================================
fig, axs = plt.subplots(1, 3, figsize=(W, 1.68))
for ax, (key, ylab, title, sc) in zip(axs, [
        ("time", "Mean journey time (s)", "(a) Journey time", 1.0),
        ("co2", "Mean CO$_2$ (g/veh)", "(b) Tailpipe CO$_2$", 1.0),
        ("stopped", "Stopped time (10$^3$ veh-s)", "(c) Network stopped time", 1e-3)]):
    for p in K.POL:
        for q in K.DEMANDS:
            pts = [x[key] * sc for x in K.R if x["policy"] == p and x["demand"] == q]
            ax.scatter([q] * len(pts), pts, s=3.5, color=CLR[p], alpha=0.30, lw=0, zorder=2)
        ax.plot(K.DEMANDS, [st.mean(x[key] for x in K.R if x["policy"] == p and x["demand"] == q) * sc
                            for q in K.DEMANDS],
                color=CLR[p], lw=1.5, marker=MRK[p], ms=3.4, mec="white", mew=0.6, label=p, zorder=3)
    ax.set_xticks(K.DEMANDS); ax.set_xticklabels(["720", "1200", "1680"])
    ax.set_xlabel("Demand (veh/h)", fontsize=6.9)
    ax.set_ylabel(ylab, fontsize=6.9)
    ax.set_title(title, loc="left", fontsize=7.6, fontweight="bold", pad=2.5)
    tidy(ax)
axs[0].legend(loc="upper left", handlelength=1.3, borderaxespad=0.15, fontsize=6.3)
fig.tight_layout(pad=0.3, w_pad=1.1)
fig.savefig(f"{OUT}/fig2_performance.pdf", bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# =====================================================================
# FIGURE 3 — regime structure
# =====================================================================
fig = plt.figure(figsize=(W, 2.72))
ax = fig.add_axes([0.125, 0.545, 0.855, 0.385])
for sig, ls, col in (("Balanced", "-", "#0072B2"), ("Arterial", (0, (4, 2)), "#D55E00")):
    for restr in K.RES:
        cs = [[k for k in K.CTXS if K.META[k] == (q, restr, sig)][0] for q in K.DEMANDS]
        ax.errorbar(K.DEMANDS, [NOISE[c]["margin"] for c in cs],
                    yerr=[2 * NOISE[c]["se"] for c in cs], color=col, ls=ls, lw=1.0, alpha=0.9,
                    marker="o", ms=2.4, mec="white", mew=0.4, capsize=1.8, elinewidth=0.7, zorder=3)
ax.axhline(0, color=INK, lw=0.8, zorder=2)
for xv, col in ((960, "#0072B2"), (1440, "#D55E00")):
    ax.axvline(xv, color=col, lw=0.8, ls=(0, (1.5, 1.8)), zorder=1)
    ax.text(xv, 1.27, str(xv), ha="center", va="bottom", fontsize=6.0, color=col)
ax.set_xlim(660, 1740); ax.set_ylim(-0.26, 1.26)
ax.set_xticks(K.DEMANDS); ax.set_xticklabels(["720", "1200", "1680"])
ax.set_xlabel("Primary demand (veh/h)")
ax.set_ylabel("Switching margin\n$C_{\\mathrm{SP}}-C_{\\mathrm{DTT}}$ (cost units)", fontsize=6.9)
ax.text(1725, 1.20, "DTT preferred", fontsize=6.2, color=MUTED, ha="right", va="center")
ax.text(1725, -0.21, "SP preferred", fontsize=6.2, color=MUTED, ha="right", va="center")
ax.legend(handles=[Line2D([], [], color="#0072B2", ls="-", lw=1.1, marker="o", ms=2.4),
                   Line2D([], [], color="#D55E00", ls=(0, (4, 2)), lw=1.1, marker="o", ms=2.4)],
          labels=["balanced signal plan", "arterial-priority plan"], loc="upper left",
          handlelength=2.1, borderaxespad=0.25, fontsize=6.3)
ax.set_title("(a) Switching margin against demand in all eight cells", loc="left", x=-0.14,
             fontsize=7.8, fontweight="bold", pad=9)
tidy(ax)
ax2 = fig.add_axes([0.125, 0.085, 0.455, 0.29])
policy_map(ax2, annotate_resolution=True)
ax2.set_title("(b) Policy with the lowest observed cost", loc="left", x=-0.06, fontsize=7.8,
              fontweight="bold", pad=4)
fig.legend(handles=[Patch(facecolor=CLR[p], alpha=0.9) for p in K.POL],
           labels=["SP", "DTT", "TECO10"], loc="center left", bbox_to_anchor=(0.615, 0.225),
           ncol=1, handlelength=1.1, fontsize=6.2, labelspacing=0.36)
fig.savefig(f"{OUT}/fig3_regime.pdf", bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# =====================================================================
# FIGURE 4 — decision value
# =====================================================================
LAD = EX["ladder"]
order = ["R0_single_best_fixed", "R1_demand_threshold", "R3_tree_depth1",
         "R2_demand_signal_threshold", "R4_tree_depth3", "R5_hindsight"]
names = ["fixed policy (single best)", "demand threshold", "regression tree, depth 1",
         "demand $\\times$ signal thresholds", "regression tree, depth 3",
         "hindsight best (not deployable)"]
BAR = ["#6b7378", "#56B4E9", "#56B4E9", "#0072B2", "#0072B2", "#bfc6cb"]
fig = plt.figure(figsize=(W, 2.95))
ax = fig.add_axes([0.375, 0.635, 0.605, 0.30])
vals = [LAD[k]["mean"] for k in order]
ax.barh(range(len(order)), vals, color=BAR, height=0.68, zorder=3)
for i, (v, k) in enumerate(zip(vals, order)):
    lab = f"{v:.5f}" if k == "R0_single_best_fixed" else f"{v:.5f}  ({LAD[k]['captured_pct']:.1f}%)"
    ax.text(v + 0.0011, i, lab, va="center", fontsize=6.0, color=INK)
ax.set_yticks(range(len(order))); ax.set_yticklabels(names, fontsize=6.4)
ax.invert_yaxis(); ax.set_xlim(0, 0.049)
ax.set_xlabel("Mean decision regret (normalised cost units)", fontsize=6.9)
ax.set_title("(a) Decision quality under leave-one-context-out", loc="left", x=-0.62,
             fontsize=7.8, fontweight="bold", pad=4)
tidy(ax, grid="x")

RD = EX["regime_decomposition"]
ax2 = fig.add_axes([0.105, 0.125, 0.335, 0.335])
ax2.bar([i - 0.19 for i in range(3)], [RD[str(q)]["DTT"] for q in K.DEMANDS], width=0.38,
        color="#D55E00", label="fixed DTT", zorder=3)
ax2.bar([i + 0.19 for i in range(3)], [RD[str(q)]["adaptive"] for q in K.DEMANDS], width=0.38,
        color="#009E73", label="adaptive", zorder=3)
for i, q in enumerate(K.DEMANDS):
    for dx, key in ((-0.19, "DTT"), (0.19, "adaptive")):
        v = RD[str(q)][key]
        ax2.text(i + dx, v + 0.0016, f"{v:.3f}" if v > 0 else "0", ha="center", va="bottom",
                 fontsize=5.2, color=MUTED, rotation=90 if v > 0 else 0)
ax2.set_xticks(range(3)); ax2.set_xticklabels([str(q) for q in K.DEMANDS], fontsize=6.4)
ax2.set_xlabel("Demand (veh/h)", fontsize=6.9)
ax2.set_ylabel("Mean decision regret", fontsize=6.9)
ax2.set_ylim(0, 0.080)
ax2.legend(loc="upper right", handlelength=1.0, fontsize=6.2, borderaxespad=0.15)
ax2.set_title("(b) Where the headroom lies", loc="left", x=-0.20, fontsize=7.8,
              fontweight="bold", pad=4)
tidy(ax2)

ex = OLDR["extrapolation"]
ax3 = fig.add_axes([0.645, 0.125, 0.335, 0.335])
ax3.bar([i - 0.19 for i in range(3)], [ex[str(q)]["dtt"] for q in K.DEMANDS], width=0.38,
        color="#D55E00", label="fixed DTT", zorder=3)
ax3.bar([i + 0.19 for i in range(3)], [ex[str(q)]["cart"] for q in K.DEMANDS], width=0.38,
        color="#009E73", label="adaptive", zorder=3)
for i, q in enumerate(K.DEMANDS):
    for dx, key in ((-0.19, "dtt"), (0.19, "cart")):
        v = ex[str(q)][key]
        ax3.text(i + dx, v + 0.004, f"{v:.3f}" if v > 0 else "0", ha="center", va="bottom",
                 fontsize=5.2, color=MUTED, rotation=90 if v > 0 else 0)
ax3.set_xticks(range(3)); ax3.set_xticklabels([str(q) for q in K.DEMANDS], fontsize=6.4)
ax3.set_xlabel("Held-out demand (veh/h)", fontsize=6.9)
ax3.set_ylabel("Mean decision regret", fontsize=6.9)
ax3.set_ylim(0, 0.222)
ax3.legend(loc="upper left", handlelength=1.0, fontsize=6.2, borderaxespad=0.15)
ax3.set_title("(c) Demand extrapolation", loc="left", x=-0.20, fontsize=7.8,
              fontweight="bold", pad=4)
tidy(ax3)
fig.savefig(f"{OUT}/fig4_decision.pdf", bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# =====================================================================
# FIGURE 5 — multi-criteria structure
# =====================================================================
def centred(M):
    return {c: {p: M[c][p] - st.mean(M[c][x] for x in K.POL) for p in K.POL} for c in K.CTXS}
Tc, Cc, Qc = centred(T), centred(C), centred(Q)
fig, axs = plt.subplots(1, 3, figsize=(W, 1.74))
ax = axs[0]
for p in K.POL:
    ax.scatter([Tc[c][p] for c in K.CTXS], [Cc[c][p] for c in K.CTXS], s=10, marker=MRK[p],
               facecolor="none", edgecolor=CLR[p], lw=0.7, label=p, zorder=3)
ax.axhline(0, color=FAINT, lw=0.6, zorder=1); ax.axvline(0, color=FAINT, lw=0.6, zorder=1)
ax.set_xlabel("Journey time $-$ context mean (s)", fontsize=6.6)
ax.set_ylabel("CO$_2$ $-$ context mean (g/veh)", fontsize=6.6)
ax.set_title("(a) Two primary criteria", loc="left", fontsize=7.5, fontweight="bold", pad=2.5)
ax.text(0.97, 0.05, "$r$ = %.2f" % EX2["criterion_correlation_within_context"]["time_co2"],
        transform=ax.transAxes, ha="right", fontsize=6.4, color=MUTED)
ax.legend(loc="upper left", handlelength=1.0, borderaxespad=0.15, scatterpoints=1, fontsize=6.0)
tidy(ax, grid="both")
ax = axs[1]
for p in K.POL:
    ax.scatter([Tc[c][p] for c in K.CTXS], [Qc[c][p] * 1e-3 for c in K.CTXS], s=10, marker=MRK[p],
               facecolor="none", edgecolor=CLR[p], lw=0.7, zorder=3)
ax.axhline(0, color=FAINT, lw=0.6, zorder=1); ax.axvline(0, color=FAINT, lw=0.6, zorder=1)
ax.set_xlabel("Journey time $-$ context mean (s)", fontsize=6.6)
ax.set_ylabel("Stopped $-$ mean (10$^3$ veh-s)", fontsize=6.6)
ax.set_title("(b) With stopped time", loc="left", fontsize=7.5, fontweight="bold", pad=2.5)
ax.text(0.97, 0.05, "$r$ = %.2f" % EX2["criterion_correlation_within_context"]["time_stopped"],
        transform=ax.transAxes, ha="right", fontsize=6.4, color=MUTED)
tidy(ax, grid="both")
ax = axs[2]
p2 = EX2["pareto"]["two_criterion"]["by_demand"]; p3 = EX2["pareto"]["three_criterion"]["by_demand"]
ax.bar([i - 0.19 for i in range(3)], [p2[str(q)] for q in K.DEMANDS], width=0.38,
       color="#6b7378", label="time, CO$_2$", zorder=3)
ax.bar([i + 0.19 for i in range(3)], [p3[str(q)] for q in K.DEMANDS], width=0.38,
       color="#CC79A7", label="+ stopped", zorder=3)
ax.axhline(1, color=INK, lw=0.7, ls=(0, (2, 2)), zorder=2)
ax.set_xticks(range(3)); ax.set_xticklabels([str(q) for q in K.DEMANDS])
ax.set_xlabel("Demand (veh/h)", fontsize=6.6)
ax.set_ylabel("Mean Pareto set size (of 3)", fontsize=6.6)
ax.set_ylim(0, 3.2)
ax.legend(loc="upper right", handlelength=1.0, borderaxespad=0.15, fontsize=6.0)
ax.set_title("(c) Comparability", loc="left", fontsize=7.5, fontweight="bold", pad=2.5)
tidy(ax)
fig.tight_layout(pad=0.3, w_pad=1.1)
fig.savefig(f"{OUT}/fig5_pareto.pdf", bbox_inches="tight", pad_inches=0.02)
plt.close(fig)
print("figures 1-5 written at LNCS width")
