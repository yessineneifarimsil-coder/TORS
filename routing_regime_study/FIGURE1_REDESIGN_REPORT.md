# Figure 1 — redesign report

Visual redesign only. No experiment, scenario, method, figure or table was added, and no
scientific content changed. `main.tex` is byte-identical to the previous commit.

---

## A. Visual problems in the old figure

| # | Problem |
|---|---|
| 1 | Plotted on a labelled x/y axis pair in metres with ticks and a frame — read as a debugging plot, not a schematic |
| 2 | Very large dead margins: the 1,500 m source stub and the ±900 m approach stubs were drawn to scale, so the 3×4 mesh filled only ~38% of the canvas |
| 3 | `U1 UR`, `C1 CR`, `L1 LR` rendered as adjacent strings — the restriction node read as part of the junction label |
| 4 | Corridor annotations ("Upper: 40 km/h, 1 lane") sat *inside* the network area, competing with links and node IDs |
| 5 | "Central: 50 km/h, 1 lane" wrapped across two lines between the U and C rows, in the busiest region |
| 6 | Source block ("Primary source / 1,500 m; 3 lanes") was a heavy free-floating text island |
| 7 | No legend; the meaning of the red segments was carried by a two-line caption under the plot |
| 8 | Flat hierarchy: junction discs, restriction segments and text all competed at similar weight |
| 9 | Every node used one identical disc, so the 12 signalized junctions were not distinguishable from restriction or approach nodes |
| 10 | Lane counts were stated only in text; nothing in the drawing encoded them |
| 11 | The sink link (C3→D, 450 m, 3 lanes) was unlabelled although the source was |

## B. What was changed

- **Rebuilt from data, not from the picture.** `analysis/make_figure1.py` reads the NETWORK
  sheet of the workbook and derives node coordinates from the stated link lengths.
- **Axes, ticks and frame removed.** The figure is now a schematic.
- **Approach stubs shortened** (O, D, N1, N2, S1, S2) and marked with the standard engineering
  break symbol, so the mesh fills the canvas instead of ~38% of it. The mesh itself stays at
  true relative scale; a note states this explicitly.
- **Hierarchy introduced.** Signalized junctions are filled dark squares; restriction nodes are
  small open accent circles; external approach ends are light open circles.
- **Line weight now encodes lane count** (1 / 2 / 3 lanes → increasing weight), so the
  engineering difference between corridors is visible before any text is read, and survives
  grayscale printing.
- **Background approaches** are lighter, thinner and dashed — clearly secondary.
- **Restriction segments** are drawn in a single accent colour at the heaviest weight of any
  link, so they are identifiable by weight alone in grayscale.
- **Label collisions resolved by repositioning, not by shrinking.** U-row IDs above the line,
  C-row IDs above the line (freeing the space below for the source/sink specs), L-row IDs below
  the line, all offset horizontally clear of the vertical connectors. `UR / CR / LR` moved below
  their own segment, well clear of `U1/C1/L1` and `U2/C2/L2`.
- **Corridor annotations moved out of the network** into the left margin, each aligned to its own
  corridor row.
- **Sink specification added** (450 m · 3 lanes) — it was already in the data and in the
  workbook, but the old figure labelled only the source.
- **Compact legend** in a dedicated band below the network.
- **Title** changed to "Engineering network — 12 signalized intersections, 29 legal primary paths".
- **Designed at print size.** The PDF is 390 pt wide against the 432 pt the manuscript allocates
  (`width=.92\linewidth`), so it is scaled up ~1.11×, not shrunk. In the old figure the text was
  being reduced to roughly 4 pt.

## C. Topology unchanged — verified against the workbook

| Property | Workbook | Drawn |
|---|---|---|
| Directed external links | 47 | 47 (29 undirected pairs) |
| Distinct nodes | 21 | 21 |
| Signalized junctions | 12 | 12 |
| Legal primary paths (stated) | 29 | 29 (title) |
| Restriction segments | U1→UR, C1→CR, L1→LR, 150 m each | identical |
| Upper corridor | 40 km/h, 1 lane | identical |
| Central corridor | 50 km/h, 1 lane | identical |
| Lower corridor | 60 km/h, 2 lanes | identical |
| Source O→C0 | 1,500 m, 3 lanes | identical |
| Sink C3→D | 450 m, 3 lanes | identical |
| Background approaches | 8 links, 600 m, columns 1 and 2 | identical |

The script asserts `len(links) == 47` and that the drawn node set equals the node set implied by
the link table; it fails loudly otherwise. No node, link, signal, speed, lane count or restriction
location was moved, added or removed. The restriction remains a **speed** restriction — nothing in
the drawing implies closure.

## D. Scientific annotations unchanged

All numerical values shown are the workbook's own: 12, 29, 40/50/60 km/h, 1/1/2 lanes, 150 m,
1,500 m · 3 lanes, 450 m · 3 lanes. The Figure 1 caption in `main.tex` is untouched and remains
correct. The "not to scale / lane counts not calibrated" status is preserved and stated in the
figure.

## E. Text overlap

Zero. Inspected at 200 dpi, at manuscript size, at half size and in grayscale: no label touches a
link, a marker, another label, the legend or the annotation blocks; nothing is clipped.

## F. Readability at manuscript size

Effective printed sizes after the 1.11× up-scale: title ~10.2 pt, corridor headings ~8.3 pt, node
IDs ~7.6 pt, legend ~6.9 pt, footnote ~6.5 pt. Grayscale tested: the restriction segments remain
distinguishable by line weight alone, so colour is not load-bearing.

## G. Output paths

| | |
|---|---|
| Generator | `analysis/make_figure1.py` |
| Figure | `paper/figures/network.pdf` (vector, 1 page, 390.3 × 229.4 pt, fonts embedded and subset) |
| Copies | `TORS26_OVERLEAF/figures/network.pdf`, `SUPERVISOR_PACKAGE/FINAL_MANUSCRIPT/figures/network.pdf` — identical md5 |

## H. Compilation

| Build | Result |
|---|---|
| `paper/main.tex` | **15 pages**, A4, 0 overfull/underfull, 0 undefined, 0 missing files |
| `TORS26_OVERLEAF` (pdflatex → bibtex → pdflatex ×2) | **15 pages**, 0 overfull/underfull, 0 undefined |

`git diff` confirms the only changed artefacts are `network.pdf` (three identical copies), the
recompiled `main.pdf`, and the new generator script. `main.tex` and Figures 2–4 are byte-identical.
