# v4.0-F1 — Terminal D2.9-kernel candidate protocol

## Status

**Prospectively opened before any v4.0 candidate result was generated.**

Parent commit: `94152793ae800a0adbfe44b84ac9ef6187a52f5d`

Branch: `protocol-v4.0-terminal-d29-kernel`

Immediately before this protocol was written, exact-token checks confirmed that development seeds `29001–29005`, reserve seeds `30001–30005`, and RNG namespace `2010` were absent from both tracked repository content and Git history.

## Rationale

v3.1 established a narrow but genuine trade-off between Layer-A structure and reachability. Further refinement of the observed tau grid would constitute adaptive tuning on consumed development data.

v4.0 therefore does **not** introduce another parameter ladder. It evaluates one single response family derived from the already frozen D2.9 admissible positive-control kernel.

## Frozen candidate

For every active C1–C7 pathway,

\[
g(o)=\theta o+\delta v o(1-o),
\]

with

\[
\delta=0.05.
\]

`delta=0.05` is fixed a priori from D2.9 and is not selectable in v4.0.

The signed coefficient `v` is generated using the frozen v3.0 symmetric alternative-specific signed-profile construction for active pathways, with the only RNG change being the fresh namespace `2010`.

Structural-zero pathways remain exactly zero. C8–C10 remain unchanged. No clipping is permitted.

## Analytic admissibility

Because `v` lies in `[-1,1]`, active `theta>=0.05`, and `delta=0.05`,

\[
\frac{dg}{do}=\theta+\delta v(1-2o)\ge\theta-\delta\ge0.
\]

Also,

\[
g(0)=0,\qquad g(1)=\theta.
\]

Therefore the response is non-decreasing and

\[
0\le g(o)\le\theta\le u.
\]

## Development cohort

- seeds: `29001–29005`;
- rho: `0.4`;
- lambda: `0.5`;
- sigma_x: `0`;
- FIT+WEIGHT contexts: `1000` per seed;
- external TEST excluded;
- namespace: `2010`.

## Frozen gates

The single candidate must pass all of:

1. frozen D2.8 numerical-null thresholds;
2. all response/boundary invariants;
3. frozen D2.9 criterion-specific Layer-A LRV/NSV thresholds;
4. frozen D2.9 pathway-specific SRE thresholds.

Layer-B, winner identity, SHAP, MCDM outcomes, and oracle outcomes cannot affect candidate adjudication.

## Stop rule

There is no parameter search and no fallback candidate inside v4.0.

If the single candidate fails development on `29001–29005`, v4.0-F1 fails. Do not tune delta, alter the profile rule, or construct another response family using those seeds.

Only if development passes is the candidate evaluated once on untouched `22001–22005`. If that one-shot structural validation fails, v4.0-F1 fails.

This protocol treats v4.0 as the **terminal response-generator family**. A development or structural-validation failure ends response-family development; the benchmark design must then be reconsidered rather than continuing adaptive threshold chasing.

`30001–30005` remain untouched and are not backup validation seeds.

D3 remains blocked until a production response generator has passed development, passed one-shot structural validation, and been frozen.
