# Research Specification v2.0

## Project

**Title:** Validating SHAP-Derived Decision Weights for ITS Prioritisation under Data Scarcity: A Controlled XAI-MCDM Benchmark

**Repository:** `SWFC`

**Computational environment:** Conda environment `swfc`, Python 3.11

**Status:** Pre-implementation scientific specification. The primary experiment must not be executed until this document, the machine-readable configuration files, the environment lock file, and the implementation smoke tests are committed. The final frozen version should be identified by a Git tag (recommended: `spec-v2.0`).

**Terminology rule:** use *pre-specified*, *frozen before execution*, or *version-controlled protocol*. Do not use *preregistered* unless the protocol is actually deposited in a public preregistration service.

---

# 1. Scientific Objective

The study investigates whether predictive feature attributions can be compressed into global criterion weights without materially degrading downstream multi-criteria decisions.

The study does **not** claim novelty from combining XGBoost, SHAP and MCDM. The central scientific question is:

> Under what conditions does predictive attribution preserve decision-relevant importance well enough to support a downstream multi-criteria ranking?

The benchmark is intentionally controlled and synthetic so that the noise-free decision utility, the attribution reference and the final decision loss are all auditable.

The benchmark does not represent observed traffic data from Tunisia and must not be interpreted as an empirical recommendation for a specific city or corridor.

---

# 2. Contribution Boundary

The contribution is the controlled audit of the chain:

\[
\text{Prediction}
\rightarrow
\text{Attribution}
\rightarrow
\text{Global weight compression}
\rightarrow
\text{MCDM decision}.
\]

Synthetic ground-truth XAI benchmarking already exists. Therefore, the study does not claim novelty from using a synthetic oracle or from computing reference Shapley values. The distinct contribution is the downstream evaluation of whether attribution fidelity survives conversion into global decision weights and, ultimately, into rankings and decision regret.

The study also explicitly separates supervised from unsupervised weighting baselines so that any advantage of SHAP is not confused with the more general advantage of having access to the prediction target.

---

# 3. Research Questions

## RQ1 — Predictive fidelity

How does data scarcity affect the ability of XGBoost to recover a known nonlinear ITS utility out of sample?

## RQ2 — Attribution fidelity

How accurately do XGBoost-TreeSHAP global weights recover oracle interventional Shapley importance under different levels of predictor dependence, signal-to-noise ratio and interaction strength?

## RQ3 — Decision fidelity

Does accurate attribution recovery translate into high ranking agreement and low decision regret after the attribution structure is compressed into a global weight vector and propagated through MOORA?

## RQ4 — Comparative value and validity boundaries

Does SHAP weighting outperform simpler supervised and unsupervised alternatives, and under which combinations of scarcity, dependence, noise, interaction strength and distribution shift does the predictive-importance-to-decision-weight transition become unreliable?

---

# 4. Fundamental Experimental Unit

Let:

- \(a=1,\ldots,6\) denote ITS alternatives,
- \(s=1,\ldots,N\) denote independent transport contexts,
- \(j=1,\ldots,10\) denote evaluation criteria.

Every context is evaluated under all six alternatives. Therefore, one context generates a complete:

\[
6\times10
\]

decision matrix.

The row-level observation is an alternative-context pair \((a,s)\), but the statistically independent unit used for splitting, resampling and uncertainty analysis is the **context** \(s\).

Rows belonging to the same context must never be split across fit, weight-calibration and test partitions.

---

# 5. ITS Alternatives

| ID | Alternative | Abbreviation |
|---|---|---|
| A1 | Adaptive Traffic Signal Control | ATSC |
| A2 | Transit Signal Priority | TSP |
| A3 | Traffic Incident Detection and Management | TIDM |
| A4 | Real-Time Multimodal Traveller Information and Dynamic Route Guidance | RMTI-DRG |
| A5 | V2X Cooperative Safety Services | V2X-CS |
| A6 | Dynamic Speed Management | DSM |

## A1 — Adaptive Traffic Signal Control

Network or corridor signal timing that dynamically adapts phase, split, offset or cycle decisions according to observed demand.

## A2 — Transit Signal Priority

Priority requests and signal responses intended to reduce transit delay and improve transit reliability while retaining general traffic control.

## A3 — Traffic Incident Detection and Management

Detection, verification, response coordination, traveller warning and recovery actions addressing non-recurring congestion and safety events.

## A4 — Real-Time Multimodal Traveller Information and Dynamic Route Guidance

Real-time information, disruption advisories and route or mode guidance delivered through roadside, web or mobile interfaces.

## A5 — V2X Cooperative Safety Services

Vehicle-to-everything communication supporting cooperative safety warnings and connected-roadway safety applications. Adaptive signal timing and transit-priority control are explicitly excluded because those functions are already represented by ATSC and TSP.

## A6 — Dynamic Speed Management

Real-time adjustment of regulatory or advisory speed limits according to traffic, roadway, incident or weather conditions to harmonise speeds, smooth flow and improve safety and reliability.

The six alternatives are compared as first-stage deployment priorities, not as mutually exclusive technologies that could never coexist in a future portfolio.

---

# 6. Evaluation Criteria

The benchmark uses ten technology-neutral criteria. Nine are benefits and one is an original cost criterion.

| Code | Criterion | Original direction |
|---|---|---|
| C1 | Mobility-efficiency improvement | Benefit |
| C2 | Travel-time reliability improvement | Benefit |
| C3 | Person-throughput improvement | Benefit |
| C4 | Safety-surrogate improvement | Benefit |
| C5 | Non-recurring-congestion resilience | Benefit |
| C6 | Environmental-efficiency improvement | Benefit |
| C7 | User and accessibility benefit | Benefit |
| C8 | Infrastructure and data readiness | Benefit |
| C9 | Interoperability and scalability | Benefit |
| C10 | Annualised lifecycle deployment burden | Cost |

All generated criterion scores are stored on \([0,1]\). C10 is transformed once into a higher-is-better score before supervised learning, objective weighting and MCDM aggregation.

---

# 7. Structural Capability Mask

For C1-C7, technology-criterion relationships are classified as:

- `D` = direct functional pathway,
- `I` = indirect functional pathway,
- `0` = no primary pathway in the benchmark.

These are structural assumptions, not empirical effect estimates.

| Alternative | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Readiness requirement | Interoperability | Burden |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSC | D | D | D | I | I | I | I | M | H | M |
| TSP | I | D | D | I | 0 | I | D | M | H | L-M |
| TIDM | I | D | I | D | D | I | I | M | H | M |
| RMTI-DRG | I | I | I | I | D | I | D | L-M | H | L-M |
| V2X-CS | I | I | 0 | D | I | I | I | H | H | H |
| DSM | D | D | I | D | D | I | I | M-H | H | M-H |

The mask must not be changed after primary results are inspected in order to favour a desired ITS ranking.

---

# 8. Latent Context Generator and Dependence CRN

Each context contains five latent factors:

\[
\mathbf h_s=(h_{D,s},h_{I,s},h_{T,s},h_{E,s},h_{R,s}),
\]

