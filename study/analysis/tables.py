"""Emit the seven LaTeX tables.  Every number is read from results.json."""
import json, os, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K

R = json.load(open(os.path.join(HERE, "..", "results", "results.json")))
OUT = os.path.join(HERE, "..", "paper", "tables")
os.makedirs(OUT, exist_ok=True)


def w(name, body):
    open(os.path.join(OUT, name + ".tex"), "w").write(body)
    print("  wrote", name + ".tex")


def pc(x, d=1):
    return f"{100*x:.{d}f}\\%"


# ---------------------------------------------------------------- table 1
w("tab1_portfolio", r"""
\begin{table}[tbp]
\caption{The routing-policy portfolio. Every policy is an established family;
none is introduced here. The last column states a hypothesis fixed before the
experiment.}
\label{tab:portfolio}
\centering\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}l p{0.30\textwidth} p{0.26\textwidth} p{0.26\textwidth}@{}}
\toprule
& Objective and information & Intended strength & Hypothesised failure mode\\
\midrule
P1 & $\min_p L(p)$; no traffic state &
  no infrastructure, cannot oscillate &
  loads the shortest corridor past its capacity\\[3pt]
P2 & $\min_p \hat\mu_p(t-\Delta)$; lagged link travel times &
  follows congestion as it forms &
  moves the whole guided cohort on stale information\\[3pt]
P3 & $\min_{p\in\mathcal{A}} \max_{e\in p}\rho_e$; lagged times, flows and own
  assignments &
  spreads load when capacity is uneven &
  diverts to longer corridors with no capacity shortage\\[3pt]
P4 & $\min_p [\hat\mu_p + \lambda\hat\sigma_p]$; lagged link travel times &
  avoids corridors with volatile travel time &
  pays a detour for variance carrying no risk\\
\bottomrule
\end{tabular}

\medskip
\footnotesize $\mathcal{A}$: paths within a declared travel-time tolerance of
the best. $\rho_e$: link utilisation. $\Delta$: information lag. $\lambda$:
dispersion weight.
\end{table}
""".strip())

# ---------------------------------------------------------------- table 2
lv = R["campaign"]["factor_levels"]
w("tab2_factors", (r"""
\begin{table}[t]
\caption{Scenario factors and levels. Demand levels are expressed as a fraction
of the measured network capacity, which ranges from """ +
f"{min(R['campaign']['factor_levels']['demand'])/3832:.2f} to "
f"{max(R['campaign']['factor_levels']['demand'])/3832:.2f}" + r""" at the
median capacity configuration. Full factorial: """ +
f"{R['campaign']['n_contexts']}" + r""" contexts.}
\label{tab:factors}
\centering\footnotesize
\begin{tabular}{@{}l l l@{}}
\toprule
Factor & Levels & Mechanism activated\\
\midrule
Demand (veh/h) & """ + ", ".join(f"{int(x)}" for x in lv["demand"]) + r""" & capacity shortage\\
Green ratio $g/C$ & """ + ", ".join(f"{x:.2f}" for x in lv["gc"]) + r""" & signalised capacity\\
Penetration & """ + ", ".join(f"{x:.1f}" for x in lv["penetration"]) + r""" & cohort size; herding\\
Information lag $\Delta$ (s) & """ + ", ".join(f"{int(x)}" for x in lv["lag"]) + r""" & staleness; oscillation\\
Incident regime & none, arterial & travel-time risk\\
Alt.\ capacity & 1, 2 lanes & load to balance\\
\bottomrule
\end{tabular}
\end{table}
""").strip())

