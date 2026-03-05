"""
opendose_poppk.database
=======================
Drug database management for OpenDose-PopPK.

Classes
-------
DrugDatabase  : Load and retrieve drug parameters from CSV
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_DRUG_COLUMNS = ("Drug", "F", "ka_h", "ke_h", "Vd_L", "dose_mg")
OPTIONAL_DRUG_COLUMNS = ("EC50_ugmL", "n_hill", "notes")


def validate_drug_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Validate and normalize drug-parameter dataset.
    """
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    missing = [c for c in REQUIRED_DRUG_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required drug columns: {missing}")
    if out.shape[0] == 0:
        raise ValueError("drug dataset has no rows")

    drug_raw = out["Drug"]
    out["Drug"] = drug_raw.astype(str).str.strip()
    empty_drug = drug_raw.isna() | (out["Drug"] == "") | (out["Drug"].str.lower() == "nan")
    if empty_drug.any():
        raise ValueError("column 'Drug' contains empty values")

    lowered = out["Drug"].str.lower()
    dup_names = sorted(out.loc[lowered.duplicated(keep=False), "Drug"].unique().tolist())
    if dup_names:
        raise ValueError(f"duplicate drug names found: {dup_names}")

    required_numeric = ["F", "ka_h", "ke_h", "Vd_L", "dose_mg"]
    for col in required_numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        bad = out[col].isna()
        if bad.any():
            bad_rows = (bad[bad].index + 2).tolist()  # +2 for header + 1-based row indexing
            raise ValueError(f"column '{col}' has missing/non-numeric values at CSV rows {bad_rows}")
        non_pos = out[col] <= 0
        if non_pos.any():
            bad_rows = (non_pos[non_pos].index + 2).tolist()
            raise ValueError(f"column '{col}' must be positive at CSV rows {bad_rows}")

    pd_complete_rows = 0
    pd_partial_rows = 0
    for col in ("EC50_ugmL", "n_hill"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "EC50_ugmL" in out.columns and "n_hill" in out.columns:
        has_ec50 = out["EC50_ugmL"].notna()
        has_nhill = out["n_hill"].notna()
        partial = has_ec50 ^ has_nhill
        if partial.any():
            bad_rows = (partial[partial].index + 2).tolist()
            raise ValueError(f"PD columns must be both filled or both empty at CSV rows {bad_rows}")

        ec50_non_pos = has_ec50 & (out["EC50_ugmL"] <= 0)
        if ec50_non_pos.any():
            bad_rows = (ec50_non_pos[ec50_non_pos].index + 2).tolist()
            raise ValueError(f"column 'EC50_ugmL' must be positive at CSV rows {bad_rows}")

        nhill_non_pos = has_nhill & (out["n_hill"] <= 0)
        if nhill_non_pos.any():
            bad_rows = (nhill_non_pos[nhill_non_pos].index + 2).tolist()
            raise ValueError(f"column 'n_hill' must be positive at CSV rows {bad_rows}")

        pd_complete_rows = int((has_ec50 & has_nhill).sum())
        pd_partial_rows = int(partial.sum())

    summary = {
        "rows": int(out.shape[0]),
        "drugs": int(out["Drug"].nunique()),
        "required_columns": list(REQUIRED_DRUG_COLUMNS),
        "optional_columns_present": [c for c in OPTIONAL_DRUG_COLUMNS if c in out.columns],
        "pd_complete_rows": int(pd_complete_rows),
        "pd_partial_rows": int(pd_partial_rows),
    }
    return out, summary


def validate_drug_csv(csv_path: str) -> tuple[pd.DataFrame, dict]:
    """
    Load, validate and normalize a drug-parameter CSV.
    """
    df = pd.read_csv(csv_path)
    return validate_drug_dataframe(df)


class DrugDatabase:
    """
    Load and provide pharmacological parameters from a CSV file.

    Expected CSV columns
    --------------------
    Drug, F, ka_h, ke_h, Vd_L, EC50_ugmL, n_hill, dose_mg, notes

    Example
    -------
    >>> db   = DrugDatabase("datasets/drugs_parameters.csv")
    >>> info = db.get_drug("Paracetamol")
    >>> pk   = PKModel(**info.pk_kwargs)
    """

    def __init__(self, csv_path: str):
        self._df = pd.read_csv(csv_path)
        self._df.columns = [c.strip() for c in self._df.columns]

    def get_drug(self, name: str) -> _DrugInfo:
        """Get drug parameters by name."""
        row = self._df[self._df["Drug"].str.lower() == name.lower()]
        if row.empty:
            raise ValueError(
                f"Drug '{name}' not found. "
                f"Available: {self.list_drugs()}"
            )
        return _DrugInfo(row.iloc[0])

    def list_drugs(self) -> list[str]:
        """Return list of available drugs."""
        return list(self._df["Drug"])

    def dataframe(self) -> pd.DataFrame:
        """Return a copy of the drugs dataframe."""
        return self._df.copy()


class _DrugInfo:
    """Container returned by DrugDatabase.get_drug()."""

    def __init__(self, row: pd.Series):
        self.name    = str(row["Drug"])
        self.F       = float(row["F"])
        self.ka      = float(row["ka_h"])
        self.ke      = float(row["ke_h"])
        self.Vd      = float(row["Vd_L"])
        self.dose    = float(row["dose_mg"])
        self.EC50    = None if pd.isna(row.get("EC50_ugmL", np.nan)) \
                       else float(row["EC50_ugmL"])
        self.n_hill  = None if pd.isna(row.get("n_hill", np.nan)) \
                       else float(row["n_hill"])
        self.notes   = str(row.get("notes", ""))

    @property
    def pk_kwargs(self) -> dict:
        """Return arguments for PKModel initialization."""
        return {"F": self.F, "ka": self.ka, "ke": self.ke, "Vd": self.Vd}

    @property
    def has_pd(self) -> bool:
        """Check if PD parameters are available."""
        return self.EC50 is not None and self.n_hill is not None

    def __repr__(self) -> str:
        return (f"DrugInfo({self.name}: F={self.F}, ka={self.ka}, "
                f"ke={self.ke}, Vd={self.Vd})")
