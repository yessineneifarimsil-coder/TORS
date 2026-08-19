# v2.1 Structural Audit at `893a727`

## Purpose and status

This document records a **descriptive structural audit** of the committed v2.1 benchmark at Git checkpoint:

`893a7274ef23eee1e8e0be2eae56845d8d840f17`

It establishes what is true of the committed design before any v2.2 redesign is attempted.

It does **not** prescribe a fix. In particular, it does not authorize changes to the capability mask, the primary alpha vector, the oracle transform, the response exponent, criterion noise, or any alternative-specific parameter.

The audit uses development seed `21001` only. Primary seeds `11001–11030` are untouched.

---

## 1. Reproduction scope

Official structural-reproduction condition:

| Item | Value |
|---|---:|
| Git HEAD | `893a727` |
| replication seed | `21001` |
| rho | `0.4` |
| estimation contexts | `1000` |
| FIT contexts | `800` |
| WEIGHT contexts | `200` |
| external TEST | **excluded** |
| alternatives/context | `6` |
| estimation rows | `6000` |
| committed criterion noise | `sigma_x = 0.02` |
| structural audit criterion noise | `sigma_x = 0` |
| response exponent | `gamma = 1.0` |
| oracle zeta | `2.0` |
| oracle lambda | `0.5` |
| primary alpha sum | `1.0` |
| oracle interaction beta | `0.2` for each of five edges |
| MOORA diagnostic weights | equal |

Before the structural audit, the committed `sigma_x=.02` technology-response master was regenerated from source and compared against:

`data/generated/technology_responses_seed21001_N1000_rho0p40.csv`

The maximum absolute difference across regenerated versus existing criterion values was:

`5.000e-13`

The working tree remained clean and the full committed test suite reported:

`101 passed, 3 known SHAP PendingDeprecationWarnings`

This self-check establishes that the structural audit exercised the committed generation pipeline rather than an independent reimplementation.

---

# 2. Layer A — response geometry

## 2.1 Committed C1–C7 response equation

The committed Step-2 generator implements, for `j = C1,...,C7`,

\[
x_{asj}
=
\operatorname{clip}
\left(
\theta_{aj}\,o_{sj}^{\gamma}
+
\eta_{asj},
0,1
\right),
\]

with

\[
\eta_{asj} = \sigma_x e_{asj}.
\]

The opportunity \(o_{sj}\) is computed once per **context × criterion**, not per alternative.

The committed opportunity functions are:

\[
\begin{aligned}
C1 &: h_D,\\
C2 &: 0.60h_D+0.40h_I,\\
C3 &: 0.60h_D+0.40h_T,\\
C4 &: 0.50h_D+0.50h_I,\\
C5 &: h_I,\\
C6 &: 0.60h_D+0.40h_E,\\
C7 &: 0.40h_D+0.60h_T.
\end{aligned}
\]

The committed response exponent is:

\[
\gamma=1.
\]

At `sigma_x=0`,

\[
g_{asj}
=
\theta_{aj}o_{sj}
\]

for C1–C7, subject only to clipping.

In the official reproduction, the realized C1–C7 range was:

\[
0 \le g_{asj}\le 0.382995331446.
\]

Thus upper clipping at 1 cannot create the observed effect.

---

## 2.2 Analytical separability under within-context normalization

For C1–C7 at `sigma_x=0`, write:

\[
g_{asj}=\theta_{aj}c_{sj},
\qquad
c_{sj}=o_{sj}^{\gamma}.
\]

For vector normalization,

\[
r_{asj}
=
\frac{g_{asj}}
{\sqrt{\sum_b g_{bsj}^2}}
=
\frac{\theta_{aj}c_{sj}}
{c_{sj}\sqrt{\sum_b\theta_{bj}^2}}
=
\frac{\theta_{aj}}
{\sqrt{\sum_b\theta_{bj}^2}},
\]

for positive \(c_{sj}\).

The systematic context factor therefore cancels.

The same common multiplicative factor also cancels under:

- sum normalization;
- max normalization;
- min–max normalization.

Therefore the issue is not specific to the vector-normalization formula used by MOORA.

---

## 2.3 Numerical reproduction of the cancellation

Across-context population SD of vector-normalized criterion values at `sigma_x=0`:

