#!/usr/bin/env python3
"""Build the central results figure from the frozen Pilot-B artefact.

The figure carries one message: information learned is not decision value added.

Panel A  Structured information vs RandomWeights, median Delta Kendall tau_b.
Panel B  Incremental choice value vs MajorityWinner, median Delta Top-1.

Scientific contract
-------------------
* Every plotted value and every threshold is read from the frozen result file.
  Nothing scientific is hard-coded into a plotting coordinate.
* No condition is selected, no threshold is tuned, no inferential quantity is
  computed. This is a rendering of a frozen table.
* Axes are untruncated and share a zero reference so the comparison is not
  visually exaggerated. Bars are annotated with their exact values.
* Output goes to outputs/paper/figures/ only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

#: Display names, in the order used by the manuscript tables.
DISPLAY = {
    "OracleAttribution": "Oracle attribution",
    "SHAP": "SHAP",
    "PermutationImportance": "Permutation importance",
    "RidgePlus": "Ridge+",
    "CRITIC": "CRITIC",
    "Entropy": "Entropy",
}

# Colour-blind-safe pair (Okabe-Ito blue / vermillion), plus a muted tone for
# methods that did not clear the panel's frozen margin.
CLEARED = "#0072B2"
NOT_CLEARED = "#BBBBBB"
EDGE = "#333333"


def load_protocol_margins() -> tuple[float, float]:
    """Read the two plotted adequacy margins out of the frozen Pilot-B protocol.

    Both are read from ``config/pilot_b_hard_stop_protocol_v1.json`` and
    cross-checked against the duplicate statement of the same margins under
    ``practical_margins``. A mismatch aborts rather than picking a value.
    """
    cfg = fz.load_json(fz.REPO_ROOT / "config/pilot_b_hard_stop_protocol_v1.json")
    gates = cfg["gates"]
    tau = float(
        gates["random_equivalence_hard_stop"]["method_separates_random_if"]
        ["kendall_clause"]["cross_seed_median_advantage_at_least"]
    )
    top1 = float(
        gates["modal_winner_effective_tie_hard_stop"]["method_escapes_modal_if"]
        ["top1_clause"]["cross_seed_median_advantage_at_least"]
    )
    pm = cfg["practical_margins"]
    tau_alt = float(pm["random_separation"]["median_kendall_advantage_at_least"])
    top1_alt = float(pm["modal_winner_escape"]["median_top1_advantage_at_least"])
    if (tau, top1) != (tau_alt, top1_alt):
        raise SystemExit(
            "frozen protocol states the margins inconsistently "
            f"(gates: {tau}, {top1}; practical_margins: {tau_alt}, {top1_alt}); "
            "refusing to choose one"
        )
    return tau, top1


def build(outdir: Path) -> list[Path]:
    assessments = fz.pilot_b_assessments()
    tau_margin, top1_margin = load_protocol_margins()

    methods = list(DISPLAY)
    labels = [DISPLAY[m] for m in methods]
    tau_vals = [assessments[m]["random_kendall_median_advantage"] for m in methods]
    top1_vals = [assessments[m]["modal_top1_median_advantage"] for m in methods]
    tau_pos = [assessments[m]["random_kendall_positive_seed_count"] for m in methods]
    top1_pos = [assessments[m]["modal_top1_positive_seed_count"] for m in methods]

    # Drawn at the LNCS text width (122.5 mm = 4.82 in) so that
    # \includegraphics[width=\linewidth] applies no downscaling and the type
    # sizes below are the sizes the reader actually sees.
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 7.0,
        "axes.edgecolor": "#444444",
        "axes.linewidth": 0.7,
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "text.color": "#111111",
        "axes.labelcolor": "#111111",
    })

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(4.82, 2.45), gridspec_kw={"wspace": 0.26}
    )
    ypos = list(range(len(methods)))[::-1]

    # ---- Panel A: vs RandomWeights, median Delta Kendall tau_b ----------
    colours = [CLEARED if v >= tau_margin else NOT_CLEARED for v in tau_vals]
    axA.barh(ypos, tau_vals, height=0.62, color=colours, edgecolor=EDGE,
             linewidth=0.5, zorder=3)
    axA.axvline(0, color="#222222", linewidth=0.9, zorder=4)
    axA.axvline(tau_margin, color="#D55E00", linestyle="--", linewidth=1.1, zorder=5)
    axA.text(tau_margin, -0.72, f"frozen margin {tau_margin:g}",
             color="#D55E00", fontsize=6.1, va="center", ha="center", zorder=6,
             bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="#D55E00", lw=0.55))
    hi = max(tau_vals)
    axA.set_xlim(0, hi * 1.55)
    axA.set_ylim(-1.25, len(methods) - 0.30)
    for y, v, p in zip(ypos, tau_vals, tau_pos):
        # Keep the label clear of the dashed margin line for short bars.
        x = max(v, tau_margin) + hi * 0.028
        axA.text(x, y, f"{v:.3f} ({p}/5)", va="center", fontsize=6.3)
    axA.set_yticks(ypos)
    axA.set_yticklabels(labels)
    axA.set_xlabel(r"median $\Delta\tau_b$ vs RandomWeights")
    axA.set_title("A  Structured information\nvs RandomWeights",
                  fontsize=7.4, loc="left", pad=5)

    # ---- Panel B: vs MajorityWinner, median Delta Top-1 -----------------
    colours = [CLEARED if v >= top1_margin else NOT_CLEARED for v in top1_vals]
    axB.barh(ypos, top1_vals, height=0.62, color=colours, edgecolor=EDGE,
             linewidth=0.5, zorder=3)
    axB.axvline(0, color="#222222", linewidth=0.9, zorder=4)
    axB.axvline(top1_margin, color="#D55E00", linestyle="--", linewidth=1.1, zorder=5)
    axB.text(top1_margin, -0.72, f"frozen margin +{top1_margin:g}",
             color="#D55E00", fontsize=6.1, va="center", ha="center", zorder=6,
             bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="#D55E00", lw=0.55))
    lo = min(top1_vals)
    span = abs(lo)
    axB.set_xlim(lo - span * 0.48, max(top1_margin * 6.5, span * 0.46))
    axB.set_ylim(-1.25, len(methods) - 0.30)
    for y, v, p in zip(ypos, top1_vals, top1_pos):
        if v < 0:
            axB.text(v - span * 0.025, y, f"{v:.3f} ({p}/5)", va="center",
                     ha="right", fontsize=6.3)
        else:
            axB.text(span * 0.035, y, f"{v:.3f} ({p}/5)", va="center",
                     ha="left", fontsize=6.3)
    axB.set_yticks(ypos)
    axB.set_yticklabels([])
    axB.set_xlabel(r"median $\Delta$Top-1 vs MajorityWinner")
    axB.set_title("B  Incremental choice value\nvs MajorityWinner",
                  fontsize=7.4, loc="left", pad=5)

    for ax in (axA, axB):
        ax.grid(axis="x", color="#DDDDDD", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)

    fig.legend(
        handles=[
            Patch(facecolor=CLEARED, edgecolor=EDGE, label="clears the frozen margin"),
            Patch(facecolor=NOT_CLEARED, edgecolor=EDGE,
                  label="does not clear the frozen margin"),
        ],
        loc="lower center", ncol=2, frameon=False, fontsize=6.4,
        bbox_to_anchor=(0.5, 0.005),
    )
    fig.subplots_adjust(left=0.245, right=0.99, top=0.80, bottom=0.30)

    outdir = Path(fz.guard_output_path(outdir))
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        target = outdir / f"decision_value_figure.{ext}"
        fz.guard_output_path(target)
        fig.savefig(target, dpi=400 if ext == "png" else None,
                    bbox_inches="tight", pad_inches=0.02)
        written.append(target)
    plt.close(fig)

    print("frozen values rendered (nothing hard-coded):")
    for m, t, b in zip(labels, tau_vals, top1_vals):
        print(f"  {m:<24s} RW dtau_b={t:+.6f}   MW dTop-1={b:+.6f}")
    print(f"frozen margins read from protocol: tau_b={tau_margin}, Top-1={top1_margin}")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", type=Path, default=fz.OUTPUT_ROOT / "figures")
    args = ap.parse_args()
    for path in build(args.outdir):
        print(f"wrote {path.relative_to(fz.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
