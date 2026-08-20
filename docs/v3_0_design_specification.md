# Protocol v3.0 — Monotone Headroom-Shape Response Redesign

## 1. Status and provenance

Protocol v3.0 is opened only after the terminal v2.5-F1 development family was
frozen as failed.

Frozen terminal v2.5 result:

`ad83a88 Freeze failed terminal v2.5-F1 ceiling-scaled curvature evaluation`

The v2.2–v2.5 development history on seeds `21001–21005` remains immutable.

The response architecture proposed here is informed by that frozen historical
development evidence, especially the v2.5 finding that sufficient signed
curvature could satisfy Layer-A only after C6 latent-pathway reachability had
fallen below its frozen D2.7 references.

v3.0 therefore changes the mathematical response class rather than retuning
the failed v2.5 family.

---

## 2. New development cohort and firewalls

The only v3.0 response-development cohort is:

`23001, 23002, 23003, 23004, 23005`.

These seeds were unused and unreferenced in tracked scientific material when
this specification was created.

The separate block

`24001, 24002, 24003, 24004, 24005`

remains reserved and untouched.

The following previously frozen evidence sets also remain untouched during
v3.0 candidate selection:

- structural-validation seeds `22001–22005`;
- primary seeds `11001–11030`;
- external TEST.

The old design seeds `21001–21005` are not used to select the v3.0 shape order.

Because the v3.0 architecture was designed after observing frozen v2.x
development failures, v3.0 candidate results on `23001–23005` are still
development evidence, not independent validation.

Independent structural validation remains `22001–22005`.

---

## 3. Structural diagnosis motivating the new class

The terminal v2.5 family exposed a non-overlapping gate frontier:

- at low-to-moderate curvature, reachability passed but Layer-A failed;
- at high curvature, Layer-A passed but `h_D->C6` and `h_E->C6`
  reachability failed.

The signed zero-endpoint curvature used in v2.5 could reduce the local
opportunity derivative.

v3.0 removes that mechanism by restricting the added headroom component to a
monotone shape function whose derivative is everywhere non-negative.

The resulting total response satisfies

\[
\frac{\partial g}{\partial o}\ge\theta
\]

for every active pathway by construction.

This is a structural change, not a criterion-specific repair.

---

## 4. Frozen v3.0-F1 response family

For every active C1–C7 pathway define the existing semantic class ceiling

\[
u_{aj}
=
\begin{cases}
0.20, & M_{aj}=I,\\
0.40, & M_{aj}=D,
\end{cases}
\]

and semantic headroom

\[
h_{aj}=u_{aj}-\theta_{aj}\ge0.
\]

For signed profile coefficient

\[
-1\le v_{aj}\le1
\]

and frozen shape order \(p\), define

\[
a_{aj}=|v_{aj}|.
\]

The headroom shape is

\[
F_{p,v}(o)
=
\begin{cases}
(1-a)o+a\,o^p,
&
v<0,
\\[4pt]
o,
&
v=0,
\\[4pt]
(1-a)o+a\left[1-(1-o)^p\right],
&
v>0.
\end{cases}
\]

The active-pathway response is

\[
\boxed{
g_{asj}(p)
=
\theta_{aj}o_{sj}
+
h_{aj}F_{p,v_{aj}}(o_{sj})
}
\]

for C1–C7.

Structural-zero pathways remain exactly

\[
g_{asj}=0.
\]

C8–C10 remain unchanged during v3.0-F1 candidate evaluation.

No criterion noise is used during structural selection:

\[
\sigma_x=0.
\]

There is no separate amplitude parameter: v3.0 uses the full pre-existing
semantic headroom \(h=u-\theta\).

---

## 5. Frozen signed alternative-specific profile

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

The complete symmetric zero-mean grid is deterministically permuted across
active alternatives once per benchmark instance and criterion using

`SeedSequence([replication_seed, 2008, criterion_number])`.