| alternative | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ATSC | 9.647e-10 | 8.901e-12 | 1.167e-11 | 3.733e-12 | 1.071e-11 | 4.192e-12 | 6.179e-12 | 3.470e-03 | 1.799e-05 | 1.981e-04 |
| TSP | 3.305e-10 | 6.372e-12 | 1.106e-11 | 4.052e-12 | 0 | 3.642e-12 | 1.354e-11 | 1.075e-02 | 3.629e-04 | 4.519e-03 |
| TIDM | 5.709e-10 | 6.735e-12 | 2.014e-12 | 9.110e-12 | 2.197e-11 | 3.823e-12 | 4.761e-12 | 1.712e-02 | 1.321e-03 | 1.122e-03 |
| RMTI-DRG | 5.122e-10 | 2.954e-12 | 4.083e-12 | 3.026e-12 | 2.212e-11 | 6.034e-12 | 1.249e-11 | 3.558e-02 | 1.870e-04 | 4.512e-03 |
| V2X-CS | 3.541e-10 | 2.794e-12 | 0 | 5.921e-12 | 3.125e-12 | 5.674e-12 | 8.760e-12 | 4.529e-02 | 3.645e-04 | 2.446e-02 |
| DSM | 1.224e-09 | 1.099e-11 | 5.491e-12 | 8.118e-12 | 1.972e-11 | 5.701e-12 | 8.144e-12 | 6.331e-03 | 1.282e-03 | 2.767e-03 |

Maximum C1–C7 SD across all six alternatives and seven criteria:

\[
1.224456124726\times10^{-9}.
\]

This is numerical-zero scale relative to the realized criterion values and is consistent with the analytical cancellation. Literal equality to zero is not expected because the normalization implementation includes numerical epsilon and floating-point arithmetic.

C8–C10 retain systematic context dependence because their committed equations are not of the same C1–C7 separable form.

For A1/ATSC, the reproduced C8–C10 SDs are:

\[
(3.470267\times10^{-3},
1.799255\times10^{-5},
1.981214\times10^{-4}).
\]

Mean across six alternatives:

\[
(1.975753\times10^{-2},
5.891585\times10^{-4},
6.262884\times10^{-3}).
\]

---

### Normalization-specific qualification

The preceding C8–C10 statement is **normalization-specific**. Under the primary vector normalization, C8–C10 retain nonzero systematic normalized context variation in the audited condition. This does not imply survival under every normalization family.

In particular, at `sigma_x=0` the committed C9 equation is

\[
g_{as9}=\iota_a+0.10h_{R,s}.
\]

Within a context, min–max normalization removes the common additive term \(0.10h_{R,s}\):

\[
\frac{
(\iota_a+0.10h_R)-(\iota_{\min}+0.10h_R)
}{
(\iota_{\max}+0.10h_R)-(\iota_{\min}+0.10h_R)
}
=
\frac{\iota_a-\iota_{\min}}
{\iota_{\max}-\iota_{\min}}.
\]

Thus C9 becomes context-invariant under min–max normalization even though it survives the primary vector normalization. This qualification does not alter the historical v2.1 conclusion about C1–C7 under MOORA's vector normalization; it clarifies that different normalization families remove different classes of common context transformations.

---

## 2.4 Equal-weight decision geometry

At `sigma_x=0`:

| normalization | distinct orderings | distinct winners | modal winner | modal share |
|---|---:|---:|---|---:|
| vector | 2 | 1 | DSM | 1.000 |
| sum | 2 | 1 | DSM | 1.000 |
| max | 2 | 1 | DSM | 1.000 |
| min–max | 2 | 1 | DSM | 1.000 |

At committed `sigma_x=.02`:

| normalization | distinct orderings | distinct winners | modal winner | modal share |
|---|---:|---:|---|---:|
| vector | 129 | 6 | DSM | .874 |
| sum | 138 | 6 | DSM | .849 |
| max | 115 | 6 | DSM | .890 |
| min–max | 75 | 5 | DSM | .941 |

Interpretation must remain criterion-specific:

- for C1–C7, systematic context dependence is eliminated by the separable structure under these normalizations at `sigma_x=0`;
- C8–C10 retain systematic context dependence;
- therefore whole-MCDM ordering diversity at `sigma_x=.02` is not attributable exclusively to criterion noise, although criterion noise restores large C1–C7 variation that is absent in the systematic normalized signal.

---

# 3. Layer B — oracle decision-frontier geometry

The committed oracle is

