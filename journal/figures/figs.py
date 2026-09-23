"""Journal figures.  Width is the elsarticle preprint text width, 390 pt = 5.42 in,
so every figure is placed at 1:1 and its text renders at the size set here."""
import json, os, sys, math, collections, itertools, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch
from matplotlib.gridspec import GridSpec
import xml.etree.ElementTree as ET
from sklearn.tree import DecisionTreeClassifier

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = "/home/user/TORS/study"
NUM = json.load(open(os.path.join(HERE, "..", "analysis", "numbers.json")))
OUT = HERE
W = 5.42

POLC = {"P1": "#1F5FA9", "P2": "#D55E00", "P3": "#1B9E77", "P4": "#7A3E9D"}
POLN = {"P1": "P1 shortest", "P2": "P2 reactive", "P3": "P3 load-balancing", "P4": "P4 reliability"}
MARK = {"P1": "o", "P2": "s", "P3": "^", "P4": "D"}
LS = {"P1": "-", "P2": "--", "P3": "-.", "P4": (0, (3, 1, 1, 1))}
INK, INK2, INK3, GRID = "#1a1a1a", "#4d4d4d", "#8c8c8c", "#e6e6e6"
POL = ["P1", "P2", "P3", "P4"]
TEXT = 8.0

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "font.family": "serif", "font.serif": ["DejaVu Serif"], "mathtext.fontset": "dejavuserif",
    "font.size": TEXT, "axes.titlesize": TEXT + 0.5, "axes.labelsize": TEXT,
    "xtick.labelsize": TEXT - 0.7, "ytick.labelsize": TEXT - 0.7, "legend.fontsize": TEXT - 0.7,
    "axes.edgecolor": INK3, "axes.linewidth": 0.6, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "grid.color": GRID, "grid.linewidth": 0.5,
    "lines.linewidth": 1.2, "lines.markersize": 3.4, "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42})

def tidy(ax, grid="y"):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    if grid: ax.grid(axis=grid, lw=0.5, color=GRID); ax.set_axisbelow(True)

def panel(ax, s, x=-0.01, y=1.06):
    ax.text(x, y, s, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=TEXT + 0.5, fontweight="bold", color=INK)

def save(fig, name):
    p = os.path.join(OUT, name + ".pdf"); fig.savefig(p); plt.close(fig)
    print("wrote", os.path.basename(p))

# ---------------------------------------------------------------- data
FACT = ["demand", "gc", "penetration", "lag", "incident", "alt"]
CRIT = {"C1": "C1_sys", "C2": "C2_sys", "C3": "C3_sys"}
def ctx_key(r):
    return (f"d{int(r['demand'])}_g{float(r['gc']):.2f}_p{float(r['penetration']):.1f}"
            f"_l{int(r['lag'])}_i{int(r['incident'])}_a{int(r['alt'])}")
cell = collections.defaultdict(list)
for l in open(os.path.join(STUDY, "results", "main.jsonl")):
    r = json.loads(l)
    if "_error" not in r: cell[(ctx_key(r), r["policy"])].append(r)
CTX = sorted({k[0] for k in cell})
C = {c: {} for c in CRIT}; VEC = {}; META = {}
for (ck, p), g in cell.items():
    g = sorted(g, key=lambda x: x["seed"])
    for c, col in CRIT.items(): C[c][(ck, p)] = st.mean(x[col] for x in g)
    VEC[(ck, p)] = [x[CRIT["C1"]] for x in g]
    META[ck] = {f: g[0][f] for f in FACT}
