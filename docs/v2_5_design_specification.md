# Protocol v2.5 — Terminal Ceiling-Scaled Signed-Curvature Redesign

## 1. Status and provenance

Protocol v2.5 is opened only after v2.4-F1 was frozen as failed.

Frozen v2.4 result:

`fc25c37 Freeze failed v2.4-F1 compensated curvature evaluation`

Earlier frozen failed development families remain immutable.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched when this specification is created.

v2.5 is an adaptive development redesign informed by frozen results obtained
on design seeds `21001–21005`.

It is explicitly the **terminal response-family redesign on these design
seeds**.

After v2.5-F1 is evaluated, no additional response architecture, coefficient,
ladder extension, criterion-specific modifier, or alternative-specific modifier
may be developed using `21001–21005`, regardless of whether v2.5 passes or
fails.

---

## 2. Frozen evidence motivating v2.5

### 2.1 v2.4-F1 outcome

At `eta=1.0`, v2.4-F1 passed:

- all D2.8 numerical gates;
- all frozen reachability gates;
- all response/invariance gates.

Only C1 and C6 remained below the complete scientific Layer-A criterion gates.

For C1:

- LRV ratio = `0.971647`;
- NSV ratio = `1.009923`.

For C6:

- LRV ratio = `0.641890`;
- NSV ratio = `0.915103`.

The weakest C6 reachability ratio remained above threshold:

- `h_D->C6` SRE ratio = `1.021066`.

### 2.2 Frozen C6 attenuation diagnosis

All six C6 capability classes are `I`, so every active C6 alternative has the
same semantic ceiling:

\[
u=0.20.
\]

Under v2.4-F1 at \(\eta=1\),

\[
g
=
u o
\left[
1+\frac{\theta}{u}v(1-o)
\right].
\]

Therefore the effective relative signed-curvature amplitude is

\[
\frac{\theta}{u}v.
\]

Across the five frozen design seeds and six C6 alternatives, the realized
\(\theta/u\) distribution was:

- minimum = `0.3109132641653613`;
- median = `0.6312483005262957`;
- maximum = `0.9489853111206733`.

The median attenuation factor `0.63125` is close to the frozen C6 LRV ratio
`0.64189`.

This supports a structural diagnosis: v2.4 retained signed curvature but scaled
it by the realized capability draw \(\theta\), so the full relative curvature
was attenuated after headroom compensation equalized the linear component
toward the common class ceiling.

---

## 3. Terminal v2.5 design principle

v2.5 removes the \(\theta/u\) attenuation without introducing a fitted
criterion-specific coefficient.

The signed curvature term is scaled by the already pre-existing semantic class
ceiling \(u_{aj}\), rather than by the realized capability draw
\(\theta_{aj}\).

The same formula is applied uniformly to every active C1–C7 pathway.

There is:

- no C6-specific parameter;
- no C1-specific parameter;
- no alternative-specific tuning;
- no second free response parameter.

The only candidate magnitude remains \(\eta\).

---

## 4. Frozen v2.5-F1 family

For each active C1–C7 pathway define

\[
u_{aj}
=
\begin{cases}
0.20, & M_{aj}=I,\\
0.40, & M_{aj}=D,
\end{cases}
\]

and

\[
h_{aj}=u_{aj}-\theta_{aj}\ge0.
\]

The terminal v2.5-F1 response is

\[
\boxed{
g_{asj}(\eta)
=
\theta_{aj}o_{sj}
+
\eta
\left[
h_{aj}o_{sj}
+
u_{aj}v_{aj}o_{sj}(1-o_{sj})
\right]
}
\]

for active C1–C7 pathways.

Equivalently,

\[
g_{asj}(\eta)
=
\left[
(1-\eta)\theta_{aj}
+
\eta u_{aj}
\right]o_{sj}
+
\eta u_{aj}v_{aj}o_{sj}(1-o_{sj}).
\]

Structural-zero pathways remain exactly

\[
g_{asj}=0.
\]

C8–C10 remain unchanged during candidate-family evaluation.

No criterion noise is used for structural selection:

\[
\sigma_x=0.
\]

---

## 5. Signed alternative-specific profile

For criterion \(j\) with \(m_j\) active alternatives define

\[
B_{m_j}
=
\left\{
-1,
-1+\frac{2}{m_j-1},
\ldots,
1
\right\}.
\]

The complete symmetric zero-mean grid is permuted across active alternatives
once per benchmark instance and criterion using

