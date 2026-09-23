# Contribution Map

Each contribution, the research question it answers, the result that supports
it, and where that result appears. Every number is generated from
`results/results.json`.

## Contribution 1 --- Characterisation of the operating regions (RQ1)

| | |
|---|---|
| **Claim** | Four established routing policies exhibit complementary performance across a factorial of demand, signal timing, penetration, information lag, disruption and alternative capacity. |
| **Evidence** | Confirmatory gate G1', declared before the campaign: 3 of 4 policies are strictly best in at least one context with a seed-resolved margin (P1, P3, P4). P2 is never a resolved winner. |
| **Scale** | 12,960 runs, 648 contexts, 5 seeds, 0 failures, completion 1.0000. |
| **Where** | Results 7.2; Table 4; Figures 4 and 5. |
| **Qualification** | The winner map is multi-factor but shallow: a constant rule is correct in 64.0% of contexts, the best single factor reaches 67.0%. |

## Contribution 2 --- Mechanistic explanation of the boundary (RQ2)

| | |
|---|---|
| **Claim** | The preference boundary is explicable in dimensionless traffic terms, not only statistically. |
| **Evidence** | The depth-2 rule splits first on `x8_ctrl_sat` = p*D/cap_C, the share of the shortest corridor's capacity the guided cohort alone would consume, at a threshold bracketed in [0.748, 0.781]. |
| **Where** | Section 6; Results 7.6; Figure 6. |
| **Qualification** | Reported as a bracket between adjacent sampled levels, never as a point threshold. The rule is an association inside a designed factorial, not an identified causal mechanism. |

## Contribution 3 --- Decision-oriented evaluation against a mechanistic rule (RQ3)

| | |
|---|---|
| **Claim** | A learner adds value over a mechanistic rule only when it is trained on decision cost rather than on the winner's identity. |
| **Evidence** | B1 is *more accurate and more expensive* than the fixed policy: 67% vs 65% top-1, 0.77 s vs 0.45 s regret. B4, predicting advantage, reaches 0.20 s while being *less* accurate than B3 (73% vs 76%). |
| **Where** | Results 7.6--7.7; Table 5; Figure 7. |
| **Qualification** | The absolute saving is 0.252 s per vehicle on a mean journey time of 474.4 s --- under a tenth of one per cent. The selector works and is not worth deploying. |

## Contribution 4 --- A selective mechanism with a safety envelope (RQ4)

| | |
|---|---|
| **Claim** | A support-and-confidence gate prevents out-of-distribution harm by abstaining. |
| **Evidence** | B5 abstains in 36% of contexts and recovers the fixed policy exactly. Under shift, the unguarded selector harms: unseen high demand 0.00 -> 0.98 s; unseen disruption regime 0.63 -> 2.22 s. B5 returns both to the fixed policy's value. |
| **Where** | Results 7.8; Table 6; Figures 8 and 9. |
| **Qualification** | The gate forgoes the in-distribution gain. It abstains because the conformal interval is wider than the effect --- correct behaviour, not a tuning failure. No coverage guarantee is claimed out of distribution. |

## The result that reframes all four

| | |
|---|---|
| **Finding** | The value of adapting the policy is 0.451 s per vehicle (0.095%). The value of choosing the right *fixed* policy is 220.2 s (46.4%). |
| **Why** | The best fixed policy is near-dominant: it loses 1.32 s on average when it is not best (34.3% of contexts) and wins by 23.1 s when it is --- an upside 18x its downside. |
| **Resolution** | Among the 222 contexts where the fixed policy is not best, the headroom exceeds its own noise band in 55 (25%). Resolving the campaign-wide mean would need about 25 seeds per context. |
| **Where complementarity does live** | On the criterion vector: 73.0% of contexts have a non-singleton Pareto set, and the reliability-aware policy minimises stopped delay in 429 of 648 contexts while minimising journey time in only 129. |

## What is deliberately not claimed

* No new routing, learning or multi-criteria decision algorithm.
* No claim that regime-dependent routing has not been studied before.
* No external validity: the environment is synthetic and every result is scoped to it.
* No causal mechanism beyond association within a designed factorial.
* No continuous threshold: boundaries are brackets between sampled levels.
* No out-of-distribution coverage guarantee from conformal prediction.
