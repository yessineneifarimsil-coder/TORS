# Protocol v2.4 — Compensated Signed-Curvature Response Redesign

## 1. Status and provenance

Protocol v2.4 is opened only after both prior response families were frozen as
failed.

Frozen v2.2 result:

`37c8f31 Freeze failed v2.2 D4-F1 candidate evaluation`

Frozen v2.3 result:

`feb442d Freeze failed v2.3-F1 headroom candidate evaluation`

Neither failed family is modified, extended, or retuned in v2.4.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched when this specification is created.

Protocol v2.4 is an adaptive development revision informed by the frozen
design-seed failures of v2.2 and v2.3. It is not an independent confirmation.

---

## 2. Frozen evidence motivating v2.4

### 2.1 v2.2 D4-F1

The signed endpoint-preserving curvature family generated sufficient
alternative-context non-separability.

At `kappa=0.9`:

- all C1–C7 scientific Layer-A gates passed;
- worst Layer-A ratio = `1.0488`;
- worst reachability ratio = `0.7633`.

At `kappa=1.0`:

- all C1–C7 scientific Layer-A gates passed;
- worst Layer-A ratio = `1.1388`;
- worst reachability ratio = `0.7481`.

Thus signed curvature was strong enough for Layer A but progressively weakened
relative latent-pathway reachability.

### 2.2 v2.3-F1

The semantic-headroom augmentation preserved reachability and all invariants
but generated insufficient scientific non-separability.

At `eta=1.0`:

- worst Layer-A ratio = `0.10595`;
- bottleneck criterion = `C3`;
- worst reachability ratio = `1.1806`;
- all lower-bound, ceiling, monotonicity-related, structural-zero, and C8–C10
  invariants passed.

The maximum observed absolute departure from the historical response was
approximately `0.1878`, showing that the v2.3 failure was not merely a lack of
raw response amplitude.

The v2.3 architecture was

\[
g
=
\theta o
+
\eta h
[
0.5o+0.5co^2
].
\]

Only the alternative-specific quadratic component produces true curvature.
The common linear headroom component largely retains multiplicative structure.
Consequently substantial raw departures can coexist with weak LRV and NSV.

---

## 3. v2.4 design principle

v2.4 combines the useful property of each frozen failed family while
introducing no second selection parameter.

The family retains:

1. the signed, alternative-specific curvature amplitude proportional to
   \(\theta\) from D4-F1, because that mechanism was capable of satisfying
   Layer-A scientific references; and

2. the semantically admissible headroom term from v2.3-F1, because headroom
   augmentation preserved and increased frozen SRE reachability.

The headroom compensation coefficient is fixed at its full admissible value
within the one-parameter family. It is not separately tuned.

---

## 4. Frozen v2.4-F1 family

For active C1–C7 pathways let

\[
u_{aj}
=
\begin{cases}
0.20, & M_{aj}=I,\\
0.40, & M_{aj}=D,
\end{cases}
\]

and define semantic headroom

\[
h_{aj}=u_{aj}-\theta_{aj}\ge0.
\]

For candidate magnitude \(\eta\), define

\[
\boxed{
g_{asj}(\eta)
=
\theta_{aj}o_{sj}
\left[
1+\eta v_{aj}(1-o_{sj})
\right]
+
\eta h_{aj}o_{sj}
}
\]

for every active C1–C7 pathway.

Structural-zero pathways remain exactly

\[
g_{asj}=0.
\]

C8–C10 remain unchanged in the first v2.4-F1 structural evaluation.

No criterion noise is used during structural selection:

\[
\sigma_x=0.
\]

The historical response is recovered exactly at

\[
\eta=0.
\]

---

## 5. Signed alternative-specific profile

For criterion \(j\) with \(m_j\) active alternatives define the frozen
symmetric grid

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

The complete grid is deterministically permuted across active alternatives
once per benchmark instance and criterion using

`SeedSequence([replication_seed, 2006, criterion_number])`.

RNG namespace `2006` is reserved exclusively for the v2.4-F1 signed profile.

The same realized \(v_{aj}\) profile is reused across:

- all candidate \(\eta\);
- every N;
- every rho;
- every target-noise condition;
- every oracle-interaction condition;
- every downstream method.

Structural-zero alternatives are excluded from the permutation.

Every active criterion/world receives the complete symmetric zero-mean grid.
No named ITS is systematically assigned a favorable curvature coefficient.

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
h=u-\theta\ge0,
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

### 6.3 Full-opportunity semantic ceiling

At \(o=1\),

\[
g(1)
=
\theta+\eta h
\le
\theta+h
=
u.
\]

### 6.4 Monotonicity

The derivative is

\[
\frac{\partial g}{\partial o}
=
\theta
+
\eta h
+
\eta\theta v(1-2o).
\]

Because

\[
v(1-2o)\ge-1,
\]

\[
\frac{\partial g}{\partial o}
\ge
\theta+\eta h-\eta\theta
=
\theta(1-\eta)+\eta h
\ge0.
\]

Thus the response is monotone non-decreasing for every admissible
\((\eta,v,o)\).