MINV = {ck: min(C["C1"][(ck, p)] for p in POL) for ck in CTX}
TIED = {ck: [p for p in POL if C["C1"][(ck, p)] == MINV[ck]] for ck in CTX}
WIN = {ck: TIED[ck][0] for ck in CTX}
SBS = NUM["headroom"]["sbs"]
SAT_C, SAT_N, CAP_FREE, CYCLE, YELLOW, FF_C = 1761.0, 1596.0, 1500.0, 90.0, 4.0, 324.0
def desc(m):
    g = (m["gc"] * CYCLE - YELLOW) / CYCLE
    cap = {"C": 2 * SAT_C * g, "N": m["alt"] * SAT_N * g, "S": CAP_FREE}
    tot = sum(cap.values()); D, p = m["demand"], m["penetration"]
    return [D / tot, D / cap["C"], cap["N"] / tot, g, p, m["lag"] / FF_C, float(m["incident"]), p * D / cap["C"]]
X = np.array([desc(META[ck]) for ck in CTX])
def resolved(a, b, k=2.0):
    d = np.asarray(a, float) - np.asarray(b, float)
    se = d.std(ddof=1) / math.sqrt(len(d))
    return bool(abs(d.mean()) > k * se), float(d.mean()), float(se)
RES = {}
for ck in CTX:
    o = sorted(POL, key=lambda p: (C["C1"][(ck, p)], POL.index(p)))
    RES[ck] = resolved(VEC[(ck, o[1])], VEC[(ck, o[0])])[0]

