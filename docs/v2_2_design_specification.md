# Protocol v2.2 Design Specification — Structural Redesign Before Implementation

## Status

**Branch:** `protocol-v2.2-design`

**Historical parent checkpoint:** `b953fb1` — *Document reproduced v2.1 structural benchmark limitations*

**Primary seeds `11001–11030`: untouched.**

This document defines the scientific design rules for v2.2 before any technology-response formula, generator parameter, oracle parameter, or decision threshold is changed.

It is intentionally separated from:

- `docs/v2_1_structural_audit.md`, which records historical facts about v2.1;
- future implementation commits, which will modify code/config only after this design specification is reviewed and frozen.

No result in this document is allowed to be justified by a desire to make SHAP, MOORA, ATSC, DSM, or any other method/alternative perform better.

---

# 1. Why v2.2 exists

The v2.1 structural audit at `b953fb1` established, before any redesign, that:

1. for C1–C7 at criterion noise `sigma_x=0`, the committed generator has the form

\[
g_{asj}=\theta_{aj}o_{sj},
\]

with a context-only opportunity \(o_{sj}\) shared across alternatives;

2. homogeneous within-context normalizations remove that common multiplicative context factor for C1–C7 up to numerical epsilon;

3. C8–C10 do not exhibit the same complete normalized collapse;

4. the noise-free oracle contains context-dependent pairwise reordering but the decision frontier is highly concentrated around DSM for the audited seed/scope;

5. a constant modal-winner baseline is therefore unusually competitive in that audited instance;

6. the fixed DSM oracle advantage is diffusely accumulated across main-effect and interaction terms rather than being explained by capability-mask density alone;

7. criterion-scale geometry interacts materially with the nonlinear oracle transform in raw-space marginal sensitivity, without implying that the frozen q-space alpha coefficients are invalid.

v2.2 exists to redesign the benchmark **structurally**, not to alter an observed ranking.

---

# 2. Scientific estimand — D1 RESOLVED

## D1 decision

v2.2 adopts:

\[
\boxed{\text{D1-B: superpopulation benchmark-instance estimand}}
\]

Each replication seed defines one plausible synthetic benchmark instance consisting of:

1. one technology-response profile drawn from the prespecified v2.2 technology-profile distribution;
2. one latent-context master generated from the prespecified context distribution and CRN construction;
3. criterion-noise and target-noise streams generated from their dedicated namespaces.

All methods and all factorial conditions are compared **within the same replication-defined benchmark instance**.

The primary estimand is therefore an average method-fidelity quantity over the prespecified distribution of plausible synthetic benchmark instances, rather than a quantity conditional on one arbitrarily frozen technology profile.

Conceptually, for a method \(m\) and experimental condition \(x\),

\[
\Psi_m(x)
=
E_{W}
\left[
E_{H,\varepsilon}
\left[
L_m(x;W,H,\varepsilon)
\mid W
\right]
\right],
\]

where:

- \(W\) denotes the replication-specific technology-response profile;
- \(H\) denotes sampled latent contexts;
- \(\varepsilon\) denotes criterion/target noise as applicable;
- \(L_m\) denotes the prespecified fidelity/decision metric.

The exact mixed-effects/statistical estimator for \(\Psi_m(x)\) is frozen later, but the scientific target is fixed here.

## D1 pairing invariant

For replication seed \(r\), the technology profile \(W_r\) must be sampled once and reused unchanged across:

\[
N,\quad \rho,\quad c,\quad \lambda,
\]

and across all weighting/decision methods evaluated for that seed.

Therefore technology-profile variation acts as **between-benchmark-instance variation**, not as an unpaired nuisance that changes between methods or factorial cells.

Any future v2.2 response-shape or deployment parameter introduced as part of \(W_r\) must obey the same rule unless explicitly classified as a factorial treatment.

## Why D1-B is chosen

The paper evaluates methodological fidelity, not the performance of one hand-crafted ITS world.

A fixed-world primary benchmark would make the conclusions conditional on one selected technology profile and would create substantial sensitivity to how that single profile was chosen.

The superpopulation design instead:

- averages conclusions over multiple plausible synthetic technology worlds;
- preserves strict paired comparisons within each seed;
- prevents selecting one favorable technology-profile draw;
- aligns naturally with the existing replication-seed architecture, in which capability and deployment parameters are already sampled once per seed and reused across \(N\) and \(\rho\);
- permits seed/benchmark instance to be treated as the repeated blocking unit in the later statistical model.

The increased between-seed variability is accepted as part of the target estimand rather than removed by fixing one world.

Under D1-B, the oracle/reference global attribution-weight target \(w_r^\star\) is itself benchmark-instance dependent because the realized distribution of \(g\) changes with \(W_r\). Consequently, seed-level \(TV_w(\widehat w_r,w_r^\star)\) is an **instance-conditional fidelity error**, while its cross-seed distribution estimates performance over the prespecified benchmark-instance superpopulation. Between-seed spread may therefore reflect both estimation/noise variation and heterogeneity in benchmark-instance difficulty; the later statistical model and reporting must make this distinction explicit.

The superpopulation is intentionally **scoped by the prespecified technology-class and response-parameter distributions**. The 30 primary seeds provide finite Monte Carlo coverage of that constrained family; they do not broaden the family beyond the distributions that v2.2 freezes.

## What D1-B does NOT authorize

D1-B does not authorize:

- selecting or rejecting a replication seed based on winner geometry;
- replacing an inconvenient primary seed;
- changing technology-profile distributions after primary results are seen;
- redrawing a technology profile separately for different methods or factorial conditions;
- using external TEST or primary seeds to select the v2.2 response family.

The technology-profile distribution itself remains a v2.2 design object and must be frozen before primary execution.

# 3. Non-negotiable v2.2 invariants

## I1 — No outcome engineering

No design choice may be justified by:

- making ATSC first;
- making DSM lose;
- producing a target number of oracle winners;
- increasing SHAP performance;
- increasing MOORA performance;
- forcing a desired ranking;
- selecting a random seed because its geometry looks favorable.

## I2 — Systematic geometry before criterion noise

All structural response-family diagnostics are first evaluated at:

\[
\sigma_x=0.
\]

Criterion noise may perturb an adequate systematic benchmark; it may not be the mechanism that creates the benchmark's decision sensitivity.

## I3 — Preserve semantic zeros

If a capability pathway is structurally absent in the benchmark specification, v2.2 must not create a nonzero pathway merely to improve geometry.

## I4 — Preserve latent-factor semantics unless independently justified

A criterion with a singleton latent support may remain singleton.

For example:

\[
C1\leftarrow h_D,
\qquad
C5\leftarrow h_I.
\]

Additional latent-factor pathways may be introduced only with an independent transport-domain justification, never simply to break separability.

## I5 — Active pathways must permit differential alternative response

For intended context-responsive pathways, the systematic response architecture must be capable of genuine alternative × context variation.

The v2.1 special case

\[
g_{asj}=\theta_{aj}c_{sj}
\]

