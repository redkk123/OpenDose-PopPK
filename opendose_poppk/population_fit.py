from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .pk_model import PKModel


def fit_population_pk(
    df: pd.DataFrame,
    init: dict | None = None,
    maxiter: int = 2000,
) -> dict:
    """
    Naive pooled PK parameter fit over all observations in a TDM table.

    Expected columns: time_h, conc, dose_mg
    """
    if df.empty:
        raise ValueError("Input dataframe is empty")

    required = {"time_h", "conc", "dose_mg"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

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
            pred[mask] = model.concentration(times[mask], D=float(dose))
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