representing demand pressure, incident pressure, transit/person-movement intensity, environmental sensitivity and digital/infrastructure readiness.

To create an equicorrelated Gaussian copula while preserving common random numbers across dependence conditions, generate once per context:

\[
z_{0,s},z_{1,s},\ldots,z_{5,s}\overset{iid}{\sim}\mathcal N(0,1),
\]

and define, for factor \(k\in\{1,\ldots,5\}\),

\[
\tilde h_{k,s}^{(\rho)}
=
\sqrt{\rho}\,z_{0,s}
+
\sqrt{1-\rho}\,z_{k,s}.
\]

Then:

\[
h_{k,s}^{(\rho)}=\Phi(\tilde h_{k,s}^{(\rho)}).
\]

This construction gives unit marginal variance and pairwise covariance \(\rho\), while reusing exactly the same base normal draws at \(\rho\in\{0,0.4,0.8\}\).

The equicorrelation structure is a controlled experimental device and is not claimed to reproduce the joint distribution of a specific city.

---

# 9. Opportunity Functions

For the first seven criteria:

\[
o_{s1}=h_{D,s},
\]

\[
o_{s2}=0.60h_{D,s}+0.40h_{I,s},
\]

\[
o_{s3}=0.60h_{D,s}+0.40h_{T,s},
\]

\[
o_{s4}=0.50h_{D,s}+0.50h_{I,s},
\]

\[
o_{s5}=h_{I,s},
\]

\[
o_{s6}=0.60h_{D,s}+0.40h_{E,s},
\]

\[
o_{s7}=0.40h_{D,s}+0.60h_{T,s}.
\]

All opportunity values remain in \([0,1]\).

---

# 10. Alternative-Specific Technology Responses

For C1-C7, the alternative-criterion response amplitude \(\delta_{aj}\) is sampled once per primary replication seed and held fixed across all factorial conditions for that seed.

If the structural pathway is `0`:

\[
\delta_{aj}=0.
\]

If the pathway is indirect:

\[
\delta_{aj}\sim U(0.05,0.20).
\]

If the pathway is direct:

\[
\delta_{aj}\sim U(0.20,0.40).
\]

The realized benefit score is:

\[
x_{asj}
=
\operatorname{clip}
\left(
\delta_{aj}o_{sj}^{\nu_j}
+
\eta_{asj},
0,
1
\right),
\qquad j=1,\ldots,7.
\]

Reference condition:

\[
\nu_j=1.
\]

Criterion-level performance noise uses common random numbers:

\[
\xi_{asj}\sim N(0,1),
\qquad
\eta_{asj}=\sigma_x\xi_{asj},
\]

with:

\[
\sigma_x=0.02.
\]

The same \(\xi_{asj}\) realization is reused across experimental factor levels for a given replication seed.

---

# 11. Readiness, Interoperability and Burden Classes

Base structural classes are:

\[
L\sim U(0.25,0.40),
\]

\[
M\sim U(0.45,0.60),
\]

\[
H\sim U(0.65,0.80).
\]

Compound classes are equal-probability mixtures of their component classes rather than continuous intervals spanning the gap:

\[
L\text{-}M:\quad \tfrac12 U(0.25,0.40)+\tfrac12 U(0.45,0.60),
\]

\[
M\text{-}H:\quad \tfrac12 U(0.45,0.60)+\tfrac12 U(0.65,0.80).
\]

For alternative \(a\):

- \(r_a\) = readiness requirement,
- \(\iota_a\) = interoperability parameter,
- \(\kappa_a\) = base lifecycle burden.

These parameters are sampled once per primary replication seed and reused across the factorial conditions for that seed.

---

# 12. Technical and Deployment Criterion Functions

## C8 — Infrastructure and data readiness

Use a one-sided readiness shortfall:

\[
x_{as8}
=
\operatorname{clip}
\left(
1-\max(0,r_a-h_{R,s})+\eta_{as8},
0,
1
\right).
\]

A context that exceeds the technology's readiness requirement is therefore not penalized for being *too ready*.

## C9 — Interoperability and scalability

\[
x_{as9}
=
\operatorname{clip}
\left(
\iota_a+0.10h_{R,s}+\eta_{as9},
0,
1
\right).
\]

## C10 — Annualised lifecycle deployment burden

\[
x_{as,10}
=
\operatorname{clip}
\left(
\kappa_a+0.20(1-h_{R,s})r_a+\eta_{as,10},
0,
1
\right).
\]

C10 remains the original cost criterion.

---

# 13. Common Direction Orientation

Before supervised learning, objective weighting and MCDM aggregation, define:

\[
g_{asj}=x_{asj},\qquad j=1,\ldots,9,
\]

and:

\[
g_{as,10}=1-x_{as,10}.
\]

Thus every \(g_{asj}\) is higher-is-better.

The original cost label is retained in metadata for interpretation, but the computational pipeline must not mix weights derived on \(g_{10}=1-x_{10}\) with an inconsistent cost formulation applied to \(x_{10}\).

---

# 14. Monotone Nonlinear Transform

For each criterion:

\[
q_j(g)=
\frac{\log(1+\zeta_jg)}{\log(1+\zeta_j)},
\qquad \zeta_j>0.
\]

Reference:

\[
\zeta_j=2\quad\forall j.
\]

This maps \([0,1]\) to \([0,1]\) and is strictly increasing.

---

# 15. Primary Heterogeneous Oracle Main Effects

Equal \(\alpha_j\) values would make the additive oracle-attribution magnitude strongly driven by predictor dispersion. The primary oracle therefore uses a heterogeneous but domain-neutral coefficient profile.

The coefficient multiset is:

\[
(0.16,0.14,0.13,0.12,0.11,0.10,0.08,0.07,0.05,0.04),
\]

which sums to one.

A dedicated design seed (`73001`) was used once to permute this multiset across the ten criterion labels before any primary result was generated. The frozen primary mapping is:

| Criterion | Primary \(\alpha_j\) |
|---|---:|
| C1 | 0.11 |
| C2 | 0.04 |
| C3 | 0.05 |
| C4 | 0.07 |
| C5 | 0.10 |
| C6 | 0.14 |
| C7 | 0.12 |
| C8 | 0.16 |
| C9 | 0.08 |
| C10 | 0.13 |

This assignment is fixed across all primary seeds and factorial conditions.

The purpose of the random permutation is to introduce meaningful heterogeneity without encoding an analyst preference for a particular ITS technology.

---

# 16. Alpha-Dispersion Alignment Stress Test

A secondary controlled diagnostic tests whether information-based weighting methods benefit from accidental alignment between oracle relevance and criterion dispersion.

The frozen heterogeneous alpha mapping defined in Section 15 remains the primary oracle structure and is not altered by this stress test.

At the reference experimental condition only, three additional structures are evaluated:

1. **Balanced:** \(\alpha_j=0.10\) for all ten criteria.
2. **Dispersion-aligned:** pair the descending heterogeneous alpha multiset with criteria ordered from largest to smallest attribution-relevant dispersion.
3. **Dispersion-anti-aligned:** pair the same descending alpha multiset with criteria ordered from smallest to largest attribution-relevant dispersion.