is insufficient because many downstream homogeneous normalizations remove \(c_{sj}\).

A v2.2 response family should generally permit:

\[
g_{asj}=f_{aj}(h_s)
\]

with alternative-specific response structure on active pathways.

## I6 — No normalization-switch “fix”

Changing vector normalization to sum, max, or min–max is not an acceptable repair for a shared multiplicative factor, because the factor cancels under all four families in the v2.1 structure.

## I7 — Primary oracle held fixed during first-pass response redesign

The first-pass v2.2 response-family analysis retains the primary:

- alpha vector;
- zeta;
- beta values;
- semantic interaction edges;
- lambda factor levels.

Oracle parameters are not changed simply because the v2.1 frontier was concentrated.

If later evidence establishes an independently justified oracle-design problem, that becomes a separately versioned design decision.

## I8 — Criterion-scale differences are not automatically errors

v2.2 must report realized criterion geometry, but must not force equal variances, equal ranges, or equal marginal derivatives across criteria without substantive justification.

## I9 — External TEST remains unavailable for tuning

The fixed external TEST pool must remain excluded from:

- generator-family selection;
- generator-parameter selection;
- threshold calibration;
- model calibration;
- background selection;
- weighting-method tuning;
- v2.2 design validation.

Historical exploratory access already documented in the v2.1 audit does not authorize future TEST use.

## I10 — Primary seeds remain untouched

Primary seeds `11001–11030` may not be inspected until final protocol freeze.

## I11 — Technology profile is frozen within a replication instance

Under D1-B, every replication-specific technology profile is sampled once and must remain identical across all \(N,\rho,c,\lambda\) cells and all methods for that replication seed.

This pairing requirement is part of the estimand and must be covered by explicit v2.2 tests.

---

# 4. Three-layer structural validation architecture

v2.2 separates three different questions.

---

## Layer A — context-to-response geometry

Question:

> Does the systematic generator create scientifically intended alternative-specific context response?

Study:

\[
h_s \rightarrow G_s.
\]

Primary diagnostics at `sigma_x=0`:

1. active-pathway response variation;
2. pairwise alternative response-ratio variability where mathematically defined;
3. matrix non-separability diagnostics;
4. normalized-signal survival under vector, sum, max, and min–max normalizations;
5. latent-factor reachability;
6. criterion scale/boundary geometry;
7. structural dominance.

### A1. Non-separability diagnostics

For each criterion \(j\), characterize the systematic context × alternative response matrix:

\[
G_j=[g_{asj}]_{s,a}.
\]

Candidate diagnostics include:

- singular-value structure of \(G_j\);
- variation in active pairwise response ratios;
- across-context variation after homogeneous normalizations.

No single diagnostic is by itself a future acceptance threshold.

### A2. Latent-factor reachability

The Gaussian-copula latent construction is:

\[
\tilde h_{ks}
=
\sqrt{\rho}\,z_{0s}
+
\sqrt{1-\rho}\,z_{ks},
\]

followed by the standard-normal CDF.

For factor-specific reachability under \(\rho>0\), do not naively shuffle the realized \(h_k\).

Use a **model-consistent idiosyncratic-shock intervention conditional on the shared factor \(z_0\)**:

- hold \(z_0\) fixed;
- hold all other idiosyncratic shocks fixed;
- resample or replace only \(z_k\);
- propagate through \(h_k\rightarrow G\rightarrow U^\star\) and decision scores.

At \(\rho=0\), ordinary independent resampling is equivalent in spirit.

Continuous score/response changes are primary; winner changes are secondary diagnostics.

---

## Layer B — oracle decision-frontier geometry

Question:

> Does systematic context variation generate decision-relevant oracle variation at the frontier?

Study:

\[
G_s \rightarrow U^\star_s.
\]

Use the two-way decomposition:

\[
U^\star_{as}
=
\mu+A_a+C_s+I_{as}.
\]

For every pair \(a,b\):

\[
D_{ab,s}
=
U^\star_{as}-U^\star_{bs}
=
G_{ab}+J_{ab,s},
\]

where

\[
G_{ab}=A_a-A_b,
\qquad
J_{ab,s}=I_{as}-I_{bs}.
\]

Mandatory descriptive diagnostics:

- \(G_{ab}\);
- \(SD(J_{ab})\);
- \(R_{ab}=SD(J_{ab})/(|G_{ab}|+\epsilon)\);
- empirical pairwise crossing frequency \(P_{\mathrm{cross},ab}\);
- oracle winner distribution;
- oracle decision-margin distribution;
- constant modal-winner Top-1 accuracy;
- Top-1 headroom;
- normalized regret of the constant modal-winner baseline;
- regret conditional on the modal baseline being non-optimal.

No hard numerical threshold for winner count, modal share, \(R_{ab}\), or \(P_{\mathrm{cross}}\) is frozen yet.

---

## Layer C — response-to-MCDM geometry

Question:

> Does systematic context information survive the transformation from responses to decision scores, independently of whether a method matches the oracle?

Study:

\[
G_s\rightarrow r_s\rightarrow S_s^{MCDM}.
\]

Diagnostics:

- equal-weight MOORA score variation at `sigma_x=0`;
- primary MOORA normalization behavior;
- TOPSIS robustness behavior;
- normalized criterion signal survival;
- factor-intervention effects on continuous MCDM scores;
- order/winner diversity as descriptive outputs.

### Prohibited Layer-C gate

Do **not** require MOORA/TOPSIS ordering diversity or fidelity to exceed a fixed fraction of oracle diversity.

That would build downstream method performance into the data-generator acceptance rule.

---

# 5. Criterion-scale and oracle-transform interface

For every criterion C1–C10, v2.2 diagnostics must record at minimum:

\[
g_{p05},\quad g_{median},\quad g_{p95},
\]

boundary masses where relevant, and:

\[
q(g),\quad q'(g).
\]

With the primary interaction oracle, also report:

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

Interpretation rule:

- alpha remains the coefficient on the q-space main effect;
- raw-space marginal sensitivity may vary because criteria occupy different parts of the nonlinear q domain;
- such differences must be quantified before being judged appropriate or inappropriate.

---

# 6. Criterion-noise calibration sequence

v2.2 separates systematic design from nuisance-noise calibration.

## Stage N0 — systematic design

Set:

\[
\sigma_x=0.
\]

Freeze the systematic response-family architecture and its scientifically justified parameterization.

## Stage N1 — criterion-noise calibration

Only after Stage N0 is frozen, evaluate candidate criterion-noise levels relative to the realized systematic signal.

The final choice must demonstrate that criterion noise perturbs rather than creates the relevant response/decision geometry.

A formal signal-share statistic must be defined before noise-level results are inspected.

## Stage N2 — final joint freeze

After the systematic response architecture and criterion-noise protocol are both frozen, rerun all downstream development diagnostics.

---

# 7. Development and validation seed policy

## 7.1 Existing development seeds

The seeds:

`21001–21005`

have already been repeatedly inspected.

