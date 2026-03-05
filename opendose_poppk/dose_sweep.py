from __future__ import annotations

from typing import Iterable

import numpy as np

from .pk_model import PKModel


def sweep_dose_response(
    pk: PKModel,
    doses: Iterable[float],
    t_end: float = 24.0,
    n_points: int = 400,
) -> dict:
    """
    Evaluate Cmax/AUC response across a set of doses.
    """
    arr = np.asarray(list(doses), dtype=float)
    if arr.size == 0:
        raise ValueError("doses cannot be empty")
    if not np.isfinite(arr).all():
        raise ValueError("doses must be finite")
    if (arr <= 0).any():
        raise ValueError("doses must be positive")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")

    t = np.linspace(0.0, float(t_end), int(n_points))
    rows = []
    for dose in arr:
        c = pk.concentration(t, D=float(dose))
        rows.append(
            {
                "dose": float(dose),
                "cmax": float(np.max(c)),
                "auc": float(pk.auc(D=float(dose))),
            }
        )

    sorted_rows = sorted(rows, key=lambda r: r["dose"])
    cmax_values = np.array([r["cmax"] for r in sorted_rows], dtype=float)
    auc_values = np.array([r["auc"] for r in sorted_rows], dtype=float)
    monotonic_cmax = bool(np.all(np.diff(cmax_values) >= -1e-12))
    monotonic_auc = bool(np.all(np.diff(auc_values) >= -1e-12))

    return {
        "rows": rows,
        "n_doses": int(arr.size),
        "dose_min": float(np.min(arr)),
        "dose_max": float(np.max(arr)),
        "t_end": float(t_end),
        "n_points": int(n_points),
        "monotonic_cmax": monotonic_cmax,
        "monotonic_auc": monotonic_auc,
    }
