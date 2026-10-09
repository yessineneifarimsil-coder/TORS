# Literature Novelty Matrix — 648-Context Routing-Policy Selection Study

Search date: 2026-10-09. Searcher: the auditing agent (see the independence caveat in
`EXECUTIVE_DECISION.md` §0).

## 1. Search method and its limits

**Tools that worked:** a web search engine (standard and extended modes), the alphaXiv
paper index (discovery plus full-text page retrieval), the Scholar Feed arXiv index (until
its anonymous quota ran out), and the Consensus index (one query before rate limiting).

**Tools that failed** (egress proxy `connect_rejected`): `api.crossref.org`,
`api.openalex.org`, `api.semanticscholar.org`, `scholar.google.com`, `doi.org`,
`arxiv.org` (direct fetch), `www.cmu.edu`, and publisher domains. **Consequence:** no DOI
below was resolved against Crossref. Bibliographic details come from publisher landing
pages, proceedings indexes (PMLR, JAIR, IEEE, SAGE, Springer) or institutional
repositories that appeared in search results. Each entry is labelled with the depth of
access actually achieved:

- **FT** — full text read (pages retrieved and inspected)
- **AB** — abstract or publisher record only
- **SN** — search-result snippet or secondary description only; treat the
  methodological characterisation as unverified

**Queries** (in combination, plus reference chasing from retrieved papers):
context-dependent routing strategy selection; algorithm selection for traffic routing
and signal control; meta-learning to select routing or route-guidance strategies;
comparison of rerouting strategies across penetration and congestion (SUMO); value of
route guidance versus penetration and congestion; per-instance algorithm selection for
VRP and TSP; SBS/VBS and closed gap; algorithm-selection generalisation and distribution
shift; safe policy improvement and fallback to a baseline; policy learning with
abstention; conformal and selective prediction for algorithm selection; decision-focused
learning; navigation-app concentration effects.

**Coverage judgement.** Coverage is good for algorithm selection, decision-focused
learning and safe fallback, and moderate for transportation routing. It is weak for
journal-only transportation literature, because TRB, Elsevier and IEEE full texts were
not reachable and arXiv under-represents transportation journals. **The absence of a
directly overlapping paper below is evidence of a gap, not proof of one.**

---

## 2. Closest-work matrix (verified facts vs interpretation)

Columns: RQ = research question; Port. = portfolio compared; Ctx = context factors
varied; Sel. = selection method; Out. = outcomes; SBS = strongest fixed alternative
evaluated; VBS = per-context optimum measured; Reg. = decision regret; HR = headroom vs
realised value separated; Val. = held-out validation; Shift = distribution shift tested;
Abst. = abstention/fallback. ✔ = yes, ✘ = no, ? = could not determine at this access level.

### 2.1 Transportation routing — strategies whose merit depends on context