## Independent design pool

The assignment-defining dispersion ordering is calculated once from a dedicated independent design pool containing:

\[
N_{\mathrm{design}}=5000
\]

independent contexts. Each context contains the complete set of six ITS alternatives, giving:

\[
5000\times6=30000
\]

alternative-context observations per criterion. No context-level or alternative-level averaging is performed before the assignment-defining dispersion statistic is calculated.

The pool uses the reference predictor-dependence condition \(\rho=0.4\) and the dedicated `alpha_stress_design_pool` namespace (`72001`). Deterministic child `SeedSequence` streams generate and freeze the latent contexts, technology-response parameters and criterion-response noise. These quantities are generated once and do not vary with primary replication seeds.

The independent design pool is excluded from FIT, WEIGHT, external TEST, model fitting, hyperparameter calibration, TreeSHAP background construction, global weight estimation and final decision evaluation.

## Attribution-relevant dispersion definition

Let the reference oracle transform be:

\[
q(g)=\frac{\log(1+2g)}{\log 3}.
\]

For criterion \(j\), define the assignment-relevant dispersion directly on the raw direction-adjusted criterion scores after the reference \(q\) transformation:

\[
D_j^{\mathrm{attr}}
=
\frac{1}{30000}
\sum_{(a,s)\in\mathcal D_{\mathrm{design}}}
\left|
q(g_{asj})-
\overline{q(g_j)}
\right|.
\]

No criterion-wise min-max transformation is applied before \(q\). This statistic is used because the main-effect oracle attribution magnitude is directly driven by deviations of \(q_j(g_j)\) from its background mean.

For the dispersion-aligned structure, the largest alpha is assigned to the criterion with the largest \(D_j^{\mathrm{attr}}\), descending thereafter. For the dispersion-anti-aligned structure, the largest alpha is assigned to the criterion with the smallest \(D_j^{\mathrm{attr}}\), ascending thereafter. Criterion index is used only as a deterministic tie-breaker.

The resulting ordering and aligned/anti-aligned alpha assignments are computed once and frozen before any weighting-method comparison. These structures remain reference-condition-only diagnostics and are not crossed with the 4050-run primary factorial.

## Secondary shape-dispersion diagnostic

The previously specified criterion-wise min-max followed by population standard deviation (`ddof=0`) is retained only as a secondary shape-dispersion diagnostic. It does not define or update the aligned or anti-aligned alpha assignments.

## Descriptive realized-dispersion diagnostic

For each replication, the Spearman association between the frozen primary alpha vector and realized FIT-partition attribution-relevant dispersion may be recorded descriptively using the same \(q(g)\)-MAD convention. This diagnostic cannot modify the primary alpha mapping, the generator, the stress-test assignments or any weighting method.
---

# 17. Oracle Interaction Structure

The interaction graph is:

\[
\mathcal E=
\{(1,2),(3,7),(4,5),(6,10),(8,9)\}.
\]

Interpretations:

- C1-C2: mobility and reliability,
- C3-C7: person throughput and user benefit,
- C4-C5: safety and resilience,
- C6-C10: environmental efficiency and deployment efficiency,
- C8-C9: readiness and interoperability.

Reference interaction coefficients are:

\[
\beta_{jk}=\frac{1}{|\mathcal E|}=0.20.
\]

The oracle utility is:

\[
U^\star_{as}
=
\frac{
\sum_{j=1}^{10}\alpha_jq_j(g_{asj})
+
\lambda
\sum_{(j,k)\in\mathcal E}
\beta_{jk}q_j(g_{asj})q_k(g_{ask})
}{1+\lambda}.
\]

Interaction strength:

\[
\lambda\in\{0,0.5,1.0\}.
\]

Because all coefficients are nonnegative and each \(q_j\) is increasing, the oracle remains monotone in every direction-adjusted criterion.

---

# 18. Signal-Relative Observation Noise

Absolute noise levels would be confounded with factors that change \(\operatorname{sd}(U^\star)\). Observation noise is therefore defined relative to the oracle signal scale.

For every replication seed and every \((\rho,\lambda)\) condition, compute the noise-free oracle utility on the complete **1000-context estimation/calibration master pool only**, excluding the fixed external TEST pool, and define:

\[
s_U=\operatorname{sd}(U^\star).
\]

Generate once:

\[
e_{as}\sim N(0,1),
\]

and for relative-noise factor \(c\):

\[
Y_{as}=U^\star_{as}+c\,s_U e_{as}.
\]

The primary levels remain:

\[
c\in\{0.10,0.30,0.60\}.
\]

The same base standard-normal target-noise draw is reused across \(c\) levels under the common-random-number design. The fixed external TEST contexts receive noisy targets using the same condition-specific \(c\,s_U\) scale but contribute nothing to the estimation of \(s_U\).

Do not clip the noisy target and do not multiply it by 100. Record imposed noise SD, realized noise SD and realized SNR. Decision fidelity is always evaluated against the noise-free oracle utility $U^\star$, not against the noisy learning target $Y$.
---

# 19. Meaning of the Oracle

The oracle is an internally defined benchmark construct.

It is:

- not a causal ground truth,
- not a stakeholder preference function,
- not a social welfare function,
- not an empirical utility calibrated for Tunisia.

Its role is methodological: to provide a known reference against which prediction, attribution and downstream decision fidelity can be measured.

---

# 20. Estimation / Weight-Calibration / Fixed External TEST Architecture

Each replication seed contains two non-overlapping context pools:

1. a **1000-context estimation/calibration master pool**;
2. a **fixed 200-context external TEST pool**.

The experimental sample-size factor \(N\) refers only to the number of estimation/calibration contexts available before the external TEST. The TEST pool is therefore not counted in \(N\).

Within every nested \(N\)-context estimation subset:

- **80% are FIT contexts**;
- **20% are WEIGHT contexts**.

The 200 external TEST contexts are identical across every \(N\) condition for the same replication seed.

## FIT partition

FIT contexts are used to:

- fit XGBoost;
- fit Ridge+;
- choose Ridge+ regularization by grouped CV within FIT;
- provide TreeSHAP background rows;
- compute oracle background moments.

## WEIGHT partition

WEIGHT contexts are used to:

- average SHAP attributions into global SHAP weights;
- average oracle attributions into oracle attribution weights;
- calculate permutation importance;
- calculate primary CRITIC weights;
- calculate primary entropy weights;
- estimate the modal-winner diagnostic when required.

CRITIC and Entropy may additionally be recomputed on FIT plus WEIGHT as a secondary fairness/robustness analysis, but their primary comparison uses WEIGHT only.

## Fixed external TEST pool

The 200 external TEST contexts are used only for:

- final predictive metrics;
- Direct-XGBoost ranking;
- final MCDM rankings;
- Kendall agreement;
- Top-1 accuracy;
- decision regret;
- decision-margin analysis.

No external TEST context may contribute to model fitting, hyperparameter selection, TreeSHAP background construction, SHAP global-weight estimation, oracle global-weight estimation, permutation importance, Ridge+ fitting, CRITIC/Entropy weight estimation or method tuning.
---

