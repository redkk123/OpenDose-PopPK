from __future__ import annotations

import numpy as np
import pandas as pd

from .covariate import CovariateModel
from .pk_model import PKModel

REQUIRED_COHORT_COLUMNS = ("patient_id",)
OPTIONAL_COHORT_COLUMNS = ("sex", "weight", "crcl", "age", "dose")


def load_cohort_csv(path: str) -> pd.DataFrame:
    """
    Load and validate cohort CSV for patient-level simulation.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in REQUIRED_COHORT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required cohort columns: {missing}")
    if df.shape[0] == 0:
        raise ValueError("cohort dataset has no rows")

    patient_raw = df["patient_id"]
    df["patient_id"] = patient_raw.astype(str).str.strip()
    empty_patient = patient_raw.isna() | (df["patient_id"] == "") | (df["patient_id"].str.lower() == "nan")
    if empty_patient.any():
        raise ValueError("column 'patient_id' contains empty values")

    for col in ("weight", "crcl", "age", "dose"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            bad = df[col].notna() & (df[col] <= 0)
            if bad.any():
                bad_rows = (bad[bad].index + 2).tolist()
                raise ValueError(f"column '{col}' must be positive at CSV rows {bad_rows}")

    if "sex" in df.columns:
        sex_norm = df["sex"].astype(str).str.strip().str.upper()
        sex_norm = sex_norm.where(df["sex"].notna(), "")
        invalid = (~sex_norm.isin(["", "M", "F"]))
        if invalid.any():
            bad_rows = (invalid[invalid].index + 2).tolist()
            raise ValueError(f"column 'sex' has invalid values at CSV rows {bad_rows}; allowed: M, F")
        df["sex"] = sex_norm

    return df


def simulate_cohort(
    df: pd.DataFrame,
    pk_template: PKModel,
    default_dose: float,
    t_end: float = 24.0,
    n_points: int = 400,
    include_iiv: bool = False,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate patient-level Cmax/AUC for a cohort table.
    """
    if default_dose <= 0:
        raise ValueError("default_dose must be positive")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")

    omega = None if include_iiv else {"Vd": 0.0, "ke": 0.0, "ka": 0.0, "F": 0.0}
    cov_model = CovariateModel(pk_template, omega=omega)
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, float(t_end), int(n_points))

    rows = []
    for row in df.to_dict(orient="records"):
        covariates = {}
        for col in ("weight", "crcl", "age"):
            val = row.get(col, None)
            if val is not None and not pd.isna(val):
                covariates[col] = float(val)

        sex = row.get("sex", "")
        if sex in (None, "") or (isinstance(sex, float) and pd.isna(sex)):
            sex = "M"
        else:
            sex = str(sex).strip().upper()
            if sex == "NAN":
                sex = "M"

        dose_raw = row.get("dose", None)
        dose = float(default_dose) if dose_raw is None or pd.isna(dose_raw) else float(dose_raw)

        params = cov_model.individualize(covariates, sex=sex, rng=rng)
        pk = PKModel(**params)
        c = pk.concentration(t, D=dose)

        rows.append(
            {
                "patient_id": str(row["patient_id"]),
                "sex": sex,
                "dose": dose,
                "F": float(params["F"]),
                "ka": float(params["ka"]),
                "ke": float(params["ke"]),
                "Vd": float(params["Vd"]),
                "cmax": float(np.max(c)),
                "auc": float(pk.auc(D=dose)),
            }
        )

    return pd.DataFrame(rows)


def summarize_cohort(df: pd.DataFrame) -> dict:
    """
    Summarize cohort simulation output table.
    """
    return {
        "patients": int(df.shape[0]),
        "cmax_mean": float(df["cmax"].mean()),
        "cmax_p50": float(df["cmax"].median()),
        "auc_mean": float(df["auc"].mean()),
        "auc_p50": float(df["auc"].median()),
    }