# ================================================================ FIGURE 1
def fig1():
    net = os.path.join(STUDY, "scenario", "agb_alt1.net.xml")
    root = ET.parse(net).getroot()
    nodes, edges = {}, {}
    for j in root.findall("junction"):
        if j.get("type") != "internal":
            nodes[j.get("id")] = (float(j.get("x")), float(j.get("y")), j.get("type"))
    for e in root.findall("edge"):
        if e.get("function") == "internal": continue
        ls = e.findall("lane")
        edges[e.get("id")] = dict(frm=e.get("from"), to=e.get("to"), n=len(ls))
    fig = plt.figure(figsize=(W, 4.25))
    gs = GridSpec(2, 1, height_ratios=[1.0, 0.60], hspace=0.10, figure=fig)
    ax = fig.add_subplot(gs[0]); COLF = {"C": POLC["P1"], "N": POLC["P3"], "S": POLC["P4"]}
    def fam(i): return ("C" if i.startswith("c") else "N" if i.startswith("n")
                        else "S" if i.startswith("s") else "A" if i in ("w_d", "m_e") else "X")
    for eid, e in edges.items():
        x0, y0, _ = nodes[e["frm"]]; x1, y1, _ = nodes[e["to"]]; f = fam(eid)
        if f == "X": ax.plot([x0, x1], [y0, y1], color=INK3, lw=0.8, zorder=1)
        elif f == "A": ax.plot([x0, x1], [y0, y1], color=INK2, lw=2.3, zorder=2, solid_capstyle="round")
        else: ax.plot([x0, x1], [y0, y1], color=COLF[f], lw=1.0 + 1.2 * e["n"], zorder=3,
                      solid_capstyle="round")
    for k, x, y, dy in (("C", 2700, 0, -15), ("N", 2700, 400, 8), ("S", 1500, -900, -17)):
        ax.annotate(k, (x, y), textcoords="offset points", xytext=(0, dy), ha="center",
                    fontsize=TEXT + 0.5, color=COLF[k], fontweight="bold")
    for nid, (x, y, t) in nodes.items():
        if t == "traffic_light":
            ax.plot(x, y, "s", ms=4.2, mfc="white", mec=INK, mew=0.9, zorder=5)
        elif nid in ("W", "E"):
            ax.plot(x, y, "o", ms=7, mfc=INK, mec="none", zorder=5)
            ax.annotate("origin" if nid == "W" else "destination", (x, y),
                        textcoords="offset points", xytext=(0, -19), ha="center",
                        fontsize=TEXT - 1.3, color=INK2)
        elif nid in ("D", "M"):
            ax.plot(x, y, "o", ms=4.8, mfc="white", mec=INK, mew=1.0, zorder=6)
            ax.annotate("diverge" if nid == "D" else "merge", (x, y), textcoords="offset points",
                        xytext=(-6 if nid == "D" else 6, 8), ha="right" if nid == "D" else "left",
                        fontsize=TEXT - 1.3, color=INK2)
        else: ax.plot(x, y, "o", ms=2.2, mfc=INK3, mec="none", zorder=4)
    ax.set_xlim(-1150, 4050); ax.set_ylim(-2750, 800); ax.set_aspect("equal"); ax.axis("off")
    h = [Line2D([], [], color=COLF["C"], lw=3.4, label="C  central arterial: 3000 m, 2 lanes, 4 signals"),
         Line2D([], [], color=COLF["N"], lw=2.2, label="N  north street: 3242 m, 1--2 lanes, 4 signals"),
         Line2D([], [], color=COLF["S"], lw=2.2, label="S  south bypass: 3963 m, 1 lane, unsignalised"),
         Line2D([], [], color=INK, marker="s", ls="none", ms=4.2, mfc="white", mew=0.9,
                label="signalised junction (2 phases, 90 s cycle)")]
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=1,
              handlelength=1.6, labelspacing=0.30, fontsize=TEXT - 1.2, borderaxespad=0.0)
    panel(ax, "(a)", x=0.0, y=0.90)

    ax2 = fig.add_subplot(gs[1]); ax2.axis("off")
    rows = [("corridor demand $D$ (veh/h)", "1200, 1800, 2400, 3000, 3600, 4200", 6),
            ("effective green ratio $g_c$", "0.35, 0.50, 0.65", 3),
            ("guidance penetration $p$", "0.2, 0.5, 0.8", 3),
            ("information lag $\\ell$ (s)", "30, 120, 300", 3),
            ("disruption", "absent, present", 2),
            ("alternative capacity", "1 or 2 lanes on N", 2)]
    y = 0.96
    for name, lv, k in rows:
        ax2.text(0.0, y, name, transform=ax2.transAxes, va="top", fontsize=TEXT - 0.4, color=INK)
        ax2.text(0.42, y, lv, transform=ax2.transAxes, va="top", fontsize=TEXT - 0.4, color=INK2)
        ax2.text(0.985, y, f"{k}", transform=ax2.transAxes, va="top", ha="right",
                 fontsize=TEXT - 0.4, color=INK2)
        y -= 0.135
    ax2.plot([0.0, 0.985], [y + 0.085, y + 0.085], transform=ax2.transAxes, color=INK3, lw=0.6)
    ax2.text(0.0, y + 0.045, "full factorial", transform=ax2.transAxes, va="top",
             fontsize=TEXT - 0.4, color=INK, fontweight="bold")
    ax2.text(0.42, y + 0.045, "$6\\times3\\times3\\times3\\times2\\times2$ contexts", transform=ax2.transAxes,
             va="top", fontsize=TEXT - 0.4, color=INK2)
    ax2.text(0.985, y + 0.045, "648 contexts", transform=ax2.transAxes, va="top", ha="right",
             fontsize=TEXT - 0.4, color=INK, fontweight="bold")
    panel(ax2, "(b)", x=0.0, y=0.99)
    save(fig, "fig1_network_design")