# ---------------------------------------------------------------- table 3
w("tab3_criteria", r"""
\begin{table}[t]
\caption{The three decision criteria. All are measured over the same cohort:
every vehicle in the network, guided or not, whose intended departure falls in
the measurement window.}
\label{tab:criteria}
\centering\footnotesize
\begin{tabularx}{\textwidth}{@{}l l X@{}}
\toprule
& Criterion & Measurement\\
\midrule
C1 & Mean journey time (s/veh) &
  mean over the cohort of insertion delay plus in-network time. Insertion delay
  is included: a policy that oversaturates the network produces vehicles that
  cannot enter it, and excluding their wait would credit the policy for the
  queue it caused.\\[2pt]
C2 & \CO{} emissions (kg) &
  total \CO{} over the cohort, HBEFA3 passenger-car petrol Euro-4 class.\\[2pt]
C3 & Total stopped delay (veh\,s) &
  total time spent below 0.1\,m/s --- the time vehicles spend \emph{stationary}
  in queues, as distinct from the time they spend travelling slowly.\\
\bottomrule
\end{tabularx}
\end{table}
""".strip())

# ---------------------------------------------------------------- table 4
cm = R["complementarity"]
n = cm["n_contexts"]
rows = []
for p in K.POLICIES:
    rows.append(f"{p} & {R['G1_confirmatory']['winner_counts_all'].get(p,0)} & "
                f"{R['G1_confirmatory']['winner_counts_resolved'].get(p,0)} & "
                f"{cm['pareto_membership'][p]} & "
                f"{pc(cm['pareto_membership'][p]/n)}\\\\")
pair_rows = []
for k, v in cm["pairwise_gap_seconds"].items():
    ident = cm["pairwise_identity"][k]
    pair_rows.append(f"{k.replace('-','--')} & {v['mean']:+.2f} & "
                     f"[{v['p05']:+.1f}, {v['p95']:+.1f}] & {pc(ident)}\\\\")
