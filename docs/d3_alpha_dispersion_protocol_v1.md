# D3-B alpha-dispersion protocol v1

Parent commit: `bd56c2d0eda7ea38f90c10407e3606e9e5229cd4`

Status: **prospectively synchronized before any D3 technology-world observation**.

This file makes the already-resolved D3-B architecture executable after the
production response generator was frozen.

Key frozen choices:

- production generator: `d29_kernel`;
- master namespace: `74001`;
- 400 deterministic child technology-world seeds are materialized in
  `config/d3_alpha_dispersion_protocol_v1.json`;
- initial ensemble: 200 worlds;
- automatic expansion only to 400 worlds;
- 1000 independent design contexts per world;
- six alternatives;
- rho = 0.4;
- sigma_x = 0;
- assignment-defining statistic: within-world q-MAD, then arithmetic mean
  across worlds;
- no min-max before q-MAD;
- primary, validation and external TEST data are excluded;
- aligned and anti-aligned mappings cannot be formed until the D3 convergence
  rule passes.

At W=200 the complete ordering must be identical at W=150 and W=200 and every
criterion must meet the maximum 5% relative 95% Monte Carlo half-width target.
If expansion is triggered, the same logic is applied prospectively at W=400
using the final consecutive 50-world comparison W=350 versus W=400.

The historical v2.1 5000-context / seed-72001 design remains preserved in Git
history and in the historical seed registry block, but is not authoritative for
D3-B.
