"""Assemble the standalone main.tex: one file, no \input, macros expanded."""
import re, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(HERE, "..", "paper")

PREAMBLE = r"""%% ---------------------------------------------------------------------------
%% Context-Dependent Selection of Established Urban Routing Policies:
%% Regime Effects, Decision Value, and Generalization Limits
%%
%% Standalone manuscript.  Compile with:
%%     pdflatex main  &&  bibtex main  &&  pdflatex main  &&  pdflatex main
%% Requires: llncs.cls and splncs04.bst (TeX Live "texlive-publishers"),
%%           references.bib, and the PDF figures in figures/.
%% ---------------------------------------------------------------------------
\documentclass[runningheads]{llncs}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs,tabularx,array}
\usepackage{graphicx}
\usepackage{hyperref}
\hypersetup{hidelinks,
  pdftitle={Context-Dependent Selection of Established Urban Routing Policies:
            Regime Effects, Decision Value, and Generalization Limits},
  pdfauthor={Anonymous Author(s)},
  pdfsubject={Routing-policy selection; algorithm selection; decision regret},
  pdfkeywords={routing-policy selection, algorithm selection, decision regret,
               microsimulation, distribution shift, selective prediction}}

\newcommand{\CO}{CO\textsubscript{2}}
\graphicspath{{figures/}}
\renewcommand{\tabularxcolumn}[1]{m{#1}}

\begin{document}

\title{Context-Dependent Selection of Established Urban Routing Policies:
Regime Effects, Decision Value, and Generalization Limits}
\titlerunning{Context-Dependent Selection of Urban Routing Policies}
\author{Anonymous Author(s)}
\authorrunning{Anonymous Author(s)}
\institute{Anonymous institution(s)}
\maketitle

"""

def figure(pdf, caption, label):
    return ("\\begin{figure}[tbp]\n\\centering\\includegraphics[width=\\textwidth]{"
            + pdf + "}\n\\caption{" + caption + "}\n\\label{" + label + "}\n"
            "\\end{figure}\n")

FIGS = {
 "network": figure("fig1_network.pdf",
   "The scenario network. One origin--destination pair is served by three "
   "structurally different corridors between a common diverge and merge, "
   "crossed by four minor streets carrying independent demand through the same "
   "signals. Geometry, lane counts and speed limits are read from the built "
   "network file; corridor capacities are measured rather than assumed.",
   "fig:network"),
 "design": figure("fig3_design.pdf",
   "Demand levels against measured network capacity. The shaded band spans the "
   "six capacity configurations produced by the green-ratio and "
   "alternative-capacity factors; the line marks the median configuration. The "
   "grid spans uncongested to oversaturated conditions, and the levels follow "
   "from measurement rather than from a chosen range.", "fig:design"),
 "regime": figure("fig5_regime_map.pdf",
   "The regime map. Left: the resolved winner in the plane of "
   "shortest-corridor saturation against guidance penetration; open circles "
   "mark contexts where the seeds resolve no winner. Right: the share of "
   "contexts each policy wins, by demand level.", "fig:regime"),
 "performance": figure("fig4_performance_pareto.pdf",
   "System mean journey time against demand at each guidance penetration "
   "level, averaged over the remaining factors. The distance-minimising policy "
   "diverges once the shortest corridor saturates, while the three adaptive "
   "policies track one another closely --- the visual form of the small "
   "decision value quantified in Section~\\ref{sec:asymmetry}.", "fig:performance"),
 "regions": figure("fig6_selection_regions.pdf",
   "Selection regions in the mechanistic feature space: the true best policy, "
   "the depth-2 mechanistic rule, and the advantage-based selector, over "
   "controlled-flow saturation and guidance penetration.", "fig:regions"),
 "ladder": figure("fig7_decision_ladder.pdf",
   "Decision quality under leave-one-context-out evaluation. Left: mean regret "
   "for each selector; the hindsight benchmark is hatched because it is not "
   "deployable. Right: the share of contexts in which each selector is within "
   "the seed noise floor, and exactly optimal.", "fig:ladder"),
 "ood": figure("fig8_ood.pdf",
   "Distribution shift, reported separately by shift type. Top: mean regret on "
   "the held-out regime for each selector. Bottom: the share of held-out "
   "contexts flagged outside the training support, and the share on which the "
   "selective selector abstained.", "fig:ood"),
}
TABS = {k: open(os.path.join(PAPER, "tables", f"{k}.tex")).read().strip()
        for k in ["tab1_portfolio", "tab2_factors", "tab3_criteria",
                  "tab4_complementarity", "tab5_ladder", "tab6_ood",
                  "tab7_sensitivity"]}

body = "\n".join(open(os.path.join(HERE, f"part{i}.tex")).read() for i in (1, 2, 3, 4))

def put(anchor, block):
    """Insert a float immediately before the given subsection heading."""
    global body
    assert anchor in body, anchor
    body = body.replace(anchor, block + "\n" + anchor, 1)

put("\\subsection{Routing Policy Portfolio}", FIGS["network"])
put("\\subsection{Decision Criteria}", TABS["tab1_portfolio"])
put("\\subsection{Mechanistic Rule}\n\nA selector that fires on raw demand",
    TABS["tab3_criteria"])
put("\\subsection{Common Random Numbers and Replications}",
    TABS["tab2_factors"] + "\n\n" + FIGS["design"])
put("\\subsection{Decision Value of Adaptation}",
    FIGS["regime"] + "\n" + TABS["tab4_complementarity"])
put("\\subsection{Why the Adaptation Headroom Is Small}", FIGS["performance"])
put("\\subsection{Advantage-Based Selector}", FIGS["regions"])
put("\\subsection{Selective Prediction and Distribution Shift}",
    TABS["tab5_ladder"] + "\n" + FIGS["ladder"])
put("\\subsection{Boundary Refinement}", TABS["tab6_ood"] + "\n" + FIGS["ood"])
put("\\subsection{Interpretation, Scope, and Limitations}", TABS["tab7_sensitivity"])

# abstract
abstract = open(os.path.join(PAPER, "abstract.tex")).read().strip()

tex = PREAMBLE + abstract + "\n\n" + body + """

\\bibliographystyle{splncs04}
\\bibliography{references}

\\end{document}
"""

# --- expand every \Num macro to its literal value
defs = dict(re.findall(r"\\newcommand\{\\(Num[A-Za-z]+)\}\{(.*)\}",
                       open(os.path.join(PAPER, "numbers.tex")).read()))
for name in sorted(defs, key=len, reverse=True):
    tex = re.sub(r"\\" + name + r"(\{\})?", defs[name].replace("\\", "\\\\"), tex)

leftover = sorted(set(re.findall(r"\\(Num[A-Za-z]+)", tex)))
assert not leftover, f"unexpanded macros: {leftover}"

open(os.path.join(HERE, "main.tex"), "w").write(tex)
print(f"wrote main.tex: {len(tex.splitlines())} lines, "
      f"{len(defs)} macro definitions expanded, 0 remaining")