Unlike v2.3-F1, v2.4 does not impose the stronger artificial constraint
\(g'(o)\ge\theta\). Scientific latent sensitivity is governed directly by the
frozen SRE gates.

### 6.5 Global semantic bound

Since

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

### 6.6 Alternative-specific non-separability

The response can be written as

\[
g
=
(\theta+\eta h+\eta\theta v)o
-
\eta\theta v o^2.
\]

For nonzero \(\eta v\), the alternative-specific quadratic term prevents the
historical rank-one form

\[
g_{asj}=\theta_{aj}o_{sj}.
\]

The signed coefficient preserves the strong source of relative
alternative-context curvature that was observed in D4-F1.

### 6.7 Departure from the historical response

\[
\Delta g
=
\eta
\left[
h o
+
\theta v o(1-o)
\right].
\]

The departure may be positive or negative relative to the historical response
for intermediate opportunity levels, but the total response remains
non-negative, monotone, and below the semantic class ceiling.

A conservative domain-wide absolute bound is

\[
|\Delta g|
\le
\eta
\left(
h+\frac{\theta}{4}
\right).
\]

Realized departures must be recorded per seed, criterion, and candidate.

---

## 7. Frozen candidate ladder

The only v2.4-F1 candidate magnitudes are

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

No interpolation, intermediate value, value above 1.0, compensation
coefficient, second curvature coefficient, second exponent, or second response
family may be introduced after v2.4-F1 candidate results are inspected.

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

## 9. Frozen references reused without modification

v2.4-F1 reuses:

- D2.7 \(T^{sci}_{LRV,j}\);
- D2.7 \(T^{sci}_{NSV,j}\);
- D2.7 \(T^{sci}_{SRE,kj}\);
- D2.8 \(T^{num}_{NS}\);
- D2.8 \(T^{num}_{LRV}\);
- D2.8 \(T^{num}_{NSV}\).

No scientific threshold is recalibrated from v2.4 candidates.

D2.7 Layer-B remains non-activated:

\[
T_R^{sci}=\mathrm{None}.
\]

Layer-B diagnostics cannot select \(\eta\).

---

## 10. Frozen candidate gates

For every design seed and C1–C7 criterion:

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

- structural-zero pathways are exactly zero;
- response lower bound holds;
- class ceiling \(u_{aj}\) is never exceeded;
- analytic monotonicity holds;
- semantic headroom is non-negative;
- C8–C10 are exactly unchanged.

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

Layer-B remains descriptive and cannot alter \(\eta^\star\).

If no candidate passes, v2.4-F1 fails and v2.4 stops before validation or
primary seeds are inspected.

---

## 12. One-shot structural validation

Only after \(\eta^\star\) is selected and frozen may structural-validation
seeds `22001–22005` be inspected.

The selected \(\eta^\star\) is evaluated exactly once.

Validation passes only if:

1. every C1–C7 criterion exceeds D2.8 numerical thresholds on every validation
   seed;
2. validation-seed median LRV50 for every criterion meets its frozen D2.7
   reference;
3. validation-seed median vector NSV for every criterion meets its frozen D2.7
   reference;
4. validation-seed median SRE for every declared pathway meets its frozen D2.7
   reference;
5. every structural-zero, lower-bound, class-ceiling, monotonicity, headroom,
   and C8–C10 invariant holds.

If validation fails, the architecture is rejected and the design-seed ladder
is not revisited.

---

## 13. Primary-seed firewall

Primary seeds `11001–11030` and external TEST remain inaccessible until:

1. v2.4-F1 candidate selection is frozen;
2. one-shot structural validation passes;
3. the decision-sensitivity Pilot-A rule is separately specified and frozen;
4. the selected response generator is promoted into the production generator
   through an audited commit;
5. the alpha-dispersion technology-world mapping is computed and frozen under
   the final generator.

No primary result may revise the response architecture.

---

## 14. Interpretation rule

v2.4 is an adaptive development redesign based on frozen evidence from the
same development/design seed family `21001–21005`.

Passing the v2.4 design-seed gates would therefore establish only development
adequacy, not independent validation.

Independent structural evidence begins with untouched seeds `22001–22005`.

Primary inferential evidence begins later with untouched seeds
`11001–11030` and the external TEST pool.

This distinction must be explicit in the manuscript.

## 15. Frozen v2.4-F1 outcome

v2.4-F1 was executed from Git commit
`56ac899ccddfb9d5735cc6209a65af1e946ff0f3` after the protocol and evaluator
were committed and after a one-line non-scientific summary-label repair.

A pre-repair/post-repair comparison showed byte-for-byte identity for all
scientific and selection artefacts; only provenance metadata and the corrected
summary label changed.

All ten candidates passed:

- D2.8 numerical gates;
- all D2.7 pathway-level reachability gates;
- all frozen response/invariance gates.

No candidate passed all D2.7 scientific Layer-A criterion gates.

At eta=1.0, only C1 and C6 remained below their criterion-level references.

Therefore:

`selected_eta = null`

and v2.4-F1 is **FAILED / CLOSED**.

No external TEST context, structural-validation seed, or primary seed was
used. Layer-B was not used for selection and the production generator was not
modified.

Per the frozen no-fallback rule, eta is not extended above 1.0 and no second
response family may be introduced inside v2.4 after this result.

Any subsequent response redesign requires a new protocol version.

