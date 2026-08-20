# Protocol v2.3 — Headroom-Augmented Response Redesign

## 1. Status and provenance

Protocol v2.3 is opened only after v2.2 D4-F1 was frozen as failed.

Frozen v2.2 parent:

`37c8f31 Freeze failed v2.2 D4-F1 candidate evaluation`

D4-F1 is not modified, extended, or retuned in v2.3.

The v2.2 gap audit is used only to motivate the new architecture. It does not
alter any D2.7 or D2.8 threshold.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched when this specification is created.

---

## 2. Motivation from the frozen v2.2 failure

The frozen D4-F1 audit showed two opposing trends.

At `kappa=0.1`:

- worst scientific Layer-A ratio = `0.1012`;
- worst reachability ratio = `0.9687`.

At `kappa=0.9`:

- all C1–C7 Layer-A gates pass;
- worst reachability ratio = `0.7633`.

At `kappa=1.0`:

- worst Layer-A ratio = `1.1388`;
- worst reachability ratio = `0.7481`.

Thus D4-F1 can generate sufficient alternative–context non-separability, but
its endpoint-preserving curvature progressively weakens relative latent
reachability.

The next architecture must therefore decouple:

1. alternative-specific non-separability; and
2. latent-driver sensitivity.

---

## 3. Impossibility constraint motivating the redesign

The historical active response is

\[
g_0(o)=\theta o,
\qquad
g_0(0)=0,
\qquad
g_0(1)=\theta.
\]

Any differentiable alternative response satisfying simultaneously

\[
g(0)=0,
\qquad
g(1)=\theta,
\qquad
g'(o)\ge\theta
\quad
\forall o\in[0,1]
\]

must satisfy

\[
\int_0^1 g'(o)\,do
=
g(1)-g(0)
=
\theta.
\]

Because the integrand is everywhere at least \(\theta\), equality of the
integral implies

\[
g'(o)=\theta
\]

almost everywhere, hence

\[
g(o)=\theta o.
\]

Therefore no nontrivial nonlinear redesign can both preserve the historical
endpoint \(g(1)=\theta\) and guarantee a slope everywhere at least as large as
the historical linear slope.

Protocol v2.3 relaxes only the realized endpoint \(\theta\), while preserving
the pre-specified semantic class ceiling.

---

## 4. Frozen v2.3-F1 family: headroom-augmented response

For active C1–C7 pathways define the class ceiling

\[
u_{aj}
=
\begin{cases}
0.20, & M_{aj}=I,\\
0.40, & M_{aj}=D.
\end{cases}
\]

The realized capability parameter remains the historical draw

\[
\theta_{aj}
\sim
U(0.05,0.20)
\quad\text{for I},
\]

or

\[
\theta_{aj}
\sim
U(0.20,0.40)
\quad\text{for D}.
\]

Define available semantic headroom

\[
h_{aj}=u_{aj}-\theta_{aj}\ge0.
\]

For candidate magnitude \(\eta\), the v2.3-F1 response is

\[
\boxed{
g_{asj}(\eta)
=
\theta_{aj}o_{sj}
+
\eta h_{aj}
\left[
\tau o_{sj}
+
(1-\tau)c_{aj}o_{sj}^{2}
\right]
}
\]

with the fixed split

\[
\tau=0.5.
\]

Structural-zero pathways remain exactly

\[
g_{asj}=0.
\]

C8–C10 remain unchanged during the first v2.3-F1 structural evaluation.

No criterion noise is used for structural selection:

\[
\sigma_x=0.
\]

---

## 5. Alternative-specific headroom coefficients

For criterion \(j\) with \(m_j\) active alternatives define

\[
C_{m_j}
=
\left\{
0,
\frac{1}{m_j-1},
\frac{2}{m_j-1},
\ldots,
1
\right\}.
\]

The complete grid is randomly permuted across active alternatives once per
benchmark instance and criterion using

`SeedSequence([replication_seed, 2005, criterion_number])`.

RNG namespace `2005` is reserved exclusively for the v2.3-F1 headroom profile.

The same realized \(c_{aj}\) profile is reused across:

- all candidate \(\eta\);
- every N;
- every rho;
- every target-noise condition;
- every oracle-interaction condition;
- every downstream method.

Structural-zero alternatives are excluded from the coefficient permutation.

Because every active criterion/world uses the full coefficient grid exactly
once, no named ITS is assigned a systematically favorable coefficient by
construction.

---

## 6. Analytic properties

For \(0\le\eta\le1\), \(0\le c_{aj}\le1\), and \(0\le o\le1\):

### 6.1 Zero-at-zero

\[
g(0)=0.
\]

### 6.2 Semantic upper bound

At full opportunity,

\[
g(1)
=
\theta
+
\eta h
[
\tau+(1-\tau)c
].
\]

Since

\[
\tau+(1-\tau)c\le1,
\]

\[
g(1)\le\theta+\eta h\le\theta+h=u.
\]

Because the response is monotone, this also gives

\[
0\le g(o)\le u.
\]

Thus no clipping is required at \(\sigma_x=0\).

### 6.3 No loss of local opportunity sensitivity

\[
\frac{\partial g}{\partial o}
=
\theta
+
\eta h
[
\tau+2(1-\tau)co
].
\]

Therefore

