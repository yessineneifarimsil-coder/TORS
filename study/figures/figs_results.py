"""Figures 4-9.  Every value is read from the campaign output or results.json;
none is typed in."""
import os, sys, json, itertools, collections, warnings
warnings.filterwarnings("ignore")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "analysis"))
import style as ST
import common as K
import policy_selectors as S

RES = json.load(open(os.path.join(HERE, "..", "results", "results.json")))
df, _ = K.load(os.path.join(HERE, "..", "results", "main.jsonl"))
bad = set(RES["validity"]["excluded_contexts"])
df = df[~df.ctx_key.isin(bad)]
CT = K.context_table(df)
W = K.winners(CT)
PAR = K.pareto_by_context(CT)


# ------------------------------------------------------------------ fig 4
def fig4():
    fig = plt.figure(figsize=(6.6, 4.1))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.78], hspace=0.62, wspace=0.28)
    pens = sorted(CT.penetration.unique())
    for j, pen in enumerate(pens):
        ax = fig.add_subplot(gs[0, j])
        sub = CT[CT.penetration == pen]
        for p in K.POLICIES:
            g = sub[sub.policy == p].groupby("demand")["C1"].mean()
            ax.plot(g.index, g.values, ST.LS[p], color=ST.POL[p], marker=ST.MARK[p],
                    ms=3.4, lw=1.3, label=ST.POLNAME[p], zorder=3)
        ax.set_title(f"penetration {pen:.0%}", pad=4, color=ST.INK2)
        ax.set_xticks([1200, 2400, 3600])
        ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True); ST.despine(ax)
        if j == 0:
            ax.set_ylabel("system mean\njourney time (s)")
        ax.set_xlabel("demand (veh/h)")
    ymax = max(a.get_ylim()[1] for a in fig.axes)
    for a in fig.axes:
        a.set_ylim(250, ymax)
    fig.axes[0].legend(loc="upper left", fontsize=ST.TEXT - 1.6, handlelength=2.0,
                       labelspacing=0.25, borderpad=0.0)

    # Pareto membership
    ax = fig.add_subplot(gs[1, 0])
    pm = RES["complementarity"]["pareto_membership"]
    n = RES["complementarity"]["n_contexts"]
    vals = [100 * pm[p] / n for p in K.POLICIES]
    ax.bar(range(4), vals, color=[ST.POL[p] for p in K.POLICIES], width=0.66)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=ST.TEXT - 1.4,
                color=ST.INK2)
    ax.set_xticks(range(4)); ax.set_xticklabels(K.POLICIES)
    ax.set_ylabel("contexts where the\npolicy is non-dominated")
    ax.set_ylim(0, 108); ax.set_yticks([0, 50, 100])
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)

    # how often each policy is strictly best on C1
    ax = fig.add_subplot(gs[1, 1])
    wc = collections.Counter(W[W.resolved].winner)
    vals = [100 * wc.get(p, 0) / len(W) for p in K.POLICIES]
    ax.bar(range(4), vals, color=[ST.POL[p] for p in K.POLICIES], width=0.66)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=ST.TEXT - 1.4,
                color=ST.INK2)
    ax.set_xticks(range(4)); ax.set_xticklabels(K.POLICIES)
    ax.set_ylabel("contexts where it is\nbest on journey time")
    ax.set_ylim(0, 108); ax.set_yticks([0, 50, 100])
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)

    # criterion conflict
    ax = fig.add_subplot(gs[1, 2])
    c = RES["criteria"]
    labs = ["time\nvs CO$_2$", "time vs\nstopped delay", "CO$_2$ vs\nstopped delay"]
    keys = ["C1_vs_C2", "C1_vs_C3", "C2_vs_C3"]
    vals = [100 * (1 - c[k]["frac_identical_ordering"]) for k in keys]
    ax.bar(range(3), vals, color=ST.INK2, width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=ST.TEXT - 1.4,
                color=ST.INK2)
    ax.set_xticks(range(3)); ax.set_xticklabels(labs, fontsize=ST.TEXT - 1.6)
    ax.set_ylabel("contexts where the two\ncriteria rank policies\ndifferently")
    ax.set_ylim(0, max(vals) * 1.3 + 4)
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)
    ST.save(fig, "fig4_performance_pareto")


