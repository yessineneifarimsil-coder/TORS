# Overlap: 432-Run Study vs 12,960-Run Study (and the Two Conference Packages)

Audit date: 2026-10-09.

## 1. Four manuscripts, two studies

| Label | File | Study | Format | Title |
|---|---|---|---|---|
| **S1-conf** | `IC_TORS26_ORIGINAL_STUDY.zip` → `routing_regime_study/final/main.tex` | 432 runs | LNCS (IC_TORS'26) | *Context-Dependent Selection of Urban Routing Policies: Regime Effects, Decision Value and Generalisation Limits* |
| **S2-conf** | `IC_TORS26_FINAL.zip` (`study/final/`) | 12,960 runs | LNCS (IC_TORS'26) | *Context-Dependent Selection of **Established** Urban Routing Policies: Regime Effects, Decision Value, and Generalization Limits* |
| **S2-journal** | `TRC_SUBMISSION.zip` (`journal/manuscript/`) | 12,960 runs | elsarticle | *Context-Dependent Selection Among Established Urban Routing Policies: Complementarity, Decision Value and Generalisation Under Distribution Shift* |
| (other) | `paper/IC_TORS26_SHAP_MCDM_conference_final_2026-08-27_v11.tex` | unrelated XAI–MCDM study | LNCS | *Do Global XAI–MCDM Weights Add Decision Value? …* |

**The repository does not record which of these, if any, was actually submitted to
IC_TORS'26.** S1-conf and S2-conf were both packaged on 2026-09-23, after the recorded
(extended) deadline of 12 September 2026. The only IC_TORS'26 file dated before that
deadline is the unrelated XAI–MCDM paper (27 August 2026). The student must establish the
true submission status before anything else. It determines the duplicate-publication
analysis in §4.

S1-conf and S2-conf have **nearly identical titles**. If both were ever submitted to the
same venue, an editor would very likely read them as duplicate submissions. Do not submit
both under these titles.

## 2. Element-by-element comparison: S1 (432) vs S2 (12,960)

| Element | S1 (432 runs) | S2 (12,960 runs) | Classification |
|---|---|---|---|
| Research question | When does the preferred established routing policy change, what is adapting worth, and does it transfer to unseen demand? | Are complementarity, decision value and deployability distinct, and how large is each? | **Shared conceptual background**; S2's RQ is broader and differently framed |
| Network | 3×4 signalised mesh, 12 signals, 29 legal paths; files absent from the repo | single OD, three disjoint corridors (C/N/S), built by script | **Distinct** (different networks; S1's cannot be rebuilt) |
| Policies | SP, DTT, TECO10 (+ ECO, TECO05/15 measured) | P1 shortest, P2 lagged travel time, P3 FBkSP-type load balancing, P4 mean–variance | **Distinct** (only shortest/travel-time objectives shared conceptually; implementations independent) |
| Context factors | demand (3) × restriction (4) × signal plan (2) = 24 | demand (6) × g/C (3) × penetration (3) × lag (3) × incident (2) × alt capacity (2) = 648 | **Distinct** |
| Seeds | 3 paired | 5 paired | Distinct |
| Decision criteria | 0.5/0.5 time + CO2 scalarisation with fixed references | C1 (journey time) primary; Pareto over C1/C2/C3; profiles for sensitivity | **Distinct** |
| Fixed and hindsight references | SBS (DTT), hindsight best | SBS (P3), VBS (in-sample; see R1) | **Reused method** (standard algorithm-selection apparatus) |
| Selection methods | demand thresholds, regression tree (depth 3) | mechanistic tree, tree, logistic, advantage GBDT, gated GBDT | **Partly reused idea** (explicit-rule vs learned ladder); implementations distinct |
| Regret / headroom | 0.03018 cost units; 79.9 % captured | 0.451 s/veh (0.238 cross-fitted); 55.8 % "closed" | **Reused method, new data** |
| Validation | LOCO; leave-one-demand-out | LOCO; 8 shift splits by type | **Partly reused** (LOCO; held-out demand ≈ O1–O3); S2 adds penetration, lag, g/C, incident and domain shifts |
| Distribution shift | one factor (demand) | eight splits, four shift types | **Newly conducted experiment** in S2 |
| Abstention / gate | none | support + conformal gate (never acted) | **New in S2** (a negative result) |
| Results / figures | 432-run numbers and figures | 12,960-run numbers and figures | **Distinct**: no shared number, table or figure; S2 code reads only `study/results/` (verified) |
| Main conclusions | value exists inside fitted regimes, fails under extrapolation | value is negligible; complementarity does not imply value or deployability | **Related but different**: S1 reports a positive in-regime gain (79.9 % of a headroom); S2 reports a negligible headroom |
| Text, equations, citations | — | — | 10-gram overlap **0.09 %** of S2-journal; 12-gram 0.03 %; 5 of 25 journal references shared (all canonical); regret/headroom equations of the same standard form |

**Verdict on S1 vs S2:** two separate studies sharing a research programme, a conceptual
vocabulary and a standard evaluation method. There is **no data, result or figure
reuse** and negligible text reuse. Publishing both is defensible **if** each paper cites
the other and states the relationship. Their headline messages pull in opposite
directions (S1: adaptation recovers 80 % of a meaningful in-regime headroom; S2:
headroom negligible). A careful editor will want that tension discussed, not hidden.

## 3. Element-by-element comparison: S2-conf vs S2-journal (the real overlap risk)

| Element | S2-conf (`IC_TORS26_FINAL.zip`) | S2-journal (`TRC_SUBMISSION.zip`) | Classification |
|---|---|---|---|
| Data | 12,960 main + supplementary campaigns | identical | **Reused data (100 %)** |
| Core results | SBS, headroom 0.451 s, ladder, 8 shift splits, G1′ | identical values (tie-corrected winner counts) | **Reused results** |
| New in journal | — | tie-aware winner counts; B5 ≡ B0 analysis; O8 support-gate blind spot; corrected boundary summary; expanded discussion | **Re-analysis of the same data**, not new experiments |
| Text | — | shared 8-grams: 1.2 % of journal text (1.8 % of conference text); 10-grams 0.8 % / 1.2 % | Low verbatim reuse |
| Figures | LNCS figures | redrawn figures of the same results | **Reused results, redrawn** |

**Verdict on S2-conf vs S2-journal:** if S2-conf was submitted to IC_TORS'26 and is under
review or accepted, the journal manuscript is an **extended version of the same study**.
Every substantive result in it already appears in the conference paper. Its additions
are re-analyses of the same 12,960 runs. Many journals accept extended conference
papers only with explicit disclosure to the editor and a substantial extension: new
experiments, new analysis or new theory. The common informal threshold is about 30 %
new material, but it varies by journal and I could not verify any journal's policy from
here. The present additions are unlikely to qualify. The external-validity experiment in
`GO_NO_GO_PLAN.md` would qualify.

## 4. Required disclosures

1. **Establish the submission status** of S1-conf and S2-conf (was either submitted? under
   review? accepted? withdrawn?).
2. If S2-conf is under review or accepted, **tell the journal editor at submission**, cite
   it, and state precisely what the journal version adds. Do not rely on low text
   overlap. Similarity checkers measure text, but editors judge duplicate publication on
   results.
3. If S1-conf is published, cite it in S2-journal as prior work by the same author on a
   different network and policy set, and explain why the two headroom conclusions differ
   (different network, portfolio, criteria and cost scale).
4. Do not submit S1-conf and S2-conf to the same venue under near-identical titles.
5. **Disclose AI assistance** as the target venue requires. Per the git history, the S2
   design, code, simulations, analysis and prose were produced by an AI agent (22
   commits authored "Claude"). For S1, the 432 simulations, the workbook and the first
   seven commits are the student's (authored "Yessine Naifar", 2026-09-21/22). The
   agent authored only the expansion commit c676a50 (`analysis2/`, `final/`).
