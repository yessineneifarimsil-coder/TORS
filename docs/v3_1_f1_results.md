# v3.1-F1 prospective development result

## Status

**FAILED — no selectable tau passed all frozen gates.**

Evaluation commit: `f40b95e5c1bb01f685bd4e22c36a2a1ae9848913`

Development cohort: `27001–27005`

RNG namespace: `2009`

No structural-validation seed, reserve seed, primary seed, or external TEST observation was used.

## Frozen selection outcome

The selectable grid was `0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9`.

Every selectable point passed the frozen D2.8 numerical gates and all response invariants.

- `tau=0.1` through `tau=0.8` passed reachability but failed Layer-A.
- `tau=0.9` failed Layer-A and also failed reachability at `h_D->C1`.
- No selectable point passed all gates.
- `selected_tau = None`.
- `family_failed = True`.

The descriptive anchors `tau=0` and `tau=1` were computed but excluded from selection.

## Closest selectable point

The closest selectable point was `tau=0.9`:

- joint minimum ratio: `0.942239058`;
- minimum Layer-A ratio: `0.942239058` at `C6`;
- minimum SRE ratio: `0.994999294` at `h_D->C1`;
- Layer-A shortfall: `5.776094%`;
- SRE shortfall: `0.500071%`.

The failure is therefore narrow but genuine.

## Protocol consequence

The frozen v3.1 stop rule applies:

1. do not refine the tau grid using `27001–27005`;
2. do not retune or replace the family using `27001–27005`;
3. do not run structural validation on `22001–22005`, because no tau was selected;
4. keep `28001–28005`, primary seeds, and external TEST untouched.

Any further candidate-family development must be prospectively specified using a new untouched development cohort.