# ------------------------------------------------------------------ fig 5
def fig5():
    """Winner map in the mechanistic plane, with the demand brackets in which
    the preferred policy changes."""
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.7), gridspec_kw=dict(wspace=0.3))
    ax = axs[0]
    for p in K.POLICIES:
        s = W[(W.winner == p) & W.resolved]
        if len(s):
            xs = [K.descriptors(r)["x2_short_sat"] for _, r in s.iterrows()]
            ax.scatter(xs, s.penetration + np.random.RandomState(0).uniform(
                -0.022, 0.022, len(s)), s=13, c=ST.POL[p], marker=ST.MARK[p],
                label=ST.POLNAME[p], linewidths=0, alpha=0.85, zorder=3)
    u = W[~W.resolved]
    xs = [K.descriptors(r)["x2_short_sat"] for _, r in u.iterrows()]
    ax.scatter(xs, u.penetration + np.random.RandomState(1).uniform(
        -0.022, 0.022, len(u)), s=9, facecolors="none", edgecolors=ST.INK3,
        linewidths=0.5, label="no resolved winner", zorder=2)
    ax.axvline(1.0, color=ST.WARN, lw=0.9, ls=":")
    ax.text(1.03, 0.905, "shortest corridor\nat capacity", fontsize=ST.TEXT - 1.5,
            color=ST.WARN, va="top")
    ax.set_xlabel("demand / capacity of the shortest corridor  $x_2$")
    ax.set_ylabel("guidance penetration  $x_5$")
    ax.set_yticks([0.2, 0.5, 0.8])
    ST.despine(ax); ax.grid(lw=0.5); ax.set_axisbelow(True)
    ax.legend(fontsize=ST.TEXT - 1.7, loc="upper left", bbox_to_anchor=(-0.02, 1.02),
              handletextpad=0.3, labelspacing=0.22, borderpad=0.0)

    ax = axs[1]
    dem = sorted(CT.demand.unique())
    for p in K.POLICIES:
        fr = []
        for d in dem:
            s = W[(W.demand == d) & W.resolved]
            fr.append(100 * (s.winner == p).sum() / max(len(W[W.demand == d]), 1))
        ax.plot(dem, fr, ST.LS[p], color=ST.POL[p], marker=ST.MARK[p], ms=3.4,
                lw=1.3, label=ST.POLNAME[p])
    ax.set_xlabel("corridor demand (veh/h)")
    ax.set_ylabel("share of contexts where the\npolicy is the resolved winner (%)")
    ax.set_xticks([1200, 2400, 3600]); ax.set_ylim(-3, 103)
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)
    ST.save(fig, "fig5_regime_map")


# ------------------------------------------------------------------ fig 6
def fig6():
    """Selection regions: what the mechanistic rule does, and where the learned
    selector departs from it."""
    ctxs, X, C, noise, meta = S.matrices(CT)
    n = len(X)
    out, ex = S.fit_predict(np.arange(n), np.arange(n), X, C)   # in-sample map
    i2, i5 = K.XCOLS.index("x2_short_sat"), K.XCOLS.index("x5_penetration")
    fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.5),
                            gridspec_kw=dict(wspace=0.26))
    titles = ["true best policy", "mechanistic rule  B1", "learned selector  B4"]
    series = [np.argmin(C, axis=1), out["B1_mechanistic"], out["B4_GBDT"]]
    rs = np.random.RandomState(0)
    for ax, t, ser in zip(axs, titles, series):
        for j, p in enumerate(K.POLICIES):
            m = ser == j
            if m.sum():
                ax.scatter(X[m, i2], X[m, i5] + rs.uniform(-0.022, 0.022, m.sum()),
                           s=8, c=ST.POL[p], marker=ST.MARK[p], linewidths=0,
                           alpha=0.8, label=ST.POLNAME[p])
        ax.set_title(t, pad=4, color=ST.INK2)
        ax.set_xlabel("$x_2$ = demand / shortest-corridor capacity")
        ax.set_yticks([0.2, 0.5, 0.8])
        ST.despine(ax); ax.grid(lw=0.5); ax.set_axisbelow(True)
    axs[0].set_ylabel("penetration  $x_5$")
    h = [Line2D([], [], color=ST.POL[p], marker=ST.MARK[p], ls="none", ms=4,
                label=ST.POLNAME[p]) for p in K.POLICIES]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=ST.TEXT - 1.5,
               bbox_to_anchor=(0.5, -0.09), handletextpad=0.3, columnspacing=1.4)
    ST.save(fig, "fig6_selection_regions")