They are therefore designated:

**v2.2 design/diagnostic seeds**

and are not clean holdout validation seeds.

## 7.2 v2.2 structural-validation seeds

Before any candidate response-family sweep, add a new non-overlapping seed family:

`v2_2_structural_validation`

Proposed reserved values:

`22001–22005`

These seeds must remain uninspected until:

1. D1 is frozen;
2. the structural metrics are frozen;
3. numerical acceptance criteria are frozen;
4. the response family and candidate-selection rule are frozen using design seeds only.

The validation seeds are then used once for the v2.2 structural validation.

## 7.3 Validation failure

If the one-shot v2.2 structural validation fails:

- do not tune against `22001–22005`;
- document the failure;
- v2.2 is not declared frozen;
- any redesign becomes a new protocol version (for example v2.3);
- a new validation seed family must be declared before that redesign is evaluated.

Primary seeds remain untouched throughout.

---

# 8. Candidate-family evaluation policy

No candidate family is approved in this document.

Potential structural families may include, after metrics/thresholds are frozen:

1. alternative-specific response-shape functions that preserve the original latent supports;
2. alternative-specific latent-factor mixtures on multi-factor supports;
3. a hybrid architecture in which singleton-support criteria use alternative-specific response shapes and multi-factor criteria use a justified combination of shape and mixture effects.

Specific candidates such as Dirichlet mixtures or exponent families are **not** considered validated.

Known cautions:

- standard `Dirichlet(kappa*w)` is undefined when the concentration vector contains zero components;
- active-support Dirichlet construction preserves structural zeros but cannot by itself break separability for singleton-support criteria;
- random alternative-specific exponent draws have already shown strong draw sensitivity in exploratory development analysis and therefore cannot be treated as a verified fallback.

### Candidate selection rule

The parameterization rule must be declared before results are inspected.

The general principle is:

> Select the minimum structural departure from the v2.1 semantics that satisfies all predeclared structural adequacy requirements.

For monotone candidate families, “minimum departure” must be defined in the correct parameter direction before evaluation.

No candidate or seed may be chosen because it produces a preferred winner distribution.

---

# 9. Technology-profile uncertainty under D1-B

Because D1-B is the primary estimand, technology-profile variation is already represented directly in the primary replication structure.

For each replication seed:

\[
W_r
=
\{\text{capability/response parameters, deployment parameters, and any frozen v2.2 response-shape parameters}\}
\]

is sampled once from the prespecified technology-profile distribution and reused across the complete factorial for that seed.

Therefore a separate technology-profile ensemble is **not required merely to establish cross-profile generalization**.

An additional reference-condition technology-profile ensemble may be added later only for a distinct purpose such as:

- variance decomposition;
- visualization of between-world geometry;
- targeted robustness to technology-profile distributional assumptions.

If added, its purpose, size, seed namespace, and analysis must be frozen independently. It must not duplicate the role of the 30 primary benchmark-instance seeds or be used to tune the primary technology-profile distribution.

No separate `G_tech` is frozen at this stage.

# 10. Existing G=50 block is an oracle ensemble

The current specification explicitly defines:

\[
G=50
\]

**oracle generators** at the reference data condition.

It varies:

- alpha;
- zeta;
- semantic interaction structure.

Its purpose is to test whether conclusions persist beyond one hand-crafted oracle.

v2.2 should rename this conceptually to:

**oracle-specification ensemble**

to distinguish it from any future technology-profile ensemble.

### Open oracle-ensemble implementation detail

The current primary oracle uses one scalar `reference_zeta`.

The research specification writes criterion-indexed ensemble draws \(\zeta_j^{(g)}\).

Before the oracle ensemble is implemented, v2.2 must explicitly decide whether ensemble zeta is:

- one scalar per oracle generator; or
- criterion-specific.

This issue is independent of the immediate technology-response redesign.

---

# 11. Downstream protocol decisions retained unless independently reopened

## 11.1 Permutation Importance at N=25

The current protocol uses context-block derangements.

At `N=25`, WEIGHT contains five contexts and:

\[
!5=44
\]

distinct derangements exist.

Twenty unique derangements are therefore computationally feasible.

Status:

**RETAIN current PI derangement protocol.**

Small-sample variance remains an empirical consequence of data scarcity, not a feasibility defect.

## 11.2 CRITIC and Entropy

Current primary:

**WEIGHT only**

Secondary fairness/robustness:

**FIT + WEIGHT**

This keeps the primary weighting comparison on the dedicated weight-calibration partition and avoids giving target-free methods automatically more rows than supervised/global-importance methods.

Status:

**RETAIN unless later evidence justifies reopening.**

## 11.3 TreeSHAP background Conflict 3

The fixed-TEST redesign makes a 100-row TreeSHAP background feasible at `N=25`.

The `{25,50,75}` candidate set is therefore explicitly reopened against the feasible 100-row candidate.

Status:

**OPEN, but deferred until the v2.2 benchmark geometry is frozen.**

---

# 12. Alpha-dispersion stress construction under D1-B — D3 ARCHITECTURE RESOLVED

The historical v2.1 alpha-dispersion stress mapping was computed once from an independent generator-dependent design pool.

Under D1-B, each replication seed defines a different technology-response world \(W_r\). Therefore the realized criterion-dispersion ordering can vary across benchmark instances. A single mapping such as “largest alpha to largest dispersion” is exact only with respect to the design distribution used to construct it; its realized alignment strength may vary by seed.

This consequence has now been independently reproduced on the already-inspected v2.2 design/diagnostic seeds `21001–21005` at `sigma_x=0`, `rho=0.4`, using FIT+WEIGHT only and excluding external TEST:

- pairwise Spearman correlation of criterion-dispersion ranks: minimum `0.636364`, median `0.781818`;
- largest-dispersion criterion by seed: `C5, C5, C8, C8, C8`;
- C8 ranks: `3, 2, 1, 1, 1`;
- C4 ranks: `5, 4, 2, 7, 8`;
- C6 rank: `9` for all five seeds;
- C9 rank: `10` for all five seeds.

These values are descriptive evidence from design seeds, not acceptance thresholds.

## 12.1 Prohibited solution

Do **not** recompute aligned/anti-aligned alpha assignments from each replication seed's FIT/WEIGHT data.

That would make the oracle stress structure seed/data-dependent and would change the estimand by coupling the oracle coefficients to the realized benchmark instance.

## 12.2 D3 decision

v2.2 adopts:

\[
\boxed{\text{D3-B: superpopulation-anchored fixed alpha-dispersion mapping}}
\]

After the v2.2 technology-response generator is frozen, construct an **independent technology-world design ensemble** excluded from FIT, WEIGHT, external TEST, structural-validation seeds, and primary seeds.

For design world \(w\), compute the attribution-relevant dispersion statistic:

\[
D_{j,w}^{attr}
=
\frac{1}{M_w}
\sum_i
\left|
q_j(g_{ijw})-\overline q_{j,w}
\right|.
\]

Aggregate across design worlds using one frozen superpopulation summary:

\[
\bar D_j^{attr}
=
E_W[D_{j,W}^{attr}],
\]

estimated only from the independent design ensemble.

The fixed aligned mapping is constructed once by assigning the largest alpha coefficient to the largest \(\bar D_j^{attr}\); the anti-aligned mapping reverses that ordering.

The resulting alpha mappings remain fixed across every development, validation, and primary benchmark instance.

## 12.3 Realized-alignment diagnostic

For each benchmark instance \(r\), compute the instance-specific dispersion vector \(D_{j,r}^{attr}\) and report the realized rank association between the frozen D3-B mapping and that instance's realized dispersion ordering as a diagnostic.

This diagnostic quantifies how strongly the superpopulation-level manipulation is expressed in a particular technology world. It does not trigger seed replacement or per-seed alpha reassignment.

## 12.4 D3 design-ensemble size — D3.1 RESOLVED

The D3-B superpopulation mapping will be estimated from a dedicated independent technology-world Monte Carlo ensemble after the v2.2 technology-response generator is frozen.

### D3.1 design

- master seed namespace: `74001`;
- child generation: `numpy.random.SeedSequence`;
- reserve: `400` deterministic child technology-world seeds;
- initial ensemble: `200` technology worlds;
- contexts per technology world: `1000` independent design contexts;
- reference dependence: `rho = 0.4`;
- criterion noise: `sigma_x = 0`;
- alternatives: all six;
- external TEST: excluded;
- development seeds `21001–21005`: excluded from the ensemble;
- structural-validation seeds `22001–22005`: excluded;
- primary seeds `11001–11030`: excluded.

The within-world attribution-relevant dispersion statistic is the frozen q-MAD definition:

\[
D_{j,w}^{attr}
=
\frac{1}{M_w}
\sum_i
\left|
q_j(g_{ijw})-\overline q_{j,w}
\right|.
\]

The superpopulation summary is the arithmetic mean:

\[
\bar D_j^{attr}
=
\frac{1}{W}
\sum_{w=1}^{W}
D_{j,w}^{attr}.
\]

### D3.1 convergence audit

Evaluate cumulative ensemble summaries at:

\[
W\in\{50,100,150,200\}.
\]

At `W=200`, compute the technology-world Monte Carlo standard error of every \(\bar D_j^{attr}\).

The initial 200-world ensemble is considered sufficiently converged only if both conditions hold:

1. the complete criterion ordering induced by \(\bar D_j^{attr}\) is identical at `W=150` and `W=200`;
2. for every criterion, the approximate 95% Monte Carlo confidence half-width satisfies

\[
1.96\,
\frac{MCSE(\bar D_j^{attr})}
     {\bar D_j^{attr}+\epsilon}
\le 0.05.
\]

The `0.05` here is a **Monte Carlo precision target** (maximum 5% relative 95% half-width), not a scientific effect-size threshold.

### Deterministic expansion rule

If either convergence condition fails at `W=200`, do not tune the ensemble size after inspecting preferred alpha mappings.

Instead, expand deterministically using the already-reserved child seeds to:

\[
W=400.
\]

Recompute the same convergence/precision audit at `W=400`.

If the criterion ordering or relative Monte Carlo precision remains unstable at 400 worlds, D3.1 fails and must be explicitly revised under a new protocol amendment before the alpha-stress mapping is frozen.

### D3.1 status

**D3.1 is RESOLVED.**

No D3-B ensemble is executed until the v2.2 technology-response generator itself has been frozen.

Historical v2.1 commit `9b9eb4f` remains valid as a record of the v2.1 mapping and is not rewritten.

---

# 13. Pilot-A redesign requirement

Historical v2.1 Pilot A used pooled five-seed warning flags:

- modal share above 0.60;
- fewer than three distinct oracle winners;

and those flags were not automatic rejection rules.

The structural audit demonstrated that pooled winner-focused warnings were insufficient to detect the normalization and decision-frontier issues.

v2.2 Pilot A must therefore be redefined before rerun.

Mandatory components should include:

- per-design-seed diagnostics;
- Layer-A non-separability/signal-survival diagnostics;
- Layer-B pairwise frontier diagnostics;
- constant-modal baseline regret/headroom;
- criterion-scale/oracle marginal geometry;
- structural dominance diagnostics.

Exact automatic-stop thresholds are **not frozen in this document**.

---

# 14. Structural metrics and threshold-freeze framework

This section freezes **what will be measured and how threshold classes will be derived** before any v2.2 candidate response family is executed.

It deliberately does not insert scientifically arbitrary numerical cutoffs.

## 14.1 Metric families frozen before candidate evaluation

### M-A1 — rank-one non-separability energy

For each criterion \(j\), form the systematic context-by-alternative matrix at `sigma_x=0`:

\[
G_j \in \mathbb R^{S\times A}.
\]

Let its singular values be:

\[
\sigma_{1j}\ge \sigma_{2j}\ge\cdots.
\]

Define:

\[
NS_j
=
1-
\frac{\sigma_{1j}^2}
{\sum_\ell \sigma_{\ell j}^2+\epsilon}.
\]

Properties:

- \(NS_j=0\) for an exact nonzero rank-one response matrix;
- it is scale-free;
- the historical v2.1 C1–C7 form is expected to lie at numerical-zero scale;
- a nonzero value is evidence of departure from pure multiplicative separability, not by itself evidence of scientific adequacy.

Structural-zero criteria/pairs are handled separately and are never “repaired” to increase this statistic.

### M-A2 — active pairwise log-ratio variability

For active alternatives \(a,b\) on criterion \(j\), and contexts where both systematic responses are above a prespecified numerical floor, define:

\[
LRV_{ab,j}
=
SD_s
\left[
\log
\frac{g_{asj}+\epsilon}
     {g_{bsj}+\epsilon}
\right].
\]

Under exact shared multiplicative separability:

\[
g_{asj}=\theta_{aj}c_{sj},
\]

the log ratio is context-invariant and \(LRV_{ab,j}\) is numerical zero.

Report the complete active-pair distribution by criterion rather than only one pooled average.

### M-A3 — normalized systematic signal survival

For normalization family \(m\), let:

\[
r^{(m)}_{sj}
=
(r^{(m)}_{1sj},\ldots,r^{(m)}_{Asj})
\]

be the within-context normalized alternative vector.

Define:

\[
NSV_{j,m}
=
\sqrt{
\frac{1}{S}
\sum_s
\left\|
r^{(m)}_{sj}
-
\bar r^{(m)}_j
\right\|_2^2
}.
\]

Compute this for:

- vector normalization;
- sum normalization;
- max normalization;
- min–max normalization.

The primary MCDM relevance is the vector-normalized value; the other three are structural robustness diagnostics.

### M-A4 — latent-factor reachability effect

For latent factor \(h_k\), use the model-consistent idiosyncratic-shock intervention defined in Section 4.

For every criterion \(j\), report:

\[
RE_{k,j}
=
\operatorname{median}_{s,a}
\left|
g_{asj}^{\,intervened(k)}
-
g_{asj}^{\,base}
\right|.
\]

Also report a scale-relative version:

\[
SRE_{k,j}
=
\frac{
RE_{k,j}
}{
IQR(g_j)+\epsilon
}.
\]

Only semantically intended factor-to-criterion pathways are evaluated as positive reachability requirements.

Reachability summaries are computed over **active alternative-pathways only** so that structural zeros do not mechanically force the median effect toward zero.

The scale-relative statistic \(SRE_{k,j}\) is the **primary reachability effect size** because raw absolute changes depend on the realized criterion scale. The raw statistic \(RE_{k,j}\) is reported alongside it as a secondary magnitude diagnostic.

The hard reachability invariant is operational only after its numerical/scientific threshold class is frozen under D2. Until then, reachability is mandatory to compute but is not assigned an arbitrary hard cutoff.

Winner changes are not used to define reachability.

### M-A5 — boundary and saturation geometry

For every criterion/alternative at `sigma_x=0`, record:

- mass at lower clipping boundary;
- mass at upper clipping boundary;
- p05 / median / p95;
- fraction of contexts within a small numerical neighborhood of either boundary.

Boundary mass is descriptive until a separate scientific saturation rule is frozen.

### M-A6 — structural Pareto dominance

Using direction-adjusted systematic \(G\), compute context-level ordered-pair Pareto dominance frequencies.

This is a structural pathology diagnostic. It must not be optimized to favor or disfavor a named ITS.

---

## 14.2 Layer-B metrics frozen before candidate evaluation

For the frozen primary oracle, compute:

### M-B1 — pairwise fixed-gap/context-interaction decomposition

\[
D_{ab,s}=G_{ab}+J_{ab,s}.
\]

Report for all unordered pairs:

\[
G_{ab},
\quad
SD(J_{ab}),
\quad
R_{ab}
=
\frac{SD(J_{ab})}{|G_{ab}|+\epsilon},
\quad
P_{\mathrm{cross},ab}.
\]

### M-B2 — constant modal-winner baseline

Report:

- modal oracle winner identity as descriptive metadata;
- modal winner share;
- Top-1 headroom:

\[
H=1-p_{\mathrm{modal}};
\]

- mean / median / p95 normalized oracle regret of always selecting the modal winner;
- conditional regret distribution when that baseline is non-optimal.

The named modal alternative must never be used as a tuning target.

### M-B3 — oracle decision-margin geometry

For each context:

\[
M_s
=
U^\star_{(1),s}
-
U^\star_{(2),s}.
\]

Report raw and within-context-range-normalized margin distributions.

### M-B4 — frontier-pair exposure

For every unordered pair \(a,b\), report the proportion of contexts in which \(\{a,b\}\) are the oracle top-two alternatives.

This distinguishes rich lower-rank pairwise crossing from context variation that actually reaches the decision frontier.

This metric is descriptive and is not a requirement that every alternative appear at the frontier.

---

## 14.3 Layer-C metrics frozen before candidate evaluation

At `sigma_x=0`, report:

### M-C1 — equal-weight MOORA systematic score variation

For every alternative, report across-context variation of the equal-weight primary MOORA score.

### M-C2 — MCDM ordering geometry

For MOORA and the TOPSIS robustness operator, report:

- distinct score orderings;
- distinct winners;
- modal winner share;
- score-margin distributions.

These are descriptive diagnostics only.

### M-C3 — latent-factor intervention on MCDM scores

Propagate the Layer-A model-consistent latent-factor intervention through the MCDM operator and record continuous score changes before considering winner changes.

No MCDM metric is allowed to serve as a generator target simply because it resembles the oracle more closely.

---

## 14.4 Numerical thresholds versus scientific thresholds

Every threshold used in v2.2 must be assigned to one of two classes.

### Class T-N — numerical discrimination threshold

Purpose:

> distinguish exact/near-exact structural collapse from floating-point noise.

For each metric that should be zero under an analytically separable null, construct an exact null using the same matrix dimensions and normalization implementation.

Define the numerical threshold from the null **before candidate execution**:

\[
T^{num}_m
=
\max
\left(
100\,Q_{0.999}(|m_{null}|),
T^{floor}_m
\right),
\]

where \(T^{floor}_m\) is a documented machine-precision floor appropriate to the metric.

The factor 100 is a numerical safety multiplier, not a scientific effect-size requirement.

The existing historical test tolerance `1e-7` remains a v2.1 characterization tolerance and is not automatically reused as every v2.2 metric threshold.

### Class T-S — scientific adequacy threshold

Purpose:

> distinguish merely nonzero structure from a substantively meaningful systematic effect.

Scientific thresholds must **not** be derived from:

- observed candidate winner counts;
- observed candidate modal shares;
- the candidate that looks best;
- primary seeds;
- external TEST;
- post-hoc comparison with SHAP performance.

Before any candidate response family is run, v2.2 must resolve Decision D2 and document the benchmark-scale smallest effects of interest used for scientific adequacy.

---

## 14.5 Decision D2 — SESOI calibration architecture RESOLVED

D2 adopts an ex-ante semantic anchor that existed before the v2.2 redesign, while explicitly separating **parameter-space meaning** from **response-space metric thresholds**.

### D2.1 Capability-amplitude anchor

The frozen v2.1 capability specification distinguishes structural zero from the weakest nonzero indirect-capability amplitude through:

\[
I \sim U(0.05,0.20).
\]

Therefore v2.2 adopts:

\[
\boxed{
\Delta_{\theta,\mathrm{cap}}^{min}=0.05
}
\]

as the benchmark's **minimum active capability-amplitude anchor**.

This is a parameter/capacity-space quantity. It is not claimed to be:

- a minimum realized context-specific response change;
- a universal additive difference in \(g\);
- a 5% multiplicative response change;
- a direct threshold for LRV, NSV, SRE, or oracle regret.

The distinction matters because for the historical C1–C7 architecture:

\[
g_{asj}=\theta_{aj}o_{sj},
\]

so the realized response associated with a capability amplitude depends on the context opportunity \(o_{sj}\).

At maximal opportunity \(o_{sj}=1\), an amplitude of `0.05` corresponds to a response capacity of `0.05`; away from maximal opportunity, the realized response is smaller.

### D2.2 No direct log-ratio conversion

v2.2 does **not** define a scientific LRV threshold by converting the `0.05` capability-amplitude anchor into a multiplicative percentage.

In particular, no identity of the form

\[
\Delta_{LR}^{min}=\log(1.05)
\]

is adopted as a benchmark scientific threshold.

That conversion would incorrectly equate an absolute capability-amplitude quantity with a 5% multiplicative response effect.

Instead, scientific reference values for M-A2 LRV, M-A3 NSV, M-A4 SRE, and any Layer-B regret quantity are obtained only by propagating a predeclared positive control whose response-space strength is calibrated to the `0.05` capability/capacity anchor.

### D2.3 Candidate-independent positive-control calibration

