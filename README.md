# Context-Dependent Selection Among Established Urban Routing Policies

The complete study is in **`study/`**: scenario, policy implementations,
simulation campaigns, analysis, figures, manuscript and audit.

Start with `study/README.md` for the layout and exact reproduction steps.

| | |
|---|---|
| **Submission package** | `IC_TORS26_FINAL.zip` — `main.tex`, `references.bib`, `figures/`, `TORS_COMPLIANCE.md` |
| Compliance / unresolved dependencies | `study/final/TORS_COMPLIANCE.md` |
| Manuscript | `study/final/main.pdf` (LNCS, 27 pp) · standalone source `study/final/main.tex` |
| Changelog | `study/CHANGELOG.md` |
| Frozen specification | `study/spec/FROZEN_SPEC.md` — committed before any evaluation run |
| Screening result and protocol deviation | `study/results/SCREENING_REPORT.md` |
| Every reported number | `study/results/results.json` |
| Scientific audit | `study/audit/SCIENTIFIC_AUDIT.md` |
| Contribution map | `study/audit/CONTRIBUTION_MAP.md` |
| Reviewer attack list | `study/audit/REVIEWER_ATTACK_LIST.md` |
| Literature audit | `study/audit/LITERATURE_AUDIT.md` |
| Quality-control gate | `study/audit/qc_gate.py` — 17 automated checks |

## Scale

18,124 SUMO runs: 384 scenario-validation, 640 screening, 12,960 main
factorial, 1,920 sensitivity, 1,080 domain-shift, 1,140 boundary-localisation.
Zero failed runs and zero teleports in the analysed campaigns.

## Other directories

`routing_regime_study/` and `V2_REDESIGN/` hold earlier development material
retained for provenance. They are not inputs to the study in `study/`, which
builds its environment from scratch; `study/INVENTORY.md` records why their
measurements are not protocol-compatible and are cited nowhere.