# 21. Nested Estimation Sample Sizes and Fixed External TEST Membership

For each replication seed, generate a total master pool of 1200 contexts.

- Context numbers 1--1000 form the estimation/calibration master pool.
- Context numbers 1001--1200 form the fixed external TEST pool.

Within the first 1000 contexts, divide the deterministic nested order into consecutive blocks of five. Each block contains exactly:

- four `FIT` roles;
- one `WEIGHT` role.

The role order is shuffled deterministically within each block using the partition-specific seed stream. The assignment is generated once per replication seed and reused across \(N\) and \(\rho\).

The scarcity subsets are exact prefixes of the same 1000-context estimation master order:

\[
\mathcal S_{25}
\subset
\mathcal S_{50}
\subset
\mathcal S_{100}
\subset
\mathcal S_{250}
\subset
\mathcal S_{1000}.
\]

Hence the exact context counts are:

| \(N\) | FIT | WEIGHT | fixed TEST |
|---:|---:|---:|---:|
| 25 | 20 | 5 | 200 |
| 50 | 40 | 10 | 200 |
| 100 | 80 | 20 | 200 |
| 250 | 200 | 50 | 200 |
| 1000 | 800 | 200 | 200 |

The 200 external TEST context identifiers are invariant across every \(N\). Across \(\rho\), both estimation and external TEST pools reuse their own underlying Gaussian CRN streams; realized contextual variables may change with \(\rho\), but context identities and base random streams remain fixed.

The original estimation-context stream is preserved under namespace `1001`. A separate deterministic namespace `1002` generates the fixed external TEST contexts. This prevents the addition of TEST contexts from changing the previously validated first 1000 context draws.
---

# 22. Oracle Interventional Shapley Definition

Let \(F=\{1,\ldots,p\}\). For an observation \(\mathbf g\) and subset \(S\subseteq F\), define the interventional value function:

\[
v^\star(S;\mathbf g)
=
E_{\mathbf G_{\bar S}\sim P_{bg}}
\left[
U^\star(\mathbf g_S,\mathbf G_{\bar S})
\right],
\]

where \(P_{bg}\) is represented by joint background rows drawn exclusively from the fit partition.

This is a marginal/interventional expectation, not a conditional expectation of missing features given observed features.

---

# 23. Closed-Form Oracle Shapley

Define:

\[
z_j=q_j(g_j),
\]

\[
\mu_j=E_{bg}[q_j(G_j)],
\]

and for every interaction pair:

\[
\mu_{jk}
=
E_{bg}[q_j(G_j)q_k(G_k)].
\]

**Important:** \(\mu_{jk}\) is the joint moment computed on the same background rows. It must not be replaced by \(\mu_j\mu_k\) when predictors are dependent.

For a main-effect term:

\[
\phi_j^{main}
=
\alpha_j(z_j-\mu_j).
\]

For an interaction term \(\beta_{jk}z_jz_k\), feature \(j\)'s interventional Shapley allocation is:

\[
\phi_j^{(jk)}
=
\frac{\beta_{jk}}{2}
\left[
 z_j\mu_k-\mu_{jk}
 +
 z_jz_k-\mu_jz_k
\right],
\]

with the symmetric expression for feature \(k\).

Therefore:

\[
\phi_j^\star(\mathbf g)
=
\frac{1}{1+\lambda}
\left[
\alpha_j(z_j-\mu_j)
+
\lambda
\sum_{k:(j,k)\in\mathcal E}
\phi_j^{(jk)}
\right],
\]

with symmetric handling when \(j\) is the second element of an interaction pair.

The closed-form implementation is the production implementation.

Exhaustive coalition enumeration is used only as a unit-test oracle on a small validation sample.

Required numerical tolerance:

\[
\max_j
|\phi_j^{closed}-\phi_j^{enum}|
<10^{-10}
\]

subject to normal floating-point precision.

Also test Shapley efficiency:

\[
E_{bg}[U^\star(\mathbf G)]
+
\sum_j\phi_j^\star(\mathbf g)
=
U^\star(\mathbf g)
\]

within numerical tolerance.

---

# 24. Oracle Global Attribution Weights

Oracle attributions are evaluated on the weight-calibration contexts using moments/background from the fit partition.

Global oracle importance:

\[
I_j^\star
=
\frac{1}{n_{weight}}
\sum_{i\in weight}
|\phi_{ij}^\star|.
\]

Oracle attribution weights:

\[
w_j^\star
=
\frac{I_j^\star}{\sum_k I_k^\star}.
\]

These are attribution-reference weights, not normative stakeholder weights.

---

# 25. XGBoost Protocol

XGBoost predicts \(Y\) from the ten direction-adjusted criteria \(\mathbf g\).

Hyperparameters are calibrated once on separate development seeds that are never used in the primary experiment. After development, the selected hyperparameters are committed and frozen.

The primary factorial experiment must not run a fresh hyperparameter search in each cell.

Primary test metrics:

- \(R^2\),
- MAE,
- RMSE.

Point estimates are calculated over held-out alternative-context rows, with uncertainty intervals clustered/resampled at the context level.

---

# 26. TreeSHAP Protocol

Use `TreeExplainer` with:

- `feature_perturbation="interventional"`;
- background rows drawn exclusively from FIT;
- TreeSHAP explanations evaluated on WEIGHT.

The background size is calibrated only on development seeds and then frozen before any primary execution.

The fixed-external-TEST redesign changes minimum-N FIT availability. At \(N=25\), the estimation pool contains 20 FIT contexts and therefore:

\[
20\times6=120
\]

FIT alternative-context rows. A 100-row background is therefore feasible under v2.1, whereas it was infeasible under the previous 15-FIT-context design.

Consequently, the earlier `{25,50,75}` candidate decision is **reopened**. The machine-readable configuration retains that set temporarily for auditability, but it is not considered finally frozen until the v2.1 development reassessment compares it against the now-feasible 100-row candidate. No primary run may begin before the final candidate set and selected background size are committed and frozen.

For every experimental condition, log both the absolute TreeSHAP background size \(B_{bg}\) and:

\[
r_{bg}=\frac{B_{bg}}{n_{FIT,\,rows}}.
\]

This makes the background-to-FIT ratio explicit across the scarcity factor.

Global SHAP importance remains:

\[
I_j^{SHAP}
=
\frac{1}{n_w}
\sum_{i\in WEIGHT}|\phi_{ij}^{XGB}|,
\qquad
w_j^{SHAP}
=
\frac{I_j^{SHAP}}{\sum_k I_k^{SHAP}}.
\]

The external TEST pool is never used for TreeSHAP background construction or global SHAP-weight estimation.

Terminology: **predictive attribution-derived surrogate weights**. These weights summarize predictive attribution after global compression; they must not be interpreted as causal effects, stakeholder preferences, or normative decision weights.
---

# 27. Attribution-Recovery Metrics

## Mean absolute weight error

\[
MAE_w
=
\frac{1}{p}
\sum_j
|w_j^{SHAP}-w_j^\star|.
\]

## Total variation distance

\[
TV_w
=
\frac12
\sum_j
|w_j^{SHAP}-w_j^\star|.
\]

