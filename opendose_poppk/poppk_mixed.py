from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .pk_model import PKModel

_PARAM_NAMES = ("ka", "ke", "Vd")


def _validate_mixed_df(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Input dataframe is empty")

    required = {"patient_id", "time_h", "conc", "dose_mg"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def _predict_one_compartment(
    times: np.ndarray,
    doses: np.ndarray,
    F: float,
    ka: float,
    ke: float,
    vd: float,
    lambda_phys: float,
) -> np.ndarray:
    pred = np.zeros_like(times, dtype=float)
    ke_eff = float(ke + lambda_phys)
    if abs(ka - ke_eff) < 1e-6:
        ke_eff *= 0.999

    for dose in np.unique(doses):
        mask = doses == dose
        t = times[mask]
        scale = (F * float(dose) * ka) / (vd * (ka - ke_eff))
        c = scale * (np.exp(-ke_eff * t) - np.exp(-ka * t))
        pred[mask] = np.maximum(c, 0.0)
    return pred


def fit_population_mixed_effects(
    df: pd.DataFrame,
    pk_template: PKModel,
    sigma_obs: float = 0.8,
    maxiter: int = 1200,
    init_theta: dict | None = None,
    init_omega: dict | None = None,
) -> dict:
    """
    Fit a simple PopPK mixed-effects model with fixed (theta) and random effects (eta).

    Model:
    - Individual parameters: p_i = theta * exp(eta_i), for p in {ka, ke, Vd}
    - Random effects prior: eta_i ~ N(0, Omega), diagonal Omega with std {omega_ka, omega_ke, omega_Vd}
    - Observation model: y_ij ~ N(C_ij, sigma_obs^2)
    """
    _validate_mixed_df(df)
    if sigma_obs <= 0:
        raise ValueError("sigma_obs must be positive")
    if maxiter < 1:
        raise ValueError("maxiter must be at least 1")

    if init_theta is None:
        init_theta = {
            "ka": float(pk_template.ka),
            "ke": float(pk_template.ke),
            "Vd": float(pk_template.Vd),
        }
    if init_omega is None:
        init_omega = {"ka": 0.30, "ke": 0.30, "Vd": 0.30}

    for p in _PARAM_NAMES:
        if float(init_theta[p]) <= 0:
            raise ValueError(f"init_theta[{p}] must be positive")
        if float(init_omega[p]) <= 0:
            raise ValueError(f"init_omega[{p}] must be positive")

    grouped = []
    for patient_id, g in df.groupby("patient_id", sort=True):
        grp = g.sort_values("time_h")
        grouped.append(
            {
                "patient_id": str(patient_id),
                "time_h": grp["time_h"].to_numpy(dtype=float),
                "conc": grp["conc"].to_numpy(dtype=float),
                "dose_mg": grp["dose_mg"].to_numpy(dtype=float),
            }
        )

    n_patients = len(grouped)
    n_params = len(_PARAM_NAMES)

    x0_theta = np.log(
        [
            max(float(init_theta["ka"]), 1e-6),
            max(float(init_theta["ke"]), 1e-6),
            max(float(init_theta["Vd"]), 1e-6),
        ]
    )
    x0_omega = np.log(
        [
            max(float(init_omega["ka"]), 1e-6),
            max(float(init_omega["ke"]), 1e-6),
            max(float(init_omega["Vd"]), 1e-6),
        ]
    )
    x0_eta = np.zeros(n_patients * n_params, dtype=float)
    x0 = np.concatenate([x0_theta, x0_omega, x0_eta])

    def _decode(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        theta = np.maximum(np.exp(x[:n_params]), 1e-6)
        omega = np.maximum(np.exp(x[n_params : 2 * n_params]), 1e-6)
        eta = x[2 * n_params :].reshape(n_patients, n_params)
        return theta, omega, eta

    def obj(x: np.ndarray) -> float:
        theta, omega, eta = _decode(x)
        sse = 0.0
        prior = 0.0
        for i, g in enumerate(grouped):
            ka_i = float(theta[0] * np.exp(eta[i, 0]))
            ke_i = float(theta[1] * np.exp(eta[i, 1]))
            vd_i = float(theta[2] * np.exp(eta[i, 2]))
            if abs(ka_i - ke_i) < 1e-4:
                return 1e8

            times = g["time_h"]
            obs = g["conc"]
            doses = g["dose_mg"]
            pred = _predict_one_compartment(
                times=times,
                doses=doses,
                F=float(pk_template.F),
                ka=ka_i,
                ke=ke_i,
                vd=vd_i,
                lambda_phys=float(pk_template.lambda_phys),
            )

            residual = obs - pred
            sse += float(np.sum(residual**2))
            prior += float(np.sum((eta[i] / omega) ** 2))

        val = 0.5 * sse / (sigma_obs**2) + 0.5 * prior + n_patients * float(np.sum(np.log(omega)))
        if not np.isfinite(val):
            return 1e12
        return float(val)

    res = minimize(
        obj,
        x0,
        method="L-BFGS-B",
        options={"maxiter": int(maxiter)},
    )

    theta, omega, eta = _decode(np.asarray(res.x, dtype=float))
    eta_rows = []
    for i, g in enumerate(grouped):
        eta_ka = float(eta[i, 0])
        eta_ke = float(eta[i, 1])
        eta_vd = float(eta[i, 2])
        ind_ka = float(theta[0] * np.exp(eta_ka))
        ind_ke = float(theta[1] * np.exp(eta_ke))
        ind_vd = float(theta[2] * np.exp(eta_vd))
        eta_rows.append(
            {
                "patient_id": g["patient_id"],
                "eta_ka": eta_ka,
                "eta_ke": eta_ke,
                "eta_Vd": eta_vd,
                "ind_ka": ind_ka,
                "ind_ke": ind_ke,
                "ind_Vd": ind_vd,
            }
        )

    return {
        "theta": {"ka": float(theta[0]), "ke": float(theta[1]), "Vd": float(theta[2])},
        "omega": {"ka": float(omega[0]), "ke": float(omega[1]), "Vd": float(omega[2])},
        "eta": eta_rows,
        "success": bool(res.success),
        "objective": float(res.fun),
        "n_patients": int(n_patients),
        "n_obs": int(df.shape[0]),
        "sigma_obs": float(sigma_obs),
    }


def eta_table_from_fit(fit: dict) -> pd.DataFrame:
    rows = fit.get("eta", [])
    if not rows:
        return pd.DataFrame(columns=["patient_id", "eta_ka", "eta_ke", "eta_Vd", "ind_ka", "ind_ke", "ind_Vd"])
    return pd.DataFrame(rows).sort_values("patient_id").reset_index(drop=True)
