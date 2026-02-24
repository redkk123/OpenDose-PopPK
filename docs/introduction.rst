Introduction
============

What is OpenDose-PopPK?
-----------------------

**OpenDose-PopPK** is an open-source Python library for Population Pharmacokinetic and
Pharmacodynamic (PopPK/PD) modelling.  It targets researchers and clinical pharmacologists
who need reproducible, scriptable simulation and estimation workflows without depending on
proprietary software (NONMEM, Monolix, Phoenix WinNonlin).

Key capabilities
----------------

- **1-compartment PK model** — analytical first-order absorption/elimination with optional
  radioactive decay (nuclear-medicine dosimetry).
- **2-compartment PK model** — numerical ODE solver for central/peripheral distribution and
  inter-compartmental flow.
- **Emax Hill PD model** — sigmoidal concentration–effect relationship with configurable
  Hill coefficient.
- **Monte Carlo population simulation** — inter-individual variability (IIV) via log-normal
  random effects; 90 % prediction intervals.
- **Covariate modelling** — weight, renal function (CrCl), age, and hepatic markers via the
  Power Model.
- **MAP estimation** — Bayesian individual fitting from sparse observed samples using
  scipy.optimize.
- **DrugDatabase** — loads and manages pharmacokinetic parameters from CSV datasets.

Design principles
-----------------

*Modularity* — every component (PK, PD, covariate, simulator, estimator) is an independent
class that can be replaced or extended.

*Reproducibility* — random seeds are explicit; all outputs are deterministic when seeded.

*Scientific transparency* — formulas are documented with TeX in :doc:`math` and cross-linked
to the companion paper.

Who should use it?
------------------

- Pharmacology / PKPD researchers prototyping new models in Python.
- Clinical teams validating dosing regimens via simulation before a trial.
- Students learning PopPK concepts with real, runnable code.

Citation
--------

If you use OpenDose-PopPK in published work, please cite it — see :doc:`citation`.
