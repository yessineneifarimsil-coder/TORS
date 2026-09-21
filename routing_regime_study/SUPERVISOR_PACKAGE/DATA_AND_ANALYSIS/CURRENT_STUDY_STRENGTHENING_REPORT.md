# Current Study Strengthening Report

Post-processing pass over the **432 completed runs**. No new simulation, strategy, scenario,
criterion, MCDM method, ML method, figure or table. Every number below is derived from the
existing run table (`analysis/runs.csv`) by `analysis/mechanism.py` and `analysis/deepdive*.py`.

---

## 1. Strongest existing scientific result

The preferred established routing policy reverses with traffic demand, the reversal is displaced
by the signal regime, adaptation across it recovers 79.9% of available headroom on held-out
contexts, and the same selector becomes harmful above its training support. That result stands.
This pass makes it **mechanistically explained, regime-decomposed and weight-audited**.

---

## 2. New mechanism evidence (from existing outputs)

The reversal is the crossing of a **fixed structural penalty** against a **growing congestion penalty**.

| SP minus DTT | A low (720) | B transition (1200) | C high (1680) |
|---|---|---|---|
| route distance (m) | **−250.3** | **−288.0** | **−277.2** |
| in-network time (s) | −17.9 | +84.8 | +113.7 |
| insertion delay (s) | 0.0 | +18.0 | +441.2 |
| journey time (s) | −17.9 | +102.8 | +554.9 |
| CO₂ (g) | −44.7 | +322.5 | +416.9 |
| stopped veh-s per vehicle | +6.4 | +104.1 | +114.3 |

SP's distance advantage is **essentially constant** across regimes (−250 to −288 m, ~8% shorter).
What changes is congestion on that shorter corridor:

| implied in-network mean speed (km/h) | 720 | 1200 | 1680 | loss |
|---|---|---|---|---|
| SP | 37.80 | 26.64 | 18.31 | **−51.6%** |
| DTT | 38.43 | 30.96 | 23.80 | −38.1% |

| CO₂ intensity (g/km) | 720 | 1200 | 1680 |
|---|---|---|---|
| SP | 255.1 | 443.6 | **590.7** |
| DTT | 248.5 | 314.1 | 423.2 |

**Supported interpretation.** At low demand the two policies achieve nearly identical speeds
(37.80 vs 38.43 km/h, a 1.6% difference) and near-identical queueing (176.1 vs 169.7 stopped
veh-s per vehicle), so DTT's 7.8% longer route is not compensated and SP wins on both criteria.
As demand rises, the shortest corridor degrades faster than the alternatives — SP loses 51.6% of
its speed against DTT's 38.1%, and its emission intensity rises to 590.7 g/km against 423.2 —
so the congestion penalty overtakes the fixed distance advantage and the sign of the margin flips.

This is stated as a **consistent decomposition, not a causal identification**: the experiment does
not isolate the corridor-loading mechanism from other consequences of higher demand.

**Data limitation.** Per-vehicle route shares and direct signal-exposure measures (e.g. stops per
signal, per-approach delay) are **not present** in the existing per-run aggregates. Queueing is
represented only by total stopped vehicle-time, and route diversity only by the default-link
fraction. Mechanism statements are limited accordingly.

---

## 3. Transition analysis

| cell | m@720 | m@1200 | m@1680 | Δ 720→1200 | Δ 1200→1680 | monotone |
|---|---|---|---|---|---|---|
| Bal/None | −0.0551 | 0.4204 | 1.0139 | +0.4755 | +0.5936 | yes |
| Bal/U | −0.0515 | 0.4382 | 0.9418 | +0.4897 | +0.5037 | yes |
| Bal/C | −0.0195 | 0.8056 | 1.1137 | +0.8250 | +0.3081 | yes |
| Bal/L | −0.0562 | 0.4196 | 1.0134 | +0.4758 | +0.5939 | yes |
| Art/None | −0.0184 | −0.1269 | 0.3249 | −0.1085 | +0.4517 | **NO** |
| Art/U | −0.0198 | −0.1318 | 0.3165 | −0.1119 | +0.4483 | **NO** |
| Art/C | −0.0423 | 0.0488 | 0.3893 | +0.0911 | +0.3405 | yes |
| Art/L | −0.0110 | −0.0954 | 0.2952 | −0.0844 | +0.3906 | **NO** |

