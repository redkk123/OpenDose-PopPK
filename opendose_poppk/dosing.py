from __future__ import annotations

import numpy as np

from .pk_model import PKModel


def recommend_dose_for_target_cmax(
    pk: PKModel,
    target_cmax: float,
    t_end: float = 24.0,
    n_points: int = 1000,
) -> dict:
    """
    Recommend a dose to hit a target Cmax using linear scaling.
    """
    if target_cmax <= 0:
        raise ValueError("target_cmax must be positive")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")

    t = np.linspace(0.0, float(t_end), int(n_points))
    unit_profile = pk.concentration(t, D=1.0)
    unit_cmax = float(np.max(unit_profile))
    if unit_cmax <= 0:
        raise ValueError("model produced non-positive unit Cmax")

    recommended_dose = float(target_cmax / unit_cmax)
    predicted_cmax = float(np.max(pk.concentration(t, D=recommended_dose)))
    return {
        "mode": "cmax",
        "target": float(target_cmax),
        "recommended_dose": recommended_dose,
        "predicted": predicted_cmax,
        "unit_response": unit_cmax,
    }


def recommend_dose_for_target_auc(pk: PKModel, target_auc: float) -> dict:
    """
    Recommend a dose to hit a target AUC using linear scaling.
    """
    if target_auc <= 0:
        raise ValueError("target_auc must be positive")

    unit_auc = float(pk.auc(D=1.0))
    if unit_auc <= 0:
        raise ValueError("model produced non-positive unit AUC")

    recommended_dose = float(target_auc / unit_auc)
    predicted_auc = float(pk.auc(D=recommended_dose))
    return {
        "mode": "auc",
        "target": float(target_auc),
        "recommended_dose": recommended_dose,
        "predicted": predicted_auc,
        "unit_response": unit_auc,
    }