Before any candidate response family is executed, construct a **candidate-independent positive control** satisfying all of the following:

1. start from the historical systematic-response architecture at `sigma_x=0`;
2. preserve every structural-zero pathway exactly;
3. introduce a deterministic alternative-by-context differential component on active pathways;
4. use label-balanced alternative contrast assignments so that no named ITS is privileged;
5. preserve the declared latent-factor support of each criterion;
6. avoid criterion-boundary clipping in the calibration region;
7. normalize the perturbation analytically so that its maximum active-path response departure over the declared context domain is exactly:

\[
\Delta_{g,\mathrm{cap}}^{max}=0.05;
\]

8. use design/diagnostic seeds only;
9. exclude external TEST, structural-validation seeds, and primary seeds;
10. propagate the same control through the unchanged primary oracle for Layer-B calibration.

The positive control is a **measurement-calibration device**. It is not a candidate technology-response family and is not eligible to become the final generator.

The exact positive-control functional form and label-balancing construction must be committed before the control is executed. This remaining pre-candidate step is designated **D2.7**.

### D2.4 Metric-specific scientific references

D2 deliberately avoids imposing one raw SESOI value across metrics with different mathematical scales.

After D2.7 is frozen and executed, derive:

- \(T^{sci}_{LRV}\) from the positive-control M-A2 distribution;
- \(T^{sci}_{NSV}\) from the positive-control primary vector-normalized M-A3 distribution;
- \(T^{sci}_{SRE}\) from the positive-control M-A4 distribution;
- a Layer-B decision-sensitivity reference from the positive-control normalized regret of the constant modal-winner baseline, if that induced reference is stable and nonzero.

M-A1 rank-one non-separability energy remains primarily a numerical/corroborating structural diagnostic rather than receiving an independently invented scientific cutoff.

### D2.5 Gate hierarchy

The following hierarchy is frozen before candidate evaluation.

**Hard numerical structural invariants**

- structural zeros remain exact zeros;
- every intended context-responsive criterion/pathway with sufficient active support exceeds its T-N numerical-collapse threshold;
- primary vector-normalized systematic variation exceeds T-N for every intended context-responsive criterion/pathway;
- technology-profile pairing and data-separation invariants hold.

**Hard scientific Layer-A gate**

- candidate M-A2 and primary-vector M-A3 must meet the metric-specific scientific references derived from D2.7 under the predeclared design-seed aggregation rule.

**Reachability**

- SRE is primary and RE secondary;
- intended latent pathways must exceed numerical reachability;
- the scientific SRE reference is derived from D2.7 rather than from an arbitrary raw number.

**Layer-B decision sensitivity**

- winner identity and number of winners remain descriptive;
- if D2.7 yields a stable nonzero decision-sensitivity reference, the hard Layer-B quantity is based on normalized regret of the constant modal-winner baseline, not on the identity of the modal winner;
- if D2.7 cannot produce a stable defensible Layer-B reference, no numeric cutoff is invented; Layer-B remains an explicit frozen hard-stop question for the subsequent Pilot-A design.

### D2.6 Design-seed aggregation rule

For every D2.7 metric-specific scientific reference:

- calculate the positive-control metric separately for design seeds `21001–21005`;
- define the frozen reference from the **median across design seeds**;
- retain all per-seed values and ranges as diagnostics;
- never replace a design seed because its value is inconvenient.

Candidate evaluation later uses the same aggregation functional.

### D2.7 — Positive-control calibration protocol FROZEN BEFORE EXECUTION

This subsection freezes the complete positive-control construction and aggregation rules before any positive-control output is inspected.

The control targets the historically collapsed context-responsive block C1–C7. C8–C10 retain their historical `sigma_x=0` equations during this calibration and are not artificially perturbed.

#### D2.7.1 Reference scope

Use only:

- design/diagnostic seeds `21001–21005`;
- `rho = 0.4`;
- complete 1000-context FIT+WEIGHT estimation pool for each seed;
- `sigma_x = 0`;
- primary oracle transform/alpha/beta/interaction graph unchanged;
- `lambda = 0.5` for Layer-B propagation;
- external TEST excluded;
- structural-validation seeds excluded;
- primary seeds excluded.

#### D2.7.2 Label-balanced contrast schedule

Order alternatives by frozen alternative ID:

\[
(A1,A2,A3,A4,A5,A6).
\]

Define the zero-sum six-level contrast vector:

\[
\mathbf b
=
(-1,-0.6,-0.2,0.2,0.6,1).
\]

For rotation

\[
\ell\in\{0,1,2,3,4,5\},
\]

assign:

\[
c_a^{(\ell)}
=
b_{(i(a)+\ell)\bmod 6},
\]

where \(i(a)\in\{0,\ldots,5\}\) is the frozen alternative-ID index.

Across the six rotations, every named alternative receives every contrast coefficient exactly once. The calibration therefore cannot depend on choosing one favorable label-to-contrast assignment.

For a structural-zero pathway, the contrast coefficient is ignored and the response remains exactly zero.

#### D2.7.3 Positive-control response formula

For C1–C7, let the historical noise-free active response be:

\[
g_{asj}^{(0)}
=
\theta_{aj}o_{sj},
\]

with:

\[
0<\theta_{aj}\le0.4,
\qquad
0\le o_{sj}\le1.
\]

Set:

\[
\delta=0.05.
\]

For every active pathway under rotation \(\ell\), define:

\[
\boxed{
g_{asj}^{PC,\ell}
=
\left[
\theta_{aj}
+
\delta\,
c_a^{(\ell)}
(2o_{sj}-1)
\right]
o_{sj}
}
\]

and for every structural-zero pathway define:

\[
g_{asj}^{PC,\ell}=0.
\]

C8–C10 are copied unchanged from the historical `sigma_x=0` response generator.

This is a calibration device only. It is not an admissible v2.2 candidate generator.

#### D2.7.4 Analytic calibration properties

For active C1–C7 pathways:

\[
g_{asj}^{PC,\ell}
-
g_{asj}^{(0)}
=
\delta\,
c_a^{(\ell)}
(2o_{sj}-1)o_{sj}.
\]

Because:

\[
|c_a^{(\ell)}|\le1
\]

and:

\[
\max_{o\in[0,1]}
|(2o-1)o|
=
1,
\]

the exact domain-wide maximum response departure is:

\[
\boxed{
\max
|g^{PC}-g^{(0)}|
=
0.05.
}
\]

The effective amplitude satisfies:

\[
\theta_{aj}
+
0.05\,c_a^{(\ell)}(2o-1)
\in[0,0.45],
\]

because every active historical amplitude is at least `0.05` and at most `0.40`.

Therefore:

\[
g_{asj}^{PC,\ell}\in[0,0.45],
\]

so the positive-control construction does not require lower or upper clipping.

The control preserves the original criterion opportunity \(o_{sj}\), and therefore preserves the declared latent-factor support of each C1–C7 criterion while introducing genuine alternative-by-context differential response.

