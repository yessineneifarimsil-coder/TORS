# Oracle B100-Matched Background Diagnostic v1

## Status

**FROZEN BEFORE ANY ORACLE B100 DIAGNOSTIC RESULT.**

This diagnostic is introduced to quantify one specific nuisance component in the
SHAP-to-Oracle comparison: the finite empirical TreeSHAP background.

It does **not** replace the primary Oracle attribution reference, reopen the
TreeSHAP background size, modify D29, alter the primary factorial design, or create
a new weighting method.

## Primary Oracle remains unchanged

The primary Oracle attribution weights remain those already frozen in
`oracle_attribution_weights_v1.py`:

\[
\mu_j^{full}
=
\frac{1}{n_{FIT}}\sum_{i\in FIT}q_{ij},
\qquad
\mu_{jk}^{full}
=
\frac{1}{n_{FIT}}\sum_{i\in FIT}q_{ij}q_{ik}.
\]

Closed-form Oracle Shapley values are evaluated on the frozen WEIGHT rows, then

\[
I_j^{full}
=
\frac{1}{n_W}\sum_{i\in W}|\phi_{ij}^{full}|,
\qquad
w_j^{full}
=
\frac{I_j^{full}}{\sum_k I_k^{full}}.
\]

The full-FIT row counts are 120, 240, 480, 1200, and 4800 at
\(N=25,50,100,250,1000\), respectively.

If total importance is \(\le10^{-12}\), the primary Oracle vector remains undefined.
Equal fallback is forbidden.

## B100 diagnostic Oracle

The secondary diagnostic uses exactly the same Oracle formula and exactly the same
WEIGHT evaluation rows. The **only change** is the empirical background used to
estimate \(\mu_j\) and \(\mu_{jk}\).

The background contains exactly

\[
B_{bg}=100
\]

FIT alternative-context rows selected by the already-frozen TreeSHAP background
constructor in `src/treeshap_background_v1.py`.

Membership is determined from the frozen namespace `83001`:

1. build one priority ordering over the complete \(N=1000\) FIT row identities from
   `SeedSequence([replication_seed, 83001])`;
2. for the requested nested \(N\), keep eligible FIT identities with
   `context_number <= N`;
3. take the first 100 rows in the frozen priority order.

The exact same 100 identities are therefore used by TreeSHAP and by the B100 Oracle
diagnostic for the same replication seed and \(N\). Membership is reused across
\(\rho\), \(c\), and \(\lambda\) and is independent of features, \(Y\), Oracle values,
SHAP values, MCDM results, and winner identity.

The B100 moments are

\[
\mu_j^{B100}
=
\frac{1}{100}\sum_{i\in B100}q_{ij},
\qquad
\mu_{jk}^{B100}
=
\frac{1}{100}\sum_{i\in B100}q_{ij}q_{ik}.
\]

These moments replace only the background moments in the closed-form Oracle
attribution calculation. The WEIGHT rows, Oracle coefficients, nonlinear transform,
interaction graph, \(\lambda\), normalization rule and undefined-weight policy remain
identical.

## Diagnostic estimand

The vector

\[
w^{full}
\]

remains the primary Oracle attribution reference.

The secondary vector

\[
w^{B100}
\]

answers a narrower diagnostic question: how much would the Oracle attribution
reference move if it were approximated using the exact same finite empirical
background as TreeSHAP?

Thus

\[
\Delta_{bg}
=
d(w^{B100},w^{full})
\]

estimates a finite-background approximation component. It is not a new benchmark
weighting method.

## Frozen metrics

When both vectors are defined, report:

\[
MAE_w
=
\frac{1}{10}\sum_j |w_j^{B100}-w_j^{full}|,
\]

\[
TV_w
=
\frac{1}{2}\sum_j |w_j^{B100}-w_j^{full}|,
\]

the maximum absolute component difference, Spearman rank correlation, Top-3 overlap
and Top-5 overlap.

Also report the maximum absolute marginal-moment difference

\[
\max_j|\mu_j^{B100}-\mu_j^{full}|
\]

and the maximum absolute joint-moment difference over the five frozen interaction
pairs.

Top-k ties are resolved by ascending criterion index only for deterministic reporting.

## Scope and reuse

The diagnostic is defined for:

- \(N\in\{25,50,100,250,1000\}\);
- \(\rho\in\{0,0.4,0.8\}\);
- \(\lambda\in\{0,0.5,1\}\).

It does not depend on target-noise factor \(c\), because neither Oracle attribution
vector uses \(Y\). Therefore a computed diagnostic for a given
(seed, \(N,\rho,\lambda\)) is reused across the three \(c\) levels.

A development reference check may use seed 21001 at
\((N,\rho,\lambda)=(250,0.4,0.5)\) before the primary pipeline.
Reserve seeds are not used before primary execution.

## Undefined policy

If either \(w^{full}\) or \(w^{B100}\) has total importance \(\le10^{-12}\):

- preserve the respective undefined flag;
- do not substitute Equal weights;
- mark the vector-comparison metrics undefined;
- do not alter the primary Oracle definition.

Undefined/fallback coverage is itself reported.

## Interpretation firewall

This diagnostic:

- cannot replace the primary full-FIT Oracle;
- cannot change \(B_{bg}=100\);
- cannot change namespace `83001`;
- cannot change the Oracle formula;
- cannot change D29;
- cannot change the factorial design;
- cannot tune SHAP or MCDM;
- cannot inspect preferred ITS winner identity.

It exists only to separate finite-background approximation from the remaining
SHAP-to-Oracle discrepancy.
