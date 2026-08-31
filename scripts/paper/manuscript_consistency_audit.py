#!/usr/bin/env python3
"""Audit the manuscripts for framing, labelling, terminology and LaTeX hygiene.

This is a guardrail against the ways this particular study can be misreported.
It checks that:

* RQ3 is not present -- the post-closure diagnostic must be DQ1, not a
  prospective research question;
* DQ1 always carries its post-closure / descriptive / non-confirmatory label;
* the required verbatim interpretation-boundary sentences are present;
* no forbidden universal or overclaiming phrasing appears
  ("SHAP failed", "materially outperformed", "proves", ...);
* no stale language from an unrelated traffic-control project survives
  (SUMO, QMIX, Max Pressure, trained-policy checkpoints, per-second logs, ...);
* the main and supplement titles agree;
* MajorityWinner is defined with all of its required properties and none of the
  forbidden ones;
* no primary or reserve world is described as having produced a result;
* every truncated digest printed in the supplement matches a recomputed digest;
* "world" is used as the statistical unit after the convention is stated;
* citations are all defined and all used, and labels are unique;
* the abstract is within the target length.

Read-only. Exits non-zero on any finding.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _frozen as fz  # noqa: E402

MAIN_TITLE = ("From Predictive Importance to Decision Value: Evaluating XAI-Based "
              "Weights for ITS Prioritisation")

#: Vocabulary belonging to a different project. None of it may appear.
STALE_TERMS = [
    "SUMO", "TraCI", "QMIX", "Max Pressure", "Max-Pressure", "MaxPressure",
    "route file", "route files", "trained-policy", "trained policy",
    "policy checkpoint", "checkpoint archive", "per-second", "traffic-signal controller",
    "signal controller", "controller implementation", "reinforcement learning",
    "CoCoSo", "Fuzzy CoCoSo", "rollout", "replay buffer",
]

#: Phrasings that overstate the closed negative result.
FORBIDDEN_PHRASES = [
    "SHAP failed", "SHAP fails", "SHAP does not work", "SHAP is useless",
    "materially outperformed", "materially outperform",
    "the benchmark contains no", "no discriminative information",
    "proves that", "proof that", "demonstrates conclusively",
    "first ever", "the first XAI--MCDM", "the first XAI-MCDM",
    "answer the three research questions", "three research questions",
    "RQ3",
    "MOORA is inadequate", "global weights never",
    "should be deployed", "we recommend deploying",
]

#: Sentences that must survive editing verbatim (whitespace-insensitive).
REQUIRED_MAIN = {
    "adequacy-failure boundary":
        "Pilot-B failure denotes failure of the prespecified adequacy requirement for "
        "the intended global-weight--\\MOORA{} comparison; it does not imply that the "
        "generator contains no discriminative decision information.",
    "freezing vs independence":
        "Prospective freezing prevents post-result modification of the gate, but it "
        "does not make the five reused development worlds independent validation data.",
    "RQ/DQ evidential split":
        "RQ1 and RQ2 are addressed by the prospectively structured "
        "benchmark-development and Pilot-B evidence. The separately frozen "
        "post-closure diagnostic addresses DQ1 descriptively and has no confirmatory "
        "role.",
    "adequacy summary":
        "Four structured methods, including SHAP, cleared the prospectively specified "
        "RandomWeights adequacy criterion, but no structured method cleared the "
        "prospectively specified MajorityWinner adequacy criterion.",
    "world convention":
        "Each replication seed defines one benchmark world",
    "MajorityWinner regret-arm limitation":
        "The regret arm uses the same prospectively frozen Top-1-derived constant "
        "reference rather than a separately optimized regret-minimizing constant "
        "policy. A future benchmark could prospectively define metric-matched "
        "constant references.",
    "closing sentence":
        "recovering structured importance is not enough; the recovered information "
        "must demonstrably change decisions in a useful way",
}

#: MajorityWinner must be described with each of these properties.
MW_REQUIRED = [
    "oracle-informed", "context-free", "estimated on WEIGHT", "evaluated on TEST",
    "Top-1 frequency",
]
#: ... and must be explicitly denied each of these.
MW_DENIED = ["not claimed to minimize regret", "operational transportation policy"]


class Audit:
    def __init__(self, main: Path, supp: Path) -> None:
        self.paths = {"main": main, "supp": supp}
        self.texts = {k: fz.read_text(v) for k, v in self.paths.items() if v.exists()}
        self.findings: list[tuple[str, str, str]] = []
        self.notes: list[tuple[str, str, str]] = []
        self.passed = 0

    def squash(self, s: str) -> str:
        return re.sub(r"\s+", "", s)

    def fail(self, where: str, rule: str, detail: str) -> None:
        self.findings.append((where, rule, detail))

    def note(self, where: str, rule: str, detail: str) -> None:
        """Record a match that is present only inside an explicit denial.

        These are shown so the guardrail stays visible, but they do not fail the
        audit: "it does not show that global weights never matter" is the
        correct framing, not a violation.
        """
        self.notes.append((where, rule, detail))

    def ok(self) -> None:
        self.passed += 1

    def _lineno(self, label: str, needle: str) -> int:
        text = self.texts[label]
        idx = text.find(needle)
        return text[:idx].count("\n") + 1 if idx >= 0 else 0

    # -- rules ---------------------------------------------------------
    def rule_stale_language(self):
        for label, text in self.texts.items():
            body = re.sub(r"(?m)^\s*%.*$", "", text)  # ignore LaTeX comments
            for term in STALE_TERMS:
                for m in re.finditer(re.escape(term), body, flags=re.IGNORECASE):
                    line = body[:m.start()].count("\n") + 1
                    self.fail(label, "stale project language",
                              f"line ~{line}: found {term!r} (belongs to another project)")
            self.ok()

    #: Cues that turn a forbidden phrase into an explicit denial of that claim.
    NEGATION = re.compile(
        r"\b(?:not|never|no|neither|nor|without|rather than|does not|do not|"
        r"cannot|is not|are not|non-)\b", re.IGNORECASE)

    def rule_forbidden_phrases(self):
        for label, text in self.texts.items():
            body = re.sub(r"(?m)^\s*%.*$", "", text)
            for phrase in FORBIDDEN_PHRASES:
                for m in re.finditer(re.escape(phrase), body, flags=re.IGNORECASE):
                    line = body[:m.start()].count("\n") + 1
                    window = body[max(0, m.start() - 320):m.start()]
                    if self.NEGATION.search(window):
                        self.note(label, "forbidden phrasing (inside a denial)",
                                  f"line ~{line}: {phrase!r}")
                    else:
                        self.fail(label, "forbidden phrasing",
                                  f"line ~{line}: {phrase!r}")
            self.ok()

    def rule_required_sentences(self):
        main = self.squash(self.texts.get("main", ""))
        for name, sentence in REQUIRED_MAIN.items():
            if self.squash(sentence) not in main:
                self.fail("main", "missing required statement",
                          f"{name}: {sentence[:90]}...")
            else:
                self.ok()

    def rule_rq_dq_structure(self):
        main = self.texts.get("main", "")
        for token in ("RQ1", "RQ2", "DQ1"):
            if token not in main:
                self.fail("main", "RQ/DQ structure", f"{token} not declared")
            else:
                self.ok()
        # DQ1 must be labelled post-closure, descriptive and non-confirmatory.
        for label, text in self.texts.items():
            if "DQ1" not in text:
                continue
            low = text.lower()
            for token in ("post-closure", "descriptive", "non-confirmatory"):
                if token not in low:
                    self.fail(label, "DQ1 labelling",
                              f"DQ1 appears but {token!r} never does")
                else:
                    self.ok()
            # It must be denied any confirmatory role.
            if not re.search(r"(cannot|does not|has no)[^.]{0,120}"
                             r"(confirmatory|reopen|modify|reinterpret)", low):
                self.fail(label, "DQ1 labelling",
                          "no explicit statement that DQ1 cannot modify/reopen Pilot B")
            else:
                self.ok()

    def rule_titles_agree(self):
        main = self.texts.get("main", "")
        supp = self.texts.get("supp", "")
        if self.squash(MAIN_TITLE) not in self.squash(main):
            self.fail("main", "title", "main title is not the agreed final title")
        else:
            self.ok()
        if self.squash(MAIN_TITLE) not in self.squash(supp):
            self.fail("supp", "title",
                      "supplement does not carry the final main title")
        else:
            self.ok()
        for obsolete in ("Do Global XAI--MCDM Weights Add Decision Value",
                         "under Data Scarcity"):
            for label, text in self.texts.items():
                if self.squash(obsolete) in self.squash(re.sub(r"(?m)^\s*%.*$", "", text)):
                    self.fail(label, "title", f"obsolete title fragment {obsolete!r}")
                else:
                    self.ok()

    def rule_majority_winner(self):
        for label, text in self.texts.items():
            if "MajorityWinner" not in text:
                continue
            squashed = self.squash(text).lower()
            for prop in MW_REQUIRED:
                if self.squash(prop).lower() not in squashed:
                    self.fail(label, "MajorityWinner definition",
                              f"required property missing: {prop!r}")
                else:
                    self.ok()
            for denial in MW_DENIED:
                if self.squash(denial).lower() not in squashed:
                    self.fail(label, "MajorityWinner definition",
                              f"required denial missing: {denial!r}")
                else:
                    self.ok()

    def rule_no_primary_results(self):
        for label, text in self.texts.items():
            body = re.sub(r"(?m)^\s*%.*$", "", text)
            # Primary/reserve identifiers may only appear as never-accessed statements.
            # Bounded so a decimal such as 0.110114266 cannot masquerade as 11011.
            for m in re.finditer(
                    r"(?<![\d.])(1100[0-9]|110[12][0-9]|11030|3000[1-5])(?![\d.])", body):
                window = body[max(0, m.start() - 260):m.start() + 260].lower()
                if not re.search(r"never accessed|not accessed|were never|barred|"
                                 r"remained barred|firewall|not authorized|blocked",
                                 window):
                    line = body[:m.start()].count("\n") + 1
                    self.fail(label, "protected-world reference",
                              f"line ~{line}: {m.group(0)} without a never-accessed "
                              "qualifier nearby")
                else:
                    self.ok()
            for m in re.finditer(r"\bprimary (?:result|finding|outcome)s?\b", body, re.I):
                line = body[:m.start()].count("\n") + 1
                window = body[max(0, m.start() - 320):m.start()]
                if self.NEGATION.search(window):
                    self.note(label, "primary-result mention (inside a denial)",
                              f"line ~{line}: {m.group(0)!r}")
                else:
                    self.fail(label, "protected-world reference",
                              f"line ~{line}: refers to a 'primary result'; "
                              "none exists under v1")
            self.ok()

    def rule_digests(self):
        supp = self.texts.get("supp", "")
        allowed = {
            fz.truncated_digest(fz.ORACLE_B100),
            fz.truncated_digest(fz.PILOT_B),
            fz.truncated_digest(fz.SELECTION_MAP),
        }
        bg = fz.load_json(fz.TREESHAP_DEV)["treeshap"]["diagnostics"][
            "background_identity_sha256"]
        allowed.add(f"{bg[:8]}...{bg[-8:]}")
        printed = re.findall(r"\\texttt\{([0-9a-f]{4,}\.\.\.[0-9a-f]{4,})\}", supp)
        if not printed:
            self.fail("supp", "digest table", "no truncated digests found")
        for p in printed:
            if p not in allowed:
                near = [a for a in allowed if a.split("...")[0] == p.split("...")[0]]
                hint = f"; correct form is {near[0]}" if near else ""
                self.fail("supp", "digest truncation",
                          f"{p!r} does not match any recomputed artefact digest{hint}")
            else:
                self.ok()

    def rule_terminology(self):
        main = self.texts.get("main", "")
        if "Each replication seed defines one benchmark world" not in main:
            self.fail("main", "terminology", "world convention never stated")
            return
        self.ok()
        body = re.sub(r"(?m)^\s*%.*$", "", main)
        intro_end = body.find("Each replication seed defines one benchmark world")
        after = body[intro_end:]
        # After the convention, "seed" should only appear in protected-firewall or
        # artefact-field contexts, never as the statistical unit.
        # "seed" is legitimate when naming a protocol object (seed firewall,
        # seed namespace, replication seed), not when used as the statistical unit.
        allowed_after = re.compile(
            r"\s+(?:firewall|namespace|definition|identifier|stream|"
            r"specification|21001|11001|30001)", re.I)
        for m in re.finditer(r"\b(?:five|5|the)\s+seeds?\b", after, re.I):
            if allowed_after.match(after[m.end():]):
                continue
            line = body[:intro_end + m.start()].count("\n") + 1
            self.fail("main", "terminology",
                      f"line ~{line}: {m.group(0)!r} -- use 'world' as the unit")
        for m in re.finditer(r"\bper[- ]seed\b|\bcross-seed\b|\bseed-specific\b",
                             after, re.I):
            line = body[:intro_end + m.start()].count("\n") + 1
            self.fail("main", "terminology",
                      f"line ~{line}: {m.group(0)!r} -- use the 'world' form")
        self.ok()

    def rule_citations_and_labels(self):
        for label, text in self.texts.items():
            body = re.sub(r"(?m)^\s*%.*$", "", text)
            defined = set(re.findall(r"\\bibitem\{([^}]+)\}", body))
            used: set[str] = set()
            for m in re.finditer(r"\\cite[a-zA-Z]*\{([^}]+)\}", body):
                used.update(k.strip() for k in m.group(1).split(","))
            for key in sorted(used - defined):
                self.fail(label, "citation", f"cited but not defined: {key}")
            for key in sorted(defined - used):
                self.fail(label, "citation", f"defined but never cited: {key}")
            if defined or used:
                self.ok()

            labels = re.findall(r"\\label\{([^}]+)\}", body)
            dupes = {x for x in labels if labels.count(x) > 1}
            for dup in sorted(dupes):
                self.fail(label, "label", f"duplicate \\label{{{dup}}}")
            refs = set()
            for m in re.finditer(r"\\(?:ref|eqref|autoref)\{([^}]+)\}", body):
                refs.add(m.group(1))
            for r in sorted(refs - set(labels)):
                self.fail(label, "label", f"reference to undefined label: {r}")
            self.ok()

    def rule_macro_spacing(self):
        """Catch \\MACRO followed by a space, which LaTeX swallows."""
        for label, text in self.texts.items():
            body = re.sub(r"(?m)^\s*%.*$", "", text)
            macros = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", body))
            for macro in sorted(macros):
                for m in re.finditer(rf"\\{macro}(?![a-zA-Z{{\\])[ ]+(?=[A-Za-z])", body):
                    line = body[:m.start()].count("\n") + 1
                    self.fail(label, "macro spacing",
                              rf"line ~{line}: \{macro} followed by a bare space; "
                              rf"use \{macro}{{}} or \{macro}\\ ")
            self.ok()

    def rule_abstract_length(self):
        main = self.texts.get("main", "")
        m = re.search(r"\\begin\{abstract\}(.*?)\\keywords", main, re.S)
        if not m:
            self.fail("main", "abstract", "abstract not found")
            return
        a = re.sub(r"\$[^$]*\$", " x ", m.group(1))
        a = re.sub(r"\\[a-zA-Z]+\{?|\}", " ", a)
        words = [w for w in re.split(r"[^A-Za-z0-9'\-]+", a) if w]
        if not 180 <= len(words) <= 230:
            self.fail("main", "abstract",
                      f"{len(words)} words; target is roughly 190-215")
        else:
            self.ok()
        print(f"  abstract length: {len(words)} words")

    def rule_anonymity_switch(self):
        for label, text in self.texts.items():
            if "\\newif\\ifanon" not in text:
                self.fail(label, "build mode", "no \\ifanon build switch present")
                continue
            self.ok()
            if not re.search(r"\\anontrue", text):
                self.fail(label, "build mode", "anonymous mode is not the default")
            else:
                self.ok()

    def run(self):
        self.rule_stale_language()
        self.rule_forbidden_phrases()
        self.rule_required_sentences()
        self.rule_rq_dq_structure()
        self.rule_titles_agree()
        self.rule_majority_winner()
        self.rule_no_primary_results()
        self.rule_digests()
        self.rule_terminology()
        self.rule_citations_and_labels()
        self.rule_macro_spacing()
        self.rule_abstract_length()
        self.rule_anonymity_switch()
        return self.findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--main", type=Path, default=fz.MAIN_TEX)
    ap.add_argument("--supp", type=Path, default=fz.SUPP_TEX)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    audit = Audit(args.main, args.supp)
    print("manuscript_consistency_audit")
    findings = audit.run()

    print(f"  rule groups passed: {audit.passed}")
    if audit.notes:
        print(f"\n  {len(audit.notes)} noted (guarded phrase used inside an explicit "
              "denial; not a finding):")
        for where, rule, detail in audit.notes:
            print(f"    [{where}] {rule}: {detail}")
    if findings:
        print(f"\n{len(findings)} FINDING(S):\n")
        for where, rule, detail in findings:
            print(f"  [{where}] {rule}: {detail}")
    else:
        print("PASS: no framing, labelling, terminology or LaTeX-hygiene findings.")

    if args.json:
        with fz.open_output(args.json) as handle:
            json.dump({"status": "FAIL" if findings else "PASS",
                       "findings": [{"file": w, "rule": r, "detail": d}
                                    for w, r, d in findings],
                       "notes": [{"file": w, "rule": r, "detail": d}
                                 for w, r, d in audit.notes]}, handle, indent=1)
        print(f"report written to {args.json}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
