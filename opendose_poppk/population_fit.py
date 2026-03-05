from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .pk_model import PKModel


def _validate_population_df(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Input dataframe is empty")

    required = {"time_h", "conc", "dose_mg"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def fit_population_pk(
    df: pd.DataFrame,
    init: dict | None = None,
    maxiter: int = 2000,
) -> dict:
    """
    Naive pooled PK parameter fit over all observations in a TDM table.

    Expected columns: time_h, conc, dose_mg
    """
    _validate_population_df(df)

    times = df["time_h"].to_numpy(dtype=float)
    obs = df["conc"].to_numpy(dtype=float)
    doses = df["dose_mg"].to_numpy(dtype=float)

    if init is None:
        init = {"F": 0.8, "ka": 1.8, "ke": 0.28, "Vd": 65.0}

    x0 = np.log(
        [
            max(float(init["F"]), 1e-6),
            max(float(init["ka"]), 1e-6),
            max(float(init["ke"]), 1e-6),
            max(float(init["Vd"]), 1e-6),
        ]
    )

    unique_doses = np.unique(doses)

    def _decode(x):
        F = float(np.clip(np.exp(x[0]), 0.01, 1.0))
        ka = float(max(np.exp(x[1]), 1e-6))
        ke = float(max(np.exp(x[2]), 1e-6))
        Vd = float(max(np.exp(x[3]), 1e-3))
        return F, ka, ke, Vd

    def obj(x):
        F, ka, ke, Vd = _decode(x)
        if abs(ka - ke) < 1e-4:
            return 1e8
        model = PKModel(F=F, ka=ka, ke=ke, Vd=Vd)
        pred = np.zeros_like(obs)
        for dose in unique_doses:
            mask = doses == dose
            idx = np.where(mask)[0]
            t_dose = times[idx]
            t_unique, inv = np.unique(t_dose, return_inverse=True)
            pred_unique = model.concentration(t_unique, D=float(dose))
            pred[idx] = pred_unique[inv]
        return float(np.mean((obs - pred) ** 2))

    res = minimize(
        obj,
        x0,
        method="Nelder-Mead",
        options={"maxiter": int(maxiter), "xatol": 1e-6, "fatol": 1e-6},
    )

    F, ka, ke, Vd = _decode(res.x)
    return {
        "params": {"F": F, "ka": ka, "ke": ke, "Vd": Vd},
        "success": bool(res.success),
        "objective_mse": float(res.fun),
        "n_obs": int(df.shape[0]),
    }


def bootstrap_population_pk(
    df: pd.DataFrame,
    n_boot: int = 200,
    seed: int = 42,
    init: dict | None = None,
    maxiter: int = 1200,
    ci_low: float = 2.5,
    ci_high: float = 97.5,
) -> dict:
    """
    Bootstrap confidence intervals for naive pooled population PK parameters.
    """
    _validate_population_df(df)
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    if not (0.0 <= ci_low < ci_high <= 100.0):
        raise ValueError("ci_low and ci_high must satisfy 0 <= ci_low < ci_high <= 100")

    rng = np.random.default_rng(seed)
    n = int(df.shape[0])
    rows = []

    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        sample = df.iloc[idx].reset_index(drop=True)
        fit = fit_population_pk(sample, init=init, maxiter=maxiter)
        p = fit["params"]
        rows.append(
            {
                "F": float(p["F"]),
                "ka": float(p["ka"]),
                "ke": float(p["ke"]),
                "Vd": float(p["Vd"]),
                "success": bool(fit["success"]),
            }
        )

    boot_df = pd.DataFrame(rows)
    params_ci = {}
    params_median = {}
    for param in ("F", "ka", "ke", "Vd"):
        vals = boot_df[param].to_numpy(dtype=float)
        lo, hi = np.percentile(vals, [ci_low, ci_high])
        params_ci[param] = {"low": float(lo), "high": float(hi)}
        params_median[param] = float(np.median(vals))

    return {
        "n_boot": int(n_boot),
        "seed": int(seed),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "success_rate": float(boot_df["success"].mean()),
        "params_median": params_median,
        "params_ci": params_ci,
    }
