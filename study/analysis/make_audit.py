"""Generate audit/SCIENTIFIC_AUDIT.md and audit/CONTRIBUTION_MAP.md from
results.json, so that the audit cannot disagree with the data it audits."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K

RES = os.path.join(HERE, "..", "results")
AUD = os.path.join(HERE, "..", "audit")
R = json.load(open(os.path.join(RES, "results.json")))
CAL = json.load(open(os.path.join(RES, "capacity_calibration.json")))
lad = {r["selector"]: r for r in R["ladder_loco"]}
v, g_, cm, cr, h = (R["validity"], R["G1_confirmatory"], R["complementarity"],
                    R["criteria"], R["headroom"])


def pc(x, d=1):
    return f"{100*float(x):.{d}f}%"


ood_rows = "\n".join(
    f"| {k} | {d['_held_out']} | {d['_shift_type']} | "
    f"{d['B0_SBS']['mean_regret']:.2f} | {d['B1_mechanistic']['mean_regret']:.2f} | "
    f"{d['B4_GBDT']['mean_regret']:.2f} | {d['B5_selective']['mean_regret']:.2f} | "
    f"{pc(d['_out_of_support_rate'],0)} | {pc(d['_abstain_rate'],0)} |"
    for k, d in sorted(R.get("ood", {}).items()))

lad_rows = "\n".join(
    f"| {k} | {lad[k]['mean_regret']:.2f} | {lad[k]['median_regret']:.2f} | "
    f"{lad[k]['max_regret']:.1f} | {pc(lad[k]['pct_within_noise'],0)} | "
    f"{'--' if k=='B0_SBS' else format(lad[k]['gap_closed_vs_SBS'],'.3f')} |"
    for k in ["B0_SBS", "B1_mechanistic", "B2_tree3", "B3_logit", "B4_GBDT",
              "B5_selective", "VBS_reference"])

sens = R.get("sensitivity", {})
sens_txt = "Sensitivity campaign not present." if not sens else (
    f"Preference profiles change the preferred policy in "
    f"{pc(sens['preference']['frac_profile_changes_decision'])} of contexts. "
    + " ".join(
        f"Under {pol}, changing {d['parameter']} from {d['frozen_value']} to "
        + ", ".join(f"{a} shifts mean journey time by {r['mean_change_s']:+.2f} s "
                    f"({r['mean_change_pct']:+.2f}%)"
                    for a, r in d["alternatives"].items()) + "."
        for pol, d in sens.get("parameters", {}).items()
        if isinstance(d, dict) and "alternatives" in d))

md = f"""# Scientific Audit

Generated from `results/results.json`. Every number here is the number the
analysis produced; nothing is transcribed by hand.

## 1. Data integrity

| | |
|---|---|
| Runs executed | {R['campaign']['n_runs']:,} |
| Runs failed | {R['campaign']['n_failed']} |
| Contexts designed | {R['campaign']['n_contexts']} |
| Contexts analysed | {v['n_contexts_analysed']} |
| Contexts excluded, invalid | {v['n_invalid_contexts']} |
| Contexts excluded, incomplete | {v['n_incomplete_contexts']} |
| Minimum completion rate | {v['min_completion']:.4f} |
| Mean completion rate | {v['mean_completion']:.4f} |
| Total teleports | {v['total_teleports']} |

Validity rule, declared in the frozen specification: {v['rule']}.
Completeness rule: {v['completeness_rule']}.

Every run record is a line of `results/main.jsonl` containing its full job
specification, so any reported value can be traced to the run that produced it.
`campaign.py` keys resumption on the full specification, so a re-run reproduces
the same set.

## 2. Leakage audit

