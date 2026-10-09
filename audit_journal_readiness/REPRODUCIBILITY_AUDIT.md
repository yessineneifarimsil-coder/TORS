# Reproducibility Audit — 648-Context Routing-Policy Selection Study

Audit date: 2026-10-09. Mode: read-only with respect to the project. Every new script and
output lives in `audit_journal_readiness/`. `git status` was checked after each executed
project script and showed no change outside this directory.

---

## 1. Which study is which

| | Larger study (subject of this audit) | Smaller study (comparison only) |
|---|---|---|
| Directory | `study/` (code, data, frozen spec, conference LNCS version in `study/final/`); `journal/` (journal manuscript) | `routing_regime_study/` |
| Packages | `TRC_SUBMISSION.zip` (journal, elsarticle); `IC_TORS26_FINAL.zip` (LNCS conference version of the **same** study) | `IC_TORS26_ORIGINAL_STUDY.zip`, `routing_regime_study/TORS26_OVERLEAF.zip` |
| Authoritative manuscript | `journal/manuscript/main.tex` (commit 19f282c, 2026-09-23 16:30 UTC, latest touching any manuscript of this study) | `routing_regime_study/final/main.tex` |
| Runs | 12,960 main (648 × 4 × 5) | 432 (24 × 6 × 3) |
| Network | single OD, three corridors (C/N/S), built by `study/scenario/build_net.py` | 3×4 signalised mesh, 29 paths; network files **absent** from the repository |

The repository README says `routing_regime_study/` is retained for provenance only.
`study/INVENTORY.md` §A.3 records that **no number from the 432 runs is used** in the larger
study. I confirmed this: the larger study's analysis reads only `study/results/*.jsonl`.

---

## 2. Artefact inventory

