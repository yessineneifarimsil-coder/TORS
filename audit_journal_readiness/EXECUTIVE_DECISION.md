# Executive Decision — Journal Readiness of the 648-Context Routing-Policy Selection Study

Audit date: 2026-10-09. Audit scope: the larger study (`study/`, journal manuscript
`journal/manuscript/main.tex`, package `TRC_SUBMISSION.zip`), compared against the
432-run study (`routing_regime_study/`) and the closest literature found.

---

## 0. Disclosure that limits this audit's independence

The git history shows that the entire larger study — frozen specification, network,
policy code, all six simulation campaigns, the analysis, the figures and both
manuscripts — was written by an AI agent (Claude) inside **this same session**,
between 01:07 and 16:30 UTC on 2026-09-23 (22 commits authored
`Claude <noreply@anthropic.com>`, trailer `Claude-Session: …session_01YMTD6ZTL1NzZWcf1APaxN9`).
I am therefore auditing work I produced. I have tried to counter that by re-running
everything from the raw run records, by testing claims the earlier work did not test,
and by searching literature the manuscript does not cite. A human reviewer should still
treat this as a self-audit.

That fact is also a finding in its own right; see §6.

---

## 1. Verdict

**Do not submit the current manuscript to a journal.** It is reproducible and honestly
written, but it does not yet carry a contribution that survives comparison with existing
work, and its single substantive finding rests on one small synthetic network.

**Recommended path: Option 2, a bounded redesign with a hard stop rule.** Run at most
two targeted experiments (defined in `GO_NO_GO_PLAN.md`). If they do not change the
picture within a fixed time budget, stop pursuing this as a journal article and keep the
infrastructure and the negative result for a thesis chapter or a short paper.

**Confidence in this recommendation: moderate.** Reasons for doubt are given in §8.

---

## 2. What the study establishes that existing papers have not

After the literature search (`LITERATURE_NOVELTY_MATRIX.md`), essentially **one
quantitative finding** survives:

> On a controlled single-OD, three-corridor SUMO benchmark with four established routing
> policies, the decision value of per-context policy selection is very small:
> at most 0.45 s/veh in-sample and ≈0.24 s/veh when the hindsight reference is
> cross-fitted (0.05–0.10 % of a 474 s mean journey time). Choosing the wrong
> *fixed* policy costs 16–220 s/veh, and changing one parameter of the best fixed
> policy moves cost by ≈17 s/veh. The opportunity is three orders of magnitude
> smaller than the fixed-policy choice and about two smaller than within-policy tuning.

Everything else in the manuscript is either an established idea applied to this domain
or a negative result about the study's own apparatus:

| Manuscript element | Status relative to the literature |
|---|---|
| Per-instance selection, SBS/VBS, "gap closed" | Established (Rice 1976; Xu et al. 2008; Bischl et al. 2016; Kerschke et al. 2018; Lindauer et al. 2019) |
| Relative merit of routing strategies depends on context (demand, penetration, control regime) | Established (Mahmassani & Jayakrishnan 1991; Yang 1998; Pan et al. 2013; Xie et al. 2014; Toso et al. 2023/24; Cornacchia et al. 2024/26) |
| Accuracy ≠ decision quality | Established (Elmachtoub & Grigas 2022; Mandi et al. 2024) |
| Fall back to a baseline when uncertain | Established (Chow 1970; Laroche et al. 2019; Ansótegui et al. 2018; Sawarni et al. 2026) |
| Conformal coverage fails under shift | Established (Shimodaira 2000; Tibshirani et al. 2019) |
| Complementarity ≠ decision value ≠ deployability | A clear framing; logically implied by the SBS/VBS literature rather than new |
| The selective gate | Never acted: B5 ≡ B0 in all 648 contexts and all 8 splits. Not a contribution |

I did not find a paper that applies the SBS/VBS decision-value lens to a portfolio of
established *traffic-routing policies*. That is a real gap, but a thin one: closing it
on one synthetic network with a negative answer is a measurement, not yet a general
result. The search was not exhaustive (Crossref, OpenAlex, Semantic Scholar, Google
Scholar, doi.org and publisher domains were blocked by the network policy), so "no
prior paper found" must not be written as "no prior paper exists".

---

## 3. Strongest argument for publishing

The study is unusually clean: a frozen specification committed before any evaluation
run; paired common random numbers; 12,960 valid runs with zero failures and zero
teleports in the analysed campaigns; leave-one-context-out with every fitted quantity
refit per fold; distribution shift reported by type; and protocol deviations disclosed
with a verifiable timeline. Every headline number reproduces from the raw run records
(27/27 descriptive checks, the full 648-fold ladder with 0 mismatches, all 8 shift
splits with 0 mismatches). It answers a practical question — "is adaptive
routing-policy selection worth building?" — with a defensible "barely, here", and it
shows why a reader should not infer deployability from complementarity.

