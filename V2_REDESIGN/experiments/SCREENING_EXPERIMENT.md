# Complementarity Screening Experiment — the first decision gate

**Purpose.** Answer one question before any ML work is authorised:

> Do the candidate policies actually become preferable under different operating conditions?

**This is a hypothesis test, not a warm-up.** If it fails, the deliverable is a negative result on
portfolio design. The network is **not** retuned until the answer changes.

---

## Size

Deliberately small. The screen exists to detect *separation*, not to estimate effect sizes.

| | Value | Rationale |
|---|---|---|
| Contexts | 12–16 | A fractional design over the 6 core factors, chosen to hit the corners where each policy's failure mode should fire |
| Policies | 4 (P1–P4) | The candidate portfolio |
| Seeds | **≥10**, paired (common random numbers) | V1's 3 seeds left 4/24 winners unstable; the screen's whole job is to beat the noise floor |
| Runs | ≈ 480–640 | Small enough to run and re-run; large enough to have power |

Contexts are chosen for **mechanism coverage**, not uniform coverage: each policy must face at least
two contexts where its hypothesised strength should appear and two where its hypothesised failure
mode should fire. Corner cases are more informative than a grid here.

---

## Measurements per run

System mean journey time (primary) · guided-cohort mean · background-cohort mean · P95 journey time ·
travel-time standard deviation · max link utilisation · total queueing/stopped time · CO₂ (retained
only to test time–CO₂ decoupling) · route-diversity index · oscillation index (share of guided
vehicles whose assigned path changes between consecutive decision epochs).

The oscillation index exists specifically to detect P2 herding. If it never rises, penetration
levels were set too low and the factor is not doing its job.

---

## Analysis

**1. Noise floor first.** For each (context, policy), estimate the seed standard error. Define the
minimum detectable difference. **A policy is declared a context winner only if it beats the runner-up
by more than the noise floor; otherwise the context is recorded as a TIE.** Ties are data, not
missing values.

**2. Per-context statistics.** Winner (or tie) · pairwise paired differences with CIs · Pareto set
over (system TT, P95, CO₂) · VBS · SBS · VBS−SBS gap.

**3. Portfolio-level statistics.** Wins and ties per policy · fraction of contexts with a
non-singleton Pareto set · rank correlation between policies across contexts (high correlation ⇒
redundancy) · **pairwise outcome-identity count** — the V1 diagnostic that exposed ECO ≡ SP in 21/24
contexts, and the fastest way to detect a degenerate portfolio.

**4. Dimensionality.** Does a single variable (e.g. saturation) reproduce the winner map? If a
one-variable rule explains the winners, complementarity is nominal, not real.

---

## Pass criteria — declared in advance

The gate **passes** if all four hold:

| # | Criterion |
|---|---|
| G1 | **≥3 of 4 policies** win at least one context beyond the noise floor |
| G2 | **≥25% of contexts** have a non-singleton Pareto set over the retained criteria |
| G3 | **No pair** of policies is outcome-identical in more than **50%** of contexts |
| G4 | A **single-variable rule does not reproduce** the winner map (i.e. ≥2 factors are needed) |

The gate **fails** if G1 or G3 fails. G2 and G4 failing while G1 and G3 pass is a *partial* pass —
the portfolio separates but the problem is low-dimensional, which is a legitimate finding and should
be reported, with the ML study scoped down accordingly rather than abandoned.

**These thresholds are declared now, before any run.** They are not adjusted after seeing results.

---

## Outcomes and what each means

| Outcome | Interpretation | Next action |
|---|---|---|
| All four pass | Genuine complementarity | Authorise Phases 3–8 |
| G1, G3 pass; G2 or G4 fail | Policies separate, but the decision is low-dimensional | Proceed with a reduced portfolio and an honest scope; B1 becomes the central comparison |
| G1 or G3 fails | Portfolio is degenerate — the V1 failure, repeated | **Stop.** Report the negative result. Diagnose whether it is the policies or the network, and change **one** of them, deliberately, with the change documented as a design decision and the screen re-run from scratch |

Retuning the network until the gate passes, without documenting it, would invalidate everything
downstream. If the network is changed, the screen is re-run and **both** screens are reported.

---

## Prerequisites (Phase 0–1, before the screen)

1. All four policies implemented, each with **known-answer unit tests** on a hand-checkable network:
   P1 returns the shortest path; P2 diverts after a link slows in the previous interval; **P3 splits
   toward the higher-capacity alternative on a two-path network**; P4 prefers the lower-variance
   path when means are equal.
2. Network frozen (`experiments/EXPERIMENTAL_DESIGN.md` §3) and committed.
3. Common random numbers verified: identical demand realisation across policies within a
   (context, seed) cell — assert this, do not assume it.
4. SUMO environment installed and version recorded.

**Note on the environment.** No V1 simulation asset exists in this project, so the V2 network, route
and configuration files are built new. This is required by the redesign anyway. **V2 runs are never
pooled with V1's 432 runs.**

---

## Scaffold

`experiments/screening_scaffold.py` implements the analysis contract: it consumes a run table with
the schema below and produces the gate report. It deliberately **refuses to run** without real
simulation output — there is no synthetic-data path, so no number in a screening report can be
anything other than measured.

Expected schema (one row per completed run):

```
context_id, policy, seed, sys_mean_tt, guided_mean_tt, bg_mean_tt,
p95_tt, sd_tt, max_util, stopped_time, co2, route_diversity, oscillation_idx
```
