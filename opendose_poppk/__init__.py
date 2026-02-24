"""
OpenDose-PopPK
==============
Population Pharmacokinetic / Pharmacodynamic Modeling Framework

Main Classes
------------
- PKModel: 1-compartment pharmacokinetic model
- PDModel: Emax pharmacodynamic model
- DrugDatabase: Load drug parameters from CSV
- CovariateModel: Apply covariates to PK parameters
- PopulationSimulator: Monte Carlo population simulation
- MAPEstimator: Bayesian individual parameter estimation

Usage
-----
    from opendose_poppk import PKModel, PDModel, MAPEstimator, PopulationSimulator
    
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    pd = PDModel(EC50=10.0, n=1.5)
    sim = PopulationSimulator(pk, pd)
    result = sim.run(n_subjects=1000)
"""

from .pk_model import PKModel, PDModel
from .database import DrugDatabase
from .covariate import CovariateModel
from .population import PopulationSimulator
from .bayesian import MAPEstimator

__version__ = "1.0.0"

__all__ = [
    "PKModel",
    "PDModel",
    "DrugDatabase",
    "CovariateModel",
    "PopulationSimulator",
    "MAPEstimator",
]

from .plotting import plot_monte_carlo, plot_population_with_covariates, plot_map_fit, plot_drug_comparison
