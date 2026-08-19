# v2.2 D2.7 Positive-Control Calibration Results

## Status

**Execution commit:** `2f8cd1ae1bb17321ef55ca7b2e03b4ab5ee0ff87`

**Branch:** `protocol-v2.2-design`

**Design seeds:** `21001–21005`

**Reference condition:** `rho=0.4`, `lambda=0.5`, `sigma_x=0`

**Scope:** FIT+WEIGHT only; external TEST, structural-validation seeds, and primary seeds excluded.

This document freezes the outputs of the positive-control calibration preregistered before execution in `docs/v2_2_design_specification.md`.

The positive control is a measurement-calibration device and is not a candidate technology-response generator.

## Frozen Layer-A scientific references

| Criterion | `T_sci_LRV` | `T_sci_NSV_vector` |
|---|---:|---:|
| C1 | 0.185606069637 | 0.101684713011 |
| C2 | 0.107107049866 | 0.069436369626 |
| C3 | 0.163029400527 | 0.064900129844 |
| C4 | 0.115796231973 | 0.069422647369 |
| C5 | 0.127963802848 | 0.073680744007 |
| C6 | 0.194899307365 | 0.129935248436 |
| C7 | 0.144080052499 | 0.073091969211 |

## Frozen reachability references

| Declared pathway | `T_sci_SRE` |
|---|---:|
| h_D->C1 | 0.556244784899 |
| h_D->C2 | 0.334436750485 |
| h_D->C3 | 0.284877795008 |
| h_D->C4 | 0.292844251422 |
| h_D->C6 | 0.431611865207 |
| h_D->C7 | 0.252575899020 |
| h_E->C6 | 0.296868971200 |
| h_I->C2 | 0.212043213359 |
| h_I->C4 | 0.294905186921 |
| h_I->C5 | 0.455271158665 |
| h_T->C3 | 0.186994773337 |
| h_T->C7 | 0.373380015550 |

## Layer-B activation outcome

The preregistered Layer-B activation rule **did not activate**.

Therefore no numeric `T_R_sci` is frozen.

| Seed | Paired mean-regret uplift |
|---|---:|
| 21001 | 0.001484855654 |
| 21002 | 0.020022118658 |
| 21003 | -0.013835954554 |
| 21004 | 0.015533756667 |
| 21005 | 0.006161241046 |

Seed `21003` produced a negative uplift. Because the preregistered rule required positive uplift above the numerical discriminator for all five design seeds, no Layer-B scientific regret threshold is created.

This result is retained as-is. The positive control is not modified or retuned to force Layer-B activation.

Layer-B decision sensitivity therefore remains an explicit frozen question for the subsequent Pilot-A/Pilot-B design. Winner identity and winner count remain descriptive, non-gating quantities.

## Provenance

The committed result directory contains the raw CSV summaries, `references.json`, `run_metadata.json`, and `summary.txt`.

`run_metadata.json` records execution commit `2f8cd1ae1bb17321ef55ca7b2e03b4ab5ee0ff87`, and confirms no external TEST, structural-validation seed, or primary-seed use.

These references are frozen before any v2.2 candidate-family evaluation.