# ================================================================ FIGURE 2
def fig2():
    fig, axs = plt.subplots(1, 3, figsize=(W, 1.78))
    dem = sorted({META[c]["demand"] for c in CTX})
    ax = axs[0]
    for p in POL:
        ax.plot(dem, [st.mean(C["C1"][(c, p)] for c in CTX if META[c]["demand"] == d) for d in dem],
                color=POLC[p], ls=LS[p], marker=MARK[p], ms=2.8, mec="white", mew=0.4, label=p)
    ax.set_xlabel("corridor demand (veh/h)"); ax.set_ylabel("mean journey time (s)")
    ax.set_xticks(dem); ax.set_xticklabels([str(int(d)) for d in dem], rotation=45, ha="right")
    ax.legend(handlelength=1.8, borderaxespad=0.2, loc="upper left")
    panel(ax, "(a)"); tidy(ax)
    ax = axs[1]
    for p in ("P2", "P3", "P4"):
        ax.plot(dem, [st.mean(C["C1"][(c, p)] for c in CTX if META[c]["demand"] == d) for d in dem],
                color=POLC[p], ls=LS[p], marker=MARK[p], ms=2.8, mec="white", mew=0.4, label=p)
    ax.set_xlabel("corridor demand (veh/h)"); ax.set_ylabel("mean journey time (s)")
    ax.set_xticks(dem); ax.set_xticklabels([str(int(d)) for d in dem], rotation=45, ha="right")
    ax.legend(handlelength=1.8, borderaxespad=0.2, loc="upper left")
    panel(ax, "(b)"); tidy(ax)
    ax = axs[2]
    pen = sorted({META[c]["penetration"] for c in CTX})
    for p in POL:
        ax.plot(pen, [st.mean(C["C1"][(c, p)] for c in CTX if META[c]["penetration"] == q) for q in pen],
                color=POLC[p], ls=LS[p], marker=MARK[p], ms=2.8, mec="white", mew=0.4)
    ax.set_xlabel("guidance penetration"); ax.set_ylabel("mean journey time (s)")
    ax.set_xticks(pen)
    panel(ax, "(c)"); tidy(ax)
    fig.tight_layout(pad=0.3, w_pad=1.5)
    save(fig, "fig3_cost_landscape")

# ================================================================ FIGURE 3
def fig3():
    fig = plt.figure(figsize=(W, 3.55))
    gs = GridSpec(2, 1, height_ratios=[1.0, 1.12], hspace=0.62, figure=fig)
    ax = fig.add_subplot(gs[0])
    dem = sorted({META[c]["demand"] for c in CTX}); pen = sorted({META[c]["penetration"] for c in CTX})
    for i, q in enumerate(pen):
        for j, d in enumerate(dem):
            sub = [c for c in CTX if META[c]["demand"] == d and META[c]["penetration"] == q]
            cnt = collections.Counter(WIN[c] for c in sub)
            w, k = cnt.most_common(1)[0]
            nres = sum(1 for c in sub if RES[c])
            ax.add_patch(Rectangle((j, -i), 1, 1, facecolor=POLC[w], alpha=0.25 + 0.55 * k / len(sub),
                                   edgecolor="white", lw=1.0))
            ax.text(j + .5, -i + .70, w, ha="center", va="center", fontsize=TEXT - 0.6,
                    fontweight="bold", color=INK)
            ax.text(j + .5, -i + .45, f"{k}/{len(sub)}", ha="center", va="center",
                    fontsize=TEXT - 1.8, color=INK2)
            ax.text(j + .5, -i + .21, f"{nres} res", ha="center", va="center",
                    fontsize=TEXT - 2.6, color=INK2)
    ax.set_xlim(0, 6); ax.set_ylim(-2, 1); ax.set_aspect("equal")
    ax.set_xticks([j + .5 for j in range(6)])
    ax.set_xticklabels([str(int(d)) for d in dem])
    ax.set_yticks([.5, -.5, -1.5]); ax.set_yticklabels([f"{q:.1f}" for q in pen])
    ax.set_xlabel("corridor demand (veh/h)"); ax.set_ylabel("guidance penetration")
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    panel(ax, "(a)", y=1.04); tidy(ax, grid=None)
    ax = fig.add_subplot(gs[1])
    rm = [100 * (sorted(C["C1"][(c, p)] for p in POL)[1] - MINV[c]) / MINV[c] for c in CTX if RES[c]]
    um = [100 * (sorted(C["C1"][(c, p)] for p in POL)[1] - MINV[c]) / MINV[c] for c in CTX if not RES[c]]
    bins = np.logspace(-5, 1.6, 34)
    ax.hist(np.clip(um, 1e-5, None), bins=bins, color=INK3, alpha=0.85, label=f"unresolved ($n={len(um)}$)")
    ax.hist(np.clip(rm, 1e-5, None), bins=bins, color=POLC["P3"], alpha=0.85, label=f"resolved ($n={len(rm)}$)")
    ax.set_xscale("log"); ax.set_xlabel("winning margin (% of best journey time)")
    ax.set_ylabel("contexts"); ax.legend(loc="upper left", borderaxespad=0.2)
    ax.axvline(st.median(um), color=INK2, ls=":", lw=0.9)
    ax.axvline(st.median(rm), color=POLC["P3"], ls=":", lw=0.9)
    panel(ax, "(b)"); tidy(ax)
    save(fig, "fig2_complementarity")