**CORRECTION to the current manuscript.** §4.1 states the margin is *"monotone in demand in all
eight cells"*. It is **monotone in 5 of 8**. In three arterial cells the margin *decreases* from
720→1200 before reversing sharply — SP's advantage first strengthens under arterial priority, then
collapses. The accelerating claim (|Δ₂|>|Δ₁|) holds in **7 of 8** and is correct as written.
This must be fixed.

Seed standard deviation of m is 0.003–0.038 at 720 and 1680 but rises to 0.018–0.121 at 1200 —
dispersion is largest exactly in the transition band. No exact threshold is estimated; brackets only.

---

## 4. Signal-regime evidence

All eight cells share the same endpoints — SP wins at low demand, DTT at high demand — and differ
only in *where* the crossing sits.

| | crossing bracket | mean m@1200 |
|---|---|---|
| Balanced | (720, 1200] in **4/4** cells | **+0.5209** |
| Arterial | (1200, 1680] in **3/4** cells | **−0.0763** |

Difference in mean margin at 1200 veh/h: **+0.5972**. The observed bracket shifts by one full grid
step, i.e. **≥480 veh/h**.

**Seed stability.** Sign of m@1200 per seed: Balanced `+++` in all four cells; Arterial `---` in
None/U/L and `++−` in C (the known outlier). The pattern is stable in 7 of 8 cells across all
three seeds.

Reported as *"the results indicate"* — the experiment varies green split and does not isolate the
mechanism, so no causal claim is made.

---

## 5. Decision-headroom decomposition

| regime | worst policy | fixed SP | fixed DTT | adaptive | hindsight | share of total headroom |
|---|---|---|---|---|---|---|
| A low (720) | 0.03422 | **0.00000** | 0.03422 | 0.00000 | 0 | **37.8%** |
| B transition (1200) | 0.32289 | 0.27864 | 0.05633 | 0.01818 | 0 | **62.2%** |
| C high (1680) | 0.67611 | 0.67611 | **0.00000** | 0.00000 | 0 | **0.0%** |

**New, sharper statement:** all decision headroom lies in regimes A and B. At high demand DTT is
optimal in every context, so there is **nothing for adaptation to win** — the penalty there is for
using the *wrong fixed* policy (SP costs 0.676), not for failing to adapt. The adaptive selector
attains zero regret in both outer regimes and carries all residual regret in the transition band.

---

## 6. ML decision interpretation

Fitted tree structure (inspection only, no retraining):

```
demand <= 1440
├── signal = Arterial → demand <= 960 ? leaf : leaf
└── signal = Balanced → demand <= 960 ? leaf : leaf
demand > 1440
├── signal = Arterial → leaf
└── signal = Balanced → leaf
```

- Features used: **demand (74.6%)**, **signal regime (25.4%)**
- Restriction-location features: importance **0.0** — never used (consistent with
  leave-one-restriction-out reproducing LOCO exactly)
- Root split at demand 1440 isolates regime C; the second-level signal split then separates the
  two transition behaviours; the demand-960 split separates regime A from B

**Why this is not simply a demand classifier:** a depth-1 tree on demand alone captures **53.1%** of
headroom. Adding the signal split raises it to **79.9%**. Signal regime carries a quarter of the
model's importance and appears in both branches.

| | |
|---|---|
| Label agreement with observed best | 18/24 (75.0%) |
| Zero-regret decisions (ties included) | 21/24 (87.5%) |
| Mean regret when correct | 0.00000 |
| Mean regret when wrong | 0.04847 (n=3, max 0.11545) |
| Residual regret by regime | A 0.00000 · **B 0.01818** · C 0.00000 |

The three non-zero-regret contexts are D009, D011, D014 — all at 1200 veh/h.

---

## 7. Prediction → ranking → decision decomposition

| category | n | mean rel. prediction error | mean regret |
|---|---|---|---|
| Prediction imperfect, decision **correct** | **18** | 5.9% | 0.00000 |
| Ranking changed, regret **negligible** (ties) | 3 | 7.7% | 0.00000 |
| Ranking changed, regret **substantial** | 3 | 10.7% | 0.04847 |

Full 3-policy ranking exactly right in **10/24**; top-1 right in **18/24**; zero regret in **21/24**.

**Decision quality (21) > top-1 ranking quality (18) > full ranking quality (10) > prediction quality.**
D021 is the clean illustration: 24.4% mean prediction error, zero regret. D014 is the converse:
18.2% error, ranking flips, regret 0.11545. This is the predict-then-optimize distinction
demonstrated empirically on our own data rather than asserted from the literature.

---

## 8. OOD interpretation