# ------------------------------------------------------------------ fig 7
def fig7():
    lad = {r["selector"]: r for r in RES["ladder_loco"]}
    order = ["B0_SBS", "B1_mechanistic", "B2_tree3", "B3_logit", "B4_GBDT",
             "B5_selective", "VBS_reference"]
    labs = ["B0\nbest fixed", "B1\nmechanistic", "B2\ntree d3", "B3\nlogistic",
            "B4\nGBDT", "B5\nselective", "VBS\n(not deployable)"]
    vals = [lad[k]["mean_regret"] for k in order]
    cols = [ST.INK2, ST.POL["P3"], ST.INK3, ST.INK3, ST.ACCENT, ST.ACCENT, ST.INK3]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.6, 2.6),
                                 gridspec_kw=dict(wspace=0.32, width_ratios=[1.35, 1]))
    b = ax.bar(range(len(order)), vals, color=cols, width=0.66)
    b[-1].set_hatch("///"); b[-1].set_edgecolor("white"); b[-1].set_linewidth(0)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.028, f"{v:.1f}", ha="center",
                fontsize=ST.TEXT - 1.4, color=ST.INK2)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labs, fontsize=ST.TEXT - 1.7)
    ax.set_ylabel("mean decision regret (s per vehicle)")
    ax.set_ylim(0, max(vals) * 1.22)
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)

    keys = ["B0_SBS", "B1_mechanistic", "B4_GBDT", "B5_selective"]
    x = np.arange(len(keys)); w = 0.38
    bx.bar(x - w / 2, [100 * lad[k]["pct_within_noise"] for k in keys], w,
           color=ST.ACCENT, label="within the seed noise floor")
    bx.bar(x + w / 2, [100 * lad[k]["pct_exact_optimal"] for k in keys], w,
           color=ST.INK3, label="exactly optimal")
    bx.set_xticks(x)
    bx.set_xticklabels(["B0", "B1", "B4", "B5"])
    bx.set_ylabel("contexts (%)"); bx.set_ylim(0, 108)
    ST.despine(bx); bx.grid(axis="y", lw=0.5); bx.set_axisbelow(True)
    bx.legend(fontsize=ST.TEXT - 1.6, loc="lower right", labelspacing=0.25)
    ST.save(fig, "fig7_decision_ladder")


# ------------------------------------------------------------------ fig 8
def fig8():
    o = RES["ood"]
    names = [k for k in o if k.startswith("O")]
    order = sorted(names)
    keys = ["B0_SBS", "B1_mechanistic", "B4_GBDT", "B5_selective"]
    cols = {"B0_SBS": ST.INK2, "B1_mechanistic": ST.POL["P3"],
            "B4_GBDT": ST.ACCENT, "B5_selective": ST.POL["P4"]}
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(6.6, 3.9),
                                 gridspec_kw=dict(height_ratios=[1.6, 1.0],
                                                  hspace=0.42))
    x = np.arange(len(order)); w = 0.2
    for i, k in enumerate(keys):
        ax.bar(x + (i - 1.5) * w, [o[s][k]["mean_regret"] for s in order], w,
               color=cols[k], label=k.split("_")[0] + " " + k.split("_", 1)[1])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s.split('_',1)[0]}\n{s.split('_',1)[1].replace('_',' ')}"
                        for s in order], fontsize=ST.TEXT - 1.7)
    ax.set_ylabel("mean regret on the held-out\nregime (s per vehicle)")
    ST.despine(ax); ax.grid(axis="y", lw=0.5); ax.set_axisbelow(True)
    ax.legend(ncol=4, fontsize=ST.TEXT - 1.6, loc="upper left",
              bbox_to_anchor=(0.0, 1.16), columnspacing=1.3, handlelength=1.4)
    for i, s in enumerate(order):
        ax.annotate(o[s]["_shift_type"].replace(" + ", "+\n"), (i, 0),
                    xytext=(0, -34), textcoords="offset points", ha="center",
                    fontsize=ST.TEXT - 2.0, color=ST.INK3, annotation_clip=False)
    bx.bar(x - 0.2, [100 * o[s]["_out_of_support_rate"] for s in order], 0.4,
           color=ST.INK3, label="flagged outside the training support")
    bx.bar(x + 0.2, [100 * o[s]["_abstain_rate"] for s in order], 0.4,
           color=ST.POL["P4"], label="abstained to the fixed policy")
    bx.set_xticks(x); bx.set_xticklabels([s.split("_")[0] for s in order])
    bx.set_ylabel("held-out contexts (%)"); bx.set_ylim(0, 108)
    ST.despine(bx); bx.grid(axis="y", lw=0.5); bx.set_axisbelow(True)
    bx.legend(fontsize=ST.TEXT - 1.6, ncol=2, loc="upper left", labelspacing=0.25)
    ST.save(fig, "fig8_ood")