# ================================================================ FIGURE 4
def fig4():
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.05))
    H = NUM["headroom"]
    ax = axs[0]
    order4 = ["P1", "P4", "P2", "P3"]
    vals = [H["penalty_s"][p] for p in order4] + [H["headroom_s"]]
    labs = [f"fix {p}" for p in order4] + ["adapt"]
    cols = [POLC[p] for p in order4] + [INK]
    ax.barh(range(5), np.maximum(vals, 2e-2), color=cols, height=0.64)
    ax.set_xscale("log"); ax.set_xlim(2e-2, 2.2e3)
    ax.set_yticks(range(5)); ax.set_yticklabels(labs, fontsize=TEXT - 1.2); ax.invert_yaxis()
    ax.set_xlabel("cost above the best\navailable choice (s/veh)")
    for i, v in enumerate(vals):
        ax.text(max(v, 2e-2) * 1.5, i, "0 (best fixed)" if v == 0 else f"{v:.3g}",
                va="center", fontsize=TEXT - 2.0, color=INK2)
    panel(ax, "(a)"); tidy(ax, grid="x")
    ax = axs[1]
    L = {r["selector"]: r for r in NUM["ladder"]["ladder"]}
    order = ["B1_mechanistic", "B0_SBS", "B5_selective", "B2_tree3", "B3_logit", "B4_GBDT", "VBS_reference"]
    nm = {"B0_SBS": "fixed (SBS)", "B1_mechanistic": "mechanistic rule", "B2_tree3": "tree, depth 3",
          "B3_logit": "logistic", "B4_GBDT": "advantage GBDT", "B5_selective": "selective",
          "VBS_reference": "hindsight (VBS)"}
    v = [L[k]["mean_regret"] for k in order]
    cc = [INK3 if k in ("B0_SBS", "B5_selective") else ("#bfc6cb" if k == "VBS_reference" else POLC["P3"])
          for k in order]
    ax.barh(range(len(order)), v, color=cc, height=0.66)
    for i, k in enumerate(order):
        ax.text(v[i] + 0.012, i, f"{v[i]:.3f}", va="center", fontsize=TEXT - 2.0, color=INK2)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([nm[k] for k in order], fontsize=TEXT - 1.4)
    ax.invert_yaxis(); ax.set_xlabel("mean decision regret (s/veh)"); ax.set_xlim(0, 0.95)
    panel(ax, "(b)"); tidy(ax, grid="x")
    ax = axs[2]
    nb = [c for c in CTX if C["C1"][(c, SBS)] > MINV[c]]
    hr = [C["C1"][(c, SBS)] - MINV[c] for c in nb]
    nz = []
    for c in nb:
        b2 = min(POL, key=lambda p: (C["C1"][(c, p)], POL.index(p)))
        d = np.array(VEC[(c, SBS)]) - np.array(VEC[(c, b2)])
        nz.append(2.0 * d.std(ddof=1) / math.sqrt(5))
    ax.scatter(nz, hr, s=5, color=POLC["P3"], alpha=0.55, lw=0)
    lim = [1e-3, 40]
    ax.plot(lim, lim, color=INK2, ls="--", lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(*lim); ax.set_ylim(*lim)
    ax.set_xlabel("replication noise band, $2\\,$SE (s)")
    ax.set_ylabel("headroom in that context (s)")
    ax.text(0.03, 0.97, f"above the line: {NUM['resolvability']['n_headroom_exceeds_noise']} of {len(nb)}",
            transform=ax.transAxes, fontsize=TEXT - 2.2, color=INK2, va="top")
    panel(ax, "(c)"); tidy(ax, grid=None)
    fig.tight_layout(pad=0.3, w_pad=2.0)
    save(fig, "fig5_decision_value")

# ================================================================ FIGURE 5
def fig5():
    y = np.array([POL.index(WIN[c]) for c in CTX])
    t = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, y)
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.05))
    ax = axs[0]
    thr = t.tree_.threshold[0]
    for p in POL:
        m = [i for i in range(len(CTX)) if WIN[CTX[i]] == p]
        if not m: continue
        ax.scatter(X[m, 7], X[m, 3], s=7, color=POLC[p], marker=MARK[p], alpha=0.6, lw=0,
                   label=POLN[p])
    ax.axvline(thr, color=INK, lw=1.0, ls="--")
    ax.annotate(f"$x_8={thr:.2f}$", (thr, 0.615), textcoords="offset points", xytext=(4, 0),
                fontsize=TEXT - 1.2, color=INK)
    ax.set_xlabel("$x_8$: guided demand / shortest-corridor capacity")
    ax.set_ylabel("$x_4$: effective green ratio")
    ax.legend(loc="lower right", handletextpad=0.2, borderaxespad=0.2, fontsize=TEXT - 1.6,
              scatterpoints=1)
    panel(ax, "(a)"); tidy(ax, grid=None)
    ax = axs[1]
    edges = np.quantile(X[:, 7], np.linspace(0, 1, 11))
    mids = 0.5 * (edges[:-1] + edges[1:])
    bot = np.zeros(len(mids))
    for p in POL:
        share = []
        for i in range(len(mids)):
            m = [j for j in range(len(CTX)) if edges[i] <= X[j, 7] <= edges[i + 1]]
            share.append(sum(1 for j in m if WIN[CTX[j]] == p) / max(len(m), 1))
        ax.bar(mids, share, bottom=bot, width=np.diff(edges) * 0.92, color=POLC[p],
               label=p, edgecolor="white", lw=0.3)
        bot += np.array(share)
    ax.axvline(thr, color=INK, lw=1.0, ls="--")
    ax.set_xlabel("$x_8$: guided demand / shortest-corridor capacity")
    ax.set_ylabel("share of contexts won")
    ax.set_ylim(0, 1); ax.set_xlim(edges[0], edges[-1])
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.16), handlelength=1.0,
              columnspacing=0.9, fontsize=TEXT - 1.6)
    panel(ax, "(b)"); tidy(ax, grid=None)
    fig.tight_layout(pad=0.3, w_pad=2.0)
    save(fig, "fig4_mechanism")

