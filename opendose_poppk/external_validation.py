from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .pk_model import PKModel

REQUIRED_EXTERNAL_COLUMNS = ("patient_id", "time_h", "dose_mg", "obs_conc")


def load_external_validation_csv(csv_path: str | Path, dropna: bool = True) -> pd.DataFrame:
    """
    Load and validate an external validation dataset.

    Required columns:
    - patient_id
    - time_h
    - dose_mg
    - obs_conc

    Optional columns:
    - ref_conc (reference software prediction, e.g., NONMEM/Monolix/Pumas)
    - study_id
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_EXTERNAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required external-validation columns: {missing}")

    df = df.copy()
    df["patient_id"] = df["patient_id"].astype(str).str.strip()
    for col in ("time_h", "dose_mg", "obs_conc"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "ref_conc" in df.columns:
        df["ref_conc"] = pd.to_numeric(df["ref_conc"], errors="coerce")

    if dropna:
        df = df.dropna(subset=list(REQUIRED_EXTERNAL_COLUMNS))

    if (df["time_h"] < 0).any():
        raise ValueError("time_h must be non-negative")
    if (df["dose_mg"] <= 0).any():
        raise ValueError("dose_mg must be positive")
    if (df["obs_conc"] < 0).any():
        raise ValueError("obs_conc must be non-negative")
    if "ref_conc" in df.columns and (df["ref_conc"] < 0).any():
        raise ValueError("ref_conc must be non-negative")

    df = df.sort_values(["patient_id", "time_h"]).reset_index(drop=True)
    return df


def _error_metrics(obs: np.ndarray, pred: np.ndarray) -> dict:
    if obs.size == 0:
        return {"n": 0, "rmse": None, "mae": None, "bias": None, "mape_pct": None}
    err = pred - obs
    mape = None
    nonzero = obs != 0
    if np.any(nonzero):
        mape = float(np.mean(np.abs(err[nonzero] / obs[nonzero])) * 100.0)
    return {
        "n": int(obs.size),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "bias": float(np.mean(err)),
        "mape_pct": mape,
    }


def build_external_validation_table(df: pd.DataFrame, pk: PKModel) -> pd.DataFrame:
    """
    Build per-observation predictions and residuals for external validation.
    """
    required = {"patient_id", "time_h", "dose_mg", "obs_conc"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rows = []
    for patient_id, g in df.groupby("patient_id", sort=True):
        grp = g.sort_values("time_h")
        times = grp["time_h"].to_numpy(dtype=float)
        doses = grp["dose_mg"].to_numpy(dtype=float)
        obs = grp["obs_conc"].to_numpy(dtype=float)
        pred = np.zeros_like(obs)

        for dose in np.unique(doses):
            mask = doses == dose
            t_unique, inv = np.unique(times[mask], return_inverse=True)
            pred_unique = pk.concentration(t_unique, D=float(dose))
            pred[mask] = pred_unique[inv]

        for i, (_, row) in enumerate(grp.iterrows()):
            out_row = {
                "patient_id": str(patient_id),
                "time_h": float(row["time_h"]),
                "dose_mg": float(row["dose_mg"]),
                "obs_conc": float(row["obs_conc"]),
                "model_pred_conc": float(pred[i]),
                "model_residual": float(row["obs_conc"] - pred[i]),
            }
            if "ref_conc" in grp.columns:
                ref_val = row["ref_conc"]
                out_row["ref_conc"] = float(ref_val) if pd.notna(ref_val) else np.nan
                out_row["ref_residual"] = (
                    float(row["obs_conc"] - ref_val) if pd.notna(ref_val) else np.nan
                )
                out_row["model_vs_ref"] = float(pred[i] - ref_val) if pd.notna(ref_val) else np.nan
            if "study_id" in grp.columns:
                out_row["study_id"] = str(row["study_id"])
            rows.append(out_row)

    return pd.DataFrame(rows).sort_values(["patient_id", "time_h"]).reset_index(drop=True)


def summarize_external_validation(table: pd.DataFrame) -> dict:
    if table.empty:
        return {
            "rows": 0,
            "patients": 0,
            "with_reference": False,
            "model_vs_obs": _error_metrics(np.array([]), np.array([])),
            "ref_vs_obs": None,
            "model_vs_ref": None,
        }

    obs = table["obs_conc"].to_numpy(dtype=float)
    model = table["model_pred_conc"].to_numpy(dtype=float)
    with_ref = "ref_conc" in table.columns and table["ref_conc"].notna().any()

    ref_vs_obs = None
    model_vs_ref = None
    if with_ref:
        mask = table["ref_conc"].notna().to_numpy(dtype=bool)
        ref = table.loc[mask, "ref_conc"].to_numpy(dtype=float)
        obs_ref = table.loc[mask, "obs_conc"].to_numpy(dtype=float)
        model_ref = table.loc[mask, "model_pred_conc"].to_numpy(dtype=float)
        ref_vs_obs = _error_metrics(obs_ref, ref)
        model_vs_ref = _error_metrics(ref, model_ref)

    by_patient = []
    for patient_id, g in table.groupby("patient_id", sort=True):
        m = _error_metrics(g["obs_conc"].to_numpy(dtype=float), g["model_pred_conc"].to_numpy(dtype=float))
        row = {
            "patient_id": str(patient_id),
            "n_obs": int(g.shape[0]),
            "rmse_model_vs_obs": m["rmse"],
            "mae_model_vs_obs": m["mae"],
        }
        if with_ref and g["ref_conc"].notna().any():
            gm = g[g["ref_conc"].notna()]
            r = _error_metrics(gm["obs_conc"].to_numpy(dtype=float), gm["ref_conc"].to_numpy(dtype=float))
            row["rmse_ref_vs_obs"] = r["rmse"]
            row["mae_ref_vs_obs"] = r["mae"]
        by_patient.append(row)

    return {
        "rows": int(table.shape[0]),
        "patients": int(table["patient_id"].nunique()),
        "with_reference": bool(with_ref),
        "model_vs_obs": _error_metrics(obs, model),
        "ref_vs_obs": ref_vs_obs,
        "model_vs_ref": model_vs_ref,
        "by_patient": by_patient,
    }


def write_external_validation_template_csv(output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = "patient_id,time_h,dose_mg,obs_conc,ref_conc,study_id\n"
    out.write_text(header, encoding="utf-8")
    return str(out)
