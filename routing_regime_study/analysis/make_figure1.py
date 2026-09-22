"""
Figure 1 — engineering network schematic.

Topology, lane counts, speeds and lengths are read from the NETWORK sheet of
the audited workbook. Nothing is drawn from visual inspection of the previous
figure. Node coordinates are derived from the stated link lengths:
  columns  x = 0, 400, 800, 1200 ; restriction nodes at x = 550 (400 + 150)
  rows     y = +300 (upper), 0 (central), -300 (lower)
  N/S approaches at +-600 m from their rows; O at -1500 m; D at +450 m from C3.

Approach stubs (O, D, N1, N2, S1, S2) are drawn shortened, marked with the
standard break symbol, so the 3x4 mesh fills the canvas. Everything else is to
relative scale. No scientific value is altered.
"""
import openpyxl, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

WB = "paper/Routing_Strategy_Selection_Regime.xlsx"
OUT = "paper/figures/network.pdf"

# ---------------------------------------------------------------- data
ws = openpyxl.load_workbook(WB, data_only=True)["NETWORK"]
links = []
for r in range(20, 70):
    if not ws.cell(r, 1).value or ws.cell(r, 1).value == "External link":
        continue
    links.append(dict(name=ws.cell(r,1).value, frm=ws.cell(r,2).value, to=ws.cell(r,3).value,
                      lanes=int(ws.cell(r,4).value), speed=int(ws.cell(r,5).value),
                      length=float(ws.cell(r,6).value)))
assert len(links) == 47, len(links)

COL = {0: 0.0, 1: 400.0, 2: 800.0, 3: 1200.0}
ROW = {"U": 300.0, "C": 0.0, "L": -300.0}
XR = 550.0                      # restriction node: 400 + 150 m
O_X, D_X = -260.0, 1540.0       # drawn (shortened) endpoints; true -1500 / +1650
NS_Y = 540.0                    # drawn (shortened); true 900

P = {}
for c in (0, 1, 2, 3):
    for k, y in ROW.items():
        P[f"{k}{c}"] = (COL[c], y)
for k in "UCL":
    P[f"{k}R"] = (XR, ROW[k])
P.update({"O": (O_X, 0.0), "D": (D_X, 0.0),
          "N1": (COL[1],  NS_Y), "N2": (COL[2],  NS_Y),
          "S1": (COL[1], -NS_Y), "S2": (COL[2], -NS_Y)})
assert set(P) == {l["frm"] for l in links} | {l["to"] for l in links}

SIGNALS = [f"{k}{c}" for c in (0,1,2,3) for k in "UCL"]      # the 12 mesh junctions
BACKGROUND = {"N1", "N2", "S1", "S2"}
RESTRICTED = {("U1","UR"), ("C1","CR"), ("L1","LR")}

# ---------------------------------------------------------------- style
INK, MUTED, FAINT = "#2f3437", "#6b7378", "#9aa3ab"
ACCENT, BG_LINE = "#eb6834", "#a9b2b9"
plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})
LW = {1: 2.0, 2: 3.1, 3: 4.0}          # line weight encodes lane count

fig, ax = plt.subplots(figsize=(6.0, 3.78))
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-1250, 1800); ax.set_ylim(-1215, 700)

def seg(a, b, **kw):
    ax.plot([P[a][0], P[b][0]], [P[a][1], P[b][1]], solid_capstyle="round", **kw)

drawn = set()
for l in links:                                   # undirected pairs drawn once
    key = frozenset((l["frm"], l["to"]))
    if key in drawn: continue
    drawn.add(key)
    a, b = l["frm"], l["to"]
    if (a, b) in RESTRICTED or (b, a) in RESTRICTED:
        seg(a, b, color=ACCENT, lw=4.6, zorder=3)
    elif a in BACKGROUND or b in BACKGROUND:
        seg(a, b, color=BG_LINE, lw=1.5, ls=(0, (5, 2.6)), zorder=1)
    else:
        seg(a, b, color=INK, lw=LW[l["lanes"]], zorder=2)

def brk(x, y, vertical=False):                    # standard "shortened" break mark
    for d in (-26, 26):
        if vertical: ax.plot([x-30, x+30], [y+d-22, y+d+22], color="white", lw=3.4, zorder=5)
        else:        ax.plot([x+d-22, x+d+22], [y-30, y+30], color="white", lw=3.4, zorder=5)
        if vertical: ax.plot([x-30, x+30], [y+d-22, y+d+22], color=MUTED, lw=1.1, zorder=6)
        else:        ax.plot([x+d-22, x+d+22], [y-30, y+30], color=MUTED, lw=1.1, zorder=6)
brk(-150, 0); brk(1400, 0)
for xx in (COL[1], COL[2]):
    brk(xx,  430, vertical=True); brk(xx, -430, vertical=True)

# nodes
ax.scatter([P[n][0] for n in SIGNALS], [P[n][1] for n in SIGNALS], s=54, marker="s",
           facecolor="#1f2933", edgecolor="white", linewidth=1.0, zorder=7)
ax.scatter([P[f"{k}R"][0] for k in "UCL"], [P[f"{k}R"][1] for k in "UCL"], s=26, marker="o",
           facecolor="white", edgecolor=ACCENT, linewidth=1.5, zorder=8)
