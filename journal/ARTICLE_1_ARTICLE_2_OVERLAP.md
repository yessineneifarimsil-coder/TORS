# Publication-Integrity Audit — relationship between the two articles

This manuscript is the second article of a two-article programme. This file
records what the two share, what distinguishes them, and how the relationship
should be disclosed to the journal.

## 1. The two articles

| | **Article 1** (conference) | **Article 2** (this manuscript) |
|---|---|---|
| Title | Context-Dependent Selection of Urban Routing Policies: Regime Effects, Decision Value and Generalisation Limits | Context-Dependent Selection Among Established Urban Routing Policies: Complementarity, Decision Value and Generalisation Under Distribution Shift |
| Venue | IC_TORS'26 (conference) | journal submission |
| Network | 12-signal 3×4 urban mesh, 29 legal paths | 3-corridor arterial/street/bypass network, 3 legal paths |
| Contexts | 24 | 648 |
| Runs | 432 | 12,960 (main campaign) |
| Policies | SP, DTT, TECO10 (3, from 6 settings measured) | P1 shortest, P2 reactive, P3 load-balancing, P4 reliability (4) |
| Factors | demand, restriction location, signal plan (3) | demand, green ratio, penetration, information lag, disruption, alternative capacity (6) |
| Seeds | 3 | 5 |
| Criteria | journey time + CO₂ (decision), stopped delay (diagnostic) | journey time (decision), CO₂ and stopped delay (Pareto) |
| Decision cost | normalised additive scalar, dimensionless | seconds per vehicle, no normalisation |
| Central finding | the preferred policy reverses with demand and the signal plan displaces the crossing; a two-threshold rule captures 79.9 % of headroom; the rule fails under demand extrapolation | complementarity, decision value and deployability are quantitatively disconnected; adaptation is worth 0.45 s/veh against 220.2 s/veh for the fixed choice; shift behaviour differs by shift type; the confidence gate never acts |
| Selectors | fixed policy, demand threshold, demand×signal threshold, depth-1 and depth-3 trees, hindsight | fixed policy, depth-2 mechanistic rule, depth-3 tree, logistic, advantage GBDT, selective GBDT, hindsight |
| Shift analysis | leave-one-demand-out, 3 folds, one shift type | 8 splits across 4 shift types, with support gate and abstention |

**No result, table, figure or number crosses between the two articles.** Article
2 contains nothing computed from the 432-run campaign, and article 1 contains
nothing computed from the 648-context campaign.

## 2. Measured textual overlap

Both manuscripts were reduced to lower-case prose, with markup, floats and
equations removed, and compared by shared word $n$-grams.

| $n$ | shared $n$-grams | share of article 2's $n$-grams |
|---:|---:|---:|
| 6 | 45 | 0.41 % |
| 8 | 10 | 0.09 % |
| 10 | 1 | 0.01 % |
| 12 | 0 | 0.00 % |

Before the integrity pass the figures were 1.50 %, 0.77 %, 0.46 % and 0.28 %.
Six passages were identified as near-identical — the opening framing of the
introduction, the algorithm-selection framing, the positioning paragraph, the
level-1/level-2 definition, the statistical disclaimer and the
complementarity/decision-value distinction — and all six were rewritten in
article 2. The single remaining shared 10-gram is a paraphrase of Rice's
formulation of the algorithm-selection problem, attached to the same citation in
both papers.

**Shared references: 5 of 25.** `rice1976`-family works
(`bischl2016aslib`, `kotthoff2014survey`, `xu2008satzilla`), `pan2013proactive`
and `lopez2018sumo`. These are the works that define the framework and the
simulator; overlap in them is unavoidable and appropriate.

## 3. Conceptual overlap that is retained deliberately

Three ideas necessarily appear in both papers because the second cannot be
stated without them: the distinction between selecting a route and selecting the
routing policy; decision regret against a single-best fixed policy and a
hindsight reference; and the separation of complementarity from decision value.

These are framework, not findings. Article 1 uses them to frame a regime-reversal
result on a two-criterion normalised cost; article 2 uses them to frame a
measurement of the gap between three properties in physical units. The wording is
independent in the two papers, and article 2 develops the framework further —
adding deployability under explicit shift, and the effect-to-noise precondition —
in ways article 1 does not contain.

## 4. Is this salami slicing?

No, on three tests.

1. **Neither article is a subset of the other.** They use different networks,
   different portfolios, different factor spaces and different decision costs.
   No number appears in both.
2. **Neither article's central claim can be derived from the other's data.**
   Article 1 cannot say anything about penetration, information lag, disruption
   or alternative capacity, because it varies none of them. Article 2 cannot say
   anything about restriction location or the 12-signal mesh, because it contains
   neither.
3. **The second article's principal finding contradicts the natural reading of
   the first.** Article 1 reports a selector capturing 79.9 % of headroom;
   article 2 shows that on a larger and more varied context space the headroom
   itself nearly vanishes relative to the fixed-policy choice. That is a
   different scientific statement, not a larger version of the same one.

## 5. Disclosure to the journal

The two studies share a research programme, an author group and a conceptual
framework, and this must be disclosed. Recommended handling:

- **If article 1 is published or accepted at submission time:** cite it in
  Section 2.3 of article 2 as prior work by the same authors, with one sentence
  stating what it established and on which network, and note explicitly that no
  data are shared.
- **If article 1 is still under review:** declare it in the cover letter as a
  related submission by the same authors, state the venue, and attach it if the
  journal asks. Add a footnote in article 2 to the same effect. Do not cite it as
  established work.
- **In either case** state in the cover letter that the two studies use disjoint
  simulation campaigns on different networks and that no result is reused.

Article 2 as submitted contains **no citation to article 1**, because its status
is unknown at the time of writing. One of the two treatments above must be
applied before submission; the placeholder for it is Section 2.3, at the end of
the algorithm-selection subsection.
