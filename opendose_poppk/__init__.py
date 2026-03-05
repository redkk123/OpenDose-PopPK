"""
OpenDose-PopPK
==============
Population Pharmacokinetic / Pharmacodynamic Modeling Framework
"""

from .pk_model import PKModel, PDModel
from .database import DrugDatabase
from .covariate import CovariateModel
from .population import PopulationSimulator
from .cohort import load_cohort_csv, simulate_cohort, summarize_cohort, write_cohort_template_csv
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
from .poppk_mixed import fit_population_mixed_effects, eta_table_from_fit
from .external_validation import (
    build_external_validation_table,
    load_external_validation_csv,
    summarize_external_validation,
    write_external_validation_template_csv,
)
from .web_app import build_web_app_payload, render_web_app_html, run_web_app_server, write_web_app_html
from .validation_report import build_validation_report, render_validation_report_markdown
from .release_tools import build_release_readiness_report, is_strict_semver, render_release_readiness_markdown
from .benchmark import benchmark_regimen_across_drugs, write_benchmark_csv
from .dosing import recommend_dose_for_target_auc, recommend_dose_for_target_cmax
from .dose_sweep import sweep_dose_response
from .regimen_dosing import (
    recommend_regimen_dose_for_target_cmax,
    recommend_regimen_dose_for_target_trough,
    recommend_regimen_dose_for_target_window,
)
from .sensitivity import local_pk_sensitivity
from .project_report import build_project_report, render_project_report_markdown
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
    "load_cohort_csv",
    "simulate_cohort",
    "summarize_cohort",
    "write_cohort_template_csv",
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
    "fit_population_mixed_effects",
    "eta_table_from_fit",
    "load_external_validation_csv",
    "build_external_validation_table",
    "summarize_external_validation",
    "write_external_validation_template_csv",
    "build_web_app_payload",
    "render_web_app_html",
    "write_web_app_html",
    "run_web_app_server",
    "build_validation_report",
    "render_validation_report_markdown",
    "is_strict_semver",
    "build_release_readiness_report",
    "render_release_readiness_markdown",
    "benchmark_regimen_across_drugs",
    "write_benchmark_csv",
    "recommend_dose_for_target_auc",
    "recommend_dose_for_target_cmax",
    "sweep_dose_response",
    "recommend_regimen_dose_for_target_cmax",
    "recommend_regimen_dose_for_target_trough",
    "recommend_regimen_dose_for_target_window",
    "local_pk_sensitivity",
    "build_project_report",
    "render_project_report_markdown",
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