ax.scatter([P["O"][0], P["D"][0]], [0, 0], s=42, marker="o",
           facecolor=INK, edgecolor="white", linewidth=1.0, zorder=7)
ax.scatter([P[n][0] for n in BACKGROUND], [P[n][1] for n in BACKGROUND], s=26, marker="o",
           facecolor="white", edgecolor=FAINT, linewidth=1.3, zorder=7)

# ---------------------------------------------------------------- labels
NL = dict(fontsize=6.9, color=INK, zorder=9)
for c in (0, 1, 2, 3):                                        # upper row: above
    dx = 46 if c == 3 else -46
    ha = "left" if c == 3 else "right"
    ax.text(COL[c]+dx, ROW["U"]+34, f"U{c}", ha=ha, va="bottom", **NL)
for c in (0, 1, 2, 3):                                        # central row: above
    dx = 46 if c == 3 else -46
    ha = "left" if c == 3 else "right"
    ax.text(COL[c]+dx, ROW["C"]+34, f"C{c}", ha=ha, va="bottom", **NL)
for c in (0, 1, 2, 3):                                        # lower row: below
    dx = 46 if c == 3 else -46
    ha = "left" if c == 3 else "right"
    ax.text(COL[c]+dx, ROW["L"]-40, f"L{c}", ha=ha, va="top", **NL)
for k in "UCL":                                # below their own segment, clear of U1/C1/L1 and U2/C2/L2
    ax.text(XR-12, ROW[k]-42, f"{k}R", ha="center", va="top",
            fontsize=6.9, color=ACCENT, zorder=9)
for n in ("N1", "N2"):
    ax.text(P[n][0], P[n][1]+46, n, ha="center", va="bottom", fontsize=6.7, color=MUTED, zorder=9)
for n in ("S1", "S2"):
    ax.text(P[n][0], P[n][1]-46, n, ha="center", va="top", fontsize=6.7, color=MUTED, zorder=9)
ax.text(P["O"][0], 40, "O", ha="center", va="bottom", fontsize=7.8, color=INK, fontweight="bold", zorder=9)
ax.text(P["D"][0], 40, "D", ha="center", va="bottom", fontsize=7.8, color=INK, fontweight="bold", zorder=9)
ax.text(-285, -92, "Primary source",     ha="center", va="top", fontsize=6.9, color=MUTED)
ax.text(-285, -158, "1,500 m · 3 lanes", ha="center", va="top", fontsize=6.6, color=FAINT)
ax.text(1430, -92, "Primary sink",       ha="center", va="top", fontsize=6.9, color=MUTED)
ax.text(1430, -158, "450 m · 3 lanes",   ha="center", va="top", fontsize=6.6, color=FAINT)

# corridor annotations, left margin, aligned to their own row
for k, name, spec in (("U", "Upper corridor", "40 km/h · 1 lane"),
                      ("C", "Central corridor", "50 km/h · 1 lane"),
                      ("L", "Lower corridor", "60 km/h · 2 lanes")):
    ax.text(-560, ROW[k]+26, name, ha="right", va="bottom", fontsize=7.5, color=INK)
    ax.text(-560, ROW[k]-26, spec, ha="right", va="top",    fontsize=7.0, color=MUTED)


# legend, lower right (clear of the S2 stub and of the sink annotation)
h = [Line2D([], [], color=INK, lw=2.0), Line2D([], [], color=INK, lw=3.1),
     Line2D([], [], color=ACCENT, lw=4.6),
     Line2D([], [], color=BG_LINE, lw=1.5, ls=(0, (5, 2.6))),
     Line2D([], [], marker="s", color="none", markerfacecolor="#1f2933",
            markeredgecolor="white", markersize=6.6)]
lab = ["Primary link (1 lane)", "Primary link (2 lanes)", "Restriction segment (150 m)",
       "Background approach", "Signalized intersection"]
lg = ax.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 0.245), frameon=True,
               ncol=2, columnspacing=2.2, fontsize=6.2, handlelength=1.8,
               labelspacing=0.5, borderpad=0.62, handletextpad=0.65)
lg.get_frame().set_edgecolor("#d7dbde"); lg.get_frame().set_linewidth(0.7)
lg.get_frame().set_facecolor("white"); lg.set_zorder(12)

ax.set_title("Engineering network — 12 signalized intersections, 29 legal primary paths",
             fontsize=9.2, color=INK, fontweight="bold", pad=10)
ax.text(275, -1098, "Schematic; the mesh is drawn to relative scale and the approach stubs are shortened at the break marks.",
        ha="center", va="top", fontsize=5.9, color=FAINT, style="italic")
ax.text(275, -1152, "Lane counts are specified inputs, not calibrated saturation capacities.",
        ha="center", va="top", fontsize=5.9, color=FAINT, style="italic")

fig.savefig(OUT, bbox_inches="tight", pad_inches=0.02)
print(f"wrote {OUT}")
print(f"links drawn {len(drawn)} undirected pairs from {len(links)} directed records")
print(f"nodes {len(P)} | signals {len(SIGNALS)} | restricted {len(RESTRICTED)}")
