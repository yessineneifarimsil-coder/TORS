# Regime-Dependent Routing-Policy Preference

Conference submission package. All results derive from the **432 completed SUMO runs**
of the existing development matrix. **No new simulation was executed in producing this
package**, and no earlier result was discarded.

## Paper
- `paper/main.tex` / `main.pdf` — manuscript (9 pp, A4, generic layout; no conference
  template was supplied, so format compliance is unverified)
- `paper/briefing.pdf` — one-page supervisor briefing
- `paper/Routing_Strategy_Selection_Regime.xlsx` — the original audited workbook with
  three added sheets (`REGIME_TRANSITION`, `DECISION_EVALUATION`, `NEGATIVE_CONTROLS`);
  all 22 original sheets are untouched

## Analysis — regenerates every number in the paper
```
python3 build_ds.py      # workbook -> runs.csv (432 runs)
python3 results.py       # -> results.json, the single source of truth
python3 transition.py    # regime structure, seed stability
python3 ml.py            # held-out selection
python3 robust.py        # hyperparameter / weight / seed / scaling robustness
python3 extrap.py        # demand-extrapolation stress test
python3 figs.py          # figures
```

## Headline results
| | |
|---|---|
| SP preferred | all 8 low-demand contexts |
| DTT preferred | all 8 high-demand contexts |
| Crossing bracket | (720, 1200] balanced · (1200, 1680] arterial |
| Available headroom vs best fixed | 0.03018 mean regret |
| Adaptive selector (leave-one-context-out) | 0.00606 — **79.9% captured**, optimal 21/24 |
| Out-of-regime extrapolation | 0.07649 vs 0.03018 — **worse than fixed** |

## Negative controls (retained, not hidden)
- ECO outcome-identical to SP in **21/24** contexts; observer route-order loss 21.62%,
  best route found in 3/8 probe panels → removed from the adaptive portfolio
- Preference weights leave **all 24** selector decisions unchanged across w_time 0→1
- Insertion-delay boundary changes the preferred policy in **0/24** contexts

## Not executed
`analysis/localize_transition.py` specifies the minimal experiment that would *localise*
the switching boundary (2 demand levels × existing cells = 144 runs, ~1.5 min). It was
**not run**: the SUMO network and configuration files were not available in this session,
and a reconstructed network would not be comparable with the 432 completed runs. The paper
reports brackets and makes no threshold estimate, so no claim depends on it.
