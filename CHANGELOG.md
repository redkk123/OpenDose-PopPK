# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] – 2024-12-01

### Added
- `PKModel`: 1-compartment analytical model with optional 2-compartment ODE mode and radioactive decay.
- `PDModel`: Emax Hill pharmacodynamic model.
- `DrugDatabase`: CSV-backed drug parameter loader.
- `CovariateModel`: Power-model covariate adjustment (weight, CrCl, age, hepatic markers).
- `PopulationSimulator`: Monte Carlo population simulation with 90 % prediction intervals.
- `MAPEstimator`: Bayesian Maximum-A-Posteriori individual parameter estimation.
- Full test suite (`pytest`) with 90 %+ coverage.
- Sphinx documentation with RTD theme, autodoc, Napoleon, nbsphinx.
- GitHub Actions CI for tests and documentation build.
- Demo notebook (`notebooks/demo_paracetamol.ipynb`).
- Companion paper draft (`paper/paper.md`).

---

## [Unreleased]

- PyPI publication.
- ReadTheDocs integration.
- Additional drug entries in `datasets/drugs_parameters.csv`.