w("tab4_complementarity", (r"""
\begin{table}[t]
\caption{Policy complementarity over """ + f"{n}" + r""" contexts. A win is
\emph{resolved} when the paired seed difference against the runner-up exceeds
twice its standard error. Pareto membership is over all three criteria.}
\label{tab:complementarity}
\centering\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}l r r r r@{}}
\toprule
& \multicolumn{2}{c}{Best on C1} & \multicolumn{2}{c}{Non-dominated}\\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
& any & resolved & n & share\\
\midrule
""" + "\n".join(rows) + r"""
\midrule
\multicolumn{5}{@{}l}{\emph{Pairwise C1 differences (s/veh); positive = first
policy slower}}\\
\midrule
Pair & mean & 5--95\% range & identical\\
\midrule
""" + "\n".join(pair_rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""").strip())

# ---------------------------------------------------------------- table 5
lad = {r["selector"]: r for r in R["ladder_loco"]}
order = ["B0_SBS", "B1_mechanistic", "B2_tree3", "B3_logit", "B4_GBDT",
         "B5_selective", "VBS_reference"]
names = {"B0_SBS": "B0 \\ best fixed policy",
         "B1_mechanistic": "B1 \\ mechanistic rule",
         "B2_tree3": "B2 \\ tree, depth 3",
         "B3_logit": "B3 \\ logistic",
         "B4_GBDT": "B4 \\ GBDT advantage",
         "B5_selective": "B5 \\ selective, abstaining",
         "VBS_reference": "~~~VBS (not deployable)"}
rows = []
for k in order:
    e = lad[k]
    gc = "---" if k == "B0_SBS" else (
        "1.000" if k == "VBS_reference" else f"{e['gap_closed_vs_SBS']:.3f}")
    rows.append(f"{names[k].replace(chr(92)+' ','~~')} & {e['mean_regret']:.2f} & "
                f"{e['median_regret']:.2f} & {e['max_regret']:.1f} & "
                f"{e['cvar90']:.1f} & {pc(e['pct_within_noise'],0)} & {gc}\\\\")
w("tab5_ladder", (r"""
\begin{table}[t]
\caption{Decision quality under leave-one-context-out evaluation. Regret is in
seconds of system mean journey time per vehicle. ``Within noise'' is the share
of contexts whose regret falls below that context's own seed noise floor.}
\label{tab:ladder}
\centering\footnotesize
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{@{}l r r r r r r@{}}
\toprule
& \multicolumn{4}{c}{Regret (s/veh)} & in & gap\\
\cmidrule(lr){2-5}
& mean & med. & max & CVaR$_{90}$ & noise & closed\\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""").strip())

def _short(h):
    return (h.replace("_", " ").replace(" = ", " ").replace(".0", "")
             .replace("incident located on the north corridor", "incident on north corr.")
             .replace("penetration", "penetr."))


# ---------------------------------------------------------------- table 6
o = R["ood"]
rows = []
for name in sorted(o):
    d = o[name]
    rows.append(
        f"{name.split('_')[0]} & {_short(d['_held_out'])} & "
        f"{d['_shift_type'].replace('covariate + concept shift','cov.+concept')} & {d['B0_SBS']['mean_regret']:.2f} & "
        f"{d['B1_mechanistic']['mean_regret']:.2f} & "
        f"{d['B4_GBDT']['mean_regret']:.2f} & "
        f"{d['B5_selective']['mean_regret']:.2f} & "
        f"{pc(d['_out_of_support_rate'],0)} & {pc(d['_abstain_rate'],0)}\\\\")
w("tab6_ood", (r"""
\begin{table}[t]
\caption{Distribution shift, reported separately by shift type. Regret in
seconds of system mean journey time per vehicle on the held-out regime. The
support column is the share of held-out contexts the support gate flagged as
outside the training envelope.}
\label{tab:ood}
\centering\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}l l l r r r r r r@{}}
\toprule
& Held out & Shift type & B0 & B1 & B4 & B5 & flagged & abstained\\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""").strip())

print("tables written to", OUT)

# ---------------------------------------------------------------- table 7
sn = R.get("sensitivity", {})
if sn and isinstance(sn.get("parameters"), dict):
    prm, pref = sn["parameters"], sn["preference"]
    st = sn.get("winner_stability", {})
    prows = []
    for pol, d in prm.items():
        if not isinstance(d, dict) or "alternatives" not in d:
            continue
        for a, rr in d["alternatives"].items():
            key = f"{pol}_{d['parameter']}={a}"
            stab = st.get(key, {}).get("frac_winner_unchanged")
            prows.append(
                f"{pol} & \\texttt{{{d['parameter'].replace('_',chr(92)+'_')}}} "
                f"& {d['frozen_value']} & {a} & {rr['mean_change_s']:+.2f} & "
                f"{rr['mean_change_pct']:+.2f}\\% & "
                f"{'--' if stab is None else pc(stab,0)}\\\\")
    frows = []
    for name, wts in pref["profiles"].items():
        agree = pref["frac_profile_agrees_with_C1"][name]
        sel = pref["selection_by_profile"][name]
        frows.append(f"{name.capitalize()} & ({wts[0]:.2f}, {wts[1]:.2f}, "
                     f"{wts[2]:.2f}) & " +
                     " & ".join(str(sel.get(p, 0)) for p in K.POLICIES) +
                     f" & {pc(agree,1)}\\\\")
    w("tab7_sensitivity", (r"""
\begin{table}[t]
\caption{Sensitivity and robustness. Upper: the two policy parameters frozen
before the experiment, the effect of changing each on that policy's own mean
journey time, and how often the identity of the best policy is unchanged.
Lower: the three declared preference profiles over normalised criteria, the
policy each selects, and how often that agrees with the journey-time choice.}
\label{tab:sensitivity}
\centering\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}l l r r r r r@{}}
\toprule
\multicolumn{7}{@{}l}{\emph{Policy parameters}}\\
\midrule
Policy & Param. & Frozen & Alt. & $\Delta$ (s) & $\Delta$ (\%) & winner same\\
\midrule
""" + "\n".join(prows) + r"""
\midrule
\multicolumn{7}{@{}l}{\emph{Preference profiles} (weights on normalised C1--C3)}\\
\midrule
Profile & Weights & P1 & P2 & P3 & P4 & agrees C1\\
\midrule
""" + "\n".join(frows) + r"""
\bottomrule
\end{tabular}
\end{table}
""").strip())