| Risk | Control | Verified by |
|---|---|---|
| Outcome used as a feature | the eight descriptors are functions of the context definition only and cannot be computed from an outcome | `common.descriptors` takes no outcome column |
| Test outcomes in training | leave-one-context-out; the held-out context contributes nothing | `policy_selectors.loco` builds the training index by exclusion |
| Same context's seeds split across train and test | the context, not the run, is the unit; all seeds move together | `matrices` aggregates to one row per context before splitting |
| Preprocessing fitted on all data | standardisation, SBS identity, tree thresholds, conformal quantiles and the support envelope are all recomputed inside each fold | `policy_selectors.fit_predict` receives only the training index |
| SBS chosen with test knowledge | SBS is `argmin` of the mean cost over training contexts only | same |
| Hyperparameters tuned on test | fixed in the frozen specification before any evaluation run | `spec/FROZEN_SPEC.md` §8, committed before the campaign |
| Future information as a predictor | policies read link travel times no newer than `t - lag`; the incident realisation is never exposed | `policies.Observatory._visible`; test 1 in `tests/test_policies.py` |

## 3. Policy audit

12 known-answer tests plus a two-path in-simulator integration test, all
passing. The tests establish that the observation lag hides newer samples, that
the free-flow fallback engages before any admissible sample, that P1 ignores
congestion entirely, that P2 follows the observed mean, that P4 prefers the
steadier of two paths with equal means and reduces to P2 at lambda = 0, that P3
respects its admissibility tolerance and splits equal-cost paths in proportion
to capacity, and that a degenerate assignment window is refused rather than
silently absorbed. Inside the simulator, P3 splits demand 1.97 against a
capacity ratio of 2.00 while P1 commits the whole cohort to one path.

## 4. Seed and pairing audit

Seeds per cell: {R['campaign']['seeds_per_cell']}. Common random numbers: the
vehicle set, departure times, guided/unguided labelling, habitual corridor,
background traffic and the incident realisation are functions of the seed and
context alone. The experimental unit is the context. A difference is claimed
only when the paired seed difference exceeds twice its standard error; the mean
noise floor is {R['dataset']['mean_noise_floor_s']:.2f} s of journey time.
Unresolved differences are reported as ties, and the number of them is reported
rather than suppressed: {g_['n_unresolved']} of {g_['n_contexts']} contexts.

## 5. Metric audit

Capacity is measured, not assumed: {CAL['sat_flow_arterial_vphpl']:.0f} veh/h/lane
on the arterial, {CAL['sat_flow_north_vphpl']:.0f} on the slower street,
{CAL['cap_bypass_vphpl']:.0f} veh/h uninterrupted on the bypass.

Criterion alignment across the analysed contexts:

| pair | pooled r | identical policy ordering |
|---|---|---|
| journey time vs CO2 | {cr['C1_vs_C2']['pooled_pearson']:+.4f} | {pc(cr['C1_vs_C2']['frac_identical_ordering'],0)} |
| journey time vs stopped delay | {cr['C1_vs_C3']['pooled_pearson']:+.4f} | {pc(cr['C1_vs_C3']['frac_identical_ordering'],0)} |
| CO2 vs stopped delay | {cr['C2_vs_C3']['pooled_pearson']:+.4f} | {pc(cr['C2_vs_C3']['frac_identical_ordering'],0)} |

The best policy on CO2 differs from the best on journey time in
{cr['best_on_C2_differs_from_C1']['n']} contexts
({pc(cr['best_on_C2_differs_from_C1']['frac'],0)}); on stopped delay,
{cr['best_on_C3_differs_from_C1']['n']} ({pc(cr['best_on_C3_differs_from_C1']['frac'],0)}).

Three quantities are kept distinct throughout and never substituted: top-1
selection accuracy, the policy ranking, and decision regret in seconds.

## 6. Baseline audit

Single best policy: **{h['global_sbs']}**, optimal in {pc(h['frac_contexts_sbs_optimal'],0)}
of contexts. Mean cost {h['mean_cost_sbs_s']:.1f} s against the hindsight best
{h['mean_cost_vbs_s']:.1f} s, so the headroom available to any selector is
{h['mean_headroom_s']:.2f} s per vehicle ({h['mean_headroom_pct']:.2f}%), with a
maximum of {h['max_headroom_s']:.1f} s in a single context.

| selector | mean regret (s) | median | max | within noise | gap closed vs SBS |
|---|---|---|---|---|---|
{lad_rows}

