"""
OpenDose-PopPK
==============
Population Pharmacokinetic / Pharmacodynamic Modeling Framework
"""

from .pk_model import PKModel, PDModel
from .database import DrugDatabase
from .covariate import CovariateModel
from .population import PopulationSimulator
from .bayesian import MAPEstimator

# plotting imports
from .plotting import (
    plot_monte_carlo,
    plot_population_with_covariates,
    plot_map_fit,
    plot_drug_comparison,
)

__version__ = "1.0.0"

__all__ = [
    "PKModel",
    "PDModel",
    "DrugDatabase",
    "CovariateModel",
    "PopulationSimulator",
    "MAPEstimator",

    # ADD THESE ↓↓↓
    "plot_monte_carlo",
    "plot_population_with_covariates",
    "plot_map_fit",
    "plot_drug_comparison",
]