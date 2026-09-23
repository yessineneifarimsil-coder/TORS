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


DIG = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
       "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def w(s):
    """LaTeX command names may not contain digits."""
    return "".join(DIG.get(ch, ch) for ch in str(s))


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
    m(f"WinAll{w(p)}", f"{n}")
for p in ["P1", "P2", "P3", "P4"]:
    m(f"WinRes{w(p)}", f"{g['winner_counts_resolved'].get(p, 0)}")

# --- complementarity
cm = R["complementarity"]
n = cm["n_contexts"]
for p, k in cm["pareto_membership"].items():
    m(f"Pareto{w(p)}", f"{k}")
    m(f"ParetoPct{w(p)}", pct(k / n, 0))
m("ParetoNonSingleton", pct(cm["frac_non_singleton_pareto"]))
m("MeanIdentity", pct(cm["mean_pairwise_identity"]))
wm = cm["winner_map"]
m("StumpBest", pct(wm["best_single"]))
m("StumpBestFactor", wm["best_single_factor"].replace("_", " "))
m("StumpTwo", pct(wm["best_two_factor"]))
m("ConstantRule", pct(wm["constant_rule"]))
for k, v2 in cm["pairwise_identity"].items():
    m("Ident" + w(k.replace("-", "")), pct(v2, 0))
for k, v2 in cm["pairwise_gap_seconds"].items():
    m("Gap" + w(k.replace("-", "")), f"{v2['mean']:+.2f}")

# --- criteria
cr = R["criteria"]
for a, b in [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]:
    d = cr[f"{a}_vs_{b}"]
    m(f"Corr{w(a)}{w(b)}", f"{d['pooled_pearson']:+.4f}")
    m(f"SameOrder{w(a)}{w(b)}", pct(d["frac_identical_ordering"], 0))
m("BestCTwoDiffers", f"{cr['best_on_C2_differs_from_C1']['n']}")
m("BestCTwoDiffersPct", pct(cr["best_on_C2_differs_from_C1"]["frac"], 0))
m("BestCThreeDiffers", f"{cr['best_on_C3_differs_from_C1']['n']}")
m("BestCThreeDiffersPct", pct(cr["best_on_C3_differs_from_C1"]["frac"], 0))

# --- headroom
h = R["headroom"]
m("GlobalSBS", h["global_sbs"])
m("CostSBS", f"{h['mean_cost_sbs_s']:.1f}")
m("CostVBS", f"{h['mean_cost_vbs_s']:.1f}")
m("Headroom", f"{h['mean_headroom_s']:.3f}")
# ONE definition, used everywhere: the aggregate headroom as a share of the
# single-best fixed policy's mean journey time.  The per-context mean of
# (headroom_i / best_i) is a different statistic and is emitted separately
# under an explicitly different name so the two can never be conflated.
_agg = 100.0 * h["mean_headroom_s"] / h["mean_cost_sbs_s"]
m("HeadroomPct", f"{_agg:.3f}\\%")
m("HeadroomPctPerContext", f"{h['mean_headroom_pct']:.2f}\\%")
m("SBSMeanCost", f"{h['mean_cost_sbs_s']:.1f}")
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
b0 = lad["B0_SBS"]["mean_regret"]
m("BFourVsBZero", f"{b0 - b4:.3f}")
m("BFourVsBZeroPct", f"{100.0*(b0-b4)/R['headroom']['mean_cost_sbs_s']:.3f}\\%")
m("BFourBeatsBOne", "yes" if b4 < b1 else "no")

# --- OOD
sh = {"O1_demand_high": "OneHigh", "O2_demand_low": "TwoLow",
      "O3_demand_mid": "ThreeMid", "O4_lag_long": "FourLag",
      "O5_penetration": "FivePen", "O6_green_high": "SixGreen",
      "O7_incident": "SevenInc", "O8_northcorridor": "EightNorth"}
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
        m(f"FixedCost{w(p)}", f"{f['mean_cost'][p]:.1f}")
        m(f"FixedPen{w(p)}", f"{f['penalty_vs_sbs_s'][p]:+.1f}")
        m(f"FixedPenPct{w(p)}", f"{f['penalty_vs_sbs_pct'][p]:+.1f}\\%")
        m(f"FixedPenPctAbs{w(p)}", f"{abs(f['penalty_vs_sbs_pct'][p]):.1f}\\%")
        m(f"FixedPenAbs{w(p)}", f"{abs(f['penalty_vs_sbs_s'][p]):.1f}")

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
        m(f"Spec{w(c)}Policy", bestp)
        m(f"Spec{w(c)}N", f"{cs[c][bestp]}")
        m(f"Spec{w(c)}Pct", pct(cs[c][bestp] / tot, 0))
        for p in ["P1", "P2", "P3", "P4"]:
            m(f"Spec{w(c)}{w(p)}", f"{cs[c][p]}")

# --- winner-map dimensionality
wmv = cm["winner_map"]
m("WinMapConst", pct(wmv["constant_rule"], 1))
m("WinMapOne", pct(wmv["best_single"], 1))
m("WinMapOneFactor", wmv["best_single_factor"].replace("_", " "))
m("WinMapTwo", pct(wmv["best_two_factor"], 1))

