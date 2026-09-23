# Scientific Audit — 648-context routing-policy selection study

Independent re-derivation of every load-bearing result from the run records,
performed before any manuscript text was written. The repository, not the
previous manuscript, was treated as the source of truth.

---

## 1. Study ledger

Built by reading `study/results/*.jsonl` directly. Every campaign, its purpose,
and what it produced.

| Campaign | Purpose | Runs | Failed | Contexts | Policies | Seeds | Factors varied | Min. completion | Teleports |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| `screen` | complementarity gates G1–G4 | 640 | 0 | 16 | 4 | 10 | demand, green, penetration, lag, disruption, alt (2 levels each) | 1.0000 | 0 |
| `validate` | scenario validation | 384 | 0 | 96 | 4 | 1 | demand (6), penetration, lag, alt, disruption | 0.9726 | 0 |
| **`main`** | **main factorial** | **12,960** | **0** | **648** | **4** | **5** | all six, full factorial | **1.0000** | **0** |
| `boundary` | boundary refinement | 1,140 | 0 | 19 brackets × 3 demand levels | 4 | 5 | demand at 150 veh/h spacing | 1.0000 | 0 |
| `sens` | policy-parameter sensitivity | 1,920 | 0 | 96 | 2 (P3, P4) | 5 | `p3_eps` ∈ {0.1, 0.3}, `p4_lambda` ∈ {0.5, 1.5} | 1.0000 | 0 |
| `ood_north` | domain-shift campaign (O8) | 1,080 | 0 | 54 | 4 | 5 | demand, penetration, lag with north-corridor disruption | 1.0000 | 0 |
| `ood_bypass` | domain-shift campaign, planned | **0** | **2,160** | — | 4 | 5 | south-bypass disruption | — | — |

**Reconciliation.** 18,124 simulations succeeded; 2,160 failed; 20,284 were
attempted. The main campaign is 12,960 of the 18,124 and is the sole basis of
every headline result. Both totals appear in the manuscript, each labelled.

Response variables recorded per run: the three criteria at system,
corridor-cohort and guided-cohort level; route split; completion; teleports;
measured corridor capacities; the realised disruption.

---

## 2. Independent recomputation

Three verification scripts were written for this audit and are in
`journal/analysis/` and `study/audit2/`.

| Script | What it recomputes | Result |
|---|---|---|
| `study/audit2/verify_core.py` | 27 descriptive quantities — run counts, validity, resolved-win counts, margins, SBS/VBS/headroom, asymmetry, Pareto sizes and membership, criterion correlations — from `main.jsonl` with code written for this audit | **27/27 match** the published `results.json` |
| `study/audit2/verify_ladder.py` | the full leave-one-context-out ladder, 648 folds, on independently rebuilt feature and cost matrices | **7/7 selectors match to 1e−9**; top-1, abstention and support rates all match |
| `study/audit2/verify_ood.py` | all eight distribution-shift splits | **8/8 match to 1e−9**; classification of helps/neutral/harms reproduces |
| `journal/analysis/build_numbers.py` | everything the manuscript uses, into `numbers.json` | boundary and parameter-sensitivity blocks also reproduce exactly |

Independently confirmed headline values: SBS = P3 at 474.3527 s; VBS 473.9018 s;
headroom 0.4509 s (0.0950 % aggregate, 0.1204 % per-context); P1 penalty
220.2056 s = 46.4223 %; resolved wins P3 227 / P4 19 / P1 11 with P2 never;
Pareto non-singleton 473/648 = 73.0 %; B4 gap closed 55.79 %; mean noise floor
20.9050 s; 55 of 222 headroom contexts exceed their own 2 SE band; 25 seeds
required to resolve the mean effect.

---

## 3. Defects found

All trace to one root cause plus two stale summary fields. None affects a
conclusion; all are corrected in the journal manuscript.

### 3.1 Non-reproducible tie-breaking (root cause)

**50 of 648 contexts (7.7 %) have an exact tie for the minimum on the primary
criterion** — two or more policies produce bit-identical system mean journey
time, because at low demand or low penetration they route the guided cohort
identically. The tied sets are P2+P4 (39), P2+P3+P4 (8) and P3+P4 (3).

The previous analysis resolved these ties through `pandas.Series.sort_values`,
which defaults to an **unstable** quicksort. The affected quantities therefore do
not reproduce:

| Quantity | Previously published | Recomputed (declared stable tie-break) |
|---|---|---|
| winner counts on C1 | P1 21, P2 80, **P3 415, P4 132** | P1 21, P2 80, **P3 418, P4 129** |
| `frac_contexts_sbs_optimal` | 0.6451 | — |
| `asymmetry.frac_contexts_sbs_best` | 0.6404 | **0.6574** (426 of 648, tie-inclusive) |
| `mean_margin_when_best_s` | 23.070 | **22.475** |
| `upside_downside_ratio` | 17.53 | **17.08** |
| winner-map constant rule | 0.6404 | **0.6451** |
| winner-map best single factor | 0.6698 (demand) | **0.6651** (demand) |
| winner-map best two-factor | 0.7099 | **0.7068** (demand + penetration) |
| C2-vs-C3 identical orderings | 221 | **222** |

