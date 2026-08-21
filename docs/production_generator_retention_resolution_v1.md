# Post-development production-generator retention resolution v1

## Context

The corrected historical eligibility audit established that production-generator
eligibility is non-unique. The original re-adjudication identified 44 eligible
points, and a supplemental contemporaneous-source audit resolved all ten v2.2
points as additionally eligible. The corrected-eligible universe therefore
contains 54 historical points.

This protocol does **not** rank those 54 points.

## Why a new optimization is not justified

All historical response families were developed adaptively using consumed
development evidence. Once the binary D2.9 gate was corrected, a retrospective
ranking of the 54 eligible points by LRV, NSV, SRE, SHAP, MCDM behavior, winner
identity, or any newly chosen performance score would create another
post-development optimization layer.

Likewise, selecting a new generator merely because a later audit exposed a
convenient semantic property would risk post-hoc criterion construction.

## Primary rule: minimal intervention and provenance stability

A production generator had already been frozen before D3:

`config/production_response_generator_v1.json`

with candidate:

`d29_kernel`

at the historical production freeze rooted at commit `bd56c2d`.

The resolution rule is therefore:

> If the already-frozen production candidate remains corrected-eligible, and no
> D3, reserve, primary, or external TEST outcomes have been observed, retain
> that frozen candidate as the primary benchmark specification rather than
> re-optimizing among the expanded corrected-eligible universe.

This is a **retention rule**, not a statistical selection rule.

## Interpretation

Retention of `d29_kernel` does not mean:

- it is uniquely eligible;
- it is empirically superior to the other 53 eligible points;
- the historical v4.0 D2.9 gate failure is rewritten;
- D2.9 LRV/NSV/SRE establish production eligibility;
- the previous adaptive development history disappears.

It means only that, after discovering that corrected eligibility is broader than
previously understood, the already-frozen primary specification is preserved to
avoid a new round of post-development optimization.

## Mandatory robustness consequence

Because corrected eligibility is non-unique, the primary benchmark must not
present `d29_kernel` as the only scientifically admissible response model.

Before primary-benchmark execution, a separate robustness protocol must be
frozen that represents the endpoint-preserving v2.2 family. That robustness
analysis is secondary and may not silently replace the retained primary
generator.

The exact v2.2 robustness design is not chosen in this protocol.

## Firewalls

No D2.9 structural metric, SHAP result, MCDM result, winner identity, primary
performance, new simulation, new seed, D3 world, reserve seed, primary seed, or
external TEST outcome may enter this retention resolution.

D3 remains paused until the retention result itself is frozen.