## Spearman weight correlation

\[
\rho_w
=
Spearman(\mathbf w^{SHAP},\mathbf w^\star).
\]

Also report:

- top-3 overlap,
- top-5 overlap.

---

# 28. Weighting Benchmarks

Primary weighting methods:

1. Oracle attribution weights
2. SHAP
3. Permutation Importance
4. Non-negative Ridge (Ridge+)
5. CRITIC
6. Entropy
7. Equal weights

Diagnostic references:

8. Random Dirichlet weights
9. Direct XGBoost ranking (not a weighting method; upper decision-information reference)
10. Modal-winner Top-1 baseline (diagnostic only)

SAGE is discussed in the related work because it is a principled global Shapley importance framework defined on predictive loss. It is not treated as an attribution-recovery estimator of the same functional as the interventional prediction-level oracle. It may be added later as a downstream supervised weighting robustness comparator if computational budget permits.

---

# 29. Equal Weights

\[
w_j^{EQ}=\frac1{10}.
\]

---

# 30. Common Min-Max Calibration for CRITIC and Entropy

CRITIC and Entropy must not be allowed to measure arbitrary criterion scale differences.

Using only the weight-calibration partition, define:

\[
\tilde g_{ij}
=
\frac{g_{ij}-\min_i g_{ij}}
{\max_i g_{ij}-\min_i g_{ij}+\varepsilon},
\]

with:

\[
\varepsilon=10^{-12}.
\]

If a criterion range is smaller than \(\varepsilon\), flag it as effectively constant and assign zero information content before final normalization.

A secondary implementation audit may compare normalized and raw variants, but the normalized variants are the primary CRITIC and Entropy baselines.

---

# 31. CRITIC

On the min-max normalized weight-calibration matrix, let \(s_j\) be the standard deviation of criterion \(j\) and \(r_{jk}\) the Pearson correlation.

\[
C_j
=
s_j\sum_{k=1}^{p}(1-r_{jk}).
\]

Then:

\[
w_j^{CRITIC}
=
\frac{C_j}{\sum_l C_l}.
\]

If all information values are zero, fall back to equal weights and record a diagnostic flag.

---

# 32. Entropy Weighting

For the min-max normalized weight-calibration matrix:

\[
p_{ij}
=
\frac{\tilde g_{ij}}{\sum_i\tilde g_{ij}}.
\]

Use the mathematical convention:

\[
0\log0=0.
\]

Entropy:

\[
e_j
=
-\frac{1}{\log n}
\sum_i p_{ij}\log p_{ij}.
\]

Diversification:

\[
d_j=1-e_j.
\]

Weight:

\[
w_j^{ENT}
=
\frac{d_j}{\sum_l d_l}.
\]

If a column sum is effectively zero, set \(d_j=0\). If all diversification values are zero, fall back to equal weights and log the event.

---

# 33. Non-Negative Ridge Baseline

Standardize predictors and target using fit-partition statistics.

Estimate:

\[
\hat{\boldsymbol\beta}
=
\arg\min_{\boldsymbol\beta\ge0}
\left[
\|\mathbf y-X\boldsymbol\beta\|_2^2
+
\tau\|\boldsymbol\beta\|_2^2
\right].
\]

Implementation may use the L2-augmented non-negative least-squares design:

\[
\begin{bmatrix}
X\\
\sqrt{\tau}I
\end{bmatrix}
\boldsymbol\beta
\approx
\begin{bmatrix}
y\\
0
\end{bmatrix},
\]

solved with `scipy.optimize.nnls` or `lsq_linear`.

Choose \(\tau\) using grouped cross-validation within the fit contexts only, over a frozen grid such as:

\[
\tau\in\{10^{-4},10^{-3},10^{-2},10^{-1},1,10,100\}.
\]

Ridge+ weights:

\[
w_j^{Ridge+}
=
\frac{\hat\beta_j}{\sum_k\hat\beta_k}.
\]

If all coefficients are zero, fall back to equal weights and log the event.

---

# 34. Permutation-Importance Baseline

Permutation importance is evaluated on the weight-calibration contexts using the XGBoost model fitted on the fit partition.

Primary loss:

\[
L=MSE.
\]

To respect the grouped decision structure, permute criterion \(j\) at the **context-block** level: the complete six-alternative vector of that criterion is reassigned between contexts rather than independently shuffling individual rows.

Every permutation repeat must be a context-block **derangement**, so no WEIGHT context block remains in its original position. Use 20 unique derangements for every primary PI estimate. This is feasible even at the smallest sample size because five WEIGHT contexts admit 44 distinct derangements.

For repeat \(b\):

\[
I_{j,b}^{PI}
=
MSE(f,X_{\pi_b(j)},Y)
-
MSE(f,X,Y).
\]

Use:

\[
B_{PI}=20
\]

permutations and report the mean and SD of \(I_{j,b}^{PI}\).

Negative mean importances are truncated at zero before normalization:

\[
w_j^{PI}
=
\frac{\max(\bar I_j^{PI},0)}
{\sum_k\max(\bar I_k^{PI},0)}.
\]

If all importances are non-positive, fall back to equal weights and record the event.

Because unrestricted permutation can force extrapolation under dependence, PI is interpreted cautiously at high \(\rho\); poor PI performance in those cells is not automatically evidence of superior SHAP validity.

---

# 35. Random-Weight Diagnostic

For each primary replication, draw:

\[
K_{rand}=200
\]

independent weight vectors:

\[
\mathbf w^{rand,k}\sim Dirichlet(\mathbf1).
\]

Propagate every random vector through MOORA on the same test contexts.

Report the median and 5th-95th percentile range of Kendall agreement, Top-1 accuracy and regret.

This is a diagnostic reference, not a serious weighting competitor.

If sophisticated methods perform no better than random weights, the benchmark is not sufficiently decision-sensitive and must not proceed to the full primary experiment without redesign and a new specification version.

---

# 36. Direct-XGBoost Decision Reference

For every test context, rank its six alternatives directly by the fitted model prediction:

\[
\hat a_s^{XGB}
=
\arg\max_a\hat Y_{as}.
\]

Evaluate the same Kendall, Top-1 and regret metrics used for MCDM rankings.

This answers whether decision-relevant information is present in the predictive model even when it is lost by the attribution-to-global-weight compression step.

Direct XGBoost is not an MCDM weighting method and must be reported separately from the weighting-method comparison.

---

# 37. Modal-Winner Diagnostic

Using the weight-calibration contexts only, identify the most frequent oracle-optimal alternative and use it as a trivial constant Top-1 prediction on the test contexts.

This provides a more meaningful structural baseline than \(1/6\) when one alternative dominates the generated decision problems.

Also record:

- number of distinct oracle winners,
- modal winner share,
- normalized winner entropy:

\[
H_{win}
=
-\frac{\sum_a p_a\log p_a}{\log 6}.
\]

---

# 38. MOORA on the Common Benefit-Oriented Representation

To avoid an orientation mismatch between weight estimation and downstream aggregation, MOORA is applied to the same higher-is-better matrix \(G_s=[g_{asj}]\).

For context \(s\):