#### D2.7.5 Layer-A calibration summaries

For every seed \(r\), rotation \(\ell\), and criterion \(j\in\{C1,\ldots,C7\}\):

1. compute the complete active-pair M-A2 values \(LRV_{ab,j}^{r,\ell}\);
2. summarize them by:

\[
LRV50_{j}^{r,\ell}
=
\operatorname{median}_{a<b,\ active}
LRV_{ab,j}^{r,\ell};
\]

3. compute primary vector-normalized M-A3:

\[
NSV_{j,\mathrm{vector}}^{r,\ell}.
\]

For each seed, remove label-assignment dependence by taking the median over all six rotations:

\[
\widetilde{LRV50}_{j}^{r}
=
\operatorname{median}_{\ell}
LRV50_{j}^{r,\ell},
\]

\[
\widetilde{NSV}_{j}^{r}
=
\operatorname{median}_{\ell}
NSV_{j,\mathrm{vector}}^{r,\ell}.
\]

Freeze the criterion-specific scientific references as:

\[
\boxed{
T^{sci}_{LRV,j}
=
\operatorname{median}_{r\in design}
\widetilde{LRV50}_{j}^{r}
}
\]

and:

\[
\boxed{
T^{sci}_{NSV,j}
=
\operatorname{median}_{r\in design}
\widetilde{NSV}_{j}^{r}.
}
\]

M-A1 `NS_j`, max-LRV, min/max normalization diagnostics, and complete pairwise LRV distributions are reported but do not replace the frozen primary summaries above.

#### D2.7.6 Model-consistent reachability calibration

For the M-A4 reachability calibration, use a deterministic paired idiosyncratic-shock reflection.

For a latent factor \(k\) under the Gaussian-copula construction:

\[
\tilde h_{ks}
=
\sqrt{\rho}z_{0s}
+
\sqrt{1-\rho}z_{ks},
\]

construct the paired intervention:

\[
\tilde h_{ks}^{(-)}
=
\sqrt{\rho}z_{0s}
-
\sqrt{1-\rho}z_{ks},
\]

while holding \(z_{0s}\) and every other idiosyncratic shock fixed, then transform both through the standard-normal CDF.

This intervention is deterministic, uses no new random draw, preserves the factor's Gaussian idiosyncratic marginal symmetry, and is consistent with the frozen copula construction.

For each declared factor-to-criterion pathway, propagate the paired intervention through the positive-control response and calculate M-A4 over **active alternative-pathways only**.

Use SRE as primary and RE as secondary.

For each seed, take the median SRE across the six label rotations. The scientific reachability reference is:

\[
\boxed{
T^{sci}_{SRE,kj}
=
\operatorname{median}_{r\in design}
\operatorname{median}_{\ell}
SRE_{k,j}^{r,\ell}.
}
\]

No naive shuffle of observed correlated \(h_k\) values is permitted.

#### D2.7.7 Layer-B calibration

For every seed and rotation, propagate the complete positive-control response table through the unchanged primary oracle at:

\[
\lambda=0.5.
\]

Within each seed/rotation:

1. determine the modal oracle winner from the positive-control oracle itself;
2. always select that modal alternative;
3. compute context-wise normalized oracle regret using the existing frozen regret definition;
4. record mean, median, p95, non-optimal-context count, and conditional regret.

The primary Layer-B calibration quantity is **mean normalized constant-modal regret**:

\[
R_{PC}^{r,\ell}.
\]

Remove label-assignment dependence:

\[
\widetilde R_{PC}^{r}
=
\operatorname{median}_{\ell}
R_{PC}^{r,\ell}.
\]

Also compute the corresponding historical `sigma_x=0` baseline mean regret for the same seed:

\[
R_0^r.
\]

Define the paired uplift:

\[
\Delta R^r
=
\widetilde R_{PC}^{r}
-
R_0^r.
\]

A numeric Layer-B scientific reference is activated **only if**:

\[
\Delta R^r > T_R^{num}
\]

for all five design seeds.

If that predeclared directional-consistency condition holds, freeze:

\[
\boxed{
T_R^{sci}
=
\operatorname{median}_{r\in design}
\widetilde R_{PC}^{r}.
}
\]

If it does not hold, D2.7 does not invent another Layer-B number. The full Layer-B outputs are retained, and decision sensitivity remains an explicit hard-stop question for the frozen Pilot-A/Pilot-B design.

Winner identity and winner count never enter this activation rule.

#### D2.7.8 Numerical threshold for regret activation

For normalized regret, use:

\[
T_R^{num}=10^{-12}.
\]

This is solely a numerical nonzero discriminator for the paired uplift and not a scientific regret SESOI.

#### D2.7.9 Candidate-use rule

After D2.7 references are committed:

- every C1–C7 candidate criterion must exceed its T-N collapse threshold;
- the candidate's design-seed median `LRV50_j` must satisfy:

\[
LRV50_j^{candidate}
\ge
T^{sci}_{LRV,j};
\]

- the candidate's design-seed median primary-vector NSV must satisfy:

\[
NSV_j^{candidate}
\ge
T^{sci}_{NSV,j};
\]

- intended latent-factor pathways are compared against their frozen \(T^{sci}_{SRE,kj}\);
- if \(T_R^{sci}\) is activated, the candidate must also satisfy that frozen Layer-B reference under the same aggregation rule.

These are criterion/pathway-level requirements, not winner-balancing rules.


#### D2.7.11 Frozen numerical conventions

The following implementation conventions are frozen before the first D2.7 execution:

- positive-support floor for M-A2 LRV: `1e-12`;
- logarithm: natural logarithm;
- LRV standard deviation: population standard deviation (`ddof = 0`);
- normalization denominator epsilon: `1e-12`;
- SRE denominator epsilon: `1e-12`;
- regret denominator epsilon: `1e-12`;
- rank-one energy denominator epsilon: `1e-12`;
- IQR definition: `Q0.75 - Q0.25` using NumPy's linear quantile interpolation;
- p95 definition: NumPy linear quantile interpolation;
- alternative tie-breaking: ascending frozen alternative ID;
- modal-winner tie-breaking: ascending frozen alternative ID;
- criterion-specific active-pair summaries exclude structural-zero pathways;
- C8–C10 are never altered by the D2.7 positive control.

These values are numerical implementation conventions, not scientific effect-size thresholds.

The D2.7 implementation must refuse a full calibration run when the Git working tree is dirty, so the reported Git commit uniquely identifies the executed code/protocol state.

#### D2.7.10 Execution and provenance rule

The D2.7 protocol must be committed before the calibration script is executed.

The subsequent calibration output must record:

- Git commit;
- design seeds;
- reference condition;
- all six label rotations;
- per-seed/per-rotation metrics;
- frozen median references;
- whether the Layer-B activation condition fired;
- confirmation that external TEST, structural-validation seeds, and primary seeds were not used.

After D2.7 outputs and references are committed, the positive-control construction is closed and may not be altered to accommodate a candidate generator.

#### D2.7.12 Frozen calibration outcome