\[
q(g)
=
\frac{\log(1+2g)}{\log 3},
\]

and

\[
U^\star
=
\frac{
\sum_j \alpha_jq(g_j)
+
\lambda\sum_{(j,k)}
\beta_{jk}q(g_j)q(g_k)
}{
1+\lambda
}.
\]

At the audit condition `lambda=.5`, the raw oracle utility remained inside its theoretical bounds, so the final numerical safeguard clip changed no value:

`max |raw U* - stored U*| = 0`.

---

## 3.1 Oracle order geometry

At `sigma_x=0`:

- distinct oracle orderings: `19`;
- distinct oracle winners: `2`;
- modal oracle winner: `DSM`;
- modal share: `0.962`.

At committed `sigma_x=.02`:

- distinct oracle orderings: `47`;
- distinct oracle winners: `5`;
- modal winner: `DSM`;
- modal share: `0.902`.

Thus criterion noise increases oracle winner/order diversity, but the noise-free oracle already contains nonzero context-dependent reordering.

---

## 3.2 Constant modal-winner baseline

A constant strategy that always selects DSM gives, at `sigma_x=0`:

- Top-1 accuracy: `0.962`;
- Top-1 headroom to a perfect selector: `0.038`;
- mean normalized oracle regret: `0.00111064`;
- median normalized regret: `0`;
- p95 normalized regret: `0`;
- maximum normalized regret: `0.08306878`.

DSM is non-optimal in only:

`38 / 1000`

estimation contexts.

Conditional on those 38 non-optimal contexts:

- mean regret: `0.02922726`;
- median: `0.02437896`;
- p25: `0.01314481`;
- p75: `0.03706595`;
- p95: `0.06930059`;
- maximum: `0.08306878`.

This demonstrates that the noise-free v2.1 oracle has very little decision headroom against a trivial context-invariant modal-winner baseline.

---

## 3.3 Two-way oracle decomposition

For descriptive diagnosis, write

\[
U^\star_{as}
=
\mu+A_a+C_s+I_{as}.
\]

The reproduction gives:

- grand mean: `0.313341518265`;
- reconstruction max error: `5.551e-17`.

Sum-of-squares shares:

- alternative main effect: `0.260148`;
- context main effect: `0.714122`;
- alternative × context interaction: `0.025729`.

The large context-main-effect share does not itself create decision heterogeneity because it shifts all alternatives within a context together. Pairwise alternative contrasts are therefore the more decision-relevant instrument.

---

## 3.4 Pairwise oracle contrasts

For alternatives \(a,b\),

\[
D_{ab,s}
=
U^\star_{as}-U^\star_{bs}
=
G_{ab}+J_{ab,s},
\]

where \(G_{ab}\) is the fixed alternative gap and \(J_{ab,s}\) is the context-dependent pairwise component.

Define descriptively:

\[
R_{ab}
=
\frac{SD(J_{ab})}{|G_{ab}|+\epsilon},
\]

and

\[
P_{\mathrm{cross},ab}
=
P\left[
D_{ab,s}
\text{ has the opposite sign from }
G_{ab}
\right].
\]

Reproduced pairwise geometry:

| pair | \(G_{ab}\) | \(SD(J)\) | \(R_{ab}\) | \(P_{cross}\) |
|---|---:|---:|---:|---:|
| TSP–TIDM | -0.000710 | 0.015716 | 22.147 | .470 |
| ATSC–RMTI-DRG | -0.004258 | 0.009056 | 2.127 | .376 |
| ATSC–TSP | 0.007874 | 0.010203 | 1.296 | .245 |
| TIDM–RMTI-DRG | -0.011422 | 0.011565 | 1.013 | .210 |
| ATSC–TIDM | 0.007165 | 0.008524 | 1.190 | .198 |
| TSP–RMTI-DRG | -0.012132 | 0.009448 | 0.779 | .103 |
| RMTI-DRG–DSM | -0.029081 | 0.016425 | 0.565 | .038 |
| TSP–DSM | -0.041212 | 0.020846 | 0.506 | .005 |
| ATSC–DSM | -0.033338 | 0.010994 | 0.330 | 0 |
| TIDM–DSM | -0.040503 | 0.011810 | 0.292 | 0 |
| RMTI-DRG–V2X-CS | 0.068586 | 0.017218 | 0.251 | 0 |
| TIDM–V2X-CS | 0.057164 | 0.013644 | 0.239 | 0 |
| TSP–V2X-CS | 0.056455 | 0.013381 | 0.237 | 0 |
| V2X-CS–DSM | -0.097667 | 0.021993 | 0.225 | 0 |
| ATSC–V2X-CS | 0.064329 | 0.013485 | 0.210 | 0 |

