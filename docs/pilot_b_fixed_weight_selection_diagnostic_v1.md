# Pilot-B fixed-weight selection diagnostic protocol v1

## Status

**FROZEN PROSPECTIVELY BEFORE ANY FIXED-WEIGHT SELECTION DIAGNOSTIC RESULT**

This is a post-hoc, development-only descriptive diagnostic. It was specified only
after Pilot B had fired, its result had been independently audited and frozen, and
v1 had been permanently closed. It cannot alter the Pilot-B result, any threshold,
the closed-v1 interpretation boundary, or authorization for protected seeds.

## Why this diagnostic is needed

The frozen Pilot-B artefact retains method-level Top-1 accuracy, normalized regret
and mean Kendall tau-b, but not each method's selected alternative or MOORA score
vector for every TEST context. Equality of aggregate Top-1 and mean regret does not
prove equality of context-level choices. Conversely, different mean Kendall values
concern complete rankings and do not prove that context-level argmax choices differ.
The missing selection map also prevents a paired context bootstrap from being
reconstructed from the closed artefact alone.

## Frozen scope

The diagnostic uses only development worlds 21001--21005 at
`(N,c,rho,lambda)=(250,0.30,0.4,0.5)` and their 200 frozen external TEST contexts.
It evaluates only the seven observed fixed vectors: OracleAttribution, SHAP,
PermutationImportance, RidgePlus, CRITIC, Entropy and Equal. The six structured
vectors are read from the immutable Pilot-B result; Equal is exactly `(0.1,...,0.1)`.
No primary or reserve seed is permitted.

## Reconstruction firewall

The frozen D29 TEST decision matrices and oracle utilities are reconstructed solely
to reproduce the archived decisions. No target outcome is generated. No model is
fit or queried. Oracle, SHAP, PI, Ridge+, CRITIC and Entropy weights are not
re-estimated. RandomWeights are not rerun. The frozen benefit-oriented MOORA
operator, common vector normalization, tie rules and decision metrics are reused.

Before any result may be written, the executor must reproduce each archived
method--world Top-1 accuracy, mean normalized regret and mean Kendall tau-b within
absolute tolerance `1e-12`. The frozen result hash, world identities, condition,
TEST order and archived weights are mandatory guards. Any mismatch aborts without
writing a result.

## Required context-level artefact

For every world, observed fixed-weight method and TEST context, persist the context
identifier; selected alternative; six MOORA scores and ranks; oracle choice,
utilities and ranks; Top-1 match; normalized regret contribution; the frozen
MajorityWinner identity; and agreement with MajorityWinner. Exactly 7000 records
are required. Full numeric precision is retained.

Per world and method, report selection counts, number of unique selected
alternatives, modal identity and share, whether selection is constant over all 200
contexts, agreement with MajorityWinner, Kendall coverage, mean Kendall tau-b,
Top-1 accuracy and mean normalized regret. Also report pairwise context-level
selection agreement among the seven observed vectors.

## Interpretation boundary

The diagnostic can describe selection invariance and agreement only for the seven
observed archived vectors, five development worlds and one reference condition. It
cannot establish a causal explanation for the closed gate, characterize unobserved
regions of the weight simplex, demonstrate universal weight irrelevance, select a
preferred method, or generalize to protected seeds.

No pass/fail threshold is defined. A paired context bootstrap is not part of this
layer. Once the context-level artefact itself has been executed, independently
audited and frozen, any resampling analysis must receive its own prospectively
frozen protocol. This ordering prevents an inferential analysis from being designed
after inspecting unarchived context-level outcomes.
