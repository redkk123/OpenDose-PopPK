from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .pk_model import PKModel


def simulate_regimen(
    pk: PKModel,
    dose: float,
    interval_h: float,
    n_doses: int,
    t_end: float | None = None,
    n_points: int = 400,
) -> dict:
    """
    Simulate repeated fixed-interval dosing for a single drug.
    """
    if interval_h <= 0:
        raise ValueError("interval_h must be positive")
    if n_doses < 1:
        raise ValueError("n_doses must be at least 1")
    if dose <= 0:
        raise ValueError("dose must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")

    if t_end is None:
        t_end = interval_h * (n_doses + 1)
    if t_end <= 0:
        raise ValueError("t_end must be positive")

    t = np.linspace(0.0, float(t_end), int(n_points))
    c = pk.concentration_multiple_dose(t, D=float(dose), interval_h=float(interval_h), n_doses=int(n_doses))
    cmax = float(np.max(c))

    # Last-interval trough proxy: minimum after final scheduled dose time.
    final_dose_time = (n_doses - 1) * interval_h
    mask_last = t >= final_dose_time
    if np.any(mask_last):
        trough_last = float(np.min(c[mask_last]))
    else:
        trough_last = float(np.min(c))

    return {
        "t": t,
        "conc": c,
        "dose": float(dose),
        "interval_h": float(interval_h),
        "n_doses": int(n_doses),
        "t_end": float(t_end),
        "cmax": cmax,
        "trough_last": trough_last,
    }


def summarize_regimen(result: dict) -> dict:
    t = np.asarray(result["t"], dtype=float)
    c = np.asarray(result["conc"], dtype=float)
    return {
        "dose": float(result["dose"]),
        "interval_h": float(result["interval_h"]),
        "n_doses": int(result["n_doses"]),
        "t_end": float(result["t_end"]),
        "n_points": int(t.shape[0]),
        "cmax": float(np.max(c)),
        "trough_last": float(result["trough_last"]),
    }


def write_regimen_csv(result: dict, output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"time_h": result["t"], "conc": result["conc"]})
    df.to_csv(out, index=False)
    return str(out)


def write_regimen_plot(result: dict, output_path: str | Path, title: str | None = None) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    t = np.asarray(result["t"], dtype=float)
    c = np.asarray(result["conc"], dtype=float)
    interval_h = float(result["interval_h"])
    n_doses = int(result["n_doses"])

    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.plot(t, c, label="Concentration")
    for k in range(n_doses):
        ax.axvline(k * interval_h, linestyle="--", alpha=0.25)
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Concentration")
    ax.set_title(title or "Repeated-dose regimen")
    ax.grid(alpha=0.2)
    ax.legend()

    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)