## 4. Strongest argument against publishing

The answer is specific to a toy network whose structure makes it likely. With three
disjoint corridors, a complete path catalogue, one OD pair and full compliance, a
capacity-aware load-balancing policy (P3) is close to dominant almost by construction,
and P2 and P4 tie exactly for the best outcome in 47 contexts. A referee will say the
tiny headroom is a property of this benchmark, and the manuscript contains no evidence
to the contrary. The methodological additions — learned selector, conformal gate,
support gate — produce either a 0.25 s/veh gain or nothing at all. What remains is a
negative result in one synthetic environment, framed around concepts that are already
standard.

---

## 5. Key numbers from this audit (independently recomputed)

| Quantity | Value | Source |
|---|---|---|
| Main campaign | 648 × 4 × 5 = 12,960 valid runs, 0 failures, 0 teleports | `outputs/verify_core.log` |
| Project total | 20,284 attempted, 18,124 succeeded, 2,160 failed (all the bypass-incident O8 campaign) | `study/results/*.log` |
| SBS | P3, mean C1 474.35 s/veh | `outputs/noise_floor.json` |
| In-sample VBS headroom | 0.4509 s/veh (0.095 %) | reproduced exactly |
| **Cross-fitted VBS headroom** (winner chosen on 4 seeds, scored on the 5th) | **0.238 s/veh**, SE over seeds 0.066 | new in this audit |
| Headroom concentration | 222 contexts > 0; 20 contexts carry half; top 10 % carry 81 % | new |
| B4 (advantage GBDT) realised gain over SBS | 0.252 s/veh; positive in all 5 seeds (0.16–0.50); SE 0.063 | new |
| B4 net gain concentration | top 10 contexts give 62 %, top 20 give 90 % | new |
| B4 deviations | 233; better on 5-seed mean in 146, worse in 78; sign-consistent across all seeds in only 29 | new |
| B1 (mechanistic rule) | −0.32 s/veh vs SBS, negative in all 5 seeds | new |
| B5 (gated) | identical to B0 in 648/648 contexts and 8/8 splits; abstains exactly where B4 deviates | reproduced |
| Wrong fixed policy | P1 +220.2, P4 +18.3, P2 +16.3 s/veh | reproduced |
| P3 tuning (ε 0.2→0.3), 96-context subset | 16.66 s/veh faster in 84 % of contexts, vs 0.21 s/veh headroom on the same subset (≈79×) | new like-for-like comparison |

---

## 6. Major risks

1. **Spec-versus-code deviation not reported anywhere (new).** The frozen specification
   (§8) defines the reference as a "cross-fitted hindsight best policy". The code
   (`policy_selectors.ladder`, `evaluate`) uses the in-sample minimum of the 5-seed
   means. This inflates the reference: the in-sample headroom is 0.451 s/veh, while the
   cross-fitted one is 0.238 s/veh. Every "gap closed" figure (B4's 55.8 %, B1's −71 %)
   has the in-sample denominator. Against the cross-fitted reference, B4 recovers
   roughly the whole achievable headroom, and the true figure lies between ≈56 % and
   ≈100 %. Neither manuscript states this.
2. **The gate's failure is mis-explained (new).** The manuscript blames a 20.90 s
   "replication noise floor". The frozen gate's per-policy conformal half-widths are
   ≈10–12 s for P2/P4 and come from GBDT prediction error on heavy-tailed advantage
   targets; replication noise in those targets is ≈0.8 s. The conclusion holds; the stated
   mechanism and the "two orders of magnitude" ratio (actually ≈1–1.5) do not.
3. **External validity.** One synthetic topology, one OD pair, three corridors, a complete
   path catalogue, homogeneous fleet and full compliance. This is the decisive weakness.
