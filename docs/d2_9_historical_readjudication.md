# D2.9 historical-family re-adjudication

## Outcome

Using the frozen D2.9 scientific references and the already frozen historical
candidate artifacts, no historical family contains a feasible candidate.

Historical selection rules were preserved exactly:

- v2.2-D4-F1: numerical + Layer-A + reachability.
- v2.3-F1 through v3.0-F1: numerical + invariants + Layer-A + reachability.

Old D2.7 Layer-A and reachability pass/fail fields were ignored. Frozen D2.8
numerical gates were retained. No candidate generator was rerun, and no
validation, primary, or external TEST seed was used.

Closest descriptive points:

- v2.2-D4-F1: kappa=0.4, joint minimum ratio 0.600554.
- v2.3-F1: eta=1.0, joint minimum ratio 0.200529.
- v2.4-F1: eta=0.6, joint minimum ratio 0.841863.
- v2.5-F1: eta=0.7, joint minimum ratio 0.947419.
- v3.0-F1: p=2, joint minimum ratio 0.956089.

The closest historical candidate is v3.0 at p=2. Its Layer-A bottleneck is C7
with ratio 0.956089, while its minimum SRE ratio is 1.020095 at h_T->C3.
At p=3, Layer-A passes but reachability fails. This identifies a narrow
cross-over between non-separability strength and latent-pathway reachability.

Any further architecture development must therefore be prospective and use a
fresh development cohort.