RNG namespace `2008` is reserved exclusively for v3.0-F1.

The same realized \(v_{aj}\) profile is reused across every candidate shape
order and all downstream conditions.

Structural-zero alternatives are excluded from the permutation.

No named ITS receives systematic preference by construction.

The shape family is balanced around the linear response because

\[
F_{p,+a}(o)
=
1-F_{p,-a}(1-o).
\]

---

## 6. Analytic properties

For

\[
p\ge1,
\qquad
-1\le v\le1,
\qquad
0\le o\le1,
\qquad
0\le\theta\le u,
\]

the following hold.

### 6.1 Endpoints of the headroom shape

For every admissible \(p,v\),

\[
F_{p,v}(0)=0,
\qquad
F_{p,v}(1)=1.
\]

Therefore

\[
g(0)=0
\]

and

\[
g(1)
=
\theta+h
=
u.
\]

### 6.2 Monotonicity of the headroom shape

For \(v<0\),

\[
F'_{p,v}(o)
=
(1-a)+ap\,o^{p-1}
\ge0.
\]

For \(v>0\),

\[
F'_{p,v}(o)
=
(1-a)+ap\,(1-o)^{p-1}
\ge0.
\]

For \(v=0\),

\[
F'_{p,0}(o)=1.
\]

Hence

\[
F'_{p,v}(o)\ge0
\]

throughout the complete domain.

### 6.3 Historical derivative floor

The total derivative is

\[
\frac{\partial g}{\partial o}
=
\theta+hF'_{p,v}(o).
\]

Therefore

\[
\boxed{
\frac{\partial g}{\partial o}\ge\theta
}
\]

for every active pathway.

This removes the derivative-loss mechanism implicated in the terminal v2.5
reachability tradeoff.

### 6.4 Global semantic bound

Because \(F\) is monotone with endpoints 0 and 1,

\[
0\le F_{p,v}(o)\le1.
\]

Thus

\[
0\le g(o)\le\theta+h=u.
\]

No clipping is required at \(\sigma_x=0\).

### 6.5 Alternative-context non-separability

For \(p>1\) and nonzero \(v\), the added component is nonlinear in
opportunity.

Because the signed shape profile differs across alternatives, the response
matrix is not constrained to the historical rank-one form
\(\theta_a o_s\).

### 6.6 Quadratic special case

For \(p=2\),

\[
F_{2,v}(o)
=
o+v\,o(1-o).
\]

Thus the lowest candidate is the simplest smooth signed monotone headroom
shape.

Higher frozen orders increase shape separation while retaining all endpoint,
monotonicity, derivative-floor, and semantic-bound guarantees.

---

## 7. Frozen shape-order ladder

The only v3.0-F1 candidate shape orders are

\[
\boxed{
p\in\{2,3,4,5\}.
}
\]

The linear case

\[
p=1
\]

is a descriptive full-headroom reference only and cannot be selected.

The upper bound \(p=5\) is frozen before the new development cohort is
inspected to avoid arbitrarily steep or step-like response shapes.

No interpolation, non-integer order, order above 5, amplitude coefficient,
criterion-specific shape order, alternative-specific shape order, or second
v3.0 response family may be introduced after candidate results are observed.

---

## 8. Frozen v3.0-F1 evaluation scope

Candidate-family development uses only:

- development seeds `23001–23005`;
- `rho=0.4`;
- `sigma_x=0`;
- all 1000 FIT+WEIGHT contexts per development seed;
- C1–C7 candidate responses;
- unchanged C8–C10;
- unchanged oracle;
- `lambda=0.5` only for descriptive Layer-B diagnostics.

Excluded from candidate selection:

- old development seeds `21001–21005`;
- reserved seeds `24001–24005`;
- structural-validation seeds `22001–22005`;
- primary seeds `11001–11030`;
- external TEST.

The production technology-response generator remains unmodified during
candidate evaluation.

---

## 9. Frozen references reused without modification

