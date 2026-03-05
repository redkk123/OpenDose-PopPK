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


def _unit_regimen_profile(
    pk: PKModel,
    interval_h: float,
    n_doses: int,
    t_end: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    t = np.linspace(0.0, float(t_end), int(n_points))
    unit_profile = pk.concentration_multiple_dose(t, D=1.0, interval_h=interval_h, n_doses=n_doses)
    final_dose_time = (n_doses - 1) * interval_h
    mask_last = t >= final_dose_time
    unit_cmax = float(np.max(unit_profile))
    unit_trough = float(np.min(unit_profile[mask_last])) if np.any(mask_last) else float(np.min(unit_profile))
    return t, unit_profile, mask_last, unit_cmax, unit_trough


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

    t, _unit_profile, _mask_last, unit_cmax, _unit_trough = _unit_regimen_profile(
        pk=pk,
        interval_h=interval_h,
        n_doses=n_doses,
        t_end=float(t_end),
        n_points=int(n_points),
    )
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

    t, _unit_profile, mask_last, _unit_cmax, unit_trough = _unit_regimen_profile(
        pk=pk,
        interval_h=interval_h,
        n_doses=n_doses,
        t_end=float(t_end),
        n_points=int(n_points),
    )
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


def recommend_regimen_dose_for_target_window(
    pk: PKModel,
    target_trough_min: float,
    target_cmax_max: float,
    interval_h: float,
    n_doses: int,
    t_end: float | None = None,
    n_points: int = 1000,
    strategy: str = "trough_min",
) -> dict:
    """
    Recommend repeated-dose amount within a therapeutic window.

    Window constraints:
    - trough_last >= target_trough_min
    - cmax <= target_cmax_max
    """
    if target_trough_min <= 0:
        raise ValueError("target_trough_min must be positive")
    if target_cmax_max <= 0:
        raise ValueError("target_cmax_max must be positive")
    if target_trough_min >= target_cmax_max:
        raise ValueError("target_trough_min must be lower than target_cmax_max")
    if strategy not in {"trough_min", "midpoint"}:
        raise ValueError("strategy must be 'trough_min' or 'midpoint'")

    if t_end is None:
        t_end = interval_h * (n_doses + 1)
    _validate_regimen_inputs(interval_h, n_doses, float(t_end), n_points)

    t, _unit_profile, mask_last, unit_cmax, unit_trough = _unit_regimen_profile(
        pk=pk,
        interval_h=interval_h,
        n_doses=n_doses,
        t_end=float(t_end),
        n_points=int(n_points),
    )
    if unit_cmax <= 0:
        raise ValueError("model produced non-positive unit regimen Cmax")
    if unit_trough <= 0:
        raise ValueError("model produced non-positive unit regimen trough")

    dose_lower = float(target_trough_min / unit_trough)
    dose_upper = float(target_cmax_max / unit_cmax)
    feasible = dose_lower <= dose_upper

    if feasible:
        if strategy == "midpoint":
            dose = float(0.5 * (dose_lower + dose_upper))
        else:
            dose = dose_lower
        pred = pk.concentration_multiple_dose(t, D=dose, interval_h=interval_h, n_doses=n_doses)
        predicted_cmax = float(np.max(pred))
        predicted_trough = float(np.min(pred[mask_last])) if np.any(mask_last) else float(np.min(pred))
    else:
        dose = None
        predicted_cmax = None
        predicted_trough = None

    return {
        "mode": "regimen_window",
        "strategy": strategy,
        "target_trough_min": float(target_trough_min),
        "target_cmax_max": float(target_cmax_max),
        "feasible": bool(feasible),
        "dose_lower_bound": dose_lower,
        "dose_upper_bound": dose_upper,
        "recommended_dose": dose,
        "predicted_cmax": predicted_cmax,
        "predicted_trough": predicted_trough,
        "unit_cmax": unit_cmax,
        "unit_trough": unit_trough,
        "interval_h": float(interval_h),
        "n_doses": int(n_doses),
        "t_end": float(t_end),
    }
