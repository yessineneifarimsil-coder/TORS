"""Figure 3 -- the operating-regime design: which factor is varied, over what
range, and which policy failure mechanism it is there to activate."""
import os, sys
import numpy as np
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as ST

SAT = {"c": 1761.0, "n": 1596.0}
CAP_FREE, CYCLE, YELLOW = 1500.0, 90.0, 4.0


def cap_total(gc, alt):
    g = (gc * CYCLE - YELLOW) / CYCLE
    return 2 * SAT["c"] * g + alt * SAT["n"] * g + CAP_FREE


FACTORS = [
    ("corridor demand (veh/h)", ["1200", "1800", "2400", "3000", "3600", "4200"],
     "capacity shortage", "P1"),
    ("green ratio $g/C$", ["0.35", "0.50", "0.65"], "signalised capacity", "P1"),
    ("guidance penetration", ["0.2", "0.5", "0.8"],
     "controlled cohort size; herding", "P2"),
    ("information lag (s)", ["30", "120", "300"], "staleness; oscillation", "P2"),
    ("incident regime", ["none", "arterial"], "travel-time risk", "P4"),
    ("alternative capacity", ["1 lane", "2 lanes"],
     "whether there is load to balance", "P3"),
]


def main():
    ST.setup()
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(6.6, 4.0),
                                 gridspec_kw=dict(height_ratios=[1.35, 1.0],
                                                  hspace=0.42))
    ax.set_xlim(0, 100); ax.set_ylim(11, 101); ax.axis("off")
    for x, h, ha in ((0, "factor", "left"), (34, "levels", "left"),
                     (64, "mechanism activated", "left"),
                     (100, "policy", "right")):
        ax.text(x, 99, h, fontsize=ST.TEXT - 0.8, color=ST.INK2, va="bottom", ha=ha)
    ax.plot([0, 100], [97, 97], color=ST.INK3, lw=0.7)
    for i, (name, levels, mech, pol) in enumerate(FACTORS):
        y = 85 - i * 15.5
        ax.text(0, y + 2.0, name, fontsize=ST.TEXT - 0.5, color=ST.INK,
                va="center")
        xs = np.linspace(35, 58, len(levels))
        ax.plot([35, 58], [y + 2.0, y + 2.0], color=ST.GRID, lw=1.0, zorder=1)
        for x, lv in zip(xs, levels):
            ax.plot(x, y + 2.0, "o", ms=3.8, color=ST.INK2, zorder=2)
            ax.text(x, y - 3.2, lv, fontsize=ST.TEXT - 1.8, color=ST.INK2,
                    ha="center", va="top")
        ax.text(64, y + 2.0, mech, fontsize=ST.TEXT - 1.1, color=ST.INK2,
                va="center")
        ax.plot([99.4, 99.4], [y - 1.0, y + 5.0], color=ST.POL[pol], lw=2.4,
                solid_capstyle="round")
        ax.text(97.6, y + 2.0, pol, fontsize=ST.TEXT - 1.3, color=ST.POL[pol],
                ha="right", va="center", fontweight="bold")

    dem = np.array([1200, 1800, 2400, 3000, 3600, 4200], float)
    cfg = [(g, a) for g in (0.35, 0.50, 0.65) for a in (1, 2)]
    lo = np.min([dem / cap_total(g, a) for g, a in cfg], axis=0)
    hi = np.max([dem / cap_total(g, a) for g, a in cfg], axis=0)
    mid = dem / cap_total(0.50, 1)
    bx.fill_between(dem, lo, hi, color=ST.ACCENT, alpha=0.16, lw=0,
                    label="range over the six capacity configurations")
    bx.plot(dem, mid, "-o", color=ST.ACCENT, lw=1.5, ms=4.5,
            label="$g/C$ = 0.50 with a 1-lane alternative")
    bx.axhline(1.0, color=ST.WARN, lw=0.9, ls=":")
    bx.text(4190, 1.045, "demand equals measured network capacity",
            fontsize=ST.TEXT - 1.4, color=ST.WARN, va="bottom", ha="right")
    for d, m in zip(dem, mid):
        bx.annotate(f"{m:.2f}", (d, m), textcoords="offset points",
                    xytext=(0, -11), ha="center", fontsize=ST.TEXT - 1.7,
                    color=ST.INK2)
    bx.set_xticks(dem); bx.set_xlabel("corridor demand (veh/h)")
    bx.set_ylabel("demand / capacity")
    bx.set_xlim(1050, 4350); bx.set_ylim(0.15, 1.35)
    bx.set_yticks([0.25, 0.50, 0.75, 1.00, 1.25])
    bx.grid(axis="y", lw=0.5); bx.set_axisbelow(True)
    ST.despine(bx)
    bx.legend(loc="upper left", bbox_to_anchor=(0.0, 1.04), handlelength=1.8,
              fontsize=ST.TEXT - 1.5, labelspacing=0.3)
    ST.save(fig, "fig3_design")


if __name__ == "__main__":
    main()
