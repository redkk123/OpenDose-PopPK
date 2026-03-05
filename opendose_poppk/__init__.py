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
from .tdm import load_tdm_csv, summarize_tdm, write_tdm_template_csv
from .tdm_fit import (
    build_tdm_prediction_table,
    fit_tdm_patients,
    summarize_fit_table,
    summarize_prediction_table,
)
from .tdm_report import build_tdm_fit_markdown_report, write_tdm_fit_markdown_report
from .population_fit import fit_population_pk, bootstrap_population_pk

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
    "write_tdm_template_csv",
    "fit_tdm_patients",
    "summarize_fit_table",
    "build_tdm_prediction_table",
    "summarize_prediction_table",
    "build_tdm_fit_markdown_report",
    "write_tdm_fit_markdown_report",
    "fit_population_pk",
    "bootstrap_population_pk",

    # ADD THESE ↓↓↓
    "plot_monte_carlo",
    "plot_population_with_covariates",
    "plot_map_fit",
    "plot_drug_comparison",
]
