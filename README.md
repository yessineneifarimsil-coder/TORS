# SWFC — SHAP-Weighted Fuzzy CoCoSo for ITS Prioritisation

Research repository for the IC_TORS'26 paper.

## Research objective

Develop and evaluate a data-driven framework combining:

1. Synthetic traffic-inspired data generation
2. XGBoost predictive modelling
3. SHAP explainability
4. Data-derived criteria weighting
5. Fuzzy CoCoSo
6. Sensitivity and robustness analysis

## Research principle

The computational experiment must be reproducible.

No numerical result will be inserted into the paper unless it can be regenerated from the code and documented data.

## Research stages

- [ ] Define criteria and alternatives
- [ ] Define synthetic-data generation mechanism
- [ ] Generate benchmark dataset
- [ ] Validate dataset
- [ ] Train XGBoost
- [ ] Cross-validation
- [ ] SHAP analysis
- [ ] Derive criteria weights
- [ ] Construct fuzzy decision matrix
- [ ] Fuzzy CoCoSo
- [ ] Sensitivity analysis
- [ ] Weight perturbation
- [ ] Alternative MCDM comparison
- [ ] Generate final tables
- [ ] Generate final figures
- [ ] Update LaTeX paper

## Environment

Python 3.11  
Conda environment: `swfc`

## Repository structure

```text
data/
    raw/
    processed/

src/

results/
    tables/
    figures/
    models/

notebooks/

docs/

paper/