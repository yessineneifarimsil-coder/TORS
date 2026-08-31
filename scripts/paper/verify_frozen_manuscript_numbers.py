#!/usr/bin/env python3
"""Verify every load-bearing number in the manuscripts against the frozen record.

For each claim the script does two things:

1. reads the value out of the frozen scientific artefact;
2. checks that the literal string printed in the manuscript matches that value
   at the precision the manuscript uses.

It never repairs a manuscript and never edits an artefact. On any disagreement it
prints the claim, the frozen value and the manuscript literal, and exits non-zero.
A disagreement is a finding to be reported, not a number to be adjusted.

Usage
-----
    python scripts/paper/verify_frozen_manuscript_numbers.py
    python scripts/paper/verify_frozen_manuscript_numbers.py --json outputs/paper/audit/numbers.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402


@dataclass
class Check:
    """One traceable claim: a frozen value, and the literal the manuscript prints."""

    name: str
    source: str
    frozen: object
    literal: str | None = None
    where: tuple[str, ...] = ()
    ok: bool = field(default=False, init=False)
    detail: str = field(default="", init=False)


class Verifier:
    def __init__(self) -> None:
        self.checks: list[Check] = []
        self.texts: dict[str, str] = {}
        for label, path in (("main", fz.MAIN_TEX), ("supp", fz.SUPP_TEX)):
            if path.exists():
                self.texts[label] = fz.read_text(path)
            else:
                print(f"WARNING: {label} manuscript not found at {path}", file=sys.stderr)

    # -- primitives ----------------------------------------------------
    @staticmethod
    def _squash(s: str) -> str:
        """Collapse all whitespace so line wrapping and table padding do not matter."""
        return re.sub(r"\s+", "", s)

    def _contains(self, label: str, literal: str) -> bool:
        text = self.texts.get(label, "")
        return literal in text or self._squash(literal) in self._squash(text)

    def add(self, name, source, frozen, literal=None, where=()):
        chk = Check(name, source, frozen, literal, where)
        if literal is None:
            chk.ok = True
            chk.detail = "frozen value recorded; no manuscript literal claimed"
        else:
            missing = [w for w in where if not self._contains(w, literal)]
            if missing:
                chk.ok = False
                chk.detail = f"literal {literal!r} absent from: {', '.join(missing)}"
            else:
                chk.ok = True
                chk.detail = f"literal {literal!r} present in {', '.join(where)}"
        self.checks.append(chk)
        return chk

    def num(self, name, source, frozen, fmt, where, prefix="", suffix=""):
        """Format a frozen number to the manuscript's precision and require it."""
        literal = prefix + format(frozen, fmt) + suffix
        return self.add(name, source, frozen, literal, where)

    # -- claim sets ----------------------------------------------------
    def pilot_b_contrasts(self):
        a = fz.pilot_b_assessments()
        src = "results/pilot_b_reference_v1/...json :: structured_method_assessments"
        # Table: cross-world median contrasts, and the counts of positive worlds.
        spec = {
            "OracleAttribution": ("-0.010", "-0.002119", "0.209", "0.023940", 1, 1, 5, 4),
            "SHAP": ("0.000", "0.000000", "0.288", "0.026060", 2, 2, 5, 4),
            "PermutationImportance": ("-0.120", "-0.004425", "0.194", "0.010658", 1, 1, 5, 4),
            "RidgePlus": ("-0.010", "-0.002119", "0.237", "0.011492", 1, 1, 5, 4),
            "CRITIC": ("-0.580", "-0.124414", "0.030", "-0.098354", 0, 0, 3, 0),
            "Entropy": ("-0.580", "-0.156641", "0.035", "-0.002807", 0, 0, 3, 1),
        }
        for method, (t1, rg, tau, rreg, pt1, prg, ptau, prreg) in spec.items():
            e = a[method]
            for label, frozen, printed, fmt in (
                ("MW dTop1", e["modal_top1_median_advantage"], t1, ".3f"),
                ("MW dregret", e["modal_regret_median_advantage"], rg, ".6f"),
                ("RW dtau_b", e["random_kendall_median_advantage"], tau, ".3f"),
                ("RW dregret", e["random_regret_median_advantage"], rreg, ".6f"),
            ):
                rounded = format(frozen, fmt)
                # normalise "-0.000" to "0.000"
                if float(rounded) == 0:
                    rounded = format(0.0, fmt)
                chk = self.add(
                    f"{method} {label}", src, frozen, f"${rounded}$", ("main",)
                )
                if rounded != printed:
                    chk.ok = False
                    chk.detail = (
                        f"frozen rounds to {rounded}, table spec expects {printed}"
                    )
            for label, frozen, expect in (
                ("MW dTop1 P", e["modal_top1_positive_seed_count"], pt1),
                ("MW dregret P", e["modal_regret_positive_seed_count"], prg),
                ("RW dtau_b P", e["random_kendall_positive_seed_count"], ptau),
                ("RW dregret P", e["random_regret_positive_seed_count"], prreg),
            ):
                chk = self.add(f"{method} {label}", src, frozen)
                if frozen != expect:
                    chk.ok = False
                    chk.detail = f"frozen {frozen} != manuscript {expect}"
                else:
                    chk.detail = f"positive-world count {frozen}"
            # Eligibility / separation verdicts.
            for label, frozen in (
                ("eligible", e["eligible"]),
                ("separates_random", e["separates_random"]),
                ("escapes_majority_winner", e["escapes_majority_winner"]),
            ):
                self.add(f"{method} {label}", src, frozen)

        # No method escaped MajorityWinner; exactly four separated from RandomWeights.
        escaped = sum(1 for e in a.values() if e["escapes_majority_winner"])
        separated = sum(1 for e in a.values() if e["separates_random"])
        eligible = sum(1 for e in a.values() if e["eligible"])
        for name, frozen, expect, literal in (
            ("methods escaping MajorityWinner", escaped, 0,
             "Zero of six methods escaped MajorityWinner"),
            ("methods separating from RandomWeights", separated, 4,
             "Four of six methods separated from RandomWeights"),
            ("eligible structured methods", eligible, 6,
             "Six structured methods eligible without fallback"),
        ):
            chk = self.add(name, src, frozen, literal, ("main",))
            if frozen != expect:
                chk.ok = False
                chk.detail = f"frozen count {frozen} != narrative {expect}"

    def pilot_b_gate(self):
        d = fz.load_json(fz.PILOT_B)
        hse = d["hard_stop_evaluation"]
        src = "results/pilot_b_reference_v1/...json :: hard_stop_evaluation"
        gates = hse["gates"]
        expected_gates = {
            "coverage_hard_stop": False,
            "random_equivalence_hard_stop": False,
            "modal_winner_effective_tie_hard_stop": True,
            "oracle_winner_dominance_hard_stop": False,
            "weight_insensitivity_hard_stop": False,
        }
        for key, expect in expected_gates.items():
            chk = self.add(f"gate {key}", src, gates[key])
            if gates[key] != expect:
                chk.ok = False
                chk.detail = f"frozen {gates[key]} != manuscript {expect}"
            else:
                chk.detail = f"flag is {gates[key]}"
        fired = [k for k, v in gates.items() if v]
        chk = self.add("exactly one stop fired", src, fired)
        if fired != ["modal_winner_effective_tie_hard_stop"]:
            chk.ok = False
            chk.detail = f"fired flags: {fired}"

        for name, frozen, expect in (
            ("hard_stop", hse["hard_stop"], True),
            ("pilot_b_pass", hse["pilot_b_pass"], False),
            ("coverage_complete", hse["coverage_complete"], True),
            ("primary_or_reserve_seed_used", d["primary_or_reserve_seed_used"], False),
            ("thresholds_changed_after_inspection",
             d["thresholds_changed_after_inspection"], False),
            ("topsis_used_for_hard_stop", d["topsis_used_for_hard_stop"], False),
        ):
            chk = self.add(name, src, frozen)
            if frozen != expect:
                chk.ok = False
                chk.detail = f"frozen {frozen} != expected {expect}"

        ows = hse["oracle_winner_summary"]
        self.num("pooled oracle modal share", src, ows["pooled_modal_winner_share"],
                 ".3f", ("main",), prefix="$", suffix="$")
        self.add("pooled modal winner id", src, ows["pooled_modal_winner_id"],
                 "$A_2$ in $526$ of $1000$ TEST contexts", ("main",))
        chk = self.add("pooled modal winner count", src, ows["pooled_modal_winner_count"])
        if ows["pooled_modal_winner_count"] != 526 or ows["pooled_contexts"] != 1000:
            chk.ok = False
            chk.detail = f"{ows['pooled_modal_winner_count']}/{ows['pooled_contexts']}"

        ris = hse["random_context_invariance_summary"]
        self.num("random invariant fraction", src, ris["pooled_invariant_fraction"],
                 ".3f", ("main",), prefix="Invariant fraction $", suffix="<0.90$")
        chk = self.add("performance width qualified worlds", src,
                       ris["performance_width_seed_count"],
                       "qualified worlds $0<4$", ("main",))
        if ris["performance_width_seed_count"] != 0:
            chk.ok = False
            chk.detail = f"frozen {ris['performance_width_seed_count']} != 0"

    def pilot_b_condition(self):
        d = fz.load_json(fz.PILOT_B)
        cond = d["condition"]
        src = "results/pilot_b_reference_v1/...json :: condition"
        chk = self.add("reference condition", src, cond,
                       "(250,0.30,0.4,0.5)", ("main", "supp"))
        if (cond["N"], cond["c"], cond["rho"], cond["lambda"]) != (250, 0.30, 0.4, 0.5):
            chk.ok = False
            chk.detail = f"frozen condition {cond}"
        chk = self.add("development worlds", src, d["development_seeds"],
                       "21001--21005", ("main", "supp"))
        if d["development_seeds"] != fz.WORLDS:
            chk.ok = False
            chk.detail = f"frozen worlds {d['development_seeds']}"

    def d29_geometry(self):
        rows = {int(r["replication_seed"]): r for r in fz.load_csv(fz.D29_LAYER_B_CSV)}
        src = "results/d29_layer_b_characterization_v1/seed_metrics.csv"
        shares = [float(r["modal_oracle_winner_share"]) for r in rows.values()]
        orders = [int(r["distinct_complete_oracle_orderings"]) for r in rows.values()]
        winners = [int(r["distinct_deterministic_oracle_winners"]) for r in rows.values()]
        srt = sorted(shares)
        self.num("min modal share", src, min(shares), ".3f", ("main",),
                 prefix="$", suffix="$")
        self.num("max modal share", src, max(shares), ".3f", ("main",),
                 prefix="$", suffix="$")
        self.num("median modal share", src, srt[len(srt) // 2], ".3f", ("main",),
                 prefix="$", suffix="$")
        self.add("min distinct orderings", src, min(orders), "$17$", ("main",))
        self.add("max distinct orderings", src, max(orders), "$78$", ("main",))
        chk = self.add("distinct winners range", src, (min(winners), max(winners)),
                       "between two and five", ("main",))
        if (min(winners), max(winners)) != (2, 5):
            chk.ok = False
            chk.detail = f"frozen range {(min(winners), max(winners))}"
        chk = self.add("worlds with modal share > 0.80", src,
                       sum(1 for s in shares if s > 0.80),
                       "In three of five worlds a single alternative was already", ("main",))
        if sum(1 for s in shares if s > 0.80) != 3:
            chk.ok = False
            chk.detail = f"frozen count {sum(1 for s in shares if s > 0.80)}"
        # World 21001, the directly comparable case.
        self.add("21001 D29 orderings", src,
                 int(rows[21001]["distinct_complete_oracle_orderings"]),
                 "from $19$ to $23$", ("main",))
        self.num("21001 D29 modal share", src,
                 float(rows[21001]["modal_oracle_winner_share"]), ".3f", ("main",),
                 prefix="$", suffix="$")
        # Supplement table transcribes every world.
        for world, row in rows.items():
            self.add(f"{world} orderings", src,
                     int(row["distinct_complete_oracle_orderings"]))
            self.num(f"{world} mean regret", src,
                     float(row["modal_baseline_mean_normalized_oracle_regret"]),
                     ".8f", ("supp",))

    def historical_collapse(self):
        text = fz.read_text(fz.DOC_NUMERICAL_NULL)
        src = "docs/v2_2_d2_8_numerical_null_results.md (frozen record)"
        lrv = float(re.search(r"max historical LRV = ([0-9.e+-]+)", text).group(1))
        nsv = float(re.search(r"max historical vector NSV = ([0-9.e+-]+)", text).group(1))
        chk = self.add("historical max LRV", src, lrv,
                       "$7.2224\\times10^{-16}$", ("main",))
        if f"{lrv:.4e}" != "7.2224e-16":
            chk.ok = False
            chk.detail = f"frozen {lrv!r} does not round to 7.2224e-16"
        chk = self.add("historical max vector NSV", src, nsv,
                       "$1.8036\\times10^{-9}$", ("main",))
        if f"{nsv:.4e}" != "1.8036e-09":
            chk.ok = False
            chk.detail = f"frozen {nsv!r} does not round to 1.8036e-9"
        self.add("world-criterion combinations", "5 worlds x 7 active criteria", 35,
                 "$35$ world--criterion combinations", ("main",))

        hist = fz.read_text(fz.DOC_V21_AUDIT)
        src21 = "docs/v2_1_structural_audit.md (frozen record)"
        chk = self.add("21001 historical orderings", src21, 19, "$19$ to $23$", ("main",))
        if "distinct oracle orderings: `19`" not in hist:
            chk.ok = False
            chk.detail = "frozen record does not state 19 orderings"
        chk = self.add("21001 historical modal share", src21, 0.962,
                       "$0.962$ to $0.983$", ("main",))
        if "modal share: `0.962`" not in hist:
            chk.ok = False
            chk.detail = "frozen record does not state modal share 0.962"

    def selection_maps(self):
        d = fz.load_json(fz.SELECTION_MAP)
        s = fz.selection_summaries()
        src = "results/pilot_b_fixed_weight_selection_diagnostic_v1/...json"
        chk = self.add("audited selection records", src, len(d["context_records"]),
                       "$5\\times7\\times200=7000$", ("main", "supp"))
        if len(d["context_records"]) != 7000:
            chk.ok = False
            chk.detail = f"frozen {len(d['context_records'])} records"

        expected_const = {
            "OracleAttribution": 1, "SHAP": 2, "PermutationImportance": 0,
            "RidgePlus": 1, "CRITIC": 2, "Entropy": 3, "Equal": 5,
        }
        expected_mw = {
            "OracleAttribution": 1, "SHAP": 2, "PermutationImportance": 0,
            "RidgePlus": 1, "CRITIC": 1, "Entropy": 2, "Equal": 4,
        }
        for method in expected_const:
            const = sum(
                1 for w in fz.WORLDS
                if s[(w, method)]["selection_constant_across_200_contexts"]
            )
            mw = sum(
                1 for w in fz.WORLDS
                if s[(w, method)]["agreement_with_majority_winner_all_200_contexts"]
            )
            for label, frozen, expect in (
                ("constant-selection worlds", const, expected_const[method]),
                ("all-context MW-match worlds", mw, expected_mw[method]),
            ):
                chk = self.add(f"{method} {label}", src, frozen,
                               f"{expect}/5", ("main",) if method else ())
                if frozen != expect:
                    chk.ok = False
                    chk.detail = f"frozen {frozen} != manuscript {expect}"

        # World 21003: identical Top-1 and regret, different tau_b.
        for method, tau in (("Equal", "0.5493"), ("CRITIC", "0.5427"),
                            ("Entropy", "0.5113")):
            row = s[(21003, method)]
            chk = self.add(f"21003 {method} Top-1", src, row["top1_accuracy"],
                           "$0.190$", ("main",))
            if f"{row['top1_accuracy']:.3f}" != "0.190":
                chk.ok = False
                chk.detail = f"frozen {row['top1_accuracy']}"
            chk = self.add(f"21003 {method} mean regret", src,
                           row["mean_normalized_oracle_regret"], "$0.316758$", ("main",))
            if f"{row['mean_normalized_oracle_regret']:.6f}" != "0.316758":
                chk.ok = False
                chk.detail = f"frozen {row['mean_normalized_oracle_regret']}"
            chk = self.add(f"21003 {method} mean tau_b", src,
                           row["mean_kendall_tau_b"], f"${tau}$", ("main",))
            if f"{row['mean_kendall_tau_b']:.4f}" != tau:
                chk.ok = False
                chk.detail = f"frozen {row['mean_kendall_tau_b']}"
            chk = self.add(f"21003 {method} selects A6 in all contexts", src,
                           row["modal_selected_alternative_id"])
            if (row["modal_selected_alternative_id"] != "A6"
                    or row["number_of_unique_selected_alternatives"] != 1):
                chk.ok = False
                chk.detail = f"frozen {row['modal_selected_alternative_id']}"

        # Post-closure firewall attestations.
        for key, expect in (
            ("model_fit_or_prediction_executed", False),
            ("weight_reestimation_executed", False),
            ("shap_or_pi_executed", False),
            ("random_weights_executed", False),
            ("paired_context_bootstrap_executed", False),
            ("primary_or_reserve_seed_used", False),
            ("primary_factorial_authorized", False),
            ("closed_pilot_b_decision_or_thresholds_changed", False),
        ):
            chk = self.add(f"post-closure {key}", src, d[key])
            if d[key] != expect:
                chk.ok = False
                chk.detail = f"frozen {d[key]} != required {expect}"
        chk = self.add("post-closure descriptive_only", src,
                       d["interpretation"]["descriptive_only"])
        if not d["interpretation"]["descriptive_only"]:
            chk.ok = False
            chk.detail = "frozen artefact does not declare descriptive_only"

    def supplement_numbers(self):
        # B100 matched-background diagnostic.
        b = fz.load_json(fz.ORACLE_B100)["diagnostic"]
        src = "results/oracle_b100_background_diagnostic_reference_v1/...json"
        vm = b["vector_metrics"]
        self.num("B100 MAE_w", src, vm["MAE_w"], ".10f", ("supp",))
        self.num("B100 TV_w", src, vm["TV_w"], ".10f", ("supp",))
        self.num("B100 max |dw|", src, vm["max_absolute_weight_difference"], ".10f",
                 ("supp",))
        self.num("B100 Spearman", src, vm["Spearman_rho_w"], ".8f", ("supp",))
        mm = b["moment_metrics"]
        self.num("B100 max marginal moment diff", src,
                 mm["max_absolute_marginal_moment_difference"], ".10f", ("supp",))
        self.num("B100 max joint moment diff", src,
                 mm["max_absolute_joint_moment_difference"], ".10f", ("supp",))
        dg = b["diagnostics"]
        self.num("B100 full-FIT total importance", src, dg["full_fit_total_importance"],
                 ".11f", ("supp",))
        self.num("B100 B100 total importance", src, dg["b100_total_importance"], ".11f",
                 ("supp",))
        for feat, full, b100, diff in (
            ("C1", "0.09663438", "0.09712037", "0.00048600"),
            ("C5", "0.14880967", "0.14667297", "0.00213669"),
            ("C8", "0.24766693", "0.25232065", "0.00465372"),
            ("C10", "0.11459290", "0.11141932", "0.00317357"),
        ):
            key = f"g_{feat}"
            ff = b["full_fit_oracle"]["weights_by_feature"][key]
            bb = b["b100_oracle"]["weights_by_feature"][key]
            for label, frozen, printed in (("full-FIT", ff, full), ("B100", bb, b100),
                                           ("absdiff", abs(ff - bb), diff)):
                chk = self.add(f"B100 {feat} {label}", src, frozen, printed, ("supp",))
                if f"{frozen:.8f}" != printed:
                    chk.ok = False
                    chk.detail = f"frozen {frozen:.8f} != printed {printed}"

        # XGBoost calibration freeze.
        x = fz.load_json(fz.XGB_SELECTED)
        srcx = "results/xgboost_development_calibration_v1/selected_parameters.json"
        self.add("XGBoost candidate id", srcx, x["selected_candidate_id"],
                 "Candidate 45", ("supp",))
        self.add("XGBoost grouped-CV RMSE", srcx, x["mean_grouped_cv_rmse"],
                 str(x["mean_grouped_cv_rmse"]), ("supp",))
        p = x["selected_parameters"]
        for key, printed in (("n_estimators", "600"), ("max_depth", "2"),
                             ("learning_rate", "0.05"), ("subsample", "0.8"),
                             ("colsample_bytree", "0.8"), ("min_child_weight", "5")):
            chk = self.add(f"XGBoost {key}", srcx, p[key])
            if str(p[key]).rstrip("0").rstrip(".") != printed.rstrip("0").rstrip("."):
                chk.ok = False
                chk.detail = f"frozen {p[key]} != printed {printed}"

        # Development TreeSHAP reference.
        ts = fz.load_json(fz.TREESHAP_DEV)["treeshap"]
        srct = "results/treeshap_reference_development_v1/...json"
        self.add("TreeSHAP total importance", srct,
                 ts["diagnostics"]["total_importance"],
                 str(ts["diagnostics"]["total_importance"]), ("supp",))
        chk = self.add("TreeSHAP local-accuracy max error", srct,
                       ts["diagnostics"]["local_accuracy_max_absolute_error"],
                       "$6.45\\times10^{-7}$", ("supp",))
        if f"{ts['diagnostics']['local_accuracy_max_absolute_error']:.2e}" != "6.45e-07":
            chk.ok = False
            chk.detail = "does not round to 6.45e-7"
        for feat, printed in (("C1", "0.124860"), ("C2", "0.113194"), ("C3", "0.069426"),
                              ("C4", "0.025945"), ("C5", "0.155169"), ("C6", "0.078339"),
                              ("C7", "0.071621"), ("C8", "0.265059"), ("C9", "0.020729"),
                              ("C10", "0.075658")):
            w = ts["weights_by_feature"][f"g_{feat}"]
            chk = self.add(f"dev SHAP weight {feat}", srct, w, printed, ("supp",))
            if f"{w:.6f}" != printed:
                chk.ok = False
                chk.detail = f"frozen {w:.6f} != printed {printed}"

        # Frozen CRITIC / Entropy vectors for world 21001.
        md = fz.load_json(fz.PILOT_B)["seed_results"][0]["method_details"]
        srcw = "results/pilot_b_reference_v1/...json :: seed_results[21001].method_details"
        order = [f"g_C{i}" for i in range(1, 11)]
        for method, printed in (
            ("CRITIC", ".079 & .075 & .101 & .093 & .150 & .099 & .097 & .111 & .084 & .111"),
            ("Entropy", ".131 & .114 & .175 & .099 & .236 & .064 & .084 & .027 & .032 & .038"),
        ):
            w = md[method]["weights_by_feature"]
            rendered = " & ".join(f"{w[k]:.3f}".lstrip("0") for k in order)
            chk = self.add(f"{method} 21001 vector", srcw, rendered, printed, ("supp",))
            if rendered != printed:
                chk.ok = False
                chk.detail = f"frozen renders as {rendered}"
            argmax = max(order, key=lambda k: w[k])
            chk = self.add(f"{method} 21001 argmax not C8/C10", srcw, argmax)
            if argmax in ("g_C8", "g_C10"):
                chk.ok = False
                chk.detail = f"argmax is {argmax}; the 'not C8/C10' claim fails"

        # Per-world Oracle and SHAP advantages over MajorityWinner.
        a = fz.pilot_b_assessments()
        srcp = "results/pilot_b_reference_v1/...json :: per-world advantages"
        for method, key, fmt, printed in (
            ("OracleAttribution", "modal_top1_advantages_by_seed", ".3f",
             ["0.000", "0.035", "-0.465", "-0.010", "-0.380"]),
            ("SHAP", "modal_top1_advantages_by_seed", ".3f",
             ["0.000", "0.030", "0.020", "0.000", "-0.035"]),
            ("OracleAttribution", "modal_regret_advantages_by_seed", ".6f",
             ["0.000000", "0.001538", "-0.143522", "-0.002119", "-0.090328"]),
            ("SHAP", "modal_regret_advantages_by_seed", ".6f",
             ["0.000000", "0.003064", "0.006717", "0.000000", "-0.002986"]),
        ):
            vals = a[method][key]
            for world, want in zip(fz.WORLDS, printed):
                got = format(vals[str(world)], fmt)
                if float(got) == 0:
                    got = format(0.0, fmt)
                chk = self.add(f"{method} {key} {world}", srcp, vals[str(world)],
                               f"${got}$", ("supp",))
                if got != want:
                    chk.ok = False
                    chk.detail = f"frozen rounds to {got}, supplement expects {want}"

        # D3 superpopulation dispersion.
        d3 = fz.load_json(fz.D3_FREEZE)
        srcd = "results/d3_alpha_dispersion_execution_v1/freeze_summary.json"
        for feat, printed in (("C8", "0.122873493"), ("C10", "0.119403289"),
                              ("C5", "0.110114266"), ("C2", "0.094820283"),
                              ("C3", "0.090482741"), ("C4", "0.088452971"),
                              ("C1", "0.087135074"), ("C7", "0.078706704"),
                              ("C6", "0.049591336"), ("C9", "0.028266887")):
            v = d3["mean_q_mad_W200"][feat]
            chk = self.add(f"D3 dispersion {feat}", srcd, v, printed, ("supp",))
            if f"{v:.9f}" != printed:
                chk.ok = False
                chk.detail = f"frozen {v:.9f} != printed {printed}"
        chk = self.add("D3 descending order", srcd, d3["final_order_descending_q_mad"],
                       "C_8>C_{10}>C_5>C_2>C_3>C_4>C_1>C_7>C_6>C_9", ("supp",))
        if d3["final_order_descending_q_mad"] != ["C8", "C10", "C5", "C2", "C3", "C4",
                                                  "C1", "C7", "C6", "C9"]:
            chk.ok = False
            chk.detail = f"frozen order {d3['final_order_descending_q_mad']}"

        # Numerical-null thresholds.
        nn = fz.read_text(fz.DOC_NUMERICAL_NULL)
        srcn = "docs/v2_2_d2_8_numerical_null_results.md (frozen record)"
        nsv = float(
            re.search(r"T\^\{num\}_\{NSV,vector\}\s*=\s*([0-9.]+)\\times\s*10\^\{-8\}", nn)
            .group(1)
        ) * 1e-8
        chk = self.add("numerical null NSV threshold", srcn, nsv,
                       "3.2506084454\\times10^{-8}", ("supp",))
        if f"{nsv:.10e}"[:12] != "3.2506084454"[:12]:
            chk.ok = False
            chk.detail = f"frozen {nsv}"

        # D2.7 scientific references.
        d27 = fz.read_text(fz.DOC_D27)
        srcr = "docs/v2_2_d2_7_calibration_results.md (frozen record)"
        for crit, lrv, nsvv in (("C1", "0.185606", "0.101685"), ("C2", "0.107107", "0.069436"),
                                ("C3", "0.163029", "0.064900"), ("C4", "0.115796", "0.069423"),
                                ("C5", "0.127964", "0.073681"), ("C6", "0.194899", "0.129935"),
                                ("C7", "0.144080", "0.073092")):
            m = re.search(rf"\|\s*{crit}\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|", d27)
            fl, fn = float(m.group(1)), float(m.group(2))
            for label, frozen, printed in (("LRV", fl, lrv), ("NSV", fn, nsvv)):
                chk = self.add(f"D2.7 {crit} {label}", srcr, frozen, printed, ("supp",))
                if f"{frozen:.6f}" != printed:
                    chk.ok = False
                    chk.detail = f"frozen {frozen:.6f} != printed {printed}"

    def eligible_universe(self):
        r = fz.load_json(fz.RETENTION_AUDIT)
        src = "results/production_generator_retention_resolution_v1/audit_summary.json"
        ev = r["eligible_universe_evidence"]
        total = r["eligible_universe_count"]
        verified = ev["historical_readjudication_verified_eligible_count"]
        v22 = ev["supplemental_v22_verified_count"]
        chk = self.add("eligible universe 54 = 44 + 10", src,
                       (total, verified, v22), "$44+10=54$", ("supp",))
        if (total, verified, v22) != (54, 44, 10) or verified + v22 != total:
            chk.ok = False
            chk.detail = (
                f"frozen total={total}, verified={verified}, v22={v22}; "
                "the 54-candidate claim is not supported as stated"
            )
        self.add("54 corrected-eligible candidates in main", src, total,
                 "$54$ corrected-eligible candidates", ("main",))
        for key, expect in (
            ("corrected_eligibility_nonunique", True),
            ("ranking_or_reoptimization_performed", False),
            ("SHAP_used_for_selection", False),
            ("MCDM_used_for_selection", False),
            ("D29_LRV_NSV_SRE_used_for_selection", False),
            ("primary_11001_11030_used", False),
            ("reserve_30001_30005_used", False),
        ):
            chk = self.add(f"retention {key}", src, r[key])
            if r[key] != expect:
                chk.ok = False
                chk.detail = f"frozen {r[key]} != required {expect}"

    def digests(self):
        src = "recomputed SHA-256 of the frozen artefacts"
        for label, path in (
            ("Oracle B100 result", fz.ORACLE_B100),
            ("Pilot-B result", fz.PILOT_B),
            ("Fixed-weight selection-map result", fz.SELECTION_MAP),
        ):
            trunc = fz.truncated_digest(path)
            self.add(f"digest {label}", src, trunc, f"\\texttt{{{trunc}}}", ("supp",))
        # The TreeSHAP background-identity digest is stored inside the artefact.
        bg = fz.load_json(fz.TREESHAP_DEV)["treeshap"]["diagnostics"][
            "background_identity_sha256"
        ]
        trunc = f"{bg[:8]}...{bg[-8:]}"
        self.add("digest TreeSHAP background identities",
                 "frozen field background_identity_sha256", trunc,
                 f"\\texttt{{{trunc}}}", ("supp",))
        # The post-closure layer records the Pilot-B digest it was built against.
        sel = fz.load_json(fz.SELECTION_MAP)
        chk = self.add("post-closure references the frozen Pilot-B digest",
                       "selection diagnostic :: frozen_pilot_b_result_sha256",
                       sel["frozen_pilot_b_result_sha256"])
        if sel["frozen_pilot_b_result_sha256"] != fz.sha256_of(fz.PILOT_B):
            chk.ok = False
            chk.detail = "post-closure layer does not match the Pilot-B artefact on disk"

    def run(self):
        self.pilot_b_condition()
        self.pilot_b_contrasts()
        self.pilot_b_gate()
        self.d29_geometry()
        self.historical_collapse()
        self.selection_maps()
        self.supplement_numbers()
        self.eligible_universe()
        self.digests()
        return self.checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None,
                    help="write a machine-readable report (under outputs/ only)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    v = Verifier()
    checks = v.run()
    failed = [c for c in checks if not c.ok]

    print(f"verify_frozen_manuscript_numbers: {len(checks)} claims checked")
    if args.verbose:
        for c in checks:
            print(f"  [{'ok' if c.ok else 'FAIL'}] {c.name}: {c.detail}")
    if failed:
        print(f"\n{len(failed)} FAILING CLAIM(S) -- report these, do not adjust them:\n")
        for c in failed:
            print(f"  FAIL  {c.name}")
            print(f"        source : {c.source}")
            print(f"        frozen : {c.frozen!r}")
            print(f"        detail : {c.detail}")
    else:
        print("PASS: every checked manuscript number traces to a frozen artefact.")

    if args.json:
        payload = {
            "checks_total": len(checks),
            "checks_failed": len(failed),
            "status": "FAIL" if failed else "PASS",
            "checks": [
                {"name": c.name, "source": c.source, "frozen": repr(c.frozen),
                 "literal": c.literal, "where": list(c.where), "ok": c.ok,
                 "detail": c.detail}
                for c in checks
            ],
        }
        with fz.open_output(args.json) as handle:
            json.dump(payload, handle, indent=1)
        print(f"report written to {args.json}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
