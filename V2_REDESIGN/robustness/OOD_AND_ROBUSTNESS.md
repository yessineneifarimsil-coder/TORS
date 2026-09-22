# Robustness and OOD — support gate, confidence gate, abstention

## Why this component exists — and it is not a fashion

V1 produced the strongest possible internal justification for it. Holding out an entire demand
level, the V1 selector was **worse than the fixed policy it replaced**: it extrapolated its learned
partition into a regime it had never seen, and could not decline. A selector that cannot say "I do
not know" is not merely uninformative outside its support — it is actively harmful.

That is the motivation. It comes from our own completed evidence, not from a methodological trend.

---

## Two gates

```
        new context x
              │
    ┌─────────▼──────────┐
    │ GATE 1 — SUPPORT   │   is x inside the region the model was fitted on?
    └─────────┬──────────┘
         pass │ fail ─────────────────┐
    ┌─────────▼──────────┐            │
    │ GATE 2 — CONFIDENCE│            │
    │ L_{a*}(x) > 0 ?    │            │
    └─────────┬──────────┘            │
         pass │ fail ─────────────────┤
              ▼                       ▼
         ACT on a*              ABSTAIN → best fixed policy
                                (selected from TRAINING data only)
```

### Gate 1 — support

Estimate distance from `x` to the training feature support. Candidate estimators: k-nearest-neighbour
distance in the standardised feature space; Mahalanobis distance; or a density/one-class estimator.
Choose one in Phase 0 with a citation, calibrate its threshold on a validation split, and **do not
tune it on the test set**.

The support gate is the only component that can catch *extrapolation*, because it looks at the
inputs rather than the model's own confidence.

### Gate 2 — confidence

**Split conformal prediction** on the advantage `Δ_a(x)`, giving a lower bound `L_a(x)`. Act only if
the best policy's lower bound is positive.

**Stated limitation, prominently.** Split conformal coverage holds under **exchangeability** between
calibration and test data. Under covariate shift that assumption fails, so conformal intervals
computed on in-distribution calibration data **do not certify coverage on OOD contexts**. Weighted
conformal variants exist but require likelihood ratios we will not have.

Therefore: **conformal prediction is a calibrated confidence gate in-distribution and a heuristic
out-of-distribution.** The support gate, not the conformal gate, is what is claimed to handle
extrapolation. This distinction must survive into the paper; conflating them would be a
methodological error of exactly the kind V1's audit process was designed to catch.

---

## Shift taxonomy — kept distinct

| Term | Meaning here | Which gate is supposed to catch it |
|---|---|---|
| **Interpolation** | New point inside the convex region of training factor levels | Neither; model should simply work |
| **Extrapolation** | Factor value beyond the training range | Support gate |
| **Covariate shift** | `P(x)` changes, `P(y\|x)` stable | Support gate (partially) |
| **Concept shift** | `P(y\|x)` itself changes | **Neither gate detects this.** State it. |
| **Domain shift** | New network topology | Support gate only if features are network-transferable |

Concept shift is not detectable by either gate. If the relationship between context and policy
advantage changes, a confident and in-support prediction can still be wrong. This is a genuine
limitation of the architecture and must be written as one.

---

## Evaluation of the selective selector

Report, per shift type and never aggregated into one number:

- **Risk–coverage curve** — regret as a function of the fraction of contexts acted on.
- **Abstention rate** and what abstention cost (regret of the fallback where the model would have
  been right).
- **Conformal empirical coverage**, in-distribution and under each shift, with the exchangeability
  caveat attached to the OOD numbers.
- **Harm rate** — fraction of acted-on contexts where the selector was worse than the fixed policy.
  This is the quantity V1's extrapolation failure would have shown, and it is arguably the single
  most informative robustness metric.
- **CVaR₉₀ regret** — tail behaviour, not just the mean.

A selector that achieves lower mean regret while increasing the harm rate has not improved.

---

## What would count as success, and what would not

**Success:** the gated selector is non-inferior to the best fixed policy under every shift type, and
strictly better in-support — i.e. it converts V1's harmful extrapolation into a safe abstention.

**Not success:** lower mean regret overall, obtained by acting confidently on shifted contexts and
being lucky. The harm rate and the per-shift breakdown exist to prevent that being reported as a win.
