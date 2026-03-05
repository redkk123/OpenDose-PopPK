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


def build_tdm_prediction_table(df: pd.DataFrame, fit_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build per-observation predictions/residuals using fitted MAP parameters.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["patient_id", "time_h", "dose_mg", "obs_conc", "pred_conc", "residual"]
        )

    required_obs = {"patient_id", "time_h", "conc", "dose_mg"}
    missing_obs = required_obs.difference(df.columns)
    if missing_obs:
        raise ValueError(f"Missing observation columns: {sorted(missing_obs)}")

    required_fit = {"patient_id", "map_F", "map_ka", "map_ke", "map_Vd"}
    missing_fit = required_fit.difference(fit_df.columns)
    if missing_fit:
        raise ValueError(f"Missing fit columns: {sorted(missing_fit)}")

    fit_index = fit_df.copy()
    fit_index["patient_id"] = fit_index["patient_id"].astype(str)
    fit_index = fit_index.set_index("patient_id")

    rows = []
    for patient_id, g in df.groupby("patient_id", sort=True):
        pid = str(patient_id)
        if pid not in fit_index.index:
            raise ValueError(f"Patient '{pid}' not found in fit table")
        fit_row = fit_index.loc[pid]
        if isinstance(fit_row, pd.DataFrame):
            fit_row = fit_row.iloc[0]

        model = PKModel(
            F=float(fit_row["map_F"]),
            ka=float(fit_row["map_ka"]),
            ke=float(fit_row["map_ke"]),
            Vd=float(fit_row["map_Vd"]),
        )

        group = g.sort_values("time_h")
        times = group["time_h"].to_numpy(dtype=float)
        doses = group["dose_mg"].to_numpy(dtype=float)
        obs = group["conc"].to_numpy(dtype=float)

        pred = pd.Series(0.0, index=group.index, dtype=float)
        for dose in pd.unique(doses):
            mask = doses == dose
            idx = group.index[mask]
            t_sel = times[mask]
            t_unique, inv = pd.unique(t_sel), None
            # Keep deterministic mapping for repeated time points.
            t_unique_sorted = pd.Index(t_unique).sort_values().to_numpy(dtype=float)
            pred_unique = model.concentration(t_unique_sorted, D=float(dose))
            map_pred = dict(zip(t_unique_sorted.tolist(), pred_unique.tolist()))
            pred.loc[idx] = [map_pred[float(t)] for t in t_sel]

        residual = obs - pred.to_numpy(dtype=float)
        for i, (_, row) in enumerate(group.iterrows()):
            rows.append(
                {
                    "patient_id": str(row["patient_id"]),
                    "time_h": float(row["time_h"]),
                    "dose_mg": float(row["dose_mg"]),
                    "obs_conc": float(row["conc"]),
                    "pred_conc": float(pred.iloc[i]),
                    "residual": float(residual[i]),
                }
            )

    return pd.DataFrame(rows).sort_values(["patient_id", "time_h"]).reset_index(drop=True)


def summarize_prediction_table(pred_df: pd.DataFrame) -> dict:
    if pred_df.empty:
        return {"prediction_rows": 0, "rmse": None, "mae": None}
    r = pred_df["residual"].to_numpy(dtype=float)
    return {
        "prediction_rows": int(pred_df.shape[0]),
        "rmse": float((r**2).mean() ** 0.5),
        "mae": float(abs(r).mean()),
    }
