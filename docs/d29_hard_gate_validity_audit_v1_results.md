# Post-v4 D2.9 hard-gate validity audit — frozen result

## Status

**FROZEN POST-DEVELOPMENT METHODOLOGICAL AUDIT**

Evaluation commit: `aa474f132660d6c5032a889a80c07b8f92e70ab2`

No new seeds, D3 worlds, reserve seeds, primary seeds, external TEST, SHAP,
MCDM, winner outcomes, threshold changes or response-parameter changes entered
this audit.

## Analysis A — matched profile-ensemble decomposition

The frozen v4.0 development worlds `29001–29005` were re-evaluated with the
six deterministic D2.9 cyclic rotations while keeping the response formula,
contexts, technology parameters, rho and sigma_x unchanged.

The profile-ensemble mismatch did **not** fully explain the historical v4.0
hard-gate failure.

Previously failing support-equivalent Layer-A criteria that remained below at
least one D2.9 reference under the matched six-rotation ensemble:

- C1
- C4
- C6
- C7

Previously failing support-equivalent reachability pathways that remained below
their D2.9 reference:

- h_D->C1
- h_D->C4
- h_I->C4

Therefore the earlier interpretation that the D2.9/candidate estimand mismatch
alone explained the v4.0 failure is rejected.

## Analysis B — exact conditional calibration of the old joint gate

Using only the already frozen D2.9 rotation tables for seeds `25001–25005`,
all `6^5 = 7776` one-rotation-per-seed pseudo-candidates were enumerated.

Exact results:

- Layer-A joint pass: `0 / 7776`;
- reachability joint pass: `0 / 7776`;
- overall old-gate pass: `0 / 7776`;
- median minimum normalized ratio: `0.868593011881834`;
- maximum minimum normalized ratio: `0.9675464164430708`.

Thus no observed candidate-style realization drawn from the frozen D2.9
positive-control rotations satisfied the simultaneous old gate.

Individual metric pass proportions ranged from `1/6 = 0.166667` to `0.75`;
therefore the defect is not that every individual reference is unattainable.
The problem is the simultaneous conjunction of many median-calibrated
references as a binary eligibility rule.

## Correct interpretation

D2.9 remains scientifically useful as an admissible positive-control
calibration and as a source of continuous structural reference levels.

This audit supports rejecting the *simultaneous binary joint gate* as a
production-generator feasibility rule. It does not support claiming that the
profile-ensemble mismatch alone rescued v4.0.

The audit is conditional on the five frozen D2.9 calibration worlds and is not
presented as an independent frequentist Type-I-error estimate.

## Remaining selection question

This audit does **not** by itself establish that `d29_kernel` is the unique
production-generator choice under the corrected eligibility rule.

Before D3 execution, all frozen historical response families should be
re-adjudicated read-only under the corrected hard gates. If multiple families
satisfy those gates, the production-generator choice must be resolved by an
explicit protocol-level rule rather than by historical candidate order or
downstream benchmark outcomes.

D3 execution remains paused until that question is settled.