\[
\frac{\partial g}{\partial o}
\ge
\theta+\eta h\tau
\ge
\theta.
\]

Unlike D4-F1, v2.3-F1 cannot reduce the local slope below the historical
multiplicative baseline for any active alternative.

### 6.4 Convex context differentiation

\[
\frac{\partial^2 g}{\partial o^2}
=
2\eta h(1-\tau)c
\ge0.
\]

Alternative-specific \(c\) values therefore create context-dependent relative
responses while preserving monotonicity and the class ceiling.

### 6.5 Departure from the historical response

\[
\Delta g
=
\eta h
[
\tau o+(1-\tau)co^2
].
\]

The domain-wide bound is

\[
0\le\Delta g\le\eta h.
\]

Since the largest possible headroom is `0.20` for a direct pathway and `0.15`
for an indirect pathway,

\[
\Delta g_{\max}
\le0.20\eta.
\]

Realized departures must be recorded per seed, criterion, and candidate.

---

## 7. Frozen candidate ladder

The only v2.3-F1 candidate magnitudes are

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

No interpolation, intermediate candidate, value above 1.0, alternative tau,
second exponent, or second response family may be introduced after candidate
results are inspected inside protocol v2.3.

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
- `lambda=0.5` for Layer-B diagnostics.

Excluded:

- external TEST;
- structural-validation seeds `22001–22005`;
- primary seeds `11001–11030`.

The production technology-response generator is not modified during candidate
evaluation.

---

## 9. Frozen references reused from v2.2

v2.3-F1 reuses without modification:

- D2.7 criterion-specific \(T^{sci}_{LRV,j}\);
- D2.7 criterion-specific \(T^{sci}_{NSV,j}\);
- D2.7 pathway-specific \(T^{sci}_{SRE,kj}\);
- D2.8 \(T^{num}_{NS}\);
- D2.8 \(T^{num}_{LRV}\);
- D2.8 \(T^{num}_{NSV}\).

No new scientific threshold is calibrated from v2.3 candidates.

D2.7 Layer-B remains non-activated:

\[
T_R^{sci}=\text{None}.
\]

Layer-B diagnostics therefore cannot select \(\eta\).

---

## 10. Frozen candidate gates

For every C1–C7 criterion and every design seed:

\[
NS_j>T^{num}_{NS},
\]

\[
LRV50_j>T^{num}_{LRV},
\]

and

\[
NSV_{j,vector}>T^{num}_{NSV}.
\]

The design-seed medians must satisfy, for every criterion,

\[
\operatorname{median}_r LRV50_{j,r}(\eta)
\ge
T^{sci}_{LRV,j},
\]

\[
\operatorname{median}_r NSV_{j,vector,r}(\eta)
\ge
T^{sci}_{NSV,j}.
\]

Every declared latent pathway must satisfy

\[
\operatorname{median}_r SRE_{kj,r}(\eta)
\ge
T^{sci}_{SRE,kj}.
\]

Additional invariant gates:

- structural-zero pathways are exactly zero;
- lower response bound holds;
- class ceiling \(u_{aj}\) is never exceeded;
- analytic derivative lower bound is satisfied;
- C8–C10 are unchanged.

---

## 11. Frozen minimum-departure selection rule

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

Winner identity, winner counts, modal winner, modal share, downstream SHAP
weights, MOORA rankings, TOPSIS rankings, and any preferred ITS alternative
are forbidden selection inputs.

Layer-B metrics are retained descriptively but cannot alter \(\eta^\star\).

If no candidate in the frozen ladder passes, v2.3-F1 fails and protocol v2.3
stops before structural-validation or primary seeds are inspected.

---

## 12. One-shot structural validation after selection

Only if an \(\eta^\star\) is selected and frozen from design seeds may
structural-validation seeds `22001–22005` be inspected.

The selected \(\eta^\star\) is evaluated once, with no reselection.

Validation passes only if:

1. every C1–C7 criterion exceeds all D2.8 numerical thresholds on every
   validation seed;
2. validation-seed median LRV50 for every criterion is at least its frozen
   D2.7 scientific reference;
3. validation-seed median vector NSV for every criterion is at least its
   frozen D2.7 scientific reference;
4. validation-seed median SRE for every declared pathway is at least its
   frozen D2.7 scientific reference;
5. all structural-zero, lower-bound, class-ceiling, and monotonicity
   invariants hold.

If this one-shot validation fails, the selected architecture is rejected.
The ladder is not revisited.

---

## 13. Primary-seed firewall

Primary seeds `11001–11030` and external TEST remain inaccessible until:

1. v2.3-F1 candidate selection is frozen;
2. one-shot structural validation passes;
3. the decision-sensitivity Pilot-A rule is separately specified and frozen;
4. the selected response generator is promoted from diagnostic candidate code
   into the production generator through an audited commit;
5. the alpha-dispersion technology-world mapping is computed and frozen under
   the final generator.

No primary result may be used to revise the response architecture.

---

## 14. Interpretation rule

Protocol v2.3 is an adaptive redesign informed by failure on development/design
seeds `21001–21005`.

It is not an independent confirmation of the architecture.

Independent evidence begins only with the untouched structural-validation
seeds `22001–22005` and, later, the untouched primary seeds.

This distinction must be stated explicitly in the manuscript.