| Artefact | Path | Status |
|---|---|---|
| Frozen specification | `study/spec/FROZEN_SPEC.md` | Present. Committed 8b08aa4 (2026-09-23 01:07:30); appended once (dd4352e, 01:07:57, screening design); **never edited afterwards** |
| Network and route definitions | `study/scenario/agb*.{nod,edg,con}.xml`, `agb_alt{1,2}.net.xml`, `build_net.py` | Present |
| Policy implementations | `study/policies/policies.py` | Present; **unchanged since the freeze commit** |
| Simulator driver | `study/sim/run.py`, `demand.py`, `campaign.py`, `mkjobs.py` | Present; `run.py` changed once after freeze (b032697, 07:57) to add a guard refusing lane closures on single-lane edges; does not affect any analysed run (arterial incident edges have 2 lanes) |
| Scenario manifests | `study/results/*_jobs.json` | Present for main, screen, sens, boundary, ood_north, ood_bypass, validate |
| Raw run records | `study/results/{validate,screen,main,sens,boundary,ood_north}.jsonl` | Present: 384 / 640 / 12,960 / 1,920 / 1,140 / 1,080 lines. **`ood_bypass.jsonl` absent** (all 2,160 runs failed; see the log) |
| Campaign logs | `study/results/*.log` | Present |
| Analysis | `study/analysis/{common,policy_selectors,ood,boundary,sensitivity,run_analysis,...}.py` | Present |
| Aggregate results | `study/results/results.json` | Present |
| Tests | `study/tests/test_{policies,twopath,capacity}.py` | Present |
| QC gate | `study/audit/qc_gate.py` | Present |
| Prior audits | `study/audit/*.md`, `study/audit2/verify_*.py`, `journal/SCIENTIFIC_AUDIT.md` | Present; written by the same agent |
| Screening report and deviations | `study/results/SCREENING_REPORT.md` | Present |
| Collision records | — | **Not recorded.** No run record contains a collision field, so collisions cannot be audited. Teleports (SUMO's usual symptom of gridlock or collision) are recorded and are zero |

---

## 3. Commands executed and results

| Command (from `audit_journal_readiness/`) | Purpose | Result |
|---|---|---|
| `python3 scripts/verify_core.py` | Independent rebuild of descriptive quantities from `main.jsonl` (copy of `study/audit2/verify_core.py` with outputs redirected) | **27/27** match `results.json`; tie diagnostics in §5 |
| `python3 scripts/verify_ladder.py` | Re-run the **frozen** `policy_selectors.loco()` on independently rebuilt X and C matrices | **0 mismatches** across 7 rows × mean/max/gap; 402 s |
| `python3 scripts/verify_ood.py` | Re-run all 8 shift splits | **0 mismatches**; help/neutral/harm classification reproduced |
| `python3 scripts/noise_floor.py` | **New.** Re-runs LOCO (413 s), then: cross-fitted VBS, per-seed realised gains, concentration, gate behaviour | `outputs/noise_floor.json` |
| `python3 scripts/sensitivity_check.py` | **New.** Paired recomputation of the P3 ε / P4 λ sensitivity from raw records | reproduces the published values |
| `python3 scripts/headroom_on_sens_subset.py` | **New.** Headroom on the same 96 contexts as the sensitivity campaign | 0.212 s/veh |
| `python3 scripts/conformal_widths.py` | **New.** Recomputes the frozen gate's per-policy conformal half-widths on 24 sampled LOCO folds | `outputs/conformal_widths.json` (finding R9) |
| `python3 scripts/text_overlap.py` | **New.** n-gram overlap among the three manuscripts | `outputs/text_overlap.json` |
| `python3 study/tests/test_policies.py` | Project's 12 known-answer policy tests | **ALL PASS** |
| `python3 study/tests/test_twopath.py` | SUMO integration test of P3 load balancing (temp dir) | **ALL PASS**; P3 split 398:202 against a 2:1 capacity ratio |
| `python3 study/audit/qc_gate.py` | Project's QC gate | **17/17 PASS.** But see §8: most checks verify that strings exist, not that behaviour is correct |

`study/tests/test_capacity.py` was **not** run because it overwrites
`study/results/capacity_calibration.json`.

---

## 4. Run accounting (verified)

| Campaign | Attempted | Valid | Failed | Min completion | Teleports | Used for |
|---|---:|---:|---:|---:|---:|---|
| validate (pre-freeze) | 384 | 384 | 0 | 0.9726 | 0 | capacity measurement, defect detection |
| screen | 640 | 640 | 0 | 1.0000 | 0 | gates G1–G4 |
| **main** | **12,960** | **12,960** | **0** | **1.0000** | **0** | **every headline number** |
| sens | 1,920 | 1,920 | 0 | 1.0000 | 0 | parameter sensitivity (exploratory) |
| boundary | 1,140 | 1,140 | 0 | 1.0000 | 0 | boundary brackets (exploratory) |
| ood_north (O8) | 1,080 | 1,080 | 0 | 1.0000 | 0 | domain-shift split (exploratory; redesigned) |
| ood_bypass (planned O8) | 2,160 | 0 | **2,160** | — | — | none |
| **Total** | **20,284** | **18,124** | **2,160** | | | |

No duplicate job keys in any file. Every main-campaign (context, policy) cell has all
five seeds. Failed runs produced no records, so they cannot leak into any estimate. The
supplementary campaigns are read only by their own analysis blocks.

---

## 5. Recomputed headline quantities

| Quantity | Published | Recomputed | Status |
|---|---|---|---|
| SBS | P3 | P3 (mean C1 474.353 s/veh) | Reproduced |
| Wrong-fixed penalty, P1 | 220.2 s (46.4 %) | 220.206 s | Reproduced |
| In-sample headroom | 0.451 s (0.095 %) | 0.45086 s; 0.0950 % | Reproduced |
| **Cross-fitted headroom** | not reported | **0.238 s** (per seed 0.19, 0.22, 0.20, 0.49, 0.09; SE 0.066) | **New** |
| P3 best, share of contexts | "64–65 %" (journal: 418 stable tie-break; 415 unique min; 426 tie-inclusive) | 415 / 418 / 426 of 648 = 64.0 / 64.5 / 65.7 % | Reproduced, convention-dependent |
| Exact ties for the C1 minimum | journal discloses | 50/648 (P2+P4 39; P2+P3+P4 8; P3+P4 3) | Reproduced |
| Resolved winners (G1′) | P3 227, P4 19, P1 11; P2 none | same | Reproduced |
| Non-singleton Pareto (C1, C2, C3) | 73.0 % | 0.72994 | Reproduced |
| P4 best on stopped delay | 429/648 (66.2 %) | 429 | Reproduced |
| B4 mean regret / gap closed | 0.199 s / 55.8 % | 0.19930 / 0.5579 | Reproduced (in-sample denominator) |
| B4 realised gain vs SBS on held-out seeds | not reported | 0.252 s; all five seeds positive (0.163–0.499); SE 0.063 | **New** |
| B1 regret / top-1 | 0.773 s / 66.7 % | 0.77293 / 0.66667 | Reproduced |
| B5 | equals B0 everywhere | equals B0 in 648/648 and in 8/8 splits; abstains in exactly the 233 contexts where B4 deviates | Reproduced |
| Abstention / out-of-support (LOCO) | 36.0 % / 4.9 % | 0.35957 / 0.04938 | Reproduced |
| P3 ε = 0.3 vs frozen 0.2 | −16.66 s | gain 16.659 s; alternative better in 84.4 % of 96 contexts | Reproduced |
| P3 ε = 0.1 | +8.10 s | loss 8.104 s | Reproduced |
| P4 λ = 0.5 / 1.5 | −0.11 / +1.27 s | 0.105 gain / 1.273 loss | Reproduced |

---

## 6. Discrepancies and defects

| ID | Finding | Type | Effect on claims |
|---|---|---|---|
| **R1** | **Hindsight reference is in-sample, not cross-fitted as the frozen spec requires.** FROZEN_SPEC §8: "ref ‖ VBS, cross-fitted hindsight best policy". `policy_selectors.evaluate()` uses `C.min(axis=1)` on the same 5-seed means used to score. | **Confirmed deviation from the frozen protocol, undisclosed in every manuscript** | Headroom 0.451 → 0.238 s/veh once cross-fitted. All "gap closed" percentages use the inflated denominator. B4's 55.8 % lies within an honest range of ≈56–100 %. The qualitative conclusion (headroom negligible) gets **stronger**, not weaker. |
| R2 | Unstable sort resolved 50 exact ties in the published winner counts | Confirmed defect (already corrected in the journal version) | Immaterial to headroom; changes winner-share wording by ≤1.7 pp |
| R3 | Stale `boundary_summary.n_narrowed = 0` | Confirmed defect (corrected in the journal version) | None on the main result |
| R4 | O8 replaced after the bypass campaign failed; the replacement (north corridor, g/C = 0.5, alt = 2, 54 contexts) was specified **after** the main LOCO results existed (main analysis committed 07:57; O8-north in 0cdb10a at 09:01) | Disclosed protocol change; post-hoc design | O8 conclusions are exploratory. The alt = 2 restriction is forced (a single-lane north corridor cannot carry a lane closure) but narrows the test |
| R5 | `qc_gate.py` mostly checks **source-text patterns** (e.g. check C passes because the string `j for j in range(n) if j != i` exists) | Limitation of the QC evidence | "17/17 QC pass" is weak evidence; the independent re-runs above are the real evidence |
| R6 | Top-1 accuracy comparison B1 vs B0 (66.7 % vs 64.5 %) depends on tie scoring: under tie-inclusive scoring B0 is 65.7 % | Plausible concern | "More accurate and more costly" still holds, by about 1 pp. Fragile as a headline |
| R7 | Mean noise floor reported as 20.90 s is **twice the largest paired SE across all three alternatives**, so it is dominated by the far-worse policies (P1) | Definitional concern | Overstates how far below "noise" the effect is. The relevant paired SD (best vs SBS, where they differ) is ≈1.80 s per context |
| **R9** | **The manuscript's explanation of why the gate never acts is incorrect.** The journal text (lines 1346–1353, 1543–1549) attributes it to a "replication noise floor" of 20.90 s. The frozen gate instead uses per-policy split-conformal half-widths of the *cross-context prediction residuals* of each policy's advantage. Recomputed on 24 sampled LOCO folds (`outputs/conformal_widths.json`), they are **P2 9.8 s, P4 12.1 s, P1 26.4 s**. Replication noise in the advantage target is ≈0.8 s (paired SD 1.8 s / √5). The width therefore comes almost entirely from **model error on heavy-tailed advantages**, not from simulation noise. The positive advantages it must certify average 0.7–2.6 s, and the GBDT's maximum predicted advantage averages 0.085 s | **Confirmed mis-explanation** | The conclusion (the gate cannot certify anything) stands; the mechanism and the "two orders of magnitude" ratio do not. The ratio is ≈1–1.5 orders (q ≈ 10–12 s vs a 0.45 s mean or ≈1 s typical positive advantage). The text must be corrected |
| R8 | A null "all policies equal to SBS" simulation in `noise_floor.py` (block C) gave 6.0 s/veh | **Rejected by the auditor** | The noise model borrowed paired-difference variances from policies that are far worse than SBS, which violates the null. It is not used as evidence anywhere |

---

## 7. Leakage and validity checks

| Concern | Finding | Classification |
|---|---|---|
| Held-out context in preprocessing, scaling, SBS, thresholds, conformal quantiles or support envelope | `fit_predict` receives training indices only. The frozen `loco()` builds `tr` by exclusion. Re-running it on independently rebuilt matrices reproduces every number | No defect found |
| Seeds of the held-out context in training | Contexts are the unit; 5-seed means are formed per context before LOCO | No defect |
| Pseudoreplication | The unit of analysis is the context; vehicles are aggregated within runs; seeds within contexts | No defect |
| Features unavailable before activation | x1–x8 use context factors and **pre-freeze measured** capacities only; x7 is the incident *regime*, not its realisation | No defect |
| Policy information access | P2/P3/P4 use 30 s samples over a 120 s window with lag D (`policies.py`). Unit tests confirm determinism and tolerance behaviour | No defect found (inspected, not formally proved) |
| Hyperparameters tuned on test folds | LightGBM parameters fixed in the frozen spec; no search code exists | No defect |
| VBS definition | In-sample (R1) | **Confirmed protocol deviation** |
| Methods changed after seeing results | Spec untouched after freeze; `policies.py` untouched; `run.py` guard only; O8 redesign post-hoc (R4) | Disclosed, limited |
| Sensitivity to frozen parameters | P3 ε moves cost by 8–17 s/veh — about 40–80× the headroom | **Substantive limitation**: the SBS's quality depends on an untuned parameter far more than on selection |
| Five seeds | Aggregate B4 gain has the same sign in all 5 seeds; context-level differences are mostly unresolved (55/222) | Limitation; aggregate claim OK, per-context claims weak |
| Incident implementation | Lane closure through TraCI; single-lane edges refused after the bypass failure | Verified in code |

---

## 8. Statistical credibility and noise floor

1. **The available gain is smaller than published.** In-sample headroom (0.451 s/veh)
   includes winner's-curse bias from taking the minimum of four noisy means.
   Cross-fitting (choose on 4 seeds, score on the 5th) gives **0.238 s/veh**.
   The true oracle headroom lies roughly between these values.
2. **It is concentrated.** 222 of 648 contexts have positive in-sample headroom. 20 of
   them carry half of it; the top 10 % carry 81 %.
3. **The best selector's gain is real in aggregate but tiny.** B4 beats SBS by
   0.252 s/veh on held-out seeds (positive in every seed; mean/SE ≈ 4, *descriptive*,
   not a test). That is 0.053 % of journey time, and 90 % of the net gain comes from 20
   contexts. Of its 233 deviations, 146 are better and 78 worse on the 5-seed mean,
   and only 29 have a consistent sign across all seeds.
4. **No operational claim beyond "negligible" is supported.** A 0.25 s/veh effect
   carried by about 20 contexts of one synthetic network cannot support a deployment
   recommendation in either direction, except "not worth it here".
5. **More seeds would not change the conclusion.** The point is not that the effect is
   unresolved; it is resolved as *small*. Seeds would sharpen the 20 contexts that
   matter and would not change the order of magnitude.

---

## 9. Distribution-shift splits (reconstructed separately)

| Split | Withheld | Type (as declared) | Train / test | B0 | B4 | B3 | B4 vs B0 (±0.05 s) | Support gate flags | Abstains | Fallback = B0? |
|---|---|---|---|---:|---:|---:|---|---:|---:|---|
| O1 | demand = 4200 | extrapolation | 540 / 108 | 0.000 | 0.983 | 0.449 | harms | 42.6 % | 16.7 % | yes; B5 = B0 |
| O2 | demand = 1200 | extrapolation | 540 / 108 | 0.528 | 0.531 | 0.278 | neutral | 14.8 % | 75.0 % | yes |
| O3 | demand = 2400 | interpolation | 540 / 108 | 0.565 | 0.167 | 0.470 | helps | 0.0 % | 25.0 % | yes |
| O4 | lag = 300 | extrapolation | 432 / 216 | 0.232 | 0.237 | 0.307 | neutral | 100 % | 38.4 % | yes |
| O5 | penetration = 0.8 | extrapolation | 432 / 216 | 0.298 | 0.293 | 0.214 | neutral | 100 % | 13.9 % | yes |
| O6 | g/C = 0.65 | extrapolation | 432 / 216 | 1.040 | 1.157 | 0.791 | harms | 100 % | 51.4 % | yes |
| O7 | trained without incidents, tested with | covariate + concept | 324 / 324 | 0.630 | 2.216 | 1.952 | harms (worst) | 32.1 % | 35.8 % | yes |
| O8 | incident on north corridor (absent in training) | domain shift | 648 / 54 | 0.314 | 0.176 | 0.081 | helps | **0.0 %** | 31.5 % | yes |

Interpretation:

- The gate "recovers" B0 on every harmful split **because it never deviates from B0
  anywhere**. It is not a selective deployment rule; it is the fixed policy. The confidence
  gate abstains wherever B4 would deviate, so the support gate never matters to the
  outcome.
- The gate fails for a reason different from the manuscript's: it is not simulation noise
  but GBDT prediction error on heavy-tailed advantage targets (R9). Recalibrating the
  conformal step would not fix this. The advantage being certified is genuinely
  smaller than the predictor's error.
- The support gate flags 100 % of O4–O6 and **0 % of O8**: the descriptors cannot encode
  *where* an incident occurs. O8 is also the split where an unguarded selector helps most.
- Conformal coverage is valid only under exchangeability. No manuscript claims more, and
  none should.

---

## 10. Protocol deviations and timeline (verified from git)

| Time (UTC, 2026-09-23) | Commit | Event |
|---|---|---|
| 01:07:30 | 8b08aa4 | Spec, network, policies, simulator frozen |
| 01:07:57 | dd4352e | Screening design declared |
| 01:26:11 | 67fde2e | Screen: G1 **FAIL**, pre-declared verdict STOP. **D-1** recorded: campaign run anyway; constraints and confirmatory **G1′** declared in the same commit |
| 02:06–02:19 | 5270075, 2e5a156 | Sensitivity and boundary analyses added; boundary chain armed (main campaign running, no main results committed yet) |
| 02:30:27 | 8bbd2da | First snapshot of main-campaign records |
| 06:49:55 | b44c236 | G1′ result recorded: PASS (P3 227, P4 19, P1 11) |
| 07:57:55 | b032697 | Full main analysis; `run.py` guard added after the bypass failure |
| 09:01:56 | 0cdb10a | O8 replaced by the north-corridor split; boundary localisation |

Fairest reading:

- **Confirmatory:** the main campaign's descriptive and LOCO results, and G1′, whose
  definition was fixed before any main result existed.
- **Exploratory:** O8-north, sensitivity, boundary refinement, the tie-corrected
  re-analysis, and everything in this audit marked *new*.
- **D-1:** the deviation is real and was honestly recorded. The STOP rule was overridden
  by the same agent that wrote it, about 19 minutes after writing it. Report it as a
  deviation, not as vindicated.

**Independent tests that would strengthen the affected claims:** a cross-fitted
re-analysis (done here: R1); a second network (see `GO_NO_GO_PLAN.md`).
