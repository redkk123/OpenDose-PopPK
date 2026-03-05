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
from .tdm_mixed import fit_tdm_mixed_by_drug, summarize_tdm_mixed_fit
from .tdm_report import (
    build_tdm_fit_markdown_report,
    write_tdm_fit_markdown_report,
    write_tdm_prediction_plot,
)
from .population_fit import fit_population_pk, bootstrap_population_pk
from .benchmark import benchmark_regimen_across_drugs, write_benchmark_csv
from .regimen import simulate_regimen, summarize_regimen, write_regimen_csv, write_regimen_plot

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
    "fit_tdm_mixed_by_drug",
    "summarize_tdm_mixed_fit",
    "build_tdm_fit_markdown_report",
    "write_tdm_fit_markdown_report",
    "write_tdm_prediction_plot",
    "fit_population_pk",
    "bootstrap_population_pk",
    "benchmark_regimen_across_drugs",
    "write_benchmark_csv",
    "simulate_regimen",
    "summarize_regimen",
    "write_regimen_csv",
    "write_regimen_plot",

    # ADD THESE ↓↓↓
    "plot_monte_carlo",
    "plot_population_with_covariates",
    "plot_map_fit",
    "plot_drug_comparison",
]
