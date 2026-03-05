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
from .tdm import load_tdm_csv, summarize_tdm
from .tdm_fit import fit_tdm_patients, summarize_fit_table

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
    "load_tdm_csv",
    "summarize_tdm",
    "fit_tdm_patients",
    "summarize_fit_table",

    # ADD THESE ↓↓↓
    "plot_monte_carlo",
    "plot_population_with_covariates",
    "plot_map_fit",
    "plot_drug_comparison",
]
