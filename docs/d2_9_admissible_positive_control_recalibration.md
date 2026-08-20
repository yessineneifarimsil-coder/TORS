# D2.9 — Admissible Positive-Control Recalibration

## 1. Status

D2.9 is a methodological correction opened after the frozen D2.7 positive
control was audited against the admissibility constraints imposed on candidate
technology-response generators.

Frozen v3.0 development state:

`519009d Freeze failed v3.0-F1 monotone headroom-shape evaluation`

D2.7 and all subsequent candidate-family results remain immutable historical
artifacts.

D2.9 does **not** rewrite or delete D2.7. It supersedes D2.7 only for future
scientific-gate calibration.

D2.8 numerical-null thresholds remain unchanged because the D2.8 null
calibration is independent of the D2.7 positive-control response family.

---

## 2. Triggering audit finding

The frozen D2.7 positive-control formula was

\[
g^{PC}(o)
=
[\theta+\delta c(2o-1)]o,
\qquad
\delta=0.05,
\]

with contrast grid

\[
c\in\{-1,-0.6,-0.2,0.2,0.6,1\}
\]

cycled across the six ITS alternatives.

A read-only admissibility audit over the five original D2.7 design seeds and
all six cyclic rotations found:

- total active rows: `1200`;
- lower-bound violations: `0`;
- semantic-ceiling violations: `95`;
- monotonicity violations: `115`;
- rows violating at least one of these invariants: `210`.

Thus `17.5%` of active positive-control rows violated at least one admissibility
constraint.

The semantic-ceiling and monotonicity violations were disjoint in this audit
(`95 + 115 = 210`).

For C6 specifically:

- semantic-ceiling violations: `16 / 180`;
- monotonicity violations: `28 / 180`.

Across the six rotations, every C6 seed-alternative pair receives both extreme
contrast signs. Therefore every realized C6 capability draw with
\(\theta<0.15\) encounters a monotonicity-violating `c=-1` rotation, whereas
every draw with \(\theta>0.15\) encounters a ceiling-violating `c=+1`
rotation.

The D2.7 control is therefore not contained in the response class against
which later scientific gates were applied.

---

## 3. Consequence for interpretation

The D2.7 Layer-A and SRE references remain historically reproducible, but they
are no longer treated as admissible positive-control scientific thresholds for
future generator adjudication.

This does **not** imply that the old thresholds should be numerically reduced
or manually adjusted.

Instead, a new positive control must:

1. create known alternative-context non-separability;
2. preserve exact structural zeros;
3. preserve the response lower bound;
4. preserve semantic class ceilings;
5. preserve monotonic non-decreasing opportunity response;
6. use no candidate-family result, winner identity, or preferred ITS as a
   calibration target.

The corrected control is frozen before its new calibration seeds are
generated.

---

## 4. Fresh calibration and reserve cohorts

The only D2.9 calibration cohort is:

`25001, 25002, 25003, 25004, 25005`.

These seeds were unused and unreferenced in tracked scientific material when
this specification was created.

The separate block

`26001, 26002, 26003, 26004, 26005`

is reserved and remains untouched.

Excluded from D2.9 calibration:

- old D2.7 / v2.x development seeds `21001–21005`;
- structural-validation seeds `22001–22005`;
- v3.0 development seeds `23001–23005`;
- reserved v3.x block `24001–24005`;
- primary seeds `11001–11030`;
- external TEST.

---

## 5. Corrected admissible positive control

For every active C1–C7 pathway define

\[
\boxed{
g^{PC+}_{asj}(o)
=
\theta_{aj}o
+
\delta c_a o(1-o)
}
\]

with

\[
\delta=0.05
\]

and the same complete symmetric contrast grid

\[
c_a
\in
\{-1,-0.6,-0.2,0.2,0.6,1\}.
\]

The six cyclic rotations are retained so that every alternative receives every
contrast coefficient exactly once per benchmark world.

Structural-zero pathways remain exactly zero.

C8–C10 remain unchanged.

No criterion noise is used:

\[
\sigma_x=0.
\]

---

## 6. Why delta = 0.05 is frozen

For the corrected quadratic control,

\[
\frac{\partial g^{PC+}}{\partial o}
=
\theta+\delta c(1-2o).
\]

Because

\[
|c|\le1,
\]

the global derivative lower bound is

\[
\frac{\partial g^{PC+}}{\partial o}
\ge
\theta-\delta.
\]

The active capability parameter support has

\[
\theta_{\min}=0.05.
\]

Therefore choosing

\[
\delta=0.05
\]

gives

\[
\frac{\partial g^{PC+}}{\partial o}
\ge0
\]

for the complete active parameter support.

Thus `delta=0.05` is the largest uniform signed quadratic coefficient of this
form that is guaranteed to preserve monotonicity for every active pathway.

It is fixed from the pre-existing capability support and is not tuned to any
candidate-family result.

---

## 7. Analytic admissibility

### 7.1 Endpoints

\[
g^{PC+}(0)=0.
\]

At full opportunity,

\[
g^{PC+}(1)=\theta.
\]

Because every active capability draw satisfies

\[
0<\theta\le u,
\]

the semantic class ceiling is preserved at the upper endpoint.

### 7.2 Monotonicity

As shown above,

\[
(g^{PC+})'(o)
=
\theta+\delta c(1-2o)
\ge
\theta-\delta
\ge0.
\]

Therefore the response is monotone non-decreasing over