# ------------------------------------------------------------------ fig 9
def fig9():
    """Risk-coverage: sort contexts by the selector's own confidence and show
    the regret incurred by acting on the most confident share."""
    ctxs, X, C, noise, meta = S.matrices(CT)
    n = len(X)
    conf = np.zeros(n); reg4 = np.zeros(n); reg0 = np.zeros(n)
    for i in range(n):
        tr = np.array([j for j in range(n) if j != i])
        out, ex = S.fit_predict(tr, np.array([i]), X, C)
        pred = ex["B4_pred"][0]
        j = int(np.argmax(pred))
        srt = np.sort(pred)[::-1]
        conf[i] = srt[0] - srt[1]
        best = C[i].min()
        reg4[i] = C[i, j] - best
        reg0[i] = C[i, ex["sbs"]] - best
    o = np.argsort(-conf)
    cov = np.arange(1, n + 1) / n
    risk = np.cumsum(reg4[o]) / np.arange(1, n + 1)
    mix = (np.cumsum(reg4[o]) + np.cumsum(reg0[o][::-1])[::-1] - reg0[o]) / n
    tot = np.array([(reg4[o][:k].sum() + reg0[o][k:].sum()) / n
                    for k in range(n + 1)])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.6, 2.5),
                                 gridspec_kw=dict(wspace=0.32))
    ax.plot(100 * cov, risk, color=ST.ACCENT, lw=1.6)
    ax.axhline(reg4.mean(), color=ST.INK3, lw=0.9, ls="--")
    ax.text(99, reg4.mean(), " act everywhere", fontsize=ST.TEXT - 1.5,
            color=ST.INK3, va="bottom", ha="right")
    ax.set_xlabel("coverage: most-confident contexts acted on (%)")
    ax.set_ylabel("mean regret among\nthe contexts acted on (s)")
    ST.despine(ax); ax.grid(lw=0.5); ax.set_axisbelow(True)

    bx.plot(100 * np.arange(n + 1) / n, tot, color=ST.POL["P4"], lw=1.6)
    bx.axhline(reg0.mean(), color=ST.INK2, lw=0.9, ls="--")
    bx.text(1, reg0.mean(), " always the fixed policy", fontsize=ST.TEXT - 1.5,
            color=ST.INK2, va="bottom")
    bx.axhline(reg4.mean(), color=ST.ACCENT, lw=0.9, ls=":")
    bx.text(99, reg4.mean(), "always the selector ", fontsize=ST.TEXT - 1.5,
            color=ST.ACCENT, va="top", ha="right")
    k = int(np.argmin(tot))
    bx.plot(100 * k / n, tot[k], "o", color=ST.POL["P4"], ms=5)
    bx.annotate(f"best coverage {100*k/n:.0f}%\nregret {tot[k]:.2f} s",
                (100 * k / n, tot[k]), textcoords="offset points", xytext=(6, 8),
                fontsize=ST.TEXT - 1.5, color=ST.POL["P4"])
    bx.set_xlabel("coverage (%)")
    bx.set_ylabel("mean regret over ALL contexts,\nabstaining below the cut (s)")
    ST.despine(bx); bx.grid(lw=0.5); bx.set_axisbelow(True)
    ST.save(fig, "fig9_risk_coverage")


if __name__ == "__main__":
    for f in (fig4, fig5, fig6, fig7, fig8, fig9):
        if len(sys.argv) > 1 and f.__name__ not in sys.argv[1:]:
            continue
        f()
