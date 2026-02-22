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
