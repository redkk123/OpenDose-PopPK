from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_TDM_COLUMNS = ("patient_id", "time_h", "conc", "dose_mg")


def load_tdm_csv(csv_path: str | Path, dropna: bool = True) -> pd.DataFrame:
    """
    Load and validate TDM observations from CSV.

    Required columns:
    - patient_id
    - time_h
    - conc
    - dose_mg
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_TDM_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required TDM columns: {missing}")

    df = df.copy()
    df["patient_id"] = df["patient_id"].astype(str).str.strip()
    for col in ("time_h", "conc", "dose_mg"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if dropna:
        df = df.dropna(subset=list(REQUIRED_TDM_COLUMNS))

    if (df["time_h"] < 0).any():
        raise ValueError("time_h must be non-negative")
    if (df["conc"] < 0).any():
        raise ValueError("conc must be non-negative")
    if (df["dose_mg"] <= 0).any():
        raise ValueError("dose_mg must be positive")

    df = df.sort_values(["patient_id", "time_h"]).reset_index(drop=True)
    return df


def summarize_tdm(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "rows": 0,
            "patients": 0,
            "time_min_h": None,
            "time_max_h": None,
            "conc_min": None,
            "conc_max": None,
        }
    return {
        "rows": int(df.shape[0]),
        "patients": int(df["patient_id"].nunique()),
        "time_min_h": float(df["time_h"].min()),
        "time_max_h": float(df["time_h"].max()),
        "conc_min": float(df["conc"].min()),
        "conc_max": float(df["conc"].max()),
    }