# ================================================================ FIGURE 6
def fig6():
    O = NUM["ood"]
    order = ["O3_demand_mid", "O2_demand_low", "O1_demand_high", "O4_lag_long",
             "O5_penetration", "O6_green_high", "O7_incident", "O8_northcorridor"]
    lab = {"O1_demand_high": "O1 demand high", "O2_demand_low": "O2 demand low",
           "O3_demand_mid": "O3 demand mid", "O4_lag_long": "O4 lag long",
           "O5_penetration": "O5 penetration", "O6_green_high": "O6 green high",
           "O7_incident": "O7 disruption", "O8_northcorridor": "O8 north corridor"}
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.45), gridspec_kw=dict(width_ratios=[1.5, 1.0]))
    ax = axs[0]
    i = np.arange(len(order)); w = 0.38
    b0 = [O[k]["B0_SBS"]["mean_regret"] for k in order]
    b4 = [O[k]["B4_GBDT"]["mean_regret"] for k in order]
    ax.barh(i - w / 2, b0, height=w, color=INK3, label="fixed policy")
    ax.barh(i + w / 2, b4, height=w, color=POLC["P3"], label="advantage GBDT")
    for j, k in enumerate(order):
        worse = b4[j] > b0[j] + 0.05
        if worse: ax.text(b4[j] + 0.04, j + w / 2, "harms", va="center",
                          fontsize=TEXT - 2.2, color="#B3261E")
    ax.set_yticks(i); ax.set_yticklabels([lab[k] for k in order], fontsize=TEXT - 1.2)
    ax.invert_yaxis(); ax.set_xlabel("mean decision regret (s/veh)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, borderaxespad=0.0,
              handlelength=1.1, fontsize=TEXT - 1.4)
    panel(ax, "(a)", y=1.20); tidy(ax, grid="x")
    ax = axs[1]
    oos = [100 * O[k]["_out_of_support_rate"] for k in order]
    ab = [100 * O[k]["_abstain_rate"] for k in order]
    ax.barh(i - w / 2, oos, height=w, color="#7A3E9D", label="flagged out of support")
    ax.barh(i + w / 2, ab, height=w, color="#D55E00", label="abstained")
    ax.set_yticks(i); ax.set_yticklabels([]); ax.invert_yaxis()
    ax.set_xlabel("share of held-out contexts (%)"); ax.set_xlim(0, 118)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=1, borderaxespad=0.0,
              handlelength=1.1, fontsize=TEXT - 1.4)
    ax.annotate("nothing flagged", (0, 7 - w / 2), textcoords="offset points",
                xytext=(5, 0), fontsize=TEXT - 2.0, color="#B3261E", va="center")
    panel(ax, "(b)", y=1.20); tidy(ax, grid="x")
    fig.tight_layout(pad=0.3, w_pad=0.8)
    save(fig, "fig7_shift")

