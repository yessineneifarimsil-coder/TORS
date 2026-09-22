# Decisions Requiring Supervisor Approval

Twelve decisions. The first four are blocking — nothing downstream can be specified until they are
settled. My recommendation is given for each, with the reasoning, so the discussion can be about
substance rather than options.

---

## BLOCKING

### D1 — Policy portfolio
**Question.** Adopt P1 static / P2 reactive DTT / P3 capacity-aware load balancing / P4
reliability-aware?

**Recommendation: yes, with P3 reformulated.** The brief's `min_x max_e ρ_e(x)` is a flow-assignment
program over a path distribution, not a per-vehicle policy, and SUMO routes vehicles individually.
Adopting it would make P3 a different kind of object from P1/P2/P4 and add a solver dependency with
no precedent as deployed guidance. Use the published load-balancing k-shortest-path family
(Pan et al. 2013) instead, which keeps the intent and is per-vehicle.

**Alternative if rejected:** drop to three policies (P1, P2, P4). Do not keep a P3 we cannot
formulate from primary literature.

### D2 — Eco-routing / CO₂
**Question.** Retain CO₂ as a criterion and eco-routing as a policy?

**Recommendation: exclude both from the core, test decoupling in the screen.** V1 established
ρ(time, CO₂) = 0.982 and ECO outcome-identical to SP in 21/24 contexts *in that network*. Whether
the V2 network decouples them is an empirical question; measure it in the screen and re-admit CO₂
only if it decouples. Carrying a redundant criterion forward would repeat V1's error.

### D3 — Primary decision objective
**Question.** System-level mean journey time over all traffic, with Pareto screening, replacing the
additive-weight layer?

**Recommendation: yes.** It is weight-free, it is what an operator acts on, and it charges policies
for externalities imposed on background traffic — which V1 showed can be substantial. Generalised
cost enters only as a sensitivity, and only once VOT/VOR/carbon values are sourced (L2, L3).

### D4 — Network family
**Question.** Grid + bypass as the primary family, parallel-corridor reserved for the topology OOD
split?

**Recommendation: yes.** A plain grid risks reproducing V1's symmetry problem. The bypass supplies
the unequal-capacity parallel alternative that P3 requires in order to mean anything. **Freeze before
Phase 4.**

---

## IMPORTANT

### D5 — Factor set
Six core factors: demand, penetration, information lag, incident state, alternative-capacity ratio,
signal green ratio. Defer OD count and incident duration; reserve topology for OOD.
**Recommendation: yes.** Penetration and incident are the two that V1 structurally lacked and
without which P2 and P4 have no distinct failure mode.

### D6 — Screening gate thresholds
G1 ≥3 policies win · G2 ≥25% non-singleton Pareto · G3 ≤50% pairwise identity · G4 multi-factor
winner map. **Recommendation: approve now, in writing, before any run.** Their value depends
entirely on being fixed in advance.

### D7 — Replication budget
≥10 paired seeds in the screen, ≥5 in the main study, common random numbers mandatory.
**Recommendation: yes.** V1's three seeds left 4/24 winners unstable; a screen at that noise level
could not distinguish separation from noise.

### D8 — ML target and model class
GBDT predicting advantage `Δ_a(x) = C_SBS(x) − C_a(x)`, SBS from training folds only.
**Recommendation: yes.** Explicitly reject GNN/RL/bandit framings — none matches this problem
structure.

### D9 — Headline scientific test
**B4 (GBDT) vs B1 (mechanistic rule)**, not B4 vs B0 (best fixed).
**Recommendation: yes — and accept in advance that B1 may win.** V1 showed a depth-1 split captures
53% of available headroom, so "beats the best fixed policy" is too low a bar to be interesting. If
the rule wins, the finding is that the decision is mechanistically simple.

---

## SECONDARY

### D10 — Reliability formulation
`μ + λσ` with λ from a published VOR/VOT ratio, or a P95 form. **Recommendation: decide in Phase 1
from the unit tests and the stability of the dispersion estimate — not from results.**

### D11 — Conformal claim strength
**Recommendation: state plainly that split conformal guarantees coverage only under exchangeability,
so it is a calibrated gate in-distribution and a heuristic out-of-distribution.** The support gate,
not the conformal gate, is what is claimed to handle extrapolation. Overclaiming here would be
exactly the kind of error V1's audit process existed to catch.

### D12 — Publication strategy
V1 stands as submitted. V2 is a separate study with separate data. **Recommendation: never pool
results and never restate V1 numbers as V2 evidence.** If the screen fails, the negative result on
portfolio design is itself publishable.

---

## Summary sheet for the meeting

| # | Decision | Recommendation |
|---|---|---|
| D1 | Portfolio | 4 policies, **P3 reformulated** to published per-vehicle load balancing |
| D2 | Eco-routing / CO₂ | Exclude from core; test decoupling in the screen |
| D3 | Objective | System mean journey time + Pareto; no arbitrary weights |
| D4 | Network | Grid + bypass; freeze before Phase 4 |
| D5 | Factors | 6 core; penetration and incident are essential |
| D6 | Gates | Approve thresholds in writing now |
| D7 | Seeds | ≥10 screen / ≥5 main, CRN mandatory |
| D8 | ML | GBDT on advantage; no GNN/RL |
| D9 | Headline test | **vs mechanistic rule**, and the rule may win |
| D10 | Reliability form | Decide in Phase 1 from unit tests |
| D11 | Conformal | In-distribution gate; heuristic OOD |
| D12 | Versioning | V1 and V2 never pooled |
