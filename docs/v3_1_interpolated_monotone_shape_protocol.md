# v3.1-F1 — Interpolated monotone headroom-shape protocol

## Status

**Prospectively opened before any v3.1 candidate result was generated.**

Parent commit: `ea8658bdb76b6d6f0e140392f89fb54529802458`

Parent branch: `protocol-v3.1-interpolated-monotone-shape`

The exact-token audit confirmed that development seeds `27001–27005`, reserve
seeds `28001–28005`, and RNG namespace `2009` were unused in the tracked
repository and Git history before this protocol was created.

## Adaptive motivation

The frozen D2.9 historical re-adjudication showed:

- v3.0 `p=2`: minimum Layer-A ratio `0.956089`, minimum SRE ratio `1.020095`;
- v3.0 `p=3`: minimum Layer-A ratio `1.264451`, minimum SRE ratio `0.926555`.

This motivates one tightly constrained interpolation family between those two
already frozen neighboring shapes.

## Shape family

Let `a=|v|` and define the frozen v3.0 shape

\[
F_{p,v}(o)=
\begin{cases}
(1-a)o+a o^p, & v<0,\\
o, & v=0,\\
(1-a)o+a[1-(1-o)^p], & v>0.
\end{cases}
\]

v3.1 defines

\[
F_{\tau,v}(o)
=
(1-\tau)F_{2,v}(o)
+
\tau F_{3,v}(o).
\]

For active C1–C7 pathways,

\[
g(o)=\theta o+(u-\theta)F_{\tau,v}(o).
\]

Structural zeros remain exactly zero. C8–C10 remain unchanged.

## Selectable grid

Selectable:

\[
\tau\in\{0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9\}.
\]

`tau=0` and `tau=1` are descriptive anchors only and cannot be selected.

## Development cohort

- development: `27001–27005`;
- reserve: `28001–28005`;
- structural validation: `22001–22005`;
- RNG namespace: `2009`;
- rho: `0.4`;
- lambda: `0.5`;
- sigma_x: `0`;
- external TEST excluded.

## Gates

A selectable `tau` must pass frozen D2.8 numerical-null gates, all response
invariants, all D2.9 Layer-A references, and all D2.9 reachability references.

Layer-B, winner identity, SHAP, MCDM outcomes, and oracle outcomes cannot affect
selection.

## Selection and stop rule

Select the minimum `tau` passing all gates.

If none passes, v3.1-F1 fails. The same development cohort may not be used to
refine the grid or tune a replacement family.

If a `tau` is selected, evaluate it exactly once on untouched `22001–22005`.
If that validation fails, v3.1-F1 fails with no fallback to another `tau`.

`28001–28005` remain untouched and are not backup validation seeds.

D3 remains blocked until a production response generator has successfully
passed structural validation and been frozen.