The oracle therefore contains substantial context-dependent pairwise reordering among several non-optimal alternatives while pairwise crossings involving DSM are rare or absent.

A precise descriptive statement is:

> Contextual interaction exists in v2.1 but is poorly positioned relative to the optimal-decision frontier.

No hard acceptance threshold is inferred from \(R_{ab}\) or \(P_{\mathrm{cross}}\) in this historical audit.

---

# 4. Layer-B fixed-gap contribution decomposition

The modal alternative's mean oracle gap to every challenger was decomposed into:

- ten main-effect criterion terms;
- five oracle interaction terms.

The pointwise sum of all 15 terms reproduced \(U^\star\) with maximum error:

`1.665e-16`.

Every modal-vs-challenger mean gap was reconstructed with error below `2.1e-17`.

## 4.1 All 15 contributions: DSM minus challenger

| term | ATSC | TSP | TIDM | RMTI-DRG | V2X-CS |
|---|---:|---:|---:|---:|---:|
| C1 | .00328568 | .01229791 | .00869369 | .00955102 | .01193315 |
| C2 | .00119199 | .00273103 | .00250338 | .00501514 | .00512863 |
| C3 | -.00457633 | -.00415902 | .00298476 | .00116679 | .00489253 |
| C4 | .00603574 | .00556109 | -.00123754 | .00711225 | .00289882 |
| C5 | .00667156 | .01605026 | -.00153025 | -.00163346 | .01311417 |
| C6 | .00335061 | .00461116 | .00419367 | -.00071788 | .00006043 |
| C7 | .00230078 | -.00591227 | .00401754 | -.00480643 | -.00070418 |
| C8 | .00080271 | -.00064102 | .00329778 | -.00350370 | .00901404 |
| C9 | .00248079 | .00174072 | .00510113 | .00281291 | .00316401 |
| C10 | .00241947 | -.00109318 | -.00044223 | .00529206 | .02643183 |
| C1×C2 | .00167646 | .00427948 | .00351594 | .00454278 | .00479236 |
| C3×C7 | -.00072905 | -.00282759 | .00114040 | -.00017898 | .00149697 |
| C4×C5 | .00348577 | .00496272 | -.00101115 | .00268309 | .00426136 |
| C6×C10 | .00167609 | .00195064 | .00180600 | .00031718 | .00292478 |
| C8×C9 | .00326610 | .00166058 | .00746974 | .00142803 | .00825833 |

## 4.2 Block totals

| block | ATSC | TSP | TIDM | RMTI-DRG | V2X-CS |
|---|---:|---:|---:|---:|---:|
| C1–C7 main | .01826003 | .03118015 | .01962527 | .01568743 | .03732354 |
| C8–C10 main | .00570298 | .00000652 | .00795668 | .00460127 | .03860988 |
| interactions | .00937537 | .01002583 | .01292094 | .00879210 | .02173379 |
| TOTAL | .03333838 | .04121250 | .04050289 | .02908080 | .09766722 |

Approximate shares of the total fixed gap:

| challenger | C1–C7 main | C8–C10 main | interactions |
|---|---:|---:|---:|
| ATSC | 54.8% | 17.1% | 28.1% |
| TSP | 75.7% | 0.0% | 24.3% |
| TIDM | 48.5% | 19.6% | 31.9% |
| RMTI-DRG | 53.9% | 15.8% | 30.2% |
| V2X-CS | 38.2% | 39.5% | 22.3% |

The fixed DSM advantage is therefore **diffusely accumulated**. It is not attributable to capability-mask criteria alone, deployment/readiness criteria alone, or interaction terms alone across all rivals.

This falsifies the narrower hypothesis that capability-mask density by itself explains the noise-free oracle concentration.

---

# 5. Layer A/B interface — realized nonlinear oracle geometry

The nonlinear transform is:

\[
q(g)=\frac{\ln(1+2g)}{\ln3},
\]

with derivative:

\[
q'(g)=\frac{2}{(1+2g)\ln3}.
\]

Because the oracle also contains interactions, the complete local raw-space marginal derivative for criterion \(j\) is:

\[
\frac{\partial U^\star}{\partial g_j}
=
\frac{q'(g_j)}{1+\lambda}
\left[
\alpha_j
+
\lambda
\sum_{k:(j,k)\in E}
\beta_{jk}q(g_k)
\right].
\]

Reproduced realized geometry:

| C | median g | median q | median q' | median full dU*/dg |
|---|---:|---:|---:|---:|
| C1 | .067858 | .115840 | 1.602935 | .132387 |
| C2 | .083860 | .141136 | 1.559002 | .053071 |
| C3 | .063849 | .109391 | 1.614332 | .065203 |
| C4 | .101185 | .167752 | 1.514076 | .083581 |
| C5 | .070460 | .120001 | 1.595625 | .120880 |
| C6 | .072036 | .122513 | 1.591227 | .209530 |
| C7 | .074589 | .126566 | 1.584156 | .140152 |
| C8 | .978816 | .987054 | .615519 | .101968 |
| C9 | .770147 | .848598 | .716641 | .082771 |
| C10 | .452105 | .586256 | .956028 | .090235 |

Interpretation:

- the nonlinear transform is materially engaged over the realized criterion ranges;
- the frozen alpha vector remains exactly the set of coefficients on **q-space main effects** that the oracle specification defines;
- because criteria occupy different realized parts of the common `[0,1]` domain, their **raw-space local marginal sensitivities** differ after the nonlinear transform and interactions;
- this fact should be quantified when evaluating criterion-scale geometry, but it does not by itself establish that alpha or `q` is incorrectly specified.

No redesign conclusion is drawn here.

---

# 6. Verified v2.1 findings

The official reproduction supports the following statements.

## Finding A1 — C1–C7 structural separability

At `sigma_x=0`, C1–C7 have a common context factor across alternatives multiplied by a fixed alternative-specific amplitude.

## Finding A2 — normalization removes the systematic C1–C7 context factor

Vector, sum, max, and min–max within-context normalizations all eliminate the common multiplicative context factor, up to floating-point epsilon.

## Finding A3 — C8–C10 are different

C8–C10 retain nonzero systematic normalized context variation under the same `sigma_x=0` audit.

## Finding B1 — criterion noise materially increases decision diversity

Moving from `sigma_x=0` to committed `sigma_x=.02` increases both MCDM and oracle order/winner diversity.

This should not be interpreted as proving that all whole-decision diversity is noise-generated, because C8–C10 retain systematic context dependence.

## Finding B2 — the noise-free oracle decision frontier is highly concentrated

DSM is oracle-optimal in 96.2% of the 1000 estimation contexts.

A constant DSM strategy has only 0.00111064 mean normalized regret and zero regret through the 95th percentile.

## Finding B3 — context-dependent oracle interaction is not globally absent

Several non-DSM pairs reverse frequently, including TSP–TIDM in 47% of contexts.

## Finding B4 — context interaction is poorly positioned relative to the optimum

Pairs involving DSM cross rarely or not at all:

- RMTI-DRG–DSM: 3.8%;
- TSP–DSM: 0.5%;
- ATSC–DSM: 0%;
- TIDM–DSM: 0%;
- V2X-CS–DSM: 0%.

## Finding B5 — DSM's fixed advantage is diffuse

The exact 15-term decomposition does not support capability-mask density as a single explanation of the DSM frontier advantage.

---

# 7. What this audit does NOT establish

This audit does not establish that v2.2 should:

- change the capability mask;
- change DSM;
- change another alternative to force winner diversity;
- change the primary alpha vector;
- change `q` or zeta;
- use a Dirichlet opportunity design;
- use alternative-specific exponents;
- alter criterion noise to make rankings more attractive;
- use a particular oracle-winner or pairwise-crossing threshold.

Those are v2.2 design questions and must be handled separately under predeclared, method-neutral criteria.

---

# 8. Protocol consequence

At this historical checkpoint:

- v2.1 generator implementation is reproducible;
- the existing 101 tests pass;
- Pilot A passed under its frozen v2.1 pooled warning rule;
- the structural audit nevertheless identifies benchmark properties not caught by those tests;
- Step 6 remains paused;
- primary seeds remain untouched;
- no `spec-v2.1` tag should be created.

The next scientific layer is a separate v2.2 design specification. It should begin only after this historical audit and its characterization tests are reviewed and committed.
