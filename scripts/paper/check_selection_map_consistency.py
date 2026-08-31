#!/usr/bin/env python3
"""Verify the 7000 archived post-closure context-level selections.

Independently re-derives, from the stored full-precision vectors alone:

* the selected alternative under the frozen tie semantics
  (absolute 1e-12 tolerance, smallest alternative ID wins);
* the oracle-selected alternative and the Top-1 match flag;
* the agreement flag against the frozen MajorityWinner identity;
* the per-(world, method) aggregates -- Top-1 accuracy, mean normalized oracle
  regret, modal selection, unique-selection count, constancy;
* the 105 pairwise selection-agreement summaries;

and compares each against what the frozen artefact stores. It also confirms that
the diagnostic's own aggregates reconcile with the Pilot-B result it was built
from, and that its firewall attestations still hold.

Scientific contract
-------------------
* Verification only. No bootstrap, no resampling, no confidence interval, no
  hypothesis test, and no metric that the post-closure protocol did not already
  prospectively define.
* Nothing is written to the frozen record. A disagreement is reported and the
  process exits non-zero; it is never repaired.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402

TIE_TOL = 1e-12
ALTS = [f"A{i}" for i in range(1, 7)]


def deterministic_top1(scores: list[float]) -> str:
    """Frozen Top-1 rule: tie set within 1e-12 of the max, smallest ID wins."""
    best = max(scores)
    tied = [ALTS[i] for i, s in enumerate(scores) if best - s <= TIE_TOL]
    return min(tied, key=lambda a: int(a[1:]))


def normalized_regret(oracle: list[float], chosen: str) -> float:
    """Frozen normalized oracle regret for the chosen alternative in one context."""
    idx = int(chosen[1:]) - 1
    hi, lo = max(oracle), min(oracle)
    return (hi - oracle[idx]) / (hi - lo + 1e-12)


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.counts: Counter = Counter()

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.counts["total"] += 1
        if ok:
            self.counts["passed"] += 1
        else:
            self.counts["failed"] += 1
            self.failures.append(f"{label}: {detail}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None,
                    help="write a machine-readable report (under outputs/ only)")
    args = ap.parse_args()

    d = fz.load_json(fz.SELECTION_MAP)
    rep = Report()
    records = d["context_records"]

    rep.check(len(records) == 7000, "record count",
              f"expected 5x7x200=7000, found {len(records)}")

    # ---- per-record re-derivation -----------------------------------
    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for r in records:
        grouped[(r["development_world"], r["method"])].append(r)

        sel = deterministic_top1(r["moora_scores_A1_to_A6"])
        rep.check(sel == r["selected_alternative_id"],
                  f"selection {r['development_world']}/{r['method']}/{r['test_context_id']}",
                  f"re-derived {sel}, stored {r['selected_alternative_id']}")

        osel = deterministic_top1(r["oracle_utilities_A1_to_A6"])
        rep.check(osel == r["oracle_selected_alternative_id"],
                  f"oracle selection {r['development_world']}/{r['test_context_id']}",
                  f"re-derived {osel}, stored {r['oracle_selected_alternative_id']}")

        rep.check((sel == osel) == r["top1_match"],
                  f"top1_match {r['development_world']}/{r['method']}/{r['test_context_id']}",
                  f"re-derived {sel == osel}, stored {r['top1_match']}")

        reg = normalized_regret(r["oracle_utilities_A1_to_A6"], sel)
        stored = r["normalized_oracle_regret_contribution"]
        rep.check(abs(reg - stored) <= 1e-12,
                  f"regret {r['development_world']}/{r['method']}/{r['test_context_id']}",
                  f"re-derived {reg!r}, stored {stored!r}")

        rep.check((sel == r["majority_winner_alternative_id"])
                  == r["agrees_with_majority_winner"],
                  f"MW agreement {r['development_world']}/{r['method']}/{r['test_context_id']}",
                  "flag disagrees with re-derived comparison")

    rep.check(len(grouped) == 35, "world x method cells", f"found {len(grouped)}")
    for key, rows in grouped.items():
        rep.check(len(rows) == 200, f"context count {key}", f"found {len(rows)}")

    # ---- per-(world, method) aggregates ------------------------------
    summaries = fz.selection_summaries()
    for key, rows in grouped.items():
        s = summaries[key]
        sels = [r["selected_alternative_id"] for r in rows]
        counts = Counter(sels)
        modal, modal_n = counts.most_common(1)[0]

        top1 = sum(1 for r in rows if r["top1_match"]) / len(rows)
        rep.check(abs(top1 - s["top1_accuracy"]) <= 1e-12, f"top1_accuracy {key}",
                  f"re-derived {top1!r}, stored {s['top1_accuracy']!r}")

        regret = sum(r["normalized_oracle_regret_contribution"] for r in rows) / len(rows)
        rep.check(abs(regret - s["mean_normalized_oracle_regret"]) <= 1e-12,
                  f"mean regret {key}",
                  f"re-derived {regret!r}, stored {s['mean_normalized_oracle_regret']!r}")

        rep.check(modal == s["modal_selected_alternative_id"], f"modal selection {key}",
                  f"re-derived {modal}, stored {s['modal_selected_alternative_id']}")
        rep.check(abs(modal_n / len(rows) - s["modal_selected_share"]) <= 1e-12,
                  f"modal share {key}", f"re-derived {modal_n / len(rows)!r}")
        rep.check(len(counts) == s["number_of_unique_selected_alternatives"],
                  f"unique selections {key}",
                  f"re-derived {len(counts)}, stored "
                  f"{s['number_of_unique_selected_alternatives']}")
        rep.check((len(counts) == 1) == s["selection_constant_across_200_contexts"],
                  f"constancy flag {key}", "flag disagrees with unique-selection count")

        agree = sum(1 for r in rows if r["agrees_with_majority_winner"]) / len(rows)
        rep.check(abs(agree - s["agreement_rate_with_majority_winner"]) <= 1e-12,
                  f"MW agreement rate {key}", f"re-derived {agree!r}")
        rep.check((agree == 1.0) == s["agreement_with_majority_winner_all_200_contexts"],
                  f"MW all-context flag {key}", "flag disagrees with agreement rate")

    # ---- 105 pairwise selection-agreement summaries ------------------
    pairs = d["pairwise_selection_agreement"]
    rep.check(len(pairs) == 105, "pairwise summaries", f"found {len(pairs)}")
    by_ctx = defaultdict(dict)
    for r in records:
        by_ctx[(r["development_world"], r["test_context_id"])][r["method"]] = \
            r["selected_alternative_id"]
    for p in pairs:
        w, ma, mb = p["development_world"], p["method_a"], p["method_b"]
        ctxs = [v for (ww, _), v in by_ctx.items() if ww == w]
        same = sum(1 for v in ctxs if v[ma] == v[mb])
        rate = same / len(ctxs)
        rep.check(abs(rate - p["selected_alternative_agreement_rate"]) <= 1e-12,
                  f"pairwise rate {w}/{ma}-{mb}",
                  f"re-derived {rate!r}, stored {p['selected_alternative_agreement_rate']!r}")
        rep.check((rate == 1.0) == p["selected_alternative_agreement_all_200_contexts"],
                  f"pairwise all-context flag {w}/{ma}-{mb}", "flag disagrees with rate")

    # ---- reconciliation with the frozen Pilot-B aggregates -----------
    val = d["aggregate_reconstruction_validations"]
    rep.check(len(val) == 35, "archived aggregate validations", f"found {len(val)}")
    for v in val:
        rep.check(v["all_archived_aggregates_match"],
                  f"archived aggregate match {v['development_world']}/{v['method']}",
                  json.dumps(v["checks"]))

    rep.check(d["frozen_pilot_b_result_sha256"] == fz.sha256_of(fz.PILOT_B),
              "Pilot-B digest referenced by the post-closure layer",
              "the diagnostic was built against a different Pilot-B artefact")

    # Cross-check the six structured methods against the Pilot-B artefact itself.
    pb = fz.load_json(fz.PILOT_B)
    for sr in pb["seed_results"]:
        w = sr["replication_seed"]
        for m in sr["structured_seed_metrics"]:
            name = m.get("method")
            if name not in fz.METHODS:
                continue
            s = summaries[(w, name)]
            for pk, sk in (("top1_accuracy", "top1_accuracy"),
                           ("mean_normalized_oracle_regret",
                            "mean_normalized_oracle_regret"),
                           ("mean_kendall_tau_b", "mean_kendall_tau_b")):
                if pk in m and m[pk] is not None:
                    rep.check(abs(m[pk] - s[sk]) <= 1e-12,
                              f"pilot-B vs post-closure {w}/{name}/{pk}",
                              f"pilot-B {m[pk]!r}, post-closure {s[sk]!r}")

    # ---- firewall attestations ---------------------------------------
    for key in ("model_fit_or_prediction_executed", "weight_reestimation_executed",
                "shap_or_pi_executed", "random_weights_executed",
                "paired_context_bootstrap_executed", "primary_or_reserve_seed_used",
                "primary_factorial_authorized",
                "closed_pilot_b_decision_or_thresholds_changed"):
        rep.check(d[key] is False, f"firewall {key}", f"artefact records {d[key]!r}")
    rep.check(d["interpretation"]["descriptive_only"] is True,
              "descriptive_only attestation", "artefact does not declare descriptive_only")

    # ---- output -------------------------------------------------------
    print(f"check_selection_map_consistency: {rep.counts['total']} checks, "
          f"{rep.counts['passed']} passed, {rep.counts['failed']} failed")
    if rep.failures:
        print(f"\n{len(rep.failures)} FAILING CHECK(S) -- report, do not repair:\n")
        for f in rep.failures[:60]:
            print(f"  FAIL  {f}")
        if len(rep.failures) > 60:
            print(f"  ... and {len(rep.failures) - 60} more")
    else:
        print("PASS: all 7000 selections, 35 aggregates and 105 pairwise summaries "
              "reconstruct exactly from the frozen vectors.")

    if args.json:
        with fz.open_output(args.json) as handle:
            json.dump({"total": rep.counts["total"], "passed": rep.counts["passed"],
                       "failed": rep.counts["failed"],
                       "status": "FAIL" if rep.failures else "PASS",
                       "failures": rep.failures}, handle, indent=1)
        print(f"report written to {args.json}")

    return 1 if rep.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
