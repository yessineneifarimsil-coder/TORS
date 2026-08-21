# Secondary v2.2-form production-generator robustness protocol v1

## Purpose

The corrected eligibility audit established 54 admissible historical response
specifications. The already-frozen `d29_kernel` was retained as the primary
generator under a minimal-intervention/provenance-stability rule, not because it
was unique or superior.

This protocol prospectively specifies the required secondary robustness
analysis before D3 or the primary benchmark is executed.

## Robustness family

The retained primary generator is

\[
g_{\mathrm{d29}}(o)=\theta o+0.05\,v\,o(1-o).
\]

The secondary endpoint-preserving v2.2-form family is

\[
g_{\kappa}(o)=\theta o\{1+\kappa v(1-o)\}
=\theta o+\kappa\theta v\,o(1-o),
\]

for every

\[
\kappa\in\{0.1,0.2,\ldots,1.0\}.
\]

No kappa is selected. All ten values must be reported.

## Matched-profile design

The robustness analysis uses the retained primary signed-profile assignment
(namespace `2010`) rather than the historical v2.2 namespace `2004`.

This is deliberate. The robustness question is whether conclusions change when
the **curvature-amplitude law** changes from fixed absolute amplitude
`delta=0.05` to relative amplitude `kappa*theta`. Using the same signed profile
holds the alternative-specific profile permutation fixed and avoids confounding
the family contrast with a second random profile assignment.

This analysis is therefore a controlled **v2.2-form robustness analysis**, not
a reconstruction or re-selection of the historical v2.2 development run.

## Common-random-number pairing

All robustness runs use the same 30 primary replication seeds,
`11001–11030`, and the same frozen primary condition grid:

- `N = {25, 50, 100, 250, 1000}`;
- `rho = {0.0, 0.4, 0.8}`.

For a given primary replication seed and condition, contexts, capability draws,
noise draws, partitions, oracle specification, and algorithmic randomness are
held identical wherever the frozen primary implementation permits.

## D3 relationship

D3 is a property of the retained primary benchmark design and is executed only
for `d29_kernel`.

The v2.2-form robustness family:

- cannot influence D3;
- does not receive a kappa-specific D3 recalibration;
- inherits the primary D3 alpha mappings unchanged.

This isolates response-generator sensitivity instead of simultaneously changing
the generator and the alpha mapping.

## Downstream analysis

For each kappa, reuse the same frozen downstream pipeline, methods, estimands,
oracle definition, alpha scenarios, and hyperparameters as the primary
benchmark.

No method or model may be retuned for an individual kappa.

For every frozen primary estimand, report:

1. its paired value by kappa and primary replication seed;
2. the across-kappa range;
3. maximum absolute paired deviation from retained d29;
4. median absolute paired deviation from retained d29;
5. sign consistency of preregistered primary method contrasts across kappa.

There is no binary robustness pass/fail gate.

## Interpretation

The robustness analysis is secondary.

It cannot:

- replace `d29_kernel` as the retained primary generator;
- select a preferred kappa;
- reopen response-family development;
- use D2.9 LRV/NSV/SRE to rank kappa;
- choose kappa from SHAP, MCDM, winner, or other downstream outcomes.

All ten kappa values are retained in the robustness record.

## Execution order

1. Freeze this robustness protocol.
2. Execute and freeze D3 for the retained `d29_kernel` only.
3. Execute the frozen primary benchmark.
4. Execute the v2.2-form robustness analysis on the same primary
   seeds/conditions.

External TEST may be used only after this protocol is frozen and only exactly
as prescribed by the frozen primary benchmark; it cannot alter generator or
kappa choice.

The reserve cohort `30001–30005` remains excluded from this robustness analysis.