D2.7 was executed from Git commit `2f8cd1ae1bb17321ef55ca7b2e03b4ab5ee0ff87` after its protocol and implementation were committed.

The frozen criterion-specific Layer-A references and pathway-specific SRE references are recorded in `docs/v2_2_d2_7_calibration_results.md` and in machine-readable form in `results/v2_2_d2_7_positive_control/references.json`.

The preregistered Layer-B activation condition **did not fire** because the paired mean-regret uplift was not positive for all five design seeds; seed `21003` produced `-0.01383595455383882`.

Therefore no numeric `T_R_sci` is frozen. The positive control is not modified to force Layer-B activation.

D2.7 is now **CLOSED**.

### D2 status

**D2 SESOI calibration architecture is RESOLVED.**

What remains unresolved is not the semantic anchor but the **D2.7 positive-control functional form, label-balancing construction, and metric-specific reference values it induces**.

No candidate-family sweep may begin before D2.7 is specified, committed, executed, and its references frozen.

## 14.6 Candidate acceptance logic

Before candidate execution, v2.2 must classify each frozen metric as one of:

1. **hard structural invariant**;
2. **hard scientific adequacy gate**;
3. **warning diagnostic**;
4. **descriptive diagnostic**.

At minimum, the following are hard structural invariants:

- semantic zeros remain zero;
- technology-profile pairing under D1-B is preserved;
- external TEST and primary seeds remain unavailable;
- intended active context-responsive pathways are not numerically separable under the primary response architecture;
- every intended context-responsive criterion/pathway with sufficient active alternative support retains systematic variation above its numerical-collapse threshold under the primary vector normalization;
- intended latent factors are computationally reachable through their declared pathways.

Layer-B winner counts and named-winner identities are never candidate-selection gates.

A **Layer-A-only repair is insufficient for generator freeze**. During design-seed candidate evaluation at \(\sigma_x=0\), the complete frozen Layer-B battery (M-B1 through M-B4) must be computed immediately from the candidate responses using the unchanged primary oracle. This occurs before criterion-noise calibration and before implementation freeze.

If D2 later assigns a hard scientific Layer-B decision-sensitivity gate, a candidate must satisfy that gate before the systematic response architecture can be frozen. If a defensible hard Layer-B threshold cannot be justified, the corresponding metrics remain warning/descriptive diagnostics and the absence of a hard cutoff must be stated explicitly rather than replaced by a post-hoc winner rule.

If a candidate passes Layer-A structural requirements but fails any frozen Layer-B/Pilot-A hard stop, the correct action is protocol failure/version bump, not iterative winner tuning.

---

## 14.7 Minimum-departure selection rule

Only after D2 and all hard/warning classifications are frozen may candidate families be evaluated on design seeds.

Among candidates that satisfy every hard requirement, select according to the predeclared minimum-departure rule.

“Minimum departure” must be expressed in terms of the candidate-family parameterization and semantic distance from v2.1 **before results are viewed**.

Examples:

- smallest alternative-specific shape spread;
- largest concentration parameter when larger concentration is closer to the v2.1 shared-mixture structure;
- fewest newly introduced response-shape degrees of freedom.

Winner diversity, oracle modal share, SHAP performance, or a preferred ITS identity may not enter the minimum-departure objective.

---

## 14.8 Statistical precision is a separate threshold class

Power/precision requirements for the final inferential analysis are not generator adequacy thresholds.

They will be derived only after:

- D1-B benchmark-instance clustering is respected;
- the repeated-seed mixed-effects specification is frozen;
- method is represented as a paired within-instance factor.

The 200 external TEST contexts within a seed are evaluation observations, not 200 independent replication units for population-level inference.

# 15. v2.2 implementation order

The following order supersedes the obsolete v2.1 immediate-order section for the redesign branch.

1. Commit the historical v2.1 structural audit (`b953fb1`) — **done**.
2. Freeze this v2.2 design specification.
3. D1 resolved: superpopulation benchmark-instance estimand; preserve within-seed technology-profile pairing.
4. D2/D2.7 positive-control calibration and metric-specific Layer-A/reachability references frozen — **done**.
5. Declare v2.2 structural-validation seeds before candidate evaluation.
6. Define candidate response families without running primary seeds or external TEST.
7. Evaluate candidate families on v2.2 design seeds at `sigma_x=0`, computing the frozen Layer-A metrics and the complete Layer-B battery M-B1 through M-B4 before any generator freeze.
8. Select/freeze the systematic response architecture only under the predeclared minimum-departure rule and all applicable frozen Layer-A/Layer-B hard requirements.
9. Calibrate/freeze criterion noise relative to the systematic signal.
10. Implement the frozen v2.2 generator and replace/retire the historical v2.1 characterization tests with v2.2 invariant tests.
11. Revalidate Step 1/Step 2 architecture and rerun the pre-oracle diagnostics.
12. Recompute oracle utility and relative-noise target generation.
13. Redefine and run v2.2 Pilot A on design seeds.
14. Run one-shot v2.2 structural validation on the untouched validation seeds.
15. Recompute/freeze the generator-dependent alpha-dispersion stress mappings.
16. Implement/validate closed-form oracle Shapley.
17. Resume XGBoost development calibration.
18. Resolve TreeSHAP background Conflict 3.
19. Implement weighting/decision pipeline and run Pilot B.
20. Run bootstrap and prespecified robustness analyses.
21. Freeze statistical analysis and measure one complete reference replication.
22. Commit final frozen v2.2 state and create `spec-v2.2`.
23. Only then unlock primary seeds `11001–11030`.

No primary factorial run is authorized before Step 22.

---

# 16. Explicitly unresolved v2.2 decisions

The following items are intentionally unresolved:

- exact v2.2 response family;
- fixed versus random response-shape parameters within a benchmark instance;
- structural adequacy thresholds;
- criterion-noise signal-share definition and final `sigma_x`;
- whether an optional reference-condition technology-profile ensemble is scientifically useful beyond the D1-B primary replication structure;
- `G_tech` size only if such an optional ensemble is later justified;
- exact v2.2 Pilot-A automatic-stop rules;
- TreeSHAP background candidate set/size;
- oracle-ensemble scalar versus criterion-specific zeta;
- final v2.2 statistical power/precision specification.

These decisions must be resolved by explicit protocol amendments before implementation reaches the corresponding dependency.

---

# 17. Prohibited actions while this document is under review

Until the v2.2 design specification is frozen:

- do not modify `config/benchmark.yaml`;
- do not modify generator equations;
- do not modify the capability mask;
- do not modify primary alpha;
- do not modify zeta;
- do not change DSM or another alternative to alter rankings;
- do not sweep kappa/gamma or other candidate parameters;
- do not inspect primary seeds;
- do not use external TEST for design;
- do not resume Step 6 / Oracle Shapley;
- do not create `spec-v2.2`.

The next action is to pre-register the v2.2 candidate response families and their minimum-departure ordering before any candidate-family execution — not tune them.