| held-out | training support | test point | selected | hindsight best | adaptive | fixed DTT | difference |
|---|---|---|---|---|---|---|---|
| q=720 | {1200, 1680} | **below** | DTT×4, TECO10×4 | SP×8 | 0.02456 | 0.03422 | −0.00966 |
| q=1200 | {720, 1680} | **inside gap** | DTT×8 | TECO10×3, SP×3, DTT×2 | 0.05633 | 0.05633 | **+0.00000** |
| q=1680 | {720, 1200} | **above** | DTT×4, TECO10×4 | DTT×8 | **0.14856** | **0.00000** | **+0.14856** |

**Sharper than "extrapolation fails".** Three distinct behaviours:
- **Interpolation into a gap** (1200) is *safe but uninformative* — the selector exactly reproduces
  the fixed policy, gaining and losing nothing.
- **Extrapolation below** support (720) is mildly beneficial versus fixed DTT but still misses the
  optimum in all 8 contexts (SP would have been free).
- **Extrapolation above** support (1680) is **actively harmful**: DTT is optimal everywhere, fixed
  DTT incurs zero regret, and the selector assigns TECO10 to half the region for 0.14856.

Operationally: a tree extends its existing partition rather than abstaining, so beyond the upper
edge of training support its errors are systematic, not merely uninformed. Abstention and conformal
methods are **future work**, not part of this experiment.

---

## 9. MCDM interpretation

Full 0.05-spaced sweep, w_time from 0 to 1 (21 weightings):

- SP wins **all** low-demand contexts and DTT wins **all** high-demand contexts at **every** tested
  weight. **No breaks.**
- The sign pattern of m@1200 across the eight transition contexts is identical (`+-+-+++-`) at
  every profile.
- Winner counts are 11/10/3 (SP/DTT/TECO10) for w_time ≥ 0.25, shifting to 11/11/2 only at w_time=0.
- All 24 held-out selector decisions are unchanged across the range.

**Statement:** the regime transition is **robust to the tested preference weights**. The preference
layer defines "preferred" formally but does not discriminate between policies in this benchmark,
because the two criteria are aligned at ρ=0.982. This is a finding about the environment; adding
further MCDM methods to two near-collinear criteria would manufacture agreement, not validate it.

---

## 10. Literature positioning

**Known.** Per-instance algorithm selection maps instance features to algorithm performance and
selects accordingly. Demand-dependent benefit of dynamic routing is established: re-routing is
worthwhile mainly in rush hours and on long routes, congestion thresholds for triggering re-routing
have been studied, and load-aware strategies have been evaluated across density ranges. Routing
preference is known analytically to move a system between efficiency phases. Eco-routing under
congestion, and the gap between predictive accuracy and decision quality, are both established.

**Missing.** These treat a single adaptive mechanism (re-route or not), mostly on analytical or
macroscopic models, and evaluate physical outcomes rather than decision regret. The interaction
between *signal control* and *routing-policy preference* is not characterised; nor is the
*operating-domain boundary* of a learned routing-policy selector.

**What this experiment adds.** On one controlled microsimulation benchmark: (i) the demand bracket
within which the preference between two established pre-trip policies reverses; (ii) the observed
displacement of that bracket by signal regime, ≥480 veh/h and stable across seeds in 7/8 cells;
(iii) a regime decomposition showing all headroom lies at low and transition demand and none at
high demand; (iv) a held-out, decision-scored evaluation with an explicit above-support failure.

No priority claim. The audit was targeted, not systematic; we state differences from named studies.

---

## 11. Exact manuscript edits recommended

| # | Section | Edit | Type |
|---|---|---|---|
| 1 | §4.1 | **Fix "monotone in all eight cells" → 5 of 8**, describe the arterial dip | **correction** |
| 2 | §4.1 | Add mechanism paragraph (distance penalty fixed, congestion penalty grows) | addition |
| 3 | §4.1 | Add seed-dispersion-by-regime sentence | addition |
| 4 | §4.2 | Add headroom-by-regime decomposition; state zero headroom at high demand | addition |
| 5 | §4.2 | Add tree structure, feature importances, and the not-a-demand-classifier point | addition |
| 6 | §4.2 | Add prediction→ranking→decision decomposition | addition |
| 7 | §4.3 | Refine to below / gap / above support | refinement |
| 8 | §4.4 | Strengthen MCDM audit with the 21-point sweep result | refinement |
| 9 | §6 | Add the mechanism limitation (no route shares / signal exposure in outputs) | addition |

All edits use existing data. No new figure, table, experiment, method or scenario.
