# Literature Audit

Every reference cited in the manuscript was checked against a primary source or
publisher record during preparation. This file records what was checked, what
was found, and what was deliberately left out.

## Method

For each reference: search for the exact title and authors, then confirm
journal or proceedings, volume, issue, page range and year against a publisher
record (INFORMS, IEEE, Elsevier, Springer, Wiley, JAIR, NeurIPS proceedings,
dblp) rather than against a secondary listing. A DOI is recorded **only when it
appeared in a retrieved record.** Three DOIs that could not be seen directly
were removed rather than inferred: Pan et al. (2013), Shimodaira (2000) and
Lei et al. (2018) are cited without a DOI. A citation without a DOI is
complete; a citation with a guessed DOI is a fabrication.

## Verified entries (23)

| Key | Verified against |
|---|---|
| rice1976 | Advances in Computers 15:65-118, 1976 |
| xu2008satzilla | JAIR 32:565-606, 2008 |
| bischl2016aslib | Artificial Intelligence 237:41-58, 2016 |
| kotthoff2014survey | AI Magazine 35(3):48-60, 2014 |
| smithmiles2009 | ACM Computing Surveys 41(1):6:1-6:25, 2009 |
| smithmiles2014instance | Computers & OR 45:12-24, 2014 |
| elmachtoub2022spo | Management Science 68(1):9-26, 2022 |
| pan2013proactive | IEEE Trans. Vehicular Technology 62(8):3551-3568, 2013 |
| lopez2018sumo | IEEE ITSC 2018:2575-2582 |
| krajzewicz2015emissions | Modeling Mobility with Open Data, LNM, Springer, 2015 |
| boriboonsomsin2012eco | IEEE T-ITS 13(4):1694-1704, 2012 |
| sen2001meanvariance | Transportation Science 35(1):37-49, 2001 |
| wardrop1952 | Proc. Inst. Civil Engineers 1(3):325-362, 1952 |
| arnott1991information | Transportation Research Part A 25(5):309-318, 1991 |
| acemoglu2018braess | Operations Research 66(4):893-917, 2018 |
| yang1998penetration | Transportation Research Part B 32(3):205-218, 1998 |
| lei2018conformal | JASA 113(523):1094-1111, 2018 |
| tibshirani2019covshift | NeurIPS 32:2526-2536, 2019 |
| vovk2005alrw | Springer, 2005, ISBN 978-0-387-00152-4 |
| shimodaira2000 | J. Statistical Planning and Inference 90(2):227-244, 2000 |
| chow1970reject | IEEE Trans. Information Theory 16(1):41-46, 1970 |
| friedman2001gbm | Annals of Statistics 29(5):1189-1232, 2001 |
| ke2017lightgbm | NeurIPS 30:3146-3154, 2017 |

## Corrections made during the audit

* **Yang's market-penetration paper is 1998, not 1999.** Transportation
  Research Part B 32(3):205-218, April 1998. It is cited with the correct year.
* **The load-balancing policy is FBkSP, not EBkSP.** Pan et al. (2013) propose
  five strategies: DSP, A\*R, RkSP, EBkSP (Entropy Balanced k-Shortest Paths)
  and FBkSP (Flow Balanced k-Shortest Paths). The policy implemented here
  balances predicted *flow* against link capacity over a travel-time-admissible
  path set, which is the FBkSP construction, not the entropy-based one. The
  manuscript names FBkSP.

## Claims checked against their sources

| Claim made in the manuscript | Source | Status |
|---|---|---|
| Per-instance algorithm selection is a named problem with an established formalism | rice1976 | supported |
| Portfolio selection with per-instance features is established practice | xu2008satzilla, bischl2016aslib, kotthoff2014survey | supported |
| VBS / SBS are standard reference points in that literature | bischl2016aslib | supported |
| Evaluating a predictor by decision cost rather than prediction error is an established distinction | elmachtoub2022spo | supported |
| Load-balancing k-shortest-path routing is an established policy family | pan2013proactive | supported |
| Mean-variance route guidance is an established policy family | sen2001meanvariance | supported |
| Providing information to drivers need not reduce congestion | arnott1991information, acemoglu2018braess | supported |
| Guidance benefits depend on market penetration | yang1998penetration | supported |
| Split conformal coverage requires exchangeability and fails under covariate shift | lei2018conformal, tibshirani2019covshift, shimodaira2000 | supported |
| Abstention with a reject option is an established decision mechanism | chow1970reject | supported |

## Deliberate non-claims

The manuscript does **not** claim that regime-dependent routing-policy
selection has never been studied. The positioning is narrower and is stated as
such: the combination of (i) an explicitly *established* policy portfolio
selected per context, (ii) evaluation by decision regret against both a best
fixed policy and a mechanistic rule, (iii) mechanism-informed dimensionless
features, (iv) distribution shift reported separately by shift type, and
(v) a support and confidence gate that abstains, is what is offered. Each
component individually has precedent, and each precedent is cited.

## Sourcing gaps, stated rather than filled

No verified source was available in this project for a value of time, a value
of reliability, or a carbon price appropriate to the setting. Rather than
invent them, the study uses **no monetary scalarisation at all**: the decision
criteria are compared by Pareto dominance, and scalar sensitivity uses declared
normalised weight profiles. This is a real limitation and is stated in the
manuscript rather than papered over with plausible-looking numbers.
