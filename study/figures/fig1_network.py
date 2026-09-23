"""Figure 1 -- the scenario network and its competing route structure.

Geometry, lane counts and speed limits are READ FROM THE BUILT NETWORK FILE,
so the figure cannot drift from the network that was actually simulated.
"""
import os, sys, xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as ST

NET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "scenario", "agb_alt1.net.xml")
CAP = {"C": 1604, "N": 727, "S": 1500}          # measured, tests/test_capacity.py


def read_net(path):
    root = ET.parse(path).getroot()
    nodes, edges = {}, {}
    for j in root.findall("junction"):
        if j.get("type") != "internal":
            nodes[j.get("id")] = (float(j.get("x")), float(j.get("y")), j.get("type"))
    for e in root.findall("edge"):
        if e.get("function") == "internal":
            continue
        ls = e.findall("lane")
        edges[e.get("id")] = dict(frm=e.get("from"), to=e.get("to"), n=len(ls),
                                  speed=float(ls[0].get("speed")),
                                  length=float(ls[0].get("length")))
    return nodes, edges


def main():
    ST.setup()
    nodes, edges = read_net(NET)
    fig = plt.figure(figsize=(4.80, 2.36))
    gs = GridSpec(1, 2, width_ratios=[1.0, 0.72], wspace=0.06, figure=fig)
    ax = fig.add_subplot(gs[0, 0]); tx = fig.add_subplot(gs[0, 1]); tx.axis("off")
    COL = {"C": ST.POL["P1"], "N": ST.POL["P3"], "S": ST.POL["P4"]}

    def fam(eid):
        return ("C" if eid.startswith("c") else "N" if eid.startswith("n")
                else "S" if eid.startswith("s") else
                "A" if eid in ("w_d", "m_e") else "X")

    for eid, e in edges.items():
        x0, y0, _ = nodes[e["frm"]]; x1, y1, _ = nodes[e["to"]]
        f = fam(eid)
        if f == "X":
            ax.plot([x0, x1], [y0, y1], color=ST.INK3, lw=0.85, zorder=1)
        elif f == "A":
            ax.plot([x0, x1], [y0, y1], color=ST.INK2, lw=2.4, zorder=2,
                    solid_capstyle="round")
        else:
            ax.plot([x0, x1], [y0, y1], color=COL[f], lw=1.0 + 1.3 * e["n"],
                    zorder=3, solid_capstyle="round")
    # corridor letters, placed in the clear span between cross streets
    for k, x, y, dy in (("C", 2700, 0, -14), ("N", 2700, 400, 8),
                        ("S", 1500, -900, -16)):
        ax.annotate(k, (x, y), textcoords="offset points", xytext=(0, dy),
                    ha="center", fontsize=ST.TEXT + 0.5, color=COL[k],
                    fontweight="bold")

    for nid, (x, y, t) in nodes.items():
        if t == "traffic_light":
            ax.plot(x, y, "s", ms=4.4, mfc="white", mec=ST.INK, mew=1.0, zorder=5)
        elif nid in ("W", "E"):
            ax.plot(x, y, "o", ms=7.5, mfc=ST.INK, mec="none", zorder=5)
            ax.annotate("origin" if nid == "W" else "destination", (x, y),
                        textcoords="offset points", xytext=(0, -20), ha="center",
                        fontsize=ST.TEXT - 1.2, color=ST.INK2)
        elif nid in ("D", "M"):
            ax.plot(x, y, "o", ms=5, mfc="white", mec=ST.INK, mew=1.1, zorder=6)
            ax.annotate("diverge" if nid == "D" else "merge", (x, y),
                        textcoords="offset points",
                        xytext=(-6 if nid == "D" else 6, 8),
                        ha="right" if nid == "D" else "left",
                        fontsize=ST.TEXT - 1.2, color=ST.INK2)
        else:
            ax.plot(x, y, "o", ms=2.4, mfc=ST.INK3, mec="none", zorder=4)

    ax.annotate("", xy=(700, 1080), xytext=(-350, 1080),
                arrowprops=dict(arrowstyle="-|>", color=ST.INK2, lw=1.0))
    ax.annotate("corridor demand, one-way", (175, 1120), ha="center", va="bottom",
                fontsize=ST.TEXT - 1.2, color=ST.INK2)
    ax.set_xlim(-1150, 4050); ax.set_ylim(-1420, 1280)
    ax.set_aspect("equal"); ax.axis("off")

    rows = [("C", "central arterial",
             "3000 m · 2 lanes · 50 km/h · 4 signals",
             f"shortest distance · capacity {CAP['C']} veh/h"),
            ("N", "north street",
             "3242 m · 1 or 2 lanes · 40 km/h · 4 signals",
             f"longer and slower · capacity {CAP['N']}–{2*CAP['N']} veh/h"),
            ("S", "south bypass",
             "3963 m · 1 lane · 50 km/h · no signals",
             f"longest, uninterrupted · capacity {CAP['S']} veh/h")]
    y = 1.00
    for k, name, geom, role in rows:
        tx.plot([0.01, 0.075], [y - 0.035, y - 0.035], color=COL[k], lw=3.0,
                transform=tx.transAxes, clip_on=False, solid_capstyle="round")
        tx.text(0.105, y, f"{k}  {name}", transform=tx.transAxes, va="top",
                fontsize=ST.TEXT, color=COL[k], fontweight="bold")
        tx.text(0.105, y - 0.105, geom, transform=tx.transAxes, va="top",
                fontsize=ST.TEXT - 1.2, color=ST.INK2)
        tx.text(0.105, y - 0.205, role, transform=tx.transAxes, va="top",
                fontsize=ST.TEXT - 1.2, color=ST.INK2)
        y -= 0.275
    h = [Line2D([], [], color=ST.INK, marker="s", ls="none", ms=4.4, mfc="white",
                mew=1.0, label="signalised junction (2 phases, 90 s)"),
         Line2D([], [], color=ST.INK3, lw=0.85, label="minor street"),
         Line2D([], [], color=ST.INK2, lw=2.4, label="shared access and egress")]
    tx.legend(handles=h, loc="lower left", bbox_to_anchor=(0.02, -0.03),
              handlelength=1.5, labelspacing=0.32, borderpad=0.0,
              fontsize=ST.TEXT - 1.2)
    ST.save(fig, "fig1_network")


if __name__ == "__main__":
    main()