v3.0-F1 reuses without recalibration:

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

Layer-B cannot select \(p\).

---

## 10. Frozen candidate gates

For every development seed and every C1–C7 criterion:

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
\operatorname{median}_r LRV50_{j,r}(p)
\ge
T^{sci}_{LRV,j},
\]

and

\[
\operatorname{median}_r NSV_{j,vector,r}(p)
\ge
T^{sci}_{NSV,j}.
\]

For every declared latent pathway:

\[
\operatorname{median}_r SRE_{kj,r}(p)
\ge
T^{sci}_{SRE,kj}.
\]

Invariant gates:

- structural-zero pathways remain exactly zero;
- lower response bound holds;
- semantic class ceiling is never exceeded;
- \(F_{p,v}\) is monotone;
- total derivative satisfies \(g'(o)\ge\theta\);
- headroom remains non-negative;
- C8–C10 remain exactly unchanged.

---

## 11. Frozen selection rule

Define

\[
p^\star
=
\min
\left\{
p\in\{2,3,4,5\}:
\text{all numerical, Layer-A, reachability, and invariant gates pass}
\right\}.
\]

Winner identities, ranking identities, modal winner, modal share, SHAP
weights, MOORA rankings, TOPSIS rankings, or any preferred ITS alternative are
forbidden selection inputs.

Layer-B remains descriptive and cannot alter \(p^\star\).

If no candidate passes, v3.0-F1 fails.

---

## 12. Terminal rule for the new development cohort

v3.0-F1 is the only response-family development stage permitted on
`23001–23005`.

After v3.0-F1 candidate results are observed:

- the order ladder cannot be extended;
- the formula cannot be modified;
- thresholds cannot be changed;
- no second v3.0 family may be introduced on these seeds.

If v3.0-F1 fails, `23001–23005` are closed for response-family development.

The reserved `24001–24005` block is not an automatic fallback and remains
untouched unless a future protocol is justified and specified before those
seeds are inspected.

---

## 13. One-shot structural validation

Only if \(p^\star\) is selected and frozen may structural-validation seeds
`22001–22005` be inspected.

The selected \(p^\star\) is evaluated exactly once.

Validation passes only if:

1. every C1–C7 criterion exceeds D2.8 numerical thresholds on every validation
   seed;
2. validation-seed median LRV50 for every criterion meets its frozen D2.7
   reference;
3. validation-seed median vector NSV for every criterion meets its frozen D2.7
   reference;
4. validation-seed median SRE for every declared pathway meets its frozen D2.7
   reference;
5. every structural-zero, lower-bound, semantic-ceiling, shape-monotonicity,
   derivative-floor, headroom, and C8–C10 invariant holds.

If one-shot validation fails, the architecture is rejected and the
development ladder is not revisited.

---

## 14. Primary-seed firewall

Primary seeds `11001–11030` and external TEST remain inaccessible until:

1. v3.0-F1 candidate selection is frozen;
2. one-shot structural validation passes;
3. the final Pilot-A decision-sensitivity rule is separately frozen;
4. the selected response is promoted into the production generator through an
   audited commit;
5. alpha-dispersion mapping is computed and frozen under the final generator.

No primary result may revise the response architecture.

---

## 15. Interpretation rule

v3.0 is still adaptive development because its mathematical class was designed
after observing the frozen v2.x failures.

The fresh `23001–23005` cohort prevents further tuning on the exhausted
`21001–21005` cohort, but it does not convert development into independent
validation because it is used to select \(p\).

Independent structural evidence begins only with untouched seeds
`22001–22005`.

Primary inferential evidence begins later with untouched seeds
`11001–11030` and external TEST.

The manuscript must disclose:

- the historical v2.x development sequence;
- closure of `21001–21005`;
- introduction of fresh development seeds `23001–23005`;
- the frozen v3.0 shape-order ladder;
- the untouched validation and primary firewalls.