\[
r_{asj}
=
\frac{g_{asj}}
{\sqrt{\sum_{a=1}^{6}g_{asj}^2}+\varepsilon}.
\]

All ten criteria are now benefit-oriented, so under weighting method \(q\):

\[
S_{as}^{(q)}
=
\sum_{j=1}^{10}w_j^{(q)}r_{asj}.
\]

Alternatives are ranked by descending \(S_{as}^{(q)}\).

MOORA is used as a transparent downstream compression device; it is not a methodological novelty claim.

---

# 39. TOPSIS Robustness Check

Classical TOPSIS is applied to the same benefit-oriented matrix \(G_s\) and the same weight vectors.

Primary substantive conclusions are considered aggregation-robust only when the qualitative comparison of weighting methods is consistent under MOORA and TOPSIS.

---

# 40. Oracle Decision Ranking

For each test context:

\[
a_s^\star
=
\arg\max_aU^\star_{as}.
\]

This is the internal benchmark choice.

---

# 41. Decision-Fidelity Metrics

## Kendall rank agreement

Use **Kendall \(\tau_b\)** with tie correction:

\[
\tau_{b,s}^{(q)}
=
Kendall_{\tau_b}
(\mathbf r_s^{(q)},\mathbf r_s^\star).
\]

Ties in method scores use average ranks. The same deterministic tie convention is applied to all methods.

## Top-1 accuracy

\[
Acc_1^{(q)}
=
\frac{1}{|S_{test}|}
\sum_s
I(\hat a_s^{(q)}=a_s^\star).
\]

## Normalized oracle regret

Use \(\varepsilon=10^{-12}\):

\[
Regret_s^{(q)}
=
\frac{
U^\star_{a_s^\star,s}
-
U^\star_{\hat a_s^{(q)},s}
}{
\max_aU^\star_{as}
-
\min_aU^\star_{as}
+
\varepsilon
}.
\]

Report:

- mean regret,
- median regret,
- 95th-percentile regret,
- context-clustered/bootstrap confidence intervals.

---

# 42. Oracle Decision Margin

Let \(U^\star_{(1),s}\) and \(U^\star_{(2),s}\) be the largest and second-largest oracle utilities in context \(s\).

Define:

\[
M_s
=
\frac{
U^\star_{(1),s}-U^\star_{(2),s}
}{
\max_aU^\star_{as}-\min_aU^\star_{as}+\varepsilon
}.
\]

Decision accuracy and regret must also be analyzed conditional on \(M_s\).

This distinguishes method failure from intrinsically ambiguous near-tie decisions.

---

# 43. Stage-Wise Decision-Fidelity Diagnostic

Do **not** describe the following as an additive decomposition of one total error. The components are evaluated on different transformations and are therefore a stage-wise diagnostic ladder.

For every test context compare the ranking/regret of:

1. **Oracle nonlinear utility**
   \[
   U^\star.
   \]

2. **Main-effect nonlinear score**
   \[
   S^{main}_{as}=\sum_j\alpha_jq_j(g_{asj}).
   \]
   This removes pairwise interactions while retaining the oracle nonlinear transforms.

3. **Oracle-attribution nonlinear score**
   \[
   S^{wq}_{as}=\sum_jw_j^\star q_j(g_{asj}).
   \]
   This replaces the oracle structure by one global attribution-weight vector while retaining \(q_j\).

4. **Oracle-attribution linear score**
   \[
   S^{wg}_{as}=\sum_jw_j^\star g_{asj}.
   \]
   This additionally removes the nonlinear \(q_j\) transforms.

5. **Oracle-weight MOORA**
   \[
   MOORA(\mathbf w^\star).
   \]
   This adds within-context vector normalization and the chosen MCDM operator.

6. **SHAP-weight MOORA**
   \[
   MOORA(\mathbf w^{SHAP}).
   \]
   This replaces oracle attribution weights with learned attribution weights.

7. **Direct XGBoost ranking**
   evaluated in parallel as a reference for information retained by the fitted predictor before any global-weight compression.

Report regret and rank agreement at each stage. Differences between adjacent stages are diagnostic contrasts, not claimed to be a strict additive causal decomposition.

A useful attribution-related contrast is:

\[
\Delta R_{attr}
=
\overline R^{SHAP-MOORA}
-
\overline R^{Oracle-MOORA}.
\]

---

# 44. Primary Experimental Factors

## Data scarcity

\[
N\in\{25,50,100,250,1000\}.
\]

Corresponding row counts:

| Contexts | Rows |
|---:|---:|
| 25 | 150 |
| 50 | 300 |
| 100 | 600 |
| 250 | 1500 |
| 1000 | 6000 |

The effective independent sample size remains \(N\), not \(6N\).

## Relative observation noise

\[
c\in\{0.10,0.30,0.60\}.
\]

## Predictor dependence

\[
\rho\in\{0.0,0.4,0.8\}.
\]

## Interaction strength

\[
\lambda\in\{0.0,0.5,1.0\}.
\]

---

# 45. Factorial Design

The full primary grid contains:

\[
5\times3\times3\times3=135
\]

conditions.

Each condition is repeated using:

\[
R=30
\]

pre-specified primary seeds.

Total primary benchmark replications:

\[
135\times30=4050.
\]

---

# 46. Reference Condition

The reference condition is:

\[
(N,c,\rho,\lambda)
=
(250,0.30,0.4,0.5).
\]

This condition is used for detailed diagnostics, bootstrap and secondary robustness analyses unless otherwise stated.

---

# 47. Mandatory Development Pilots and Degeneracy Gates

The development validation is split into two dependency-correct pilots. Primary seeds are not inspected until both pilots, all development decisions and the final protocol freeze have been completed.

## Pilot A — Oracle / decision-geometry gate

Run after the generator, oracle and relative-noise implementation exist, but before model-dependent diagnostics.

Using the five reserved development seeds at the reference condition, record:

- criterion distributions and clipping diagnostics;
- \(s_U\) and realized SNR;
- number of distinct oracle winners;
- modal oracle-winner share;
- winner entropy;
- oracle decision-margin distribution;
- structural/Pareto dominance diagnostics.

Pre-specified early-warning flags are:

- modal winner share above 0.60;
- fewer than three distinct oracle winners across the development pilot.

These two numerical flags trigger investigation but are not, by themselves, automatic rejection rules.

## Pilot B — End-to-end decision-sensitivity gate

Run only after XGBoost hyperparameters, TreeSHAP background protocol, weighting methods, decision operators and decision-fidelity metrics exist.

Record:

- Random-Dirichlet Kendall and regret distributions;
- Equal-weight performance;
- Direct-XGBoost performance;
- modal-winner baseline performance;
- structured weighting-method performance.

**Hard stop rule:** do not run the primary factorial if random weights are statistically indistinguishable from the structured methods, if a trivial modal-winner reference effectively ties the structured methods in both Top-1 and regret, if one alternative dominates nearly all evaluated contexts, or if the decision geometry is effectively insensitive to weighting.

If the hard stop fires, document the finding, revise transparently using development data only, create a new specification version and Git tag, and repeat the relevant pilot. No redesign may be justified by a desire to make SHAP or a preferred ITS win.
---

