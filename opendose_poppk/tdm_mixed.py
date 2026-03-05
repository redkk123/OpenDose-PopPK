from __future__ import annotations

import pandas as pd

from .bayesian import MAPEstimator
from .covariate import CovariateModel
from .database import DrugDatabase
from .pk_model import PKModel
from .tdm_fit import _first_valid


def fit_tdm_mixed_by_drug(
    df: pd.DataFrame,
    dataset: str,
    sigma_obs: float = 0.8,
    n_iter: int = 3000,
) -> pd.DataFrame:
    """
    Fit MAP parameters by patient for mixed-drug TDM tables.

    Required columns:
    - patient_id
    - drug
    - time_h
    - conc
    - dose_mg
    """
    required = {"patient_id", "drug", "time_h", "conc", "dose_mg"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required mixed-TDM columns: {sorted(missing)}")

    db = DrugDatabase(dataset)
    rows = []

    for (patient_id, drug_name), g in df.groupby(["patient_id", "drug"], sort=True):
        drug = db.get_drug(str(drug_name))
        pk = PKModel(**drug.pk_kwargs)
        cov = CovariateModel(pk)
        est = MAPEstimator(pk=pk, covariate_model=cov, sigma_obs=sigma_obs)

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
                "drug": str(drug.name),
                "n_obs": int(group.shape[0]),
                "dose_mg": dose,
                "converged": bool(res["converged"]),
                "obj_value": float(res["obj_value"]),
                "map_F": float(res["params_map"]["F"]),
                "map_ka": float(res["params_map"]["ka"]),
                "map_ke": float(res["params_map"]["ke"]),
                "map_Vd": float(res["params_map"]["Vd"]),
            }
        )

    return pd.DataFrame(rows).sort_values(["drug", "patient_id"]).reset_index(drop=True)


def summarize_tdm_mixed_fit(fit_df: pd.DataFrame) -> dict:
    if fit_df.empty:
        return {"groups": 0, "patients": 0, "drugs": 0, "converged": 0}
    return {
        "groups": int(fit_df.shape[0]),
        "patients": int(fit_df["patient_id"].nunique()),
        "drugs": int(fit_df["drug"].nunique()),
        "converged": int(fit_df["converged"].sum()),
    }