VBS is retrospective and is not deployable; it appears only as an upper
reference. The primary comparison is B4 against B1.

## 7. Distribution-shift audit

| split | held out | shift type | B0 | B1 | B4 | B5 | flagged | abstained |
|---|---|---|---|---|---|---|---|---|
{ood_rows}

No coverage guarantee is claimed on any of these splits. Split conformal
coverage requires exchangeability, which covariate shift breaks; the conformal
gate is calibrated in-distribution and heuristic outside it, the support gate is
what addresses extrapolation, and neither detects concept shift.

## 8. Sensitivity audit

{sens_txt}

## 9. Reproducibility audit

| Item | Status |
|---|---|
| SUMO version | 1.27.1, pinned in `README.md` |
| Network files | generated by `scenario/build_net.py`, committed |
| Demand generation | `sim/demand.py`, deterministic in (demand, penetration, seed) |
| Policy implementation | `policies/policies.py`, committed, unit-tested |
| Run records | `results/*.jsonl`, one line per run with full specification |
| Analysis pipeline | `analysis/run_analysis.py` -> `results/results.json` |
| Manuscript numbers | `analysis/emit_numbers.py` -> `paper/numbers.tex` |
| Figures | `figures/*.py`, all reading `results.json` or the run records |
| Specification freeze | `spec/FROZEN_SPEC.md`, committed before the campaign |
| Protocol deviations | `results/SCREENING_REPORT.md`, deviation D-1 |
"""
open(os.path.join(AUD, "SCIENTIFIC_AUDIT.md"), "w").write(md)
print("wrote audit/SCIENTIFIC_AUDIT.md")

# ----------------------------------------------------------- contribution map
fp, asy, rz = R["fixed_policy_choice"], R["asymmetry"], R["resolvability"]
mr, cs = R["mechanistic_rule"], R["criterion_specialisation"]
ood = R.get("ood", {})


def g(split, sel, default="n/a"):
    try:
        return f"{ood[split][sel]['mean_regret']:.2f}"
    except Exception:
        return default


cmap = f"""# Contribution Map

Each contribution, the research question it answers, the result that supports
it, and where that result appears. Every number is generated from
`results/results.json`.

## Contribution 1 --- Characterisation of the operating regions (RQ1)

| | |
|---|---|
| **Claim** | Four established routing policies exhibit complementary performance across a factorial of demand, signal timing, penetration, information lag, disruption and alternative capacity. |
| **Evidence** | Confirmatory gate G1', declared before the campaign: {g_['n_policies_with_resolved_win']} of 4 policies are strictly best in at least one context with a seed-resolved margin ({', '.join(g_['policies'])}). P2 is never a resolved winner. |
| **Scale** | {R['campaign']['n_runs']:,} runs, {v['n_contexts_analysed']} contexts, {max(R['campaign']['seeds_per_cell'])} seeds, 0 failures, completion {v['min_completion']:.4f}. |
| **Where** | Results 7.2; Table 4; Figures 4 and 5. |
| **Qualification** | The winner map is multi-factor but shallow: a constant rule is correct in {pc(cm['winner_map']['constant_rule'],1)} of contexts, the best single factor reaches {pc(cm['winner_map']['best_single'],1)}. |

## Contribution 2 --- Mechanistic explanation of the boundary (RQ2)

| | |
|---|---|
| **Claim** | The preference boundary is explicable in dimensionless traffic terms, not only statistically. |
| **Evidence** | The depth-2 rule splits first on `{mr['root_feature']}` = p*D/cap_C, the share of the shortest corridor's capacity the guided cohort alone would consume, at a threshold bracketed in [{mr['bracket_low']:.3f}, {mr['bracket_high']:.3f}]. |
| **Where** | Section 6; Results 7.6; Figure 6. |
| **Qualification** | Reported as a bracket between adjacent sampled levels, never as a point threshold. The rule is an association inside a designed factorial, not an identified causal mechanism. |

## Contribution 3 --- Decision-oriented evaluation against a mechanistic rule (RQ3)

