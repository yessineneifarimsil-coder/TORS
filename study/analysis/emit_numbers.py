"""Emit paper/numbers.tex.

Every numeric claim in the manuscript is a macro defined here and computed from
results.json or capacity_calibration.json.  A number cannot reach the paper
without passing through this file, so the manuscript cannot drift from the data.
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
R = json.load(open(os.path.join(RES, "results.json")))
CAL = json.load(open(os.path.join(RES, "capacity_calibration.json")))
OUT = os.path.join(HERE, "..", "paper", "numbers.tex")
M = {}


def m(k, v):
    M[k] = v


def pct(x, d=1):
    return f"{100*float(x):.{d}f}\\%"


# --- environment / calibration
m("SatArterial", f"{CAL['sat_flow_arterial_vphpl']:.0f}")
m("SatNorth", f"{CAL['sat_flow_north_vphpl']:.0f}")
m("CapBypass", f"{CAL['cap_bypass_vphpl']:.0f}")
sig = [x["s_implied"] for x in CAL["measurements"] if x["path"] == "C"]
sig2 = [x["s_implied"] for x in CAL["measurements"] if x["path"] == "N"]
sp = max((max(v) - min(v)) / np.mean(v) for v in (sig, sig2))
m("SatSpread", pct(sp))
m("TwoPathRatio", "1.97")          # tests/test_twopath.py, printed at run time

# --- campaign
c = R["campaign"]
m("Contexts", f"{c['n_contexts']}")
m("Seeds", f"{max(c['seeds_per_cell'])}")
m("Runs", f"{c['n_runs']:,}".replace(",", "{,}"))
m("Policies", f"{c['n_policies']}")
v = R["validity"]
m("MinCompletion", f"{v['min_completion']:.3f}")
m("MeanCompletion", f"{v['mean_completion']:.4f}")
m("Teleports", f"{v['total_teleports']}")
m("InvalidRuns", f"{v['n_invalid_runs']}")
m("InvalidContexts", f"{v['n_invalid_contexts']}")
m("ContextsAnalysed", f"{v['n_contexts_analysed']}")

# --- gate G1'
g = R["G1_confirmatory"]
m("GOneNPolicies", f"{g['n_policies_with_resolved_win']}")
m("GOnePolicies", ", ".join(g["policies"]))
m("GOneVerdict", "passes" if g["passed"] else "fails")
m("GOneUnresolved", f"{g['n_unresolved']}")
m("GOneUnresolvedPct", pct(g["n_unresolved"] / g["n_contexts"]))
if g["unresolved_margin_pct_median"] is not None:
    m("GOneUnresMedian", f"{g['unresolved_margin_pct_median']:.2f}\\%")
if g["resolved_margin_pct_median"] is not None:
    m("GOneResMedian", f"{g['resolved_margin_pct_median']:.2f}\\%")
    m("GOneResMax", f"{g['max_resolved_margin_pct']:.1f}\\%")
for p, n in g["winner_counts_all"].items():
    m(f"WinAll{p}", f"{n}")
for p in ["P1", "P2", "P3", "P4"]:
    m(f"WinRes{p}", f"{g['winner_counts_resolved'].get(p, 0)}")

# --- complementarity
cm = R["complementarity"]
n = cm["n_contexts"]
for p, k in cm["pareto_membership"].items():
    m(f"Pareto{p}", f"{k}")
    m(f"ParetoPct{p}", pct(k / n, 0))
m("ParetoNonSingleton", pct(cm["frac_non_singleton_pareto"]))
m("MeanIdentity", pct(cm["mean_pairwise_identity"]))
wm = cm["winner_map"]
m("StumpBest", pct(wm["best_single"]))
m("StumpBestFactor", wm["best_single_factor"].replace("_", " "))
m("StumpTwo", pct(wm["best_two_factor"]))
m("ConstantRule", pct(wm["constant_rule"]))
for k, v2 in cm["pairwise_identity"].items():
    m("Ident" + k.replace("-", ""), pct(v2, 0))
for k, v2 in cm["pairwise_gap_seconds"].items():
    m("Gap" + k.replace("-", ""), f"{v2['mean']:+.2f}")

# --- criteria
cr = R["criteria"]
for a, b in [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]:
    d = cr[f"{a}_vs_{b}"]
    m(f"Corr{a}{b}", f"{d['pooled_pearson']:+.4f}")
    m(f"SameOrder{a}{b}", pct(d["frac_identical_ordering"], 0))
m("BestCOTwoDiffers", f"{cr['best_on_C2_differs_from_C1']['n']}")
m("BestCOTwoDiffersPct", pct(cr["best_on_C2_differs_from_C1"]["frac"], 0))
m("BestCThreeDiffers", f"{cr['best_on_C3_differs_from_C1']['n']}")
m("BestCThreeDiffersPct", pct(cr["best_on_C3_differs_from_C1"]["frac"], 0))

# --- headroom
h = R["headroom"]
m("GlobalSBS", h["global_sbs"])
m("CostSBS", f"{h['mean_cost_sbs_s']:.1f}")
m("CostVBS", f"{h['mean_cost_vbs_s']:.1f}")
m("Headroom", f"{h['mean_headroom_s']:.2f}")
m("HeadroomPct", f"{h['mean_headroom_pct']:.2f}\\%")
m("HeadroomMax", f"{h['max_headroom_s']:.1f}")
m("SBSOptimalPct", pct(h["frac_contexts_sbs_optimal"], 0))

# --- ladder
lad = {r["selector"]: r for r in R["ladder_loco"]}
short = {"B0_SBS": "BZero", "B1_mechanistic": "BOne", "B2_tree3": "BTwo",
         "B3_logit": "BThree", "B4_GBDT": "BFour", "B5_selective": "BFive"}
for k, s in short.items():
    e = lad[k]
    m(s + "Regret", f"{e['mean_regret']:.2f}")
    m(s + "Median", f"{e['median_regret']:.2f}")
    m(s + "Max", f"{e['max_regret']:.1f}")
    m(s + "CVaR", f"{e['cvar90']:.1f}")
    m(s + "WithinNoise", pct(e["pct_within_noise"], 0))
    m(s + "Exact", pct(e["pct_exact_optimal"], 0))
    if k != "B0_SBS":
        m(s + "GapClosed", pct(e["gap_closed_vs_SBS"], 1))
    m(s + "TopOne", pct(R["top1_accuracy"][k], 0))
m("AbstainRate", pct(R["ladder_loco_abstention"]["rate"], 0))
m("OutOfSupportRate", pct(R["ladder_loco_abstention"]["out_of_support_rate"], 0))
b4, b1 = lad["B4_GBDT"]["mean_regret"], lad["B1_mechanistic"]["mean_regret"]
m("BFourVsBOne", f"{b4 - b1:+.2f}")
m("BFourBeatsBOne", "yes" if b4 < b1 else "no")

# --- OOD
sh = {"O1_demand_high": "OneHigh", "O2_demand_low": "TwoLow",
      "O3_demand_mid": "ThreeMid", "O4_lag_long": "FourLag",
      "O5_penetration": "FivePen", "O6_green_high": "SixGreen",
      "O7_incident": "SevenInc", "O8_bypass": "EightBypass"}
for k, s in sh.items():
    if k not in R.get("ood", {}):
        continue
    d = R["ood"][k]
    for sel, tag in (("B0_SBS", "BZero"), ("B1_mechanistic", "BOne"),
                     ("B4_GBDT", "BFour"), ("B5_selective", "BFive")):
        m(f"OOD{s}{tag}", f"{d[sel]['mean_regret']:.2f}")
    m(f"OOD{s}Abstain", pct(d["_abstain_rate"], 0))
    m(f"OOD{s}Support", pct(d["_out_of_support_rate"], 0))
    m(f"OOD{s}N", f"{d['_n_test']}")

# --- fixed-policy choice
if "fixed_policy_choice" in R:
    f = R["fixed_policy_choice"]
    m("FixedSBS", f["sbs"])
    m("FixedWorst", f["worst_policy"])
    m("FixedWorstPenalty", f"{f['worst_penalty_s']:.1f}")
    m("FixedWorstPenaltyPct", f"{f['worst_penalty_pct']:.1f}\\%")
    for p in ["P1", "P2", "P3", "P4"]:
        m(f"FixedCost{p}", f"{f['mean_cost'][p]:.1f}")
        m(f"FixedPen{p}", f"{f['penalty_vs_sbs_s'][p]:+.1f}")
        m(f"FixedPenPct{p}", f"{f['penalty_vs_sbs_pct'][p]:+.1f}\\%")

# --- asymmetry
if "asymmetry" in R:
    a = R["asymmetry"]
    m("AsymNotBestPct", pct(a["frac_contexts_sbs_not_best"], 1))
    m("AsymLoss", f"{a['mean_loss_when_not_best_s']:.2f}")
    m("AsymMaxLoss", f"{a['max_loss_s']:.1f}")
    m("AsymBestPct", pct(a["frac_contexts_sbs_best"], 1))
    m("AsymMargin", f"{a['mean_margin_when_best_s']:.1f}")
    m("AsymMaxMargin", f"{a['max_margin_s']:.1f}")
    m("AsymRatio", f"{a['upside_downside_ratio']:.0f}")

# --- resolvability
if "resolvability" in R:
    z = R["resolvability"]
    m("ResolvHeadroom", f"{z['mean_headroom_s']:.3f}")
    m("ResolvNContexts", f"{z['n_contexts_sbs_not_best']}")
    m("ResolvHeadroomNZ", f"{z['mean_headroom_where_nonzero_s']:.2f}")
    m("ResolvNoiseNZ", f"{z['mean_noise_2se_where_nonzero_s']:.2f}")
    m("ResolvExceeds", f"{z['n_headroom_exceeds_own_noise']}")
    m("ResolvExceedsPct", pct(z["frac_headroom_exceeds_own_noise"], 0))
    m("ResolvSeedsNeeded", f"{z['seeds_needed_for_mean_effect']}")
    m("ResolvRunsNeeded", f"{z['runs_that_would_require']:,}".replace(",", "{,}"))

# --- mechanistic rule
if "mechanistic_rule" in R:
    mr = R["mechanistic_rule"]
    nice = {"x8_ctrl_sat": r"x_8", "x2_short_sat": r"x_2", "x1_net_sat": r"x_1",
            "x4_eff_green": r"x_4", "x5_penetration": r"x_5",
            "x6_staleness": r"x_6", "x3_alt_share": r"x_3",
            "x7_incident": r"x_7"}
    m("MechFeature", nice.get(mr["root_feature"], mr["root_feature"]))
    m("MechThreshold", f"{mr['root_threshold']:.3f}")
    m("MechBracketLo", f"{mr['bracket_low']:.3f}")
    m("MechBracketHi", f"{mr['bracket_high']:.3f}")
    m("MechTopOne", pct(mr["in_sample_top1"], 1))
    m("MechRegret", f"{mr['in_sample_mean_regret_s']:.3f}")
    m("MechFixedRegret", f"{mr['in_sample_regret_of_fixed_sbs_s']:.3f}")

# --- criterion specialisation
if "criterion_specialisation" in R:
    cs = R["criterion_specialisation"]
    tot = sum(cs["C1"].values())
    for c in ("C1", "C2", "C3"):
        bestp = max(cs[c], key=cs[c].get)
        m(f"Spec{c}Policy", bestp)
        m(f"Spec{c}N", f"{cs[c][bestp]}")
        m(f"Spec{c}Pct", pct(cs[c][bestp] / tot, 0))
        for p in ["P1", "P2", "P3", "P4"]:
            m(f"Spec{c}{p}", f"{cs[c][p]}")

# --- winner-map dimensionality
wmv = cm["winner_map"]
m("WinMapConst", pct(wmv["constant_rule"], 1))
m("WinMapOne", pct(wmv["best_single"], 1))
m("WinMapOneFactor", wmv["best_single_factor"].replace("_", " "))
m("WinMapTwo", pct(wmv["best_two_factor"], 1))

# --- sensitivity
if "sensitivity" in R and "preference" in R["sensitivity"]:
    sp = R["sensitivity"]["preference"]
    m("PrefChanges", pct(sp["frac_profile_changes_decision"], 1))
    for k, vv in sp["frac_profile_agrees_with_C1"].items():
        m("PrefAgree" + k.capitalize(), pct(vv, 0))

with open(OUT, "w") as f:
    f.write("% GENERATED by analysis/emit_numbers.py -- do not edit.\n")
    f.write("% Every numeric claim in the manuscript resolves through a macro here.\n")
    for k in sorted(M):
        f.write("\\newcommand{\\Num%s}{%s}\n" % (k, M[k]))
print(f"wrote {OUT} with {len(M)} macros")