4. **Duplicate-publication risk.** The same 12,960-run study was packaged for IC_TORS'26
   (`IC_TORS26_FINAL.zip`, LNCS, title *"Context-Dependent Selection of Established Urban
   Routing Policies: Regime Effects, Decision Value, and Generalization Limits"*), and the
   432-run study was packaged for the same conference under an almost identical title. The
   repository does not record which, if either, was submitted, and the recorded deadline
   (12 Sept 2026) precedes both packages. If the 648-context conference paper is under
   review or published, the journal manuscript reuses 100 % of its data and results.
   Text overlap is low (1.2 % shared 8-grams), but that does not make reused results new.
   See `OVERLAP_432_VS_12960.md`.
5. **Authorship and accountability.** The study design, implementation, analysis and
   prose were generated by an AI agent. As far as I know, major publishers' AI policies do
   not allow an AI to be an author and require authors to disclose AI use and take full
   responsibility for the work; I could not retrieve any current policy text from this
   environment, so check the target journal's policy directly. The student must be able to defend every design choice
   (factor levels, ε = 0.20, λ = 1.0, the descriptor set, the gates) as their own
   scientific judgement, and must check the target journal's AI-use policy. This is not
   a reason the science is wrong. It is a reason the student must re-own it before
   putting their name on it.
6. **Statistical resolution.** The adaptation effect is ≈0.25 s/veh against
   per-context paired-difference standard deviations of ≈1.8 s. It is consistent in sign
   across seeds in aggregate, but it is carried by ≈20 contexts and resolved in only
   55 of the 222 contexts where the SBS is not best.
7. **Post-hoc elements.** Deviation D-1 (G1 failed, campaign run anyway); G1′ declared
   before the campaign (verified from the commit timeline); the O8 domain-shift split
   redesigned *after* the main results were known (north corridor, restricted to
   alt = 2 and g/C = 0.5, 54 contexts); the sensitivity campaign added during the main
   run. All are disclosed. The confirmatory core is the main campaign plus G1′; O8-north
   and the sensitivity results are exploratory.
8. **Tie handling.** In 50 of 648 contexts the C1 minimum is an exact tie. Published
   winner counts relied on an unstable sort. This is corrected in the journal version
   and immaterial to the headroom result.

---

## 7. Scores (0–5; structured judgements, not measurements)

| Criterion | Score | Reason |
|---|:-:|---|
| Originality relative to direct competitors | **2** | Every methodological component is established (A3, A7, D1–D4 in the matrix). Context-dependent merit of routing strategies is established (Pan 2013, Xie 2014, Cornacchia). Only the SBS–VBS measurement for routing policies appears new. |
| Importance of the research question | **3** | Whether to build context-aware routing-policy selection is a real operator question. Its practical weight is limited once the answer is "rarely worth it". |
| Strength of empirical evidence | **3** | Large, paired, fully replicated and reproducible within the benchmark. Weak beyond it: one synthetic network. |
| Reproducibility | **4** | Code, data, frozen spec and logs present; every headline number reproduces exactly. Deductions: tie-break defect, in-sample VBS contrary to the spec, collisions not logged. |
| Statistical credibility | **2** | The aggregate is consistent in sign across seeds, but the effect is 0.25 s/veh, carried by about 20 contexts, with an inflated reference denominator and a gate argument built on the wrong quantity. |
| Generalisation evidence | **1** | Shift splits are internal to one toy network; the abstention mechanism never acts; no second network. |
| Methodological or theoretical contribution | **1** | No new method. The gate is standard and inactive. The three-property framing is useful but follows from existing practice. |
| Suitability for a journal article (current form) | **1** | A single-benchmark negative result, framed around standard concepts, with unresolved conference-overlap and authorship issues. |

**Single most important unresolved issue:** whether the negligible decision value
generalises beyond the three-corridor toy network (`GO_NO_GO_PLAN.md`, E2).

**Minimum work for a defensible submission:** resolve the conference status (M1), re-own
the design (M2), apply the two analysis corrections (M3), and complete the
second-network replication with a decisive outcome (E2).

## 8. What would change this recommendation

- **Toward submission:** a replication on one realistic multi-OD network, with
  general-network versions of the four policies, showing either (a) a materially larger
  headroom that a selector can capture, which makes selection a real problem, or (b) a
  similarly negligible headroom against a tuned fixed policy, which makes the negative
  result general enough to publish.
- **Toward stopping:** if the policies cannot be generalised to a multi-OD network
  within the time box, or if the conference version of the 648-context study turns out to
  be published or under review and the journal requires a substantial extension the
  replication cannot provide.
- **My own uncertainty:** some journals publish well-designed negative simulation results
  on a single benchmark. If the student's target is a mid-tier venue rather than a Q1
  journal, a shortened version scoped honestly to one benchmark may be acceptable now.
  I could not verify any journal's scope or author guidelines from this environment.

---

## 9. Plain-language answer

**Do not keep polishing this manuscript.** Its core result is real and reproducible,
but it is a small negative finding on one toy network. The parts that look like
methodological contributions are either standard ideas or did nothing (the gate never
acted). Give it one bounded test of external validity, as specified in
`GO_NO_GO_PLAN.md`, with a fixed budget of about 4–6 weeks. If that test cannot be
done, or leaves the picture unchanged, stop treating this as a journal article. Keep the
simulator, the policies and the negative result for your thesis, and spend your PhD time
on a question where the answer is not already implied by "the best fixed policy is
almost always best here".
