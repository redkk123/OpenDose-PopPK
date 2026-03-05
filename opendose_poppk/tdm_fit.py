from __future__ import annotations

import pandas as pd

from .bayesian import MAPEstimator
from .covariate import CovariateModel
from .pk_model import PKModel


def _first_valid(group: pd.DataFrame, col: str):
    if col not in group.columns:
        return None
    series = pd.to_numeric(group[col], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[0])


def fit_tdm_patients(
    df: pd.DataFrame,
    pk: PKModel,
    sigma_obs: float = 0.8,
    n_iter: int = 3000,
) -> pd.DataFrame:
    """
    Fit MAP individual parameters for each patient in a validated TDM dataframe.

    Expected columns at minimum:
    - patient_id
    - time_h
    - conc
    - dose_mg

    Optional covariate columns:
    - weight, crcl, age
    """
    rows = []
    cov = CovariateModel(pk)
    est = MAPEstimator(pk=pk, covariate_model=cov, sigma_obs=sigma_obs)

    for patient_id, g in df.groupby("patient_id", sort=True):
        group = g.sort_values("time_h")
        times = group["time_h"].to_numpy(dtype=float)
        obs = group["conc"].to_numpy(dtype=float)
        dose = float(group["dose_mg"].iloc[0])

        patient_covariates = {}
        for name in ("weight", "crcl", "age"):
            value = _first_valid(group, name)
            if value is not None:
                patient_covariates[name] = value

        res = est.fit(
            times=times,
            obs=obs,
            patient_covariates=patient_covariates,
            dose=dose,
            n_iter=n_iter,
        )

        rows.append(
            {
                "patient_id": str(patient_id),
                "n_obs": int(group.shape[0]),
                "dose_mg": dose,
                "converged": bool(res["converged"]),
                "obj_value": float(res["obj_value"]),
                "map_F": float(res["params_map"]["F"]),
                "map_ka": float(res["params_map"]["ka"]),
                "map_ke": float(res["params_map"]["ke"]),
                "map_Vd": float(res["params_map"]["Vd"]),
                "eta_F": float(res["eta_map"]["F"]),
                "eta_ka": float(res["eta_map"]["ka"]),
                "eta_ke": float(res["eta_map"]["ke"]),
                "eta_Vd": float(res["eta_map"]["Vd"]),
            }
        )

    return pd.DataFrame(rows).sort_values("patient_id").reset_index(drop=True)


def summarize_fit_table(fit_df: pd.DataFrame) -> dict:
    if fit_df.empty:
        return {"patients": 0, "converged": 0, "convergence_rate": 0.0}
    converged = int(fit_df["converged"].sum())
    total = int(fit_df.shape[0])
    return {
        "patients": total,
        "converged": converged,
        "convergence_rate": float(converged / total),
    }
