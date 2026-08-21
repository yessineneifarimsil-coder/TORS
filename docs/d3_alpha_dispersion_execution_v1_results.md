# D3-B superpopulation alpha-dispersion execution — frozen result

## Status

**FROZEN CONVERGED D3-B MAPPING**

Evaluation commit: `b0b76e76ce7caacb5878de2eb270b92e15858789`

The first and only D3 execution converged at the prospectively specified
initial ensemble size of 200 technology worlds. No expansion to worlds
201--400 was required.

## Mapping-defining estimand

For each world \(w\) and criterion \(j\),

\[
D_{j,w}^{attr}
=
\frac{1}{6000}
\sum_i
\left|
q(g_{ijw})-\overline q_{j,w}
\right|,
\qquad
q(g)=\frac{\log(1+2g)}{\log 3}.
\]

The superpopulation summary is the arithmetic mean of the world-specific
q-MAD values.

At W=200:

- complete criterion ordering at W=150 and W=200 was identical;
- all ten criteria satisfied the frozen relative 95% Monte Carlo half-width
  target of 0.05;
- the maximum observed relative half-width was approximately 0.031768.

The frozen descending q-MAD order is:

`C8 > C10 > C5 > C2 > C3 > C4 > C1 > C7 > C6 > C9`.

## Frozen alpha mappings

Dispersion-aligned:

- C8 = 0.16
- C10 = 0.14
- C5 = 0.13
- C2 = 0.12
- C3 = 0.11
- C4 = 0.10
- C1 = 0.08
- C7 = 0.07
- C6 = 0.05
- C9 = 0.04

Dispersion-anti-aligned:

- C9 = 0.16
- C6 = 0.14
- C7 = 0.13
- C1 = 0.12
- C4 = 0.11
- C3 = 0.10
- C2 = 0.08
- C5 = 0.07
- C10 = 0.05
- C8 = 0.04

Balanced remains 0.10 for every criterion.

The frozen primary heterogeneous alpha mapping is unchanged.

## Secondary legacy min-max + population-SD diagnostic

The historical pre-D3 design specified a criterion-wise min-max transform over
a single independent 30,000-observation design pool followed by population
standard deviation (`ddof=0`).

The later D3-B redesign replaced that single pool with a superpopulation of
technology worlds. The frozen D3-B protocol retained the legacy diagnostic as
secondary and non-mapping, but did **not** specify how that historical
single-pool statistic should be transported to the multi-world architecture:
for example, whether to pool all worlds before normalization/SD or to compute
a world-specific statistic followed by superpopulation aggregation.

Because that choice was not prospectively frozen, no post-result convention is
introduced here. The legacy diagnostic remains:

`NOT_COMPUTED_UNDERSPECIFIED_LEGACY_DIAGNOSTIC`.

This is a documented protocol deviation limited to a non-mapping secondary
diagnostic. It does not affect the q-MAD convergence rule, criterion order,
aligned/anti-aligned mappings, primary alpha mapping, or any protected outcome.

## Firewalls

The D3 execution used:

- no primary seeds 11001--11030;
- no reserve seeds 30001--30005;
- no external TEST observations;
- no FIT/WEIGHT partition roles;
- no SHAP result;
- no MCDM result;
- no winner identity;
- no v2.2 robustness outcome.

No world seed was generated, replaced, or selected after observing results.
