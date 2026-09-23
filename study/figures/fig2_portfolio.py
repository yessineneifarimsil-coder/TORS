"""Figure 2 -- the policy portfolio and the failure mechanism each one is
exposed to.  The two right-hand entries state a HYPOTHESIS, fixed before the
experiment; the paper reports whether each was observed."""
import os, sys, textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as ST

ROWS = [
    ("P1", "Static / shortest", r"$\min_p\ L(p)$", "none",
     "needs no infrastructure and cannot oscillate",
     "loads the shortest corridor past its capacity"),
    ("P2", "Reactive dynamic travel time", r"$\min_p\ \hat\mu_p(t-\Delta)$",
     "lagged link travel times",
     "follows congestion as it forms",
     "moves the whole guided cohort together on stale information"),
    ("P3", "Capacity-aware load balancing",
     r"$\min_{p\in\mathcal{A}}\ \max_{e\in p}\ \rho_e$",
     "lagged travel times and flows, plus its own recent assignments",
     "spreads load when capacity is unevenly distributed",
     "diverts to longer corridors when no capacity shortage exists"),
    ("P4", "Reliability-aware", r"$\min_p\ [\hat\mu_p + \lambda\hat\sigma_p]$",
     "lagged link travel times",
     "avoids corridors whose travel time is volatile",
     "pays a detour for variance that carries no risk"),
]
# column left edge, wrap width in characters
COLS = {"policy": (4.0, 22), "obj": (26.0, 0), "info": (43.0, 22),
        "mech": (65.0, 33)}


def main():
    ST.setup()
    fig, ax = plt.subplots(figsize=(6.6, 3.75))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    for key, head in (("policy", "policy"), ("obj", "objective"),
                      ("info", "information used"),
                      ("mech", "intended strength  /  hypothesised failure mode")):
        ax.text(COLS[key][0], 96.0, head, fontsize=ST.TEXT - 0.8,
                color=ST.INK2, va="bottom")
    ax.plot([1.0, 99], [94.6, 94.6], color=ST.INK3, lw=0.7)

    top, h = 89.5, 22.0
    for i, (pid, name, obj, info, strength, fail) in enumerate(ROWS):
        y = top - i * h
        c = ST.POL[pid]
        ax.add_patch(FancyBboxPatch((1.2, y - h + 5.0), 1.1, h - 6.5,
                                    boxstyle="round,pad=0,rounding_size=0.5",
                                    facecolor=c, edgecolor="none"))
        ax.text(COLS["policy"][0], y, pid, fontsize=ST.TEXT + 0.5, color=c,
                fontweight="bold", va="top")
        ax.text(COLS["policy"][0], y - 5.0,
                "\n".join(textwrap.wrap(name, COLS["policy"][1])),
                fontsize=ST.TEXT - 1.3, color=ST.INK2, va="top", linespacing=1.4)
        ax.text(COLS["obj"][0], y - 1.0, obj, fontsize=ST.TEXT, color=ST.INK,
                va="top")
        ax.text(COLS["info"][0], y,
                "\n".join(textwrap.wrap(info, COLS["info"][1])),
                fontsize=ST.TEXT - 1.3, color=ST.INK2, va="top", linespacing=1.45)
        sw = textwrap.wrap(strength, COLS["mech"][1])
        ax.text(COLS["mech"][0], y, "\n".join(sw), fontsize=ST.TEXT - 1.3,
                color=ST.INK, va="top", linespacing=1.45)
        ax.text(COLS["mech"][0], y - 4.6 * len(sw) - 1.6,
                "\n".join(textwrap.wrap(fail, COLS["mech"][1])),
                fontsize=ST.TEXT - 1.3, color=ST.WARN, va="top", linespacing=1.45)
        if i < len(ROWS) - 1:
            ax.plot([1.0, 99], [y - h + 3.0, y - h + 3.0], color=ST.GRID, lw=0.6)
    ax.text(1.0, -3.0, r"$\mathcal{A}$: paths within a declared travel-time "
            r"tolerance of the best.  $\rho_e$: link utilisation.  "
            r"$\Delta$: information lag.  $\lambda$: dispersion weight.",
            fontsize=ST.TEXT - 1.5, color=ST.INK3, va="bottom")
    ST.save(fig, "fig2_portfolio")


if __name__ == "__main__":
    main()
