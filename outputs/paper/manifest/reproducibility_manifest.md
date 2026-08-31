# Reproducibility manifest

Generated 2026-08-29T02:57:13Z - anonymous review package.

## Study state

| Item | Value |
|---|---|
| `pilot_b` | executed once against a prospectively frozen gate; FAILED |
| `stop_that_fired` | modal_winner_effective_tie_hard_stop |
| `primary_factorial_authorized` | False |
| `primary_worlds_accessed` | False |
| `reserve_worlds_accessed` | False |
| `post_closure_layer` | descriptive, non-confirmatory; cannot reopen the gate |

## Key artefacts

| Artefact | Path | Truncated SHA-256 |
|---|---|---|
| Pilot-B confirmatory adequacy result | `results/pilot_b_reference_v1/pilot_b_reference_N250_c0p30_rho0p4_lambda0p5.json` | `05072857...9f787a88` |
| Post-closure descriptive selection-map result | `results/pilot_b_fixed_weight_selection_diagnostic_v1/pilot_b_fixed_weight_selection_N250_c0p30_rho0p4_lambda0p5.json` | `a1f293b6...d7e20f4e` |
| D29 decision-geometry characterization | `results/d29_layer_b_characterization_v1/seed_metrics.csv` | `a26ca942...d7b8c9c8` |
| Oracle B100 matched-background diagnostic | `results/oracle_b100_background_diagnostic_reference_v1/seed21001_N250_rho0p4_lambda0p5.json` | `7f9864bd...439c9fb0` |
| Development TreeSHAP reference | `results/treeshap_reference_development_v1/seed21001_N250_c0p30_rho0p4_lambda0p5.json` | `dee9fac2...3fbe4256` |
| XGBoost calibration freeze | `results/xgboost_development_calibration_v1/selected_parameters.json` | `b1f48e6e...8fb38e17` |
| Frozen Pilot-B hard-stop protocol | `config/pilot_b_hard_stop_protocol_v1.json` | `30630a80...0ca278a2` |
| Frozen post-closure diagnostic protocol | `config/pilot_b_fixed_weight_selection_diagnostic_v1.json` | `09056cb5...56bed913` |

## Contents

| Section | Root | Files |
|---|---|---|
| Synthetic benchmark generator and pipeline | `src` | 46 |
| Frozen configuration and protocol files | `config` | 23 |
| Frozen protocol and result records | `docs` | 45 |
| Frozen scientific result artefacts | `results` | 198 |
| Software test suite | `tests` | 84 |
| Manuscript sources | `paper` | 5 |
| Manuscript-support scripts (read-only) | `scripts/paper` | 8 |

Total files inventoried: **409**

## Deliberately not included

- Generated benchmark worlds: regenerated deterministically from the frozen seeds and configurations rather than stored.
- Primary (11001-11030) and reserve (30001-30005) worlds: never accessed; no artefact exists.
- Primary factorial results: the gate barred execution; none exist.

## Provenance

- Repository identifiers are withheld for anonymous review. The complete version-controlled provenance record accompanies the public package after review.

## Reproducing the reported tables, figure and checks

```bash
python scripts/paper/verify_frozen_manuscript_numbers.py
python scripts/paper/check_selection_map_consistency.py
python scripts/paper/build_pilot_b_tables.py
python scripts/paper/make_decision_value_figure.py
python scripts/paper/manuscript_consistency_audit.py
python scripts/paper/latex_preflight.py
```
