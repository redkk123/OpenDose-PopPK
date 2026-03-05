from __future__ import annotations

import numpy as np

from .pk_model import PKModel


def _validate_regimen_inputs(
    interval_h: float,
    n_doses: int,
    t_end: float,
    n_points: int,
) -> None:
    if interval_h <= 0:
        raise ValueError("interval_h must be positive")
    if n_doses < 1:
        raise ValueError("n_doses must be at least 1")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")


def recommend_regimen_dose_for_target_cmax(
    pk: PKModel,
    target_cmax: float,
    interval_h: float,
    n_doses: int,
    t_end: float | None = None,
    n_points: int = 1000,
) -> dict:
    """
    Recommend dose per administration for repeated-dosing regimen Cmax target.
    """
    if target_cmax <= 0:
        raise ValueError("target_cmax must be positive")

    if t_end is None:
        t_end = interval_h * (n_doses + 1)
    _validate_regimen_inputs(interval_h, n_doses, float(t_end), n_points)

    t = np.linspace(0.0, float(t_end), int(n_points))
    unit_profile = pk.concentration_multiple_dose(t, D=1.0, interval_h=interval_h, n_doses=n_doses)
    unit_cmax = float(np.max(unit_profile))
    if unit_cmax <= 0:
        raise ValueError("model produced non-positive unit regimen Cmax")

    dose = float(target_cmax / unit_cmax)
    pred = pk.concentration_multiple_dose(t, D=dose, interval_h=interval_h, n_doses=n_doses)
    return {
        "mode": "regimen_cmax",
        "target": float(target_cmax),
        "recommended_dose": dose,
        "predicted": float(np.max(pred)),
        "unit_response": unit_cmax,
        "interval_h": float(interval_h),
        "n_doses": int(n_doses),
        "t_end": float(t_end),
    }


def recommend_regimen_dose_for_target_trough(
    pk: PKModel,
    target_trough: float,
    interval_h: float,
    n_doses: int,
    t_end: float | None = None,
    n_points: int = 1000,
) -> dict:
    """
    Recommend dose per administration for repeated-dosing regimen trough target.
    """
    if target_trough <= 0:
        raise ValueError("target_trough must be positive")

    if t_end is None:
        t_end = interval_h * (n_doses + 1)
    _validate_regimen_inputs(interval_h, n_doses, float(t_end), n_points)

    t = np.linspace(0.0, float(t_end), int(n_points))
    unit_profile = pk.concentration_multiple_dose(t, D=1.0, interval_h=interval_h, n_doses=n_doses)
    final_dose_time = (n_doses - 1) * interval_h
    mask_last = t >= final_dose_time
    unit_trough = float(np.min(unit_profile[mask_last])) if np.any(mask_last) else float(np.min(unit_profile))
    if unit_trough <= 0:
        raise ValueError("model produced non-positive unit regimen trough")

    dose = float(target_trough / unit_trough)
    pred = pk.concentration_multiple_dose(t, D=dose, interval_h=interval_h, n_doses=n_doses)
    pred_trough = float(np.min(pred[mask_last])) if np.any(mask_last) else float(np.min(pred))
    return {
        "mode": "regimen_trough",
        "target": float(target_trough),
        "recommended_dose": dose,
        "predicted": pred_trough,
        "unit_response": unit_trough,
        "interval_h": float(interval_h),
        "n_doses": int(n_doses),
        "t_end": float(t_end),
    }
