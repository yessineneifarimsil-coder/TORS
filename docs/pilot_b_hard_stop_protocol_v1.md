# Pilot-B prospective hard-stop protocol v1

## Status

**FROZEN PROSPECTIVELY BEFORE ANY PILOT-B RESULT IS COMPUTED OR INSPECTED**

This protocol turns the qualitative Pilot-B language in the frozen weighting/MCDM
specification into deterministic numerical gates. Pilot B is a development-only
benchmark-validity gate. It is not method selection, SHAP tuning, generator tuning
for a preferred ITS, or a primary analysis.

## Frozen scope

Pilot B uses only development seeds 21001--21005 at the reference condition
`(N,c,rho,lambda)=(250,0.30,0.4,0.5)`. Each seed uses its 200 fixed external
TEST contexts. The primary operator is MOORA. Each seed has 200 frozen
`Dirichlet(1,...,1)` random-weight vectors from namespace 81001.

The structured gate methods are OracleAttribution, SHAP,
PermutationImportance, RidgePlus, CRITIC, and Entropy. Equal, RandomWeights,
MajorityWinner, and DirectXGBoost are reported references; they cannot clear a
structured-method gate. DirectXGBoost remains a parallel predictive reference.

## Coverage before performance

A structured method is gate-eligible only if its weights are defined for all five
seeds, it uses no Equal fallback in any seed, and Kendall tau-b is defined in at
least 190 of 200 TEST contexts in every seed. Each seed must contain all 200 TEST
contexts and all 200 random draws; at least 190 random draws per seed must meet
the Kendall-coverage rule. Missing required output or insufficient coverage means
Pilot B cannot pass. Undefined vectors are recorded, never replaced.

## Aggregation

For each seed and scored representation, compute mean Kendall tau-b over defined
contexts, Top-1 accuracy, and mean normalized oracle regret. For RandomWeights,
each draw is scored over all 200 TEST contexts. Within each seed, use the median
random performance as its center and linear p05/p95 quantiles for widths. Across
the five seeds use the median. A sign-consistency clause requires a strictly
positive structured advantage in at least four of five seeds.

All advantages are oriented so positive favors the structured method:

- random Kendall advantage = structured mean tau-b minus random median mean tau-b;
- random regret advantage = random median mean regret minus structured mean regret;
- modal Top-1 advantage = structured Top-1 minus MajorityWinner Top-1;
- modal regret advantage = MajorityWinner mean regret minus structured mean regret.

## Gate 1: separation from RandomWeights

A gate-eligible structured method separates from RandomWeights if either:

1. its median Kendall advantage is at least 0.05 and the advantage is strictly
   positive in at least four of five seeds; or
2. its median mean-regret advantage is at least 0.01 and the advantage is strictly
   positive in at least four of five seeds.

Hard stop if no structured method separates. This is a prospective practical-
separation rule with replication consistency. It deliberately does not equate a
failure to reject a null hypothesis, with only five seeds, to evidence of
equivalence.

## Gate 2: escape from MajorityWinner

A gate-eligible structured method escapes the constant modal-winner reference if
either its median Top-1 advantage is at least 0.02 or its median mean-regret
advantage is at least 0.01, with a strictly positive advantage in at least four
of five seeds for the corresponding metric. Hard stop if no structured method
escapes.

## Gate 3: oracle-winner dominance

Pool the 1000 external TEST contexts across the five development seeds, using the
frozen ascending-alternative-ID oracle tie break. Hard stop if one alternative's
oracle-winner share is at least 0.90. Winner identity is descriptive only.

## Gate 4: effective insensitivity to weights

For every seed-context pair, find the modal Top-1 choice across the 200 random
weights. The context is random-weight invariant if that modal share is at least
0.95. Hard stop if at least 0.90 of the pooled 1000 seed-contexts are invariant.

An alternative performance-width clause also hard-stops if, in at least four of
five seeds, all three RandomWeights p95-minus-p05 widths are simultaneously at
most 0.05 for mean Kendall, 0.02 for Top-1, and 0.01 for mean regret. The two
insensitivity clauses are joined by OR.

## Overall rule

Coverage failure, no RandomWeights separation, no MajorityWinner escape, oracle-
winner dominance, or weight insensitivity each independently triggers the hard
stop. Pilot B passes only if every hard-stop flag is false. A hard stop forbids
the primary factorial; the finding must be documented and any revision must use
development data only, create a new specification version, and be tagged before
retry. Thresholds may not change after Pilot-B execution.
