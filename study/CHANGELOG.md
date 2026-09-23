# Changelog

## Submission version (final)

Science frozen. No experiment was rerun, no hypothesis changed, no policy added
or removed, no factor level altered, no metric changed after the fact. All edits
below are corrections traceable to an existing artefact, or presentation.

### Verified numerical corrections

| # | Issue | Resolution |
|---|---|---|
| 1 | **Two different percentages for the same effect.** The manuscript reported the adaptation headroom as 0.12% while its surrounding phrasing implied 0.095%. These are different statistics: the per-context mean of `headroom_i / best_i` (0.1204%) and the aggregate `mean headroom / mean SBS cost` (0.0950%). | One definition is now used throughout: **0.095%**, the aggregate, with its denominator (474.4 s) stated next to it. The per-context statistic is emitted under a separate macro name so the two can never be conflated. |
| 2 | **Execution counts conflated.** "18,124 runs" and "12,960 runs" were used without stating their relationship. | Reconciled and stated in the manuscript: 12,960 valid main-campaign runs; 20,284 simulations attempted in total, of which 18,124 succeeded, itemised by campaign. Every result derives from the 12,960 unless stated. |
| 3 | **The 46.4% figure had no stated denominator.** | Now given as: using the distance-minimising policy throughout increases system mean journey time by 220.2 s/vehicle relative to the single-best fixed policy, which is 46.4% of that policy's 474.4 s mean. Signless macros added so the figure reads correctly in prose. |
| 4 | **Two figures were never cited** (`fig:design`, `fig:performance`). | Both now cited at the point they support. |
| 5 | **Hard-coded section cross-references** ("Section 5.2", "Section 5.4") would break on renumbering. | Replaced with `\label`/`\ref`. |

### Corrected scientific claim

| # | Issue | Resolution |
|---|---|---|
| 6 | **The abstract claimed adaptation "harms under every extrapolation and shift tested."** The distribution-shift table does not support this. | Rewritten to match the table exactly. Across 8 splits at a stated 0.05 s/veh tolerance, the unguarded selector **helps on 2** (the interpolation control O3 and the domain shift O8), is **indistinguishable on 3** (O2, O4, O5) and **harms on 3** (O1, O6 and, worst, the concept shift O7 at 0.63 to 2.22 s). The selective gate recovered the fixed policy exactly on each of the 3 harmful splits. The same correction was applied in the results, discussion and conclusion. |

### Presentation and structure

- Reformatted to `llncs` (`runningheads`, anonymous), matching the document class of the repository's own prior IC_TORS'26 submission. No official template was found; see `paper/README_SUBMISSION.md`.
- Final title applied consistently to manuscript, running head and PDF metadata.
- Related Work reduced from five bold paragraphs to **exactly three numbered subsections** plus a positioning paragraph.
- Problem Formulation given its own section, with the level-1/level-2 distinction, regret, headroom, SBS and VBS defined, and the explicit hierarchy **complementarity ≠ decision value ≠ deployability**.
- Results reordered into the ten-part progression ending with the Pareto structure; a dedicated **Experimental Integrity and Deviations** section added.
- Methodology condensed (1,594 → 1,378 words) by removing prose duplicating the tables.
- All figures regenerated at LNCS text width (4.80 in) so their text renders at true size rather than being downscaled to ~5.8 pt.
- Figure 2 (policy portfolio) removed as redundant with Table 1; Figure 3 reduced to its informative panel; Figure 4 reduced to its top row; risk–coverage figure withdrawn from the paper and retained in the repository.
- Tables rebuilt to fit the 347.1 pt column: 49 overfull boxes above 15 pt reduced to 0.
- Floats relocated beside the text that cites them; most now sit within one page of their first citation.

### Unchanged

Every experimental result, all run records, the frozen specification, protocol
deviation D-1 and the infeasible-split replacement remain exactly as recorded.
