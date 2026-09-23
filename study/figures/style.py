"""Shared figure style.  One place, so every figure is the same object."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Validated categorical palette (six-check validator, light surface):
# worst adjacent CVD separation dE 11.3 deutan / 22.7 tritan, all checks PASS.
POL = {"P1": "#1F5FA9", "P2": "#D55E00", "P3": "#1B9E77", "P4": "#7A3E9D"}
POLNAME = {"P1": "P1 shortest", "P2": "P2 reactive", "P3": "P3 load-balancing",
           "P4": "P4 reliability"}
# secondary encoding, so identity never rests on colour alone
MARK = {"P1": "o", "P2": "s", "P3": "^", "P4": "D"}
LS = {"P1": "-", "P2": "--", "P3": "-.", "P4": (0, (3, 1, 1, 1))}
INK, INK2, INK3 = "#1a1a1a", "#4d4d4d", "#8c8c8c"
GRID, SURF = "#e6e6e6", "#ffffff"
ACCENT, WARN = "#1F5FA9", "#B3261E"

TEXT = 7.2   # LNCS body is 10pt; figures are placed at 1:1


def setup():
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF,
        "savefig.facecolor": SURF, "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"], "mathtext.fontset": "dejavuserif",
        "font.size": TEXT, "axes.titlesize": TEXT + 0.5,
        "axes.labelsize": TEXT, "xtick.labelsize": TEXT - 0.5,
        "ytick.labelsize": TEXT - 0.5, "legend.fontsize": TEXT - 0.5,
        "axes.edgecolor": INK3, "axes.linewidth": 0.6,
        "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "grid.color": GRID, "grid.linewidth": 0.5,
        "lines.linewidth": 1.2, "lines.markersize": 3.4,
        "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


def save(fig, name):
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    # pass bbox explicitly: the rcParam form is not reliably honoured when a
    # figure-level legend sits outside the axes, and silently crops axis labels
    fig.savefig(p + ".pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(p + ".png", dpi=200, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("  wrote", name + ".pdf")
