# Literature Map

**Two tables, and the distinction between them is not cosmetic.**

Table 1 lists sources **retrieved and checked during this project**. Table 2 lists the places where
V2 *requires* a citation that I do not have. Nothing in Table 2 may be written into a paper until it
is obtained. No DOI, page number, author list or year has been reconstructed from memory anywhere in
this document.

---

## Table 1 — Verified in-session

| Strand | Source | What it establishes | What V2 borrows | What V2 must NOT claim |
|---|---|---|---|---|
| Routing foundations | Dijkstra (1959), *Numerische Mathematik* | Shortest path on additive link costs | P1 | That shortest-path routing is ours |
| Dynamic / traffic-informed routing | Gao & Chabini (2006), *TR-B*; Levering et al. (2021), *TR-B*; Pi & Qian (2017), *TR-B*; Ding et al. (2023) | Optimal routing policies in stochastic time-dependent networks; real-time control formulations | Framing of P2 as a reactive policy under lagged information | That P2 is predictive, or that we solve the STD routing problem |
| **Load balancing / proactive rerouting** | **Pan et al. (2013), *IEEE T-VT*** — DSP, AR*, RkSP, EBkSP, FBkSP | A published family of **per-vehicle** load-balancing rerouting strategies | **The formulation basis for P3** (see `policies/POLICY_COMPARISON.md`) | That load-balancing rerouting is new |
| Load-aware detour | Chen et al. (2025), *Phys. Rev. E* | Local-traffic-load detour strategy evaluated across density ranges | Supporting precedent for P3; density-dependence of benefit | Transfer of its cellular-automaton results to microsimulation |
| Rerouting with vehicle selection | Tseng et al. (2021), *IEEE T-VT*; Ho et al. (2023), *IEEE T-ITS*; Tay et al. (2025), *EAAI* | Selecting *which* vehicles to reroute; penetration/ratio effects | Motivation for penetration as a factor | That we study vehicle selection — we do not |
| **When is rerouting worthwhile** | **Falek et al. (2021), *J. ITS*** | Re-routing seldom useful except rush hours / long routes, on three cities' data | Direct precedent that guidance benefit is regime-dependent | That demand-dependence of routing benefit is our discovery |
| Congestion thresholds | Novikov et al. (2018) | Congestion threshold for triggering dynamic rerouting | Precedent for threshold framing | A universal threshold value |
| Regime / phase structure | *Routing-induced phase transitions…*, **Phys. Rev. Research (2026)** — **author list not captured; must be completed** | Shortest-time vs shortest-distance preference produces distinct efficiency phases | Closest conceptual precedent for regime structure | That regime structure in routing is unreported |
| Learning vs rule-based rerouting | Du et al. (2023), *CACIE* | Advantage of learning-based over rule-based rerouting is itself regime-dependent (varies with rerouting ratio) | Justification for baseline **B1** and for penetration as a factor | That ML rerouting is new |
| Algorithm selection | Rice (1976); Xu et al. (2008), *JAIR*; Bischl et al. (2016), *Artificial Intelligence* | Per-instance algorithm selection; VBS/SBS benchmarking; portfolio evaluation | The entire evaluation discipline, VBS/SBS, regret | That applying selection to routing is a first |
| Route-choice model selection in SUMO | Xie et al. (2014), *TRR* | Comparison of route-choice models in SUMO, with discussion of automatic selection | Direct precedent — must be cited prominently | That context-aware routing-policy selection is conceptually new |
| Prediction vs decision | Elmachtoub & Grigas (2022), *Management Science* | Predictive accuracy and decision quality need not coincide | The advantage-target rationale | That we implement an SPO training loss — we do not |
| Regret / robust decision | Kouvelis & Yu (1997) | Opportunity loss against the best available alternative | Regret definition | — |
| Eco-routing | Boriboonsomsin et al. (2012); Zeng et al. (2016, 2017); Huang & Peng (2018) | Eco-routing and time-constrained eco-routing | Basis for excluding eco-routing unless decoupling is demonstrated | That we contribute to eco-routing |
| MCDM | Keeney & Raiffa (1993); Hwang & Yoon (1981); Opricovic & Tzeng (2004); Brans & Vincke (1985) | Additive value, TOPSIS, VIKOR, PROMETHEE | Context for *not* making MCDM central | Any novelty in decision method |
| Adaptive route choice behaviour | Venkatraman et al. (2021); Ding-Mastera et al. (2019), *TR-B* | Traveller adaptation and latent-class routing-policy choice | Distinguishes *traveller* policy choice from *operator* policy choice | That we model traveller behaviour |
| Trees | Breiman et al., CART | Regression trees | B3 baseline | — |

---

## Table 2 — Required but NOT yet obtained

Each row is a hard blocker for the corresponding V2 component. **Phase 0 is not complete until every
row is filled with a real, checked reference.**

| # | Needed for | What must be sourced | Blocks |
|---|---|---|---|
| L1 | **P4 reliability-aware routing** | A primary formulation of mean–variance / reliability-based route choice (`μ + λσ` or a percentile form), with the estimator defined | P4 specification, Phase 1 |
| L2 | **P4 `λ`, and the generalised-cost sensitivity** | Published **value of time (VOT)** and **value of reliability (VOR)** for urban car travel, with currency, year and jurisdiction | P4 parameterisation; `DECISION_FRAMEWORK.md` step 3 |
| L3 | Generalised cost | Published **carbon price** `p_CO2` | Step-3 sensitivity only |
| L4 | **P3 exact variant** | The precise EBkSP / FBkSP definition from Pan et al. (2013), read in full, not from the abstract | P3 implementation and unit tests |
| L5 | **Conformal gate** | A primary reference for **split conformal prediction** for regression, and for the exchangeability requirement | `OOD_AND_ROBUSTNESS.md` gate 2 |
| L6 | **Support gate** | A reference for the chosen support/novelty estimator (kNN distance, Mahalanobis, or one-class) | Gate 1 |
| L7 | **GBDT** | The primary reference for the gradient-boosting implementation actually used | `ML_ARCHITECTURE.md` §2 |
| L8 | Tail risk metric | A reference for **CVaR** as used for risk-sensitive evaluation | Metrics |
| L9 | Phase-transition paper | The **author list and full citation** for the Phys. Rev. Research (2026) entry above | Related work |
| L10 | Penetration effects | A primary source quantifying **guidance penetration / compliance effects** on network outcomes | Justifying penetration levels |
| L11 | Incident modelling | A source for realistic **incident severity and duration** distributions in urban networks | Incident factor levels |
| L12 | Signal setting | A source for defensible **green-ratio ranges** for urban arterials | Signal factor levels |

**Rule.** Where a number is required and L1–L12 have not supplied it (notably VOT, VOR, carbon
price, incident durations, green ratios), the V2 documents state "to be sourced" rather than a
placeholder value. A placeholder number in a methods document has a way of becoming a result.

---

## Positioning statement (safe wording)

> The individual routing objectives, per-instance algorithm selection, gradient-boosted trees,
> regret-based evaluation and conformal prediction are all established. What this study proposes is
> an empirical characterisation of **when established route-guidance policies have complementary
> operating regions** in a controlled microsimulation, together with an uncertainty-aware selection
> procedure that is permitted to abstain. Demand-dependence of guidance benefit is already
> established in the literature (Falek et al. 2021; Novikov et al. 2018; Du et al. 2023); this study
> asks the narrower question of whether *several distinct policies* separate, and whether that
> separation is identifiable before deployment.

Do not write "first", "novel algorithm", "state of the art" or "unprecedented" anywhere.