# ================================================================ FIGURE 7
def fig7():
    fig, axs = plt.subplots(1, 3, figsize=(W, 1.78))
    ax = axs[0]
    s = NUM["pareto"]["sizes"]
    ks = sorted(int(k) for k in s)
    ax.bar(ks, [s[str(k)] for k in ks], color=POLC["P3"], width=0.62)
    for k in ks: ax.text(k, s[str(k)] + 8, s[str(k)], ha="center", fontsize=TEXT - 2.0, color=INK2)
    ax.set_xlabel("policies in the Pareto set"); ax.set_ylabel("contexts"); ax.set_xticks(ks)
    ax.set_ylim(0, 290)
    panel(ax, "(a)"); tidy(ax)
    ax = axs[1]
    B = NUM["best_by_criterion"]; crits = ["C1", "C2", "C3"]
    cl = {"C1": "journey time", "C2": "CO$_2$", "C3": "stopped delay"}
    bot = np.zeros(3)
    for p in POL:
        v = np.array([B[c].get(p, 0) for c in crits])
        ax.bar(range(3), v, bottom=bot, color=POLC[p], label=p, width=0.62, edgecolor="white", lw=0.4)
        bot += v
    ax.set_xticks(range(3)); ax.set_xticklabels(["time", "CO$_2$", "stopped"], fontsize=TEXT - 1.2)
    ax.set_ylabel("contexts where best"); ax.set_ylim(0, 648)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.17), handlelength=0.9,
              columnspacing=0.7, fontsize=TEXT - 1.8)
    panel(ax, "(b)"); tidy(ax)
    ax = axs[2]
    pairs = [("C1_C2", "time\nvs CO$_2$"), ("C1_C3", "time vs\nstopped"), ("C2_C3", "CO$_2$ vs\nstopped")]
    v = [NUM["criteria"][k]["within"] for k, _ in pairs]
    ax.bar(range(3), v, color=INK3, width=0.62)
    for i, x in enumerate(v): ax.text(i, x + 0.02, f"{x:.2f}", ha="center", fontsize=TEXT - 2.0, color=INK2)
    ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in pairs], fontsize=TEXT - 1.6)
    ax.set_ylabel("mean within-context\nrank correlation"); ax.set_ylim(0, 1.0)
    panel(ax, "(c)"); tidy(ax)
    fig.tight_layout(pad=0.3, w_pad=1.6)
    save(fig, "fig6_criteria")

for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7): f()