| # | Paper (access) | RQ | Port. | Ctx | Sel. | Out. | SBS | VBS | Reg. | HR | Val. | Shift | Abst. | Relation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | **Pan, Sandu Popa, Zeitouni, Borcea (2013).** Proactive vehicular traffic rerouting for lower travel time. *IEEE Trans. Vehicular Technology* 62(8):3551–3568. [NJIT PDF](https://web.njit.edu/~borcea/papers/ieee-tvt13.pdf) · [HAL](https://hal.archives-ouvertes.fr/hal-00935601) (**AB**) | Design proactive rerouting strategies that approach DTA travel times at lower cost | DSP, AR\*, RkSP, EBkSP, FBkSP | adoption/compliance, networks | none (fixed choice per run) | travel time, re-routing frequency, computation | ? | ✘ | ✘ | ✘ | ? | ✘ | ✘ | **Strongly related.** Shows the strategies trade off effectiveness against computation, and supplies the P3 (FBkSP) construction. Does not select per context (from the abstract). |
| T2 | **Xie, Feng, Smith, Head (2014).** Unified route choice framework: specification and application to urban traffic control. *Transportation Research Record* 2466. doi 10.3141/2466-12. [SAGE](https://journals.sagepub.com/doi/pdf/10.3141/2466-12) · [Arizona](https://experts.arizona.edu/en/publications/unified-route-choice-framework-specification-and-application-to-u/) (**AB**) | Compare route-choice models under different signal-control regimes | several agent-based route-choice models | fixed-time vs adaptive (SURTRAC) control; 32-intersection Pittsburgh network | none; framework allows hybrid models | network performance | ? | ✘ | ✘ | ✘ | ? | ✘ | ✘ | **Strongly related — closest domain precedent found.** Its abstract reports that specific route-choice models perform differently under conventional and adaptive control: context-dependent relative merit on a *real* network. It proposes hybrid models but no selector or regret evaluation. |
| T3 | **Toso, Frasca, Kibangou (2023; v3 2024).** Potential detrimental effects of real-time route recommendations in traffic networks. arXiv:2303.17923. [alphaXiv](https://www.alphaxiv.org/abs/2303.17923) (**FT**) | How app penetration affects efficiency on a two-route OD with supply–demand constraints | informed (logit) vs fixed-preference drivers | penetration α, demand Φ, compliance | none | travel time, partial demand transfer, PoA | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **Background / mechanism.** Proves (two-route ODE model, validated in Aimsun) that higher penetration can degrade efficiency and cause partial demand transfer, with a demand-dependent threshold. Establishes the guidance-overreaction mechanism behind P2's weakness. |
| T4 | **Cornacchia, Nanni, Pedreschi, Pappalardo.** *Navigation services amplify concentration of traffic and emissions in our cities*, arXiv:2407.20004 (2024); reported as published in *Nature Communications* as *"The traffic concentration effects of urban navigation services"* (date unverified). [arXiv](https://arxiv.org/abs/2407.20004v1) (**SN/AB**) | Effect of navigation-app adoption on route diversity, congestion and CO2 | app-recommended vs habitual routes | adoption 0–100 %, load, 3 cities | none | route diversity, CO2, travel time | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **Strongly related on the "it depends" claim.** Reports CO2 benefits at low adoption that vanish above a city- and service-dependent threshold. Real road networks with GPS-derived demand: a far stronger external-validity setting than the present study. |
| T5 | **Wang, Yang, Hung (2026).** HLSR: Hybrid live–forecast selective dynamic vehicle rerouting for real-time congestion avoidance. arXiv:2608.18056. [alphaXiv](https://www.alphaxiv.org/abs/2608.18056) (**FT**) | New selective rerouting method | HLSR vs NRR, ReFOCUS+, Du-GAQ, live Dijkstra variants | demand 8k/16k/20k vehicles, Tainan SUMO network | none (method paper) | travel time, time loss, reroutes | ✔ (network-wide live Dijkstra) | ✘ | ✘ | ✘ | ✘ (single seed 42) | ✘ | ✘ | **Background.** Incidentally shows a method's rank changing with demand (Du-GAQ competitive at 8,000 vehicles, poor at 16,000–20,000). Single seed. |
| T6 | **Mahmassani & Jayakrishnan (1991)**, *System performance and user response under real-time information in a congested traffic corridor*, Transportation Research Part A; **Jayakrishnan, Mahmassani, Hu (1994)** (**SN** only, via secondary citations in [ROSAP](https://rosap.ntl.bts.gov/view/dot/3026/dot_3026_DS1.pdf)) | Benefit of real-time information vs market penetration | informed vs uninformed | penetration, congestion | none | travel time | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | **Background.** The classical result that guidance benefits depend on penetration and congestion, with diminishing returns. Details unverified. |
| T7 | **Yang (1998)**, TR-B 32(3):205–218; **Arnott, de Palma, Lindsey (1991)**, TR-A 25(5):309–318; **Acemoglu et al. (2018)**, *Operations Research* 66(4):893–917 (already cited by the manuscript; verified earlier against publisher records) | Equilibrium effects of information penetration | — | penetration | — | — | — | — | — | — | — | — | — | **Background.** Information need not reduce congestion, and benefits depend on penetration. |
| T8 | **Sen, Pillai, Joshi, Rathi (2001)**, *Transportation Science* 35(1):37–49 (cited by the manuscript) | Mean–variance route guidance | — | — | — | — | — | — | — | — | — | — | — | **Background.** Source of the P4 objective. |

### 2.2 Algorithm selection and portfolios

| # | Paper (access) | RQ | Port. | Ctx | Sel. | Out. | SBS | VBS | Reg. | HR | Val. | Shift | Abst. | Relation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | **Rice (1976)**, The algorithm selection problem, *Advances in Computers* 15:65–118 (cited; publisher record) | Formalise per-instance selection | — | instance features | mapping | performance | — | — | — | — | — | — | — | **Methodological foundation.** |
| A2 | **Xu, Hutter, Hoos, Leyton-Brown (2008)**, SATzilla, *JAIR* 32:565–606 (cited) | Portfolio selection for SAT | SAT solvers | instance features | empirical hardness models | runtime | ✔ | ✔ | ✔ | ✔ | ✔ | ✘ | ✘ | **Methodologically related.** Regression of each solver's performance and argmin is exactly the B4/B2 pattern. |
| A3 | **Bischl et al. (2016)**, ASlib, *Artificial Intelligence* 237:41–58 (cited) | Standard benchmark and evaluation for selection | many | many | many | PAR10 etc. | ✔ | ✔ | ✔ | ✔ (gap closed) | ✔ (CV) | ✘ | ✘ | **Methodologically related.** SBS/VBS/gap-closed evaluation is standard here. |
| A4 | **Kerschke, Kotthoff, Bossek, Hoos, Trautmann (2018)**, Leveraging TSP solver complementarity through machine learning, *Evolutionary Computation* 26(4):597–620, doi 10.1162/evco_a_00215. [Paderborn RIS](https://ris.uni-paderborn.de/record/46352) (**AB**) | Per-instance selection among inexact TSP solvers | 5 TSP solvers | instance features | ML selectors | solution quality/time | ✔ | ✔ | ✔ | ✔ | ✔ | ? | ✘ | **Methodologically related (routing-adjacent).** Complementarity of routing-problem *solvers* and selection beating the SBS, in a different problem class (combinatorial solver choice, not traffic assignment policy). |
| A5 | **Lindauer, van Rijn, Kotthoff (2019)**, The algorithm selection competitions 2015 and 2017, *Artificial Intelligence* 272:86–100. [arXiv 1805.01214](https://arxiv.org/abs/1805.01214) (**AB**) | State of algorithm selection | many | many | many | — | ✔ | ✔ | ✔ | ? | ✔ | ✘ | ✘ | **Methodologically related.** Reports scenarios where selection is hard. The closed-gap definition was not verified from the retrieved text. |
| A6 | **Balcan, Sandholm, Vitercik (2021)**, Generalization in portfolio-based algorithm selection, AAAI. arXiv:2012.13315 (**AB**) | Sample-complexity guarantees for selectors | — | — | — | — | — | — | — | — | — | ✘ | ✘ | **Methodologically related.** Theoretical generalisation; large portfolios overfit. |
| A7 | **Ansótegui, Sellmann, Tierney (2018)**, Self-configuring cost-sensitive hierarchical clustering with recourse, CP 2018, LNCS 11008:524–534, doi 10.1007/978-3-319-98334-9_34. [Bielefeld](https://pub.uni-bielefeld.de/record/2958229) (**AB**) | Selector that estimates its own confidence | solver portfolios | instance features | selection + confidence-based recourse | solver performance | ✔ | ? | ? | ? | ? | ✘ | **✔ (defensive recourse overrides the recommendation)** | **Directly overlapping with the B5 idea.** Confidence-gated fallback in algorithm selection predates this study. |

### 2.3 Decision-focused learning, safe fallback, abstention, shift

| # | Paper (access) | Relation to the manuscript |
|---|---|---|
| D1 | **Elmachtoub & Grigas (2022)**, Smart "predict, then optimize", *Management Science* 68(1):9–26 (cited) | **Directly covers the "accuracy ≠ decision quality" claim**; its experiments include shortest-path problems. |
| D2 | **Mandi, Kotary, Berden, Mulamba, Bucarey, Guns, Fioretto (2024)**, Decision-focused learning: foundations, state of the art, benchmark and future opportunities, *JAIR* 80:1623–1701, doi 10.1613/jair.1.15320. [JAIR](https://www.jair.org/index.php/jair/article/view/15320) (**AB**) | **Methodologically related.** Survey and benchmark of 11 methods on 7 problems. Training on decision cost rather than prediction error is an established research area. |
| D3 | **Laroche, Trichelair, Tachet des Combes (2019)**, Safe policy improvement with baseline bootstrapping, ICML, PMLR 97:3652–3661. [PMLR](https://proceedings.mlr.press/v97/laroche19a.html) (**AB**) | **Methodologically overlapping with B5.** Revert to the baseline policy where uncertainty is high, with improvement guarantees. |
| D4 | **Sawarni, Jin, Whitehouse, Syrgkanis (2026)**, Policy learning with abstention, AISTATS, PMLR 300:4465–4473. [PMLR](https://proceedings.mlr.press/v300/sawarni26a.html) (**AB**) | **Methodologically overlapping with B5.** Policies that defer to a safe default, with regret guarantees and links to safe policy improvement. |
| D5 | **Chow (1970)**, IEEE Trans. Information Theory 16(1):41–46 (cited) | Reject-option foundation. |
| D6 | **Tibshirani, Barber, Candès, Ramdas (2019)**, Conformal prediction under covariate shift, NeurIPS 32 (cited); **Shimodaira (2000)** (cited) | **Establishes** that split-conformal coverage fails under covariate shift, which the manuscript correctly states. |

---

## 3. Required novelty verdict

**Q1. Has choosing among established algorithms based on context already been studied?**
Yes, extensively: Rice (1976), SATzilla, ASlib, Kerschke et al. (2018) and the
competition series. **Established.**

**Q2. Has context-dependent selection among transportation-routing policies been studied?**
Context-dependent *relative performance* of routing strategies is well documented
(T1, T2, T4, T6, T7; T2 shows route-choice-model performance changing with the control
regime on a real network). An explicit *learned per-context selector* among established
traffic-routing policies, evaluated against SBS and VBS, was **not found**. This is a
narrow gap whose existence I could not confirm exhaustively.

**Q3. Has someone measured the gap between the best fixed policy and the per-context best
for a comparable routing problem?** Not found for traffic-routing *policies*. For routing
*solvers* (TSP; A4) the SBS–VBS gap is standard. The idea is established; the domain
measurement appears new.

**Q4. Has someone shown that winner-prediction accuracy can improve while decision regret
worsens?** Yes in general (D1, D2, and the ASlib practice of scoring by performance rather
than accuracy). The manuscript's instance (B1: 66.7 % top-1 vs 64.5 %, but 0.77 vs 0.45 s
regret) is a domain illustration of an **established** phenomenon. Its accuracy margin is
also only 1–2 percentage points and depends on how the 50 exact ties are scored.

**Q5. Has someone evaluated selective routing-policy selection under multiple types of
distribution shift?** Not found in transportation. Selector generalisation (A6) and
conformal coverage under shift (D6) are established in general. In this study the
selective rule never acted, so the manuscript has nothing positive to contribute here.

**Q6. Has someone combined fixed-policy baselines, regret/headroom, multi-criteria
evaluation and abstention/fallback in a comparable transportation simulation?** Not
found. A7 (selection plus confidence recourse), D3/D4 (fallback to a baseline) and A3
(SBS/VBS evaluation) together contain every methodological ingredient. The combination in
a traffic simulation appears unpublished, but §13 of the brief applies: combining known
ideas is a contribution only if it yields new insight.

**Q7. Established, extension, or possibly new?**

| Element | Classification |
|---|---|
| Per-instance selection; SBS/VBS; gap closed | Established |
| Accuracy ≠ regret | Established |
| Abstention / baseline fallback / recourse | Established |
| Conformal failure under shift | Established |
| Relative merit of routing strategies depends on demand, penetration and control | Established |
| Mechanistic dimensionless descriptors (x1–x8) | Minor extension (domain feature engineering) |
| Shift splits reported separately by type in a routing setting | Minor extension (good practice) |
| **Measured SBS–VBS headroom for established traffic-routing policies, and its size relative to the wrong-fixed-policy cost and to within-policy tuning** | **Possibly new**, on one benchmark |

**Q8. Which papers threaten the novelty most seriously?** For framing: the combination
**A3 + A7 + D3**. Per-instance selection evaluated by SBS/VBS gap with a
confidence-gated fallback to the fixed choice is already the standard algorithm-selection
toolkit, so the manuscript's method section is a re-instantiation. For the domain claim:
**T2 (Xie et al. 2014)** together with **T4 (Cornacchia et al.)**. They already establish,
on real networks, that which routing approach works best depends on the operating regime
(control system, adoption, load). That is the premise of RQ1, so the study's
"complementarity" finding confirms rather than discovers.

**Q9. What exact contribution remains?** A **quantified negative result**: on a controlled
SUMO benchmark, per-context selection among four established routing policies has a
decision value of 0.24–0.45 s/veh (0.05–0.10 %), concentrated in about 20 of 648
contexts. That is at least one, and up to three, orders of magnitude smaller than the
cost of choosing the wrong fixed policy (16–220 s/veh) or of one parameter of the
best fixed policy (≈17 s/veh on a 96-context subset). The study also shows that the
complementarity documented in the literature does not by itself imply decision value.
This is publishable in principle **only if it generalises beyond one synthetic
three-corridor network**, which is exactly what is missing.

---

## 4. Literature the manuscript should cite but does not

The journal bibliography already cites T3 (Toso et al.) and T4 (Cornacchia et al., as an
arXiv preprint; the reported *Nature Communications* version should be checked and
cited if confirmed). It does **not** cite T2 Xie et al. (2014), A4 Kerschke et al. (2018),
A5 Lindauer et al. (2019), A7 Ansótegui et al. (2018), D2 Mandi et al. (2024),
D3 Laroche et al. (2019) or D4 Sawarni et al. (2026). A7, D3 and D4 matter most: without them the gate reads as a
novel mechanism, which it is not. **Verify every entry against the publisher record before
citing.** None was resolved against Crossref from this environment.
