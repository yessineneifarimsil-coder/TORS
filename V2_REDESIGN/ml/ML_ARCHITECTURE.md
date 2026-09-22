# ML Architecture — mechanism-informed advantage model

**Status: specification. No V2 model has been trained and no accuracy, regret or headroom figure
exists.**

---

## 1. What the model predicts, and why it is not raw outcomes

V1 predicted raw policy outcomes (travel time, CO₂) and then applied a decision rule. That works,
but it spends model capacity on the part of the signal the decision does not use — the large common
component of travel time shared by every policy in a context.

V2 predicts **advantage relative to a baseline**:

```
Δ_a(x) = C_SBS(x) − C_a(x)
```

`Δ_a > 0` means policy `a` is expected to beat the baseline in context `x`; `Δ_a < 0` means it is
worse. The quantity is centred on zero at the decision boundary, which is exactly where accuracy
matters, and it removes the context-level common mode.

**Leakage control specific to this target.** `C_SBS` must be the single-best-solver **determined on
training folds only**, and the advantage labels for a fold must be constructed without reference to
that fold's outcomes. Getting this wrong would make the target itself leak; it is the first item on
the Phase 5 leakage checklist.

---

## 2. Model class

**Gradient-boosted decision trees** (e.g. LightGBM), one regressor per policy, or a multi-output
formulation.

Justification, stated plainly: the feature space is low-dimensional, tabular, heterogeneous and
interaction-heavy, with a few hundred to a few thousand context-level instances. That is the regime
where boosted trees are the appropriate default. **This is not a claim of novelty** — the model
class is standard, and its role is to be a strong, honest tabular learner.

**Deliberately excluded:**

| Excluded | Why |
|---|---|
| Graph neural networks | The instance is a scenario configuration, not a graph-structured prediction task. A GNN would be sophistication without a matching problem structure. |
| Reinforcement learning | There is no sequential control problem here. One policy is chosen per episode; there is no within-episode action sequence to optimise. |
| Contextual bandits | The simulator gives full-information feedback on every policy in every context. Bandit machinery solves a partial-feedback problem we do not have. |
| Deep tabular models | No evidence they would beat GBDT at this sample size; they would weaken interpretability without a compensating gain. |

If GBDT does not beat the mechanistic rule, adding a more complex model is unlikely to be the
answer, and the honest conclusion is that the decision is mechanistically simple.

---

## 3. Features — mechanistic and dimensionless

All features are computed from **design variables and static network geometry only**. None uses a
realised outcome.

| Feature | Form | Mechanism it encodes |
|---|---|---|
| Degree of saturation, static path | `demand / declared capacity` | When P1 should fail |
| Network cut v/c | demand across the min-cut / cut capacity | Global tightness |
| Alternative-capacity share | `cap(alt) / Σ cap(paths)` | Whether P3 has room to balance |
| Route-overlap index | shared link length / total path length | Whether diversion actually relieves anything |
| Guidance penetration rate | fraction, dimensionless | Herding potential for P2 |
| Information-lag ratio | `Δ / T_freeflow(OD)` | Staleness relative to trip length |
| Incident-on-static-path × severity | indicator × severity | Non-recurrent shock to P1/P2 |
| Incident announced | binary | Whether a policy could have known |
| Signal green ratio | `g/C` | Effective corridor capacity |
| Effective capacity ratio (alt ÷ static) | after applying `g/C` | Capacity asymmetry actually available |

Two deliberate choices:

- **Continuous physical encodings replace categorical labels.** V1 used a binary
  `signal = balanced/arterial`; V2 uses `g/C` so the model sees the physical quantity, and so that
  an unseen signal configuration can be *interpolated* rather than treated as a new category.
- **Ratios rather than levels.** Dimensionless features transfer across networks of different size,
  which matters for the topology OOD split.

**Every feature is audited for leakage before Phase 5 proceeds**, and the audit is a written
artefact, not an assertion.

---

## 4. Decision rule

```
context x
   │
   ├─► GBDT ──► Δ̂_a(x) for every policy a
   │
   ├─► split-conformal interval ──► lower bound  L_a(x)  on Δ_a(x)
   │
   ├─► support gate ──► in-support?  (see robustness/)
   │
   ▼
 act on  a* = argmax_a Δ̂_a(x)   ONLY IF   in-support  AND  L_{a*}(x) > 0
 otherwise ABSTAIN → best fixed policy from TRAINING data
```

The condition `L_{a*}(x) > 0` is the operationally meaningful one: it says the chosen policy's
advantage over the baseline is positive *with confidence*, not merely in point estimate. Abstention
is a first-class outcome, not a failure.

---

## 5. Baseline ladder

| | Baseline | Purpose |
|---|---|---|
| B0 | Best fixed policy (from training folds) | Can adaptation beat doing nothing? |
| B1 | **Mechanistic threshold rule** | **The real test.** A 2–3 variable rule on saturation and penetration. |
| B2 | Standard cost-sensitive algorithm-selection model | Does the domain framing add anything over off-the-shelf? |
| B3 | V1-style simple selector (shallow tree on raw outcomes) | Does the advantage target help? |
| B4 | Proposed mechanism-informed GBDT | — |
| B5 | B4 + support/confidence gates and abstention | Does selectivity help under shift? |
| — | Cross-fitted hindsight best (VBS) | Upper reference. **Not deployable.** |

**The headline scientific test is B4 vs B1**, not B4 vs B0. V1 already showed that beating the best
fixed policy in-support is achievable with a depth-1 split; that bar is too low to be interesting.

If B4 does not beat B1, the finding is that the policy-selection structure in this environment is
mechanistically simple. That is a legitimate and reportable result, and the design must present it
as such rather than escalating model complexity until something wins.

---

## 6. Metrics

**Primary:** held-out mean regret; fraction of the VBS−SBS gap closed; CVaR₉₀ regret (tail risk of
bad selections); non-inferiority to the best fixed policy; per-shift-type performance.

**Secondary:** selection accuracy; ε-optimal selection rate; pairwise ranking accuracy; seed
stability; calibration; conformal coverage; risk–coverage curve; abstention rate; realised travel
time, P95 and CO₂; background-traffic effects; training and inference cost.

All statistical procedures operate at the **context** level. Vehicles are not instances.
Replications of a context are not independent observations.