\[
o\in[0,1].
\]

### 7.3 Global response bounds

Because the response is monotone with

\[
g^{PC+}(0)=0
\]

and

\[
g^{PC+}(1)=\theta\le u,
\]

it follows that

\[
0\le g^{PC+}(o)\le u
\]

throughout the complete domain.

No clipping is required.

### 7.4 Maximum response departure

Relative to the historical response \(g^0=\theta o\),

\[
\Delta g
=
\delta c o(1-o).
\]

Since

\[
\max_{o\in[0,1]}o(1-o)=\frac14,
\]

the maximum absolute response departure is

\[
\boxed{
|\Delta g|_{\max}
=
\frac{\delta}{4}
=
0.0125
}
\]

for \(|c|=1\).

The historical D2.7 statement that a `0.05` coefficient implied a `0.05`
maximum response departure is therefore not carried forward.

D2.9 treats `0.05` as the frozen admissible curvature coefficient and
`0.0125` as its actual maximum response departure.

---

## 8. Frozen D2.9 calibration procedure

For each calibration seed in `25001–25005`:

1. generate the standard 1000 FIT+WEIGHT contexts at `rho=0.4`;
2. generate the standard capability parameters;
3. set `sigma_x=0`;
4. apply all six cyclic contrast rotations to the corrected positive control;
5. verify exact structural zeros;
6. verify response lower bounds;
7. verify semantic class ceilings;
8. verify monotonicity analytically and numerically;
9. compute the same D2.7 Layer-A metrics:
   - LRV50;
   - vector NSV;
10. compute the same model-consistent SRE pathways;
11. keep Layer-B descriptive only.

No candidate response family is evaluated during D2.9 calibration.

---

## 9. Frozen aggregation rule

D2.9 preserves the D2.7 aggregation semantics.

For every criterion \(j\), define:

\[
T^{sci+}_{LRV,j}
=
\operatorname{median}_{r\in\{25001,\ldots,25005\}}
LRV50^{PC+}_{j,r},
\]

and

\[
T^{sci+}_{NSV,j}
=
\operatorname{median}_{r\in\{25001,\ldots,25005\}}
NSV^{PC+}_{j,r}.
\]

For every declared latent pathway \((k,j)\),

\[
T^{sci+}_{SRE,kj}
=
\operatorname{median}_{r\in\{25001,\ldots,25005\}}
SRE^{PC+}_{kj,r}.
\]

Layer-B remains non-activated and cannot define a selection threshold.

---

## 10. D2.8 numerical thresholds remain frozen

The following D2.8 thresholds are not recalibrated:

\[
T^{num}_{NS}=10^{-12},
\]

\[
T^{num}_{LRV}=10^{-10},
\]

\[
T^{num}_{NSV}
=
3.2506084454037334\times10^{-8}.
\]

D2.9 changes only the scientific positive-control references.

---

## 11. No candidate tuning during recalibration

Before D2.9 thresholds are frozen, it is forbidden to:

- modify any frozen v2.x or v3.0 response family;
- design a new response family;
- use `24001–24005` or `26001–26005`;
- inspect structural-validation seeds `22001–22005`;
- inspect primary seeds `11001–11030`;
- inspect external TEST;
- choose D2.9 thresholds to make a particular historical candidate pass.

The corrected thresholds are purely outputs of the frozen admissible positive
control.

---

## 12. Downstream re-adjudication rule

After D2.9 thresholds are frozen, historical candidate results may be
re-adjudicated **without modifying or rerunning their response generators**.

The re-adjudication must use:

- the already frozen candidate artifacts;
- unchanged D2.8 numerical thresholds;
- new frozen D2.9 scientific references;
- each family's already frozen response invariants;
- each family's original within-family minimum-parameter selection rule.

This is a threshold-correction audit, not a new candidate search.

Any architecture promoted for independent structural validation remains
development-selected and must still pass a one-shot evaluation on untouched
seeds `22001–22005`.

---

## 13. Interpretation and reporting

The manuscript must distinguish:

1. historical D2.7 calibration, which is reproducible but was later found to
   violate admissibility constraints;
2. D2.9 corrected admissible calibration;
3. historical candidate-family evaluations under the old references;
4. any subsequent re-adjudication under D2.9;
5. independent one-shot structural validation.

The correction must be reported transparently as a methodological
self-audit, not hidden as routine retuning.

## 14. Frozen D2.9 calibration outcome

D2.9 was executed from Git commit
`3463d5d294798e8d2770d6c95ee63ecf01230dca` after both the protocol and
evaluator had been committed.

The calibration used only fresh seeds `25001–25005`.

All 1260 admissibility diagnostic rows passed lower-bound, semantic-ceiling,
monotonicity, and structural-zero checks. The minimum analytic derivative
floor was `0.0`, consistent with the frozen non-decreasing monotonicity
requirement. The maximum absolute response departure was exactly `0.0125`.

The calibration was reproduced from the same execution commit and all nine
output artifacts were byte-for-byte identical.

The resulting Layer-A and SRE references are therefore frozen for downstream
scientific re-adjudication. Layer-B remains descriptive only
(`activated=false`, `T_R_sci=null`).

The D2.8 numerical-null thresholds remain unchanged.

No external TEST, structural-validation seed, primary seed, old D2.7 design
seed, v3.0 development seed, or D2.9 reserved seed was used.

Historical D2.7 thresholds remain preserved for provenance but are superseded
for future scientific-gate adjudication.