# 48. Bootstrap Uncertainty Propagation

At the reference condition:

\[
B=200.
\]

Resample FIT contexts and WEIGHT contexts separately with replacement. The **same 200 fixed external TEST contexts remain untouched and fixed for every bootstrap iteration**.

Each bootstrap iteration repeats:

\[
FIT\ bootstrap
\rightarrow
XGBoost
\rightarrow
TreeSHAP
\rightarrow
Weights
\rightarrow
MOORA/TOPSIS
\rightarrow
External\ TEST\ metrics.
\]

Bootstrap outputs focus on method-level quantities:

- confidence intervals for SHAP weights;
- \(TV_w\);
- Kendall \(\tau_b\);
- Top-1 accuracy;
- mean regret;
- 95th-percentile regret.

Do not report a global cross-context probability that a particular ITS is rank 1. The scientific objective is weighting-method validity, not declaring one synthetic ITS globally optimal.
---

# 49. Generator-Ensemble Validation

A secondary ensemble contains:

\[
G=50
\]

oracle generators at the reference data condition.

For generator \(g\):

\[
\boldsymbol\alpha^{(g)}\sim Dirichlet(5\mathbf1),
\]

\[
\zeta_j^{(g)}\sim U(0.5,3.0),
\]

and interaction pairs are sampled from a pre-specified pool of semantically defensible criterion pairs.

Relative noise is recalibrated using the generator-specific \(s_U\), so differences among generator structures are not confounded with absolute noise scale.

The purpose is to test whether conclusions persist beyond one hand-crafted oracle.

---

# 50. Covariate-Shift Tests

Two out-of-distribution tests are conducted at the reference data size.

## Demand shift

- test contexts: upper 20% of \(h_D\),
- remaining lower 80% split into fit and weight-calibration sets in a 75/25 ratio, yielding approximately 60/20/20 overall.

## Readiness shift

- test contexts: lower 20% of \(h_R\),
- remaining upper 80% split into fit and weight-calibration sets in a 75/25 ratio.

The purpose is not domain adaptation. The goal is to determine whether predictive and attribution fidelity deteriorate when the operating environment changes.

---

# 51. Criterion-Removal and Weight-Perturbation Sensitivity

Secondary diagnostics:

- remove each criterion once and renormalize remaining weights,
- perturb one SHAP weight at a time by ±10%, ±20% and ±30%, then renormalize.

Bootstrap uncertainty remains the primary statistical uncertainty analysis.

---

# 52. Leave-One-Alternative-Out Sensitivity

At the reference condition, repeat the complete learning-weighting-ranking pipeline while excluding each alternative in turn:

- ATSC,
- TSP,
- TIDM,
- RMTI-DRG,
- V2X-CS,
- DSM.

This tests whether conclusions about weighting-method reliability depend disproportionately on the composition of the alternative set.

Particular attention is paid to V2X-CS because connected-vehicle applications can otherwise become overly broad umbrella alternatives.

---

# 53. Statistical Factor and Method Analysis

For a response metric \(Z\), such as \(TV_w\), Kendall \(\tau_b\), Top-1 accuracy or regret, summarize factor effects using a repeated-seed regression / mixed-effects response model that includes **method explicitly as a paired within-instance factor**.

A generic specification is:

\[
Z
=
\beta_0
+
\beta_N\log N
+
\beta_c c
+
\beta_\rho\rho
+
\beta_\lambda\lambda
+
\beta_m Method
+
\text{pre-specified interactions}
+
u_{seed}
+
\epsilon.
\]

All weighting methods are evaluated on the same seed-by-condition benchmark instances, so method contrasts are paired. Seed is a repeated simulation factor. The exact interaction set must be frozen before primary analysis.

Emphasize effect sizes, paired contrasts and uncertainty intervals rather than binary significance alone.
---

# 54. Random Seeds

Seed families must be non-overlapping and stored in `config/seeds.yaml`.

Recommended families:

- primary seeds: 30 seeds in one dedicated range,
- development seeds: separate range,
- bootstrap: master `SeedSequence`,
- generator ensemble: separate master `SeedSequence`,
- covariate shift: separate master seed,
- robustness: separate master seed,
- primary-alpha design permutation seed: `73001`.

No primary seed may be silently replaced because it produces inconvenient results.

---

# 55. Required Software Smoke Test

Before writing the full experiment, create `tests/test_shap_xgboost_smoke.py`.

The test must:

1. fit a tiny `XGBRegressor`,
2. create `TreeExplainer(model, data=background, feature_perturbation="interventional")`,
3. compute SHAP values on held-out observations,
4. verify local accuracy:

\[
E[f(X)] + \sum_j\phi_j(x) \approx f(x),
\]

within an explicit numerical tolerance.

This test must pass in the actual `swfc` environment before the primary pipeline is implemented.

---

# 56. Required Unit Tests

At minimum:

## Data generator

- values in expected domains;
- 1200 unique master contexts per replication seed;
- contexts 1--1000 form the estimation/calibration pool;
- contexts 1001--1200 form the fixed external TEST pool;
- no duplicated context identifier.

## Common random numbers

- the same estimation-pool base normal draws are reused across \(\rho\);
- the same external-TEST base normal draws are reused across \(\rho\);
- the original 1000-context estimation stream is generated from namespace `1001`;
- the external TEST stream is generated from separate namespace `1002`;
- technology parameters are invariant across factorial conditions for a given seed;
- target noise uses the same standard-normal draw scaled by \(c\,s_U\).

## Nested estimation samples and fixed TEST

For every configured \(N\):

- estimation subsets are exact nested prefixes;
- FIT/WEIGHT counts are exactly 80/20 within \(N\);
- exactly 200 external TEST contexts are appended;
- external TEST identifiers are identical across all \(N\);
- no external TEST identifier appears in FIT or WEIGHT;
- partition identities are reused across \(\rho\).

Expected context counts are 20/5/200 at \(N=25\), 40/10/200 at \(N=50\), 80/20/200 at \(N=100\), 200/50/200 at \(N=250\), and 800/200/200 at \(N=1000\).

## Technology responses

- six alternatives per context;
- 7200 rows in the 1200-context master response matrix;
- nested estimation responses remain exact prefixes;
- the 1200 external TEST response rows are exactly reused across every \(N\) condition for a fixed seed and \(\rho\);
- C1--C10 formula reconstruction tests continue to pass.

## Oracle monotonicity

Increasing one direction-adjusted criterion while holding others fixed must never reduce \(U^\star\).

## Closed-form Shapley

- matches exhaustive enumeration;
- preserves joint \(\mu_{jk}\);
- satisfies efficiency.

## Weights

Every weight vector must satisfy:

\[
w_j\ge0,
\qquad
\sum_jw_j=1
\]

within tolerance.

## Decision operators

The benefit-oriented MOORA ratio-system implementation and TOPSIS must pass hand-computable toy examples.

## Test isolation

No external TEST context identifier may appear in model fitting, background data, global weight estimation, PI, Ridge+, CRITIC/Entropy estimation or method tuning.
---