**Correction applied.** The manuscript declares a stable tie-break (portfolio
order), reports the tie count explicitly, and gives the winner table three ways:
under the tie-break, restricted to the 598 contexts with a unique minimum, and
tie-inclusive. No count in the paper depends on sort stability. The 222 contexts
in which the fixed policy is *strictly* beaten — which drives the headroom
result — is unaffected by tie-breaking and reproduces exactly.

### 3.2 Stale boundary summary fields

`boundary_summary.n_narrowed = 0` and `n_seed_resolved_narrowed = 0` contradict
the entries they summarise: 13 of 19 transitions narrow the point-estimate
bracket, and 7 of those 13 have at least one endpoint of the changepoint
interval seed-resolved. **Correction applied:** the manuscript reports 19
transitions, 13 monotone and 6 non-monotone, 9 narrowing to 150 veh/h and 4
staying at 600, with 7 of 13 having a resolved endpoint.

### 3.3 Definitional ambiguity in "pairwise identity"

`pairwise_identity` counts a policy pair as identical when the paired difference
is unresolved **and** the route split differs by under 2 % of the guided cohort.
That is not exact outcome equality (P2–P4 exactly equal in 134 contexts, not
276). **Correction applied:** the manuscript calls this *operational
indistinguishability* and states the criterion.

---

## 4. Leakage and protocol audit

Checked component by component against `analysis/policy_selectors.py`.

| Component | Fitted where | Verdict |
|---|---|---|
| Feature construction | context definition only; no outcome enters any descriptor | clean |
| Standardisation | inside each training fold | clean |
| Winner labels (B1–B3) | training fold only | clean |
| Advantage target (B4) | training-fold SBS | clean |
| Tree thresholds | training fold | clean |
| SBS identity | `argmin` over training-fold mean cost | clean |
| Conformal quantiles | 30 % calibration split of the training fold | clean |
| Support envelope | 95th percentile of training-fold kNN distance | clean |
| Replication grouping | contexts are the fold unit; all 5 seeds move together | clean |
| Evaluation noise band | computed from held-out data, used only for reporting `pct_within_noise`, never for fitting | clean, noted |

No leakage was found. The one quantity computed from held-out data, the
per-context noise band, is a reporting statistic and enters no fitted component.

---

## 5. Contribution hierarchy

**Primary.** The quantitative separation of policy complementarity from decision
value. The portfolio is complementary on three of four policies and on the
criterion vector in 73.0 % of contexts, while the headroom over the best fixed
policy is 0.45 s/veh (0.095 %) against 220.2 s/veh (46.4 %) for the first-order
fixed choice — a ratio of roughly 490. The mechanism is identified: the fixed
policy has a 17× upside-to-downside ratio, so it absorbs most of the winner-map
variation. This is a measurement, and the negative half of it is the point.

**Secondary.**
1. Accuracy and decision quality order the candidate rules differently. The
   mechanistic rule is more accurate than doing nothing and costs 71 % more;
   the most accurate learned rule is not the cheapest; the only rule trained on
   advantage is both the cheapest and the only one that improves the tail.
2. Distribution shift reported by type: helps 2, neutral 3, harms 3, with the
   worst damage under concept shift, and the support gate flagging 100 % of
   three extrapolations and 0 % of the domain shift its features cannot encode.
3. Selective prediction is structurally inapplicable at this effect-to-noise
   ratio: the gate never certified a deviation in 648 contexts or 8 splits.

**Supporting.** Criterion specialisation (P4 minimises stopped delay in 429 of
648 contexts and journey time in 129); the $x_8$ organising descriptor;
boundary refinement; parameter sensitivity (P3's frozen tolerance is
conservative by 16.66 s/veh, 37× the adaptation headroom).

**Not contributions.** The run count. The simulator. The policies. The
descriptors. Any of the selector model classes.

**What a sceptical reviewer will call the biggest contribution:** that a
carefully measured, fully replicated benchmark shows adaptive policy selection
to be worth two orders of magnitude less than the literature's framing implies,
with the mechanism for that gap identified and reproducible.

**What a sceptical reviewer will call the biggest weakness:** one synthetic
three-corridor network with a complete path catalogue, from which no external
validity follows; and the possibility that the result is an artefact of a
portfolio whose members are, by the study's own measure, operationally
indistinguishable in up to 42.6 % of contexts.

---

## 6. Decision gate

**YELLOW.** Scientifically coherent, internally consistent, fully reproduced,
and distinct from the companion article. Two substantive issues remain and are
disclosed rather than resolved:

1. **External validity is untested.** One synthetic network, one OD structure,
   complete path catalogue, full compliance. Every magnitude is
   benchmark-specific. This bounds the claims but does not contradict them, and
   it is stated in the abstract, the introduction and the limitations.
2. **The journal's author guidelines could not be retrieved** in this
   environment (all publisher domains blocked), so scope fit is argued from
   search-result summaries and the format follows Elsevier's own `elsarticle`
   class rather than a verified instruction. See `JOURNAL_COMPLIANCE.md`.

Neither is a scientific defect. GREEN is withheld because a submission-ready
classification should not be asserted while the target journal's requirements
are unverified.