`SeedSequence([replication_seed, 2007, criterion_number])`.

RNG namespace `2007` is reserved exclusively for v2.5-F1.

The same realized \(v_{aj}\) profile is reused across:

- all candidate \(\eta\);
- every N;
- every rho;
- every target-noise condition;
- every oracle-interaction condition;
- every downstream method.

Structural-zero alternatives are excluded from the permutation.

No named ITS receives systematic preference by construction.

---

## 6. Analytic properties

For

\[
0\le\eta\le1,
\qquad
-1\le v\le1,
\qquad
0\le o\le1,
\qquad
0\le\theta\le u,
\]

the following properties hold.

### 6.1 Historical reference

At \(\eta=0\),

\[
g(o)=\theta o.
\]

### 6.2 Zero-at-zero

\[
g(0)=0.
\]

### 6.3 Full-opportunity response

At \(o=1\),

\[
g(1)
=
(1-\eta)\theta+\eta u
\le u.
\]

### 6.4 Monotonicity

The derivative is

\[
\frac{\partial g}{\partial o}
=
(1-\eta)\theta
+
\eta u
+
\eta u v(1-2o).
\]

Since

\[
v(1-2o)\ge-1,
\]

\[
\frac{\partial g}{\partial o}
\ge
(1-\eta)\theta
+
\eta u
-
\eta u
=
(1-\eta)\theta
\ge0.
\]

Thus the response is monotone non-decreasing over the complete admissible
domain.

### 6.5 Global semantic bound

Because

\[
g(0)=0,
\]

the response is monotone, and

\[
g(1)\le u,
\]

it follows that

\[
0\le g(o)\le u
\qquad
\forall o\in[0,1].
\]

No clipping is required at \(\sigma_x=0\).

### 6.6 Removal of class-ceiling attenuation

At \(\eta=1\),

\[
g(o)
=
u o
\left[
1+v(1-o)
\right].
\]

For alternatives sharing the same capability class ceiling \(u\), the common
scale \(u\) cancels under relative normalization. The relative
alternative-specific curvature is therefore governed by \(v\), not by
\((\theta/u)v\).

This is the specific structural defect targeted by v2.5.

### 6.7 Departure from the historical response

\[
\Delta g
=
\eta
\left[
h o
+
u v o(1-o)
\right].
\]

A conservative domain-wide absolute bound is

\[
|\Delta g|
\le
\eta
\left(
h+\frac{u}{4}
\right).
\]

Realized departures must be recorded for every design seed, criterion, and
candidate.

---

## 7. Frozen candidate ladder

The only v2.5-F1 candidate magnitudes are

\[
\eta
\in
\{
0.10,0.20,0.30,0.40,0.50,
0.60,0.70,0.80,0.90,1.00
\}.
\]

\[
\eta=0
\]

is the historical v2.1 reference only.

No interpolation, value above 1.0, second coefficient, criterion-specific
multiplier, alternative-specific multiplier, exponent, or second response
family may be added after results are observed.

---

## 8. Frozen evaluation scope

Candidate-family development uses only:

- design seeds `21001–21005`;
- `rho=0.4`;
- `sigma_x=0`;
- all 1000 FIT+WEIGHT contexts per design seed;
- C1–C7 candidate responses;
- unchanged C8–C10;
- unchanged oracle;
- `lambda=0.5` for descriptive Layer-B diagnostics.

Excluded:

- external TEST;
- structural-validation seeds `22001–22005`;
- primary seeds `11001–11030`.

The production technology-response generator remains unmodified during
candidate evaluation.

---

## 9. Frozen references reused without modification

v2.5-F1 reuses without recalibration:

- D2.7 \(T^{sci}_{LRV,j}\);
- D2.7 \(T^{sci}_{NSV,j}\);
- D2.7 \(T^{sci}_{SRE,kj}\);
- D2.8 \(T^{num}_{NS}\);
- D2.8 \(T^{num}_{LRV}\);
- D2.8 \(T^{num}_{NSV}\).

D2.7 Layer-B remains non-activated:

\[
T_R^{sci}=\mathrm{None}.
\]

Layer-B cannot select \(\eta\).

---

## 10. Frozen candidate gates

For every design seed and every C1–C7 criterion:

\[
NS_j>T^{num}_{NS},
\]

\[
LRV50_j>T^{num}_{LRV},
\]

\[
NSV_{j,vector}>T^{num}_{NSV}.
\]

For every criterion:

\[
\operatorname{median}_r LRV50_{j,r}(\eta)
\ge
T^{sci}_{LRV,j},
\]

and

\[
\operatorname{median}_r NSV_{j,vector,r}(\eta)
\ge
T^{sci}_{NSV,j}.
\]

For every declared latent pathway:

\[
\operatorname{median}_r SRE_{kj,r}(\eta)
\ge
T^{sci}_{SRE,kj}.
\]

Invariant gates:

- structural-zero pathways remain exactly zero;
- lower response bound holds;
- semantic class ceiling is never exceeded;
- analytic monotonicity holds;
- headroom remains non-negative;
- C8–C10 remain exactly unchanged.

---

## 11. Frozen selection rule

Define

\[
\eta^\star
=
\min
\left\{
\eta:
\text{all numerical, Layer-A, reachability, and invariant gates pass}
\right\}.
\]

Winner identities, ranking identities, modal winner, modal share, SHAP weights,
MOORA rankings, TOPSIS rankings, or any preferred ITS alternative are forbidden
selection inputs.

If no candidate passes, v2.5-F1 fails.

---

## 12. Terminal-development rule

v2.5-F1 is the final response-family development step using
`21001–21005`.

After candidate results are observed:

- the eta ladder cannot be extended;
- the formula cannot be modified;
- thresholds cannot be changed;
- no second v2.5 family may be created;
- no v2.6 response redesign may use `21001–21005`.

If v2.5-F1 fails, response-family development on this design cohort terminates.

If future redesign were ever scientifically necessary, it would require a
newly declared development cohort and a new protocol before examining that
cohort.

---

## 13. One-shot structural validation

Only if \(\eta^\star\) is selected and frozen may structural-validation seeds
`22001–22005` be inspected.

The selected \(\eta^\star\) is evaluated exactly once.

Validation passes only if:

1. every C1–C7 criterion exceeds the D2.8 numerical thresholds on every
   validation seed;
2. validation-seed median LRV50 for every criterion meets its frozen D2.7
   reference;
3. validation-seed median vector NSV for every criterion meets its frozen D2.7
   reference;
4. validation-seed median SRE for every declared pathway meets its frozen D2.7
   reference;
5. all structural-zero, lower-bound, semantic-ceiling, monotonicity, headroom,
   and C8–C10 invariants hold.

If one-shot validation fails, the architecture is rejected.

The design ladder is not revisited.

---

## 14. Primary-seed firewall

Primary seeds `11001–11030` and external TEST remain inaccessible until:

1. v2.5-F1 candidate selection is frozen;
2. one-shot structural validation passes;
3. the final Pilot-A decision-sensitivity rule is separately frozen;
4. the selected generator is promoted into the production generator through
   an audited commit;
5. alpha-dispersion mapping is computed and frozen under the final generator.

No primary result may revise the response architecture.

---

## 15. Interpretation rule

v2.5 remains development evidence because its architecture was informed by
earlier results on the same design-seed family.

Passing design-seed gates does not constitute independent validation.

Independent structural evidence begins only with untouched seeds
`22001–22005`.

Primary inferential evidence begins later with untouched seeds
`11001–11030` and the external TEST pool.

The manuscript must explicitly disclose the sequence of frozen development
families and the terminal-development rule.

## 16. Frozen terminal v2.5-F1 outcome

v2.5-F1 was executed from Git commit
`869c749c0160fc454f267b4a5b073edfa18e07df` after the terminal protocol and
evaluator were committed.

All ten candidates passed D2.8 numerical gates and all frozen response
invariants.

The scientific Layer-A and latent-pathway reachability gates did not overlap:

- eta<=0.6 retained reachability but failed at least C3 and C6 Layer-A;
- eta=0.7–0.8 failed only C6 Layer-A and also failed h_D->C6 and h_E->C6
  reachability;
- eta=0.9–1.0 passed all Layer-A criteria but still failed h_D->C6 and
  h_E->C6 reachability.

Therefore:

`selected_eta = null`

and terminal v2.5-F1 is **FAILED / CLOSED**.

No external TEST context, structural-validation seed, or primary seed was
used. Layer-B was not used for selection and the production generator was not
modified.

Per the frozen terminal-development rule, no further response-family redesign,
criterion-specific modifier, coefficient, or ladder extension may be developed
using design seeds `21001–21005`.

Future redesign, if scientifically necessary, requires a newly declared
development cohort and a new protocol before that cohort is inspected.