# 57. Numerical Constants

Use one central constant:

\[
\varepsilon=10^{-12}.
\]

Do not scatter different undocumented epsilon values throughout the code.

---

# 58. Environment Reproducibility

The high-level `environment.yml` must include at least:

- python 3.11,
- numpy,
- pandas,
- scipy,
- scikit-learn,
- xgboost,
- shap,
- matplotlib,
- openpyxl,
- pyyaml,
- pytest,
- statsmodels,
- joblib,
- tqdm,
- psutil.

After the environment is validated, export exact versions without build strings:

```bat
conda env export --no-builds > environment.lock.yml
```

Commit both files.

When replications are parallelized externally with `joblib`, set XGBoost `n_jobs=1` inside each worker to avoid thread oversubscription. For single-run debugging, a larger internal `n_jobs` value may be used.

---

# 59. Runtime and Execution Reporting

Record:

- wall-clock runtime by pipeline stage;
- number of model fits;
- TreeSHAP background size;
- FIT alternative-context row count;
- TreeSHAP background-to-FIT-row ratio \(B_{bg}/n_{FIT,rows}\);
- peak memory where feasible;
- CPU information;
- Python and package versions;
- random seed;
- Git commit hash.

Measure at least one complete reference replication end-to-end before launching the full grid and use the measured value to plan the compute budget.

Do not fabricate runtime estimates in the manuscript.
---

# 60. Output Philosophy

Python is the computational source of truth.

Excel is permitted only as a human-readable documentation and inspection artifact.

All final scientific tables and figures must be generated programmatically.

No numerical paper result may be manually edited in Excel or typed by hand after computation.

---

# 61. Primary Planned Outputs

## Tables

1. Predictive performance and Direct-XGBoost decision fidelity.
2. Oracle and recovered criterion weights.
3. Weight-recovery and downstream decision-fidelity comparison.
4. Factorial validity-boundary summary.
5. Alpha-dispersion alignment stress test.
6. Bootstrap uncertainty summary.
7. Generator-ensemble and covariate-shift robustness.
8. Leave-one-alternative-out robustness.

## Figures

1. Methodological pipeline.
2. Attribution error versus sample size and dependence.
3. Decision regret versus sample size and dependence.
4. Prediction fidelity versus attribution fidelity.
5. Attribution fidelity versus decision fidelity.
6. Decision accuracy/regret versus oracle decision margin.
7. Validity-boundary heatmap.
8. Stage-wise fidelity ladder.

---

# 62. Frozen-Design Rules

1. No fabricated real-world observations.
2. No fabricated expert judgments.
3. No fabricated numerical results.
4. No changing the capability mask after primary outcomes are inspected.
5. No changing response bands to make a preferred ITS rank first.
6. No changing oracle coefficients to make SHAP win.
7. No replacing primary seeds because results are inconvenient.
8. No test-set information in training or weight estimation.
9. No manually edited final tables.
10. Every primary result must be reproducible from code.
11. Every random seed must be recorded.
12. Every final figure must be generated programmatically.
13. The benchmark must always be described as synthetic and controlled.
14. SHAP weights must not be described as causal or stakeholder-preference weights.
15. The identity of the top-ranked ITS is not the scientific objective.
16. Null findings are valid.
17. Ridge+, Equal, CRITIC or another simple method outperforming SHAP is a valid result.
18. Direct XGBoost outperforming every global-weight method is a scientifically important result, not a failure.
19. Any generator redesign after pilot failure requires a documented new specification version and Git tag before primary execution.

---

# 63. Interpretation Rules

## Outcome A — SHAP succeeds broadly

Interpretation: predictive attribution can provide useful surrogate decision weights under the identified conditions.

## Outcome B — SHAP succeeds only in identifiable regimes

Interpretation: the study identifies validity boundaries in sample size, dependence, SNR or interaction strength.

## Outcome C — SHAP does not outperform simpler supervised methods

Interpretation: sophisticated prediction explanations should not automatically be interpreted as superior decision-weight estimators.

## Outcome D — Direct XGBoost ranks well but SHAP-weight MOORA does not

Interpretation: the predictive model retains decision-relevant information that is lost when local predictive structure is compressed into one global criterion-weight vector and additive MCDM rule.

## Outcome E — all weighting methods resemble random weights

Interpretation: the synthetic decision geometry is insufficiently weight-sensitive. The benchmark must be redesigned transparently before primary execution.

---

# 64. Scope of Claims

The study may claim conclusions about:

- predictive fidelity,
- attribution fidelity,
- surrogate-weight recovery,
- downstream decision fidelity,
- validity under controlled scarcity, dependence, SNR, interactions and shift.

The study may not claim:

- that one ITS is empirically optimal for Tunisia,
- that oracle attribution weights represent policymaker preferences,
- that SHAP identifies causal effects,
- that the synthetic generator reproduces a specific real corridor,
- that the identified thresholds generalize automatically to all MCDM problems.

---

# 65. Future Empirical Extension

A later empirical or simulation study may replace:

- synthetic contexts with measured traffic/network states,
- response functions with calibrated SUMO/TraCI intervention scenarios,
- synthetic operational criteria with calibrated performance outputs,
- technical assumptions with infrastructure inventories,
- synthetic lifecycle burden with audited cost evidence.

Expert or stakeholder weights may then be included as a separate normative comparator.

This empirical extension is separate from the controlled methodological benchmark.

---

# 66. Repository Audit Trail

Every major methodological change must correspond to a Git commit.

Before the primary experiment:

1. commit the final v2.1 specification and synchronized YAML/code/tests,
2. pass all smoke and unit tests,
3. complete Pilot A and Pilot B on development seeds only,
4. freeze XGBoost and TreeSHAP calibration choices,
5. measure one complete reference replication end-to-end,
6. commit the final frozen protocol state,
7. create the mandatory Git tag `spec-v2.1` before any primary run.

The exact Git commit used for final results must be reported in the repository metadata.

---

# 67. Immediate Implementation Order

1. Synchronize Protocol Re-Audit v2.1: fixed external TEST architecture, attribution-relevant alpha-dispersion definition, pilot split and supporting diagnostics.
2. Revalidate Step 1 and Step 2 under the 1200-context master architecture.
3. Run the pre-oracle generator audit on development seeds only.
4. Implement oracle utility and relative-noise scaling.
5. Implement closed-form oracle Shapley and exhaustive unit tests.
6. Run Pilot A on development seeds only.
7. Calibrate and freeze XGBoost on development seeds.
8. Reassess, select and freeze the TreeSHAP background candidate set/size on development seeds.
9. Implement weighting baselines, benefit-oriented MOORA, TOPSIS, Direct-XGBoost and diagnostic references.
10. Implement decision-fidelity metrics and the complete stage-wise ladder.
11. Run Pilot B and apply the hard decision-sensitivity gate.
12. Run reference bootstrap and pre-specified robustness analyses.
13. Freeze the statistical analysis protocol.
14. Measure one complete end-to-end reference replication and record compute requirements.
15. Commit the final frozen state and create mandatory tag `spec-v2.1`.
16. Only then launch the 4050-run primary factorial experiment.