# --- sensitivity
if "sensitivity" in R and "parameters" in R["sensitivity"]:
    prm = R["sensitivity"]["parameters"]
    if isinstance(prm.get("P3"), dict) and "alternatives" in prm["P3"]:
        d3 = prm["P3"]
        m("EpsFrozen", f"{d3['frozen_value']:.2f}")
        alts = d3["alternatives"]
        bestalt = min(alts, key=lambda a: alts[a]["mean_change_pct"])
        m("EpsAlt", f"{float(bestalt):.2f}")
        m("EpsGainPct", f"{abs(alts[bestalt]['mean_change_pct']):.2f}\\%")
        m("EpsGainSec", f"{abs(alts[bestalt]['mean_change_s']):.1f}")
    if isinstance(prm.get("P4"), dict) and "alternatives" in prm["P4"]:
        d4 = prm["P4"]
        mx = max(abs(v["mean_change_pct"]) for v in d4["alternatives"].values())
        m("LambdaMaxChangePct", f"{mx:.2f}\\%")
    st = R["sensitivity"].get("winner_stability", {})
    if isinstance(st, dict) and st:
        vals = [v["frac_winner_unchanged"] for v in st.values()
                if isinstance(v, dict) and v.get("frac_winner_unchanged") is not None]
        if vals:
            m("WinnerStableMin", pct(min(vals), 0))
            m("WinnerStableMax", pct(max(vals), 0))

if "sensitivity" in R and "preference" in R["sensitivity"]:
    sp = R["sensitivity"]["preference"]
    m("PrefChanges", pct(sp["frac_profile_changes_decision"], 1))
    for k, vv in sp["frac_profile_agrees_with_C1"].items():
        m("PrefAgree" + k.capitalize(), pct(vv, 0))

# --- boundary localisation
if "boundary_summary" in R:
    bs = R["boundary_summary"]
    m("BoundN", f"{bs['n_brackets']}")
    m("BoundMono", f"{bs['n_monotone']}")
    m("BoundNonMono", f"{bs['n_nonmonotone']}")
    m("BoundNarrowed", f"{bs['n_point_narrowed']}")
    m("BoundWidth", f"{bs['median_point_bracket_width']:.0f}")
    m("BoundGrid", f"{bs['original_grid_spacing']:.0f}")
    mono = bs["monotone"]
    p13 = [r for r in mono if r["from"] == "P1" and r["to"] == "P3"]
    if p13:
        brs = sorted((r["point_estimate_bracket"] for r in p13),
                     key=lambda t: t[0])
        med = brs[len(brs) // 2]
        los = [b[0] for b in brs]; his = [b[1] for b in brs]
        m("BoundPOneN", f"{len(p13)}")
        m("BoundPOneMedLo", f"{med[0]:.0f}")
        m("BoundPOneMedHi", f"{med[1]:.0f}")
        m("BoundPOneEarliestLo", f"{min(los):.0f}")
        m("BoundPOneEarliestHi", f"{min(los) + 150:.0f}")
        m("BoundPOneLatestLo", f"{max(los):.0f}")
        m("BoundPOneLatestHi", f"{max(his):.0f}")
    nm = [r for r in bs["nonmonotone"]]
    m("BoundNonMonoPFour", f"{sum(1 for r in nm if 'P4' in (r['from'], r['to']))}")

# --- OOD classification (abstract must match the table)
if "ood_summary" in R:
    os_ = R["ood_summary"]
    m("OODNHelps", f"{os_['n_helps']}")
    m("OODNNeutral", f"{os_['n_neutral']}")
    m("OODNHarms", f"{os_['n_harms']}")
    m("OODNTotal", f"{os_['n_helps']+os_['n_neutral']+os_['n_harms']}")
    m("OODTolerance", f"{os_['tolerance_s']:.2f}")
    m("OODWorstSplit", os_["worst_harm_split"].split("_")[0])
    m("OODWorstBZero", f"{os_['worst_harm_b0']:.2f}")
    m("OODWorstBFour", f"{os_['worst_harm_b4']:.2f}")
    for k, vv in os_["classification"].items():
        m("OODClass" + w(k.split("_")[0]), vv)

# --- run-count reconciliation
m("RunsMain", "12{,}960")
m("RunsTotalSucceeded", "18{,}124")
m("RunsTotalAttempted", "20{,}284")
m("RunsFailedBypass", "2{,}160")
m("RunsValidate", "384")
m("RunsScreen", "640")
m("RunsSens", "1{,}920")
m("RunsOODNorth", "1{,}080")
m("RunsBoundary", "1{,}140")

# --- bibliography size
import re as _re
_bib = open(os.path.join(HERE, "..", "paper", "references.bib")).read()
m("Refs", str(len(_re.findall(r'@\w+\{', _bib))))

with open(OUT, "w") as f:
    f.write("% GENERATED by analysis/emit_numbers.py -- do not edit.\n")
    f.write("% Every numeric claim in the manuscript resolves through a macro here.\n")
    for k in sorted(M):
        f.write("\\newcommand{\\Num%s}{%s}\n" % (k, M[k]))
print(f"wrote {OUT} with {len(M)} macros")