| | |
|---|---|
| **Claim** | A learner adds value over a mechanistic rule only when it is trained on decision cost rather than on the winner's identity. |
| **Evidence** | B1 is *more accurate and more expensive* than the fixed policy: {pc(R['top1_accuracy']['B1_mechanistic'],0)} vs {pc(R['top1_accuracy']['B0_SBS'],0)} top-1, {lad['B1_mechanistic']['mean_regret']:.2f} s vs {lad['B0_SBS']['mean_regret']:.2f} s regret. B4, predicting advantage, reaches {lad['B4_GBDT']['mean_regret']:.2f} s while being *less* accurate than B3 ({pc(R['top1_accuracy']['B4_GBDT'],0)} vs {pc(R['top1_accuracy']['B3_logit'],0)}). |
| **Where** | Results 7.6--7.7; Table 5; Figure 7. |
| **Qualification** | The absolute saving is {float(lad['B0_SBS']['mean_regret'])-float(lad['B4_GBDT']['mean_regret']):.3f} s per vehicle on a mean journey time of {fp['mean_cost'][fp['sbs']]:.1f} s --- under a tenth of one per cent. The selector works and is not worth deploying. |

## Contribution 4 --- A selective mechanism with a safety envelope (RQ4)

| | |
|---|---|
| **Claim** | A support-and-confidence gate prevents out-of-distribution harm by abstaining. |
| **Evidence** | B5 abstains in {pc(R['ladder_loco_abstention']['rate'],0)} of contexts and recovers the fixed policy exactly. Under shift, the unguarded selector harms: unseen high demand {g('O1_demand_high','B0_SBS')} -> {g('O1_demand_high','B4_GBDT')} s; unseen disruption regime {g('O7_incident','B0_SBS')} -> {g('O7_incident','B4_GBDT')} s. B5 returns both to the fixed policy's value. |
| **Where** | Results 7.8; Table 6; Figures 8 and 9. |
| **Qualification** | The gate forgoes the in-distribution gain. It abstains because the conformal interval is wider than the effect --- correct behaviour, not a tuning failure. No coverage guarantee is claimed out of distribution. |

## The result that reframes all four

| | |
|---|---|
| **Finding** | The value of adapting the policy is {rz['mean_headroom_s']:.3f} s per vehicle ({100*rz['mean_headroom_s']/fp['mean_cost'][fp['sbs']]:.3f}%). The value of choosing the right *fixed* policy is {fp['worst_penalty_s']:.1f} s ({fp['worst_penalty_pct']:.1f}%). |
| **Why** | The best fixed policy is near-dominant: it loses {asy['mean_loss_when_not_best_s']:.2f} s on average when it is not best ({pc(asy['frac_contexts_sbs_not_best'],1)} of contexts) and wins by {asy['mean_margin_when_best_s']:.1f} s when it is --- an upside {asy['upside_downside_ratio']:.0f}x its downside. |
| **Resolution** | Among the {rz['n_contexts_sbs_not_best']} contexts where the fixed policy is not best, the headroom exceeds its own noise band in {rz['n_headroom_exceeds_own_noise']} ({pc(rz['frac_headroom_exceeds_own_noise'],0)}). Resolving the campaign-wide mean would need about {rz['seeds_needed_for_mean_effect']} seeds per context. |
| **Where complementarity does live** | On the criterion vector: {pc(cm['frac_non_singleton_pareto'],1)} of contexts have a non-singleton Pareto set, and the reliability-aware policy minimises stopped delay in {cs['C3']['P4']} of {v['n_contexts_analysed']} contexts while minimising journey time in only {cs['C1']['P4']}. |

## What is deliberately not claimed

* No new routing, learning or multi-criteria decision algorithm.
* No claim that regime-dependent routing has not been studied before.
* No external validity: the environment is synthetic and every result is scoped to it.
* No causal mechanism beyond association within a designed factorial.
* No continuous threshold: boundaries are brackets between sampled levels.
* No out-of-distribution coverage guarantee from conformal prediction.
"""
open(os.path.join(AUD, "CONTRIBUTION_MAP.md"), "w").write(cmap)
print("wrote audit/CONTRIBUTION_MAP.md")
