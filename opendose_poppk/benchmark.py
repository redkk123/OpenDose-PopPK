from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .database import DrugDatabase
from .pk_model import PKModel
from .regimen import simulate_regimen


def _parse_drug_list(drugs: str | None) -> list[str] | None:
    if drugs is None:
        return None
    names = [d.strip() for d in drugs.split(",") if d.strip()]
    return names or None


def benchmark_regimen_across_drugs(
    dataset: str,
    drugs: str | None = None,
    interval_h: float = 12.0,
    n_doses: int = 4,
    t_end: float | None = None,
    n_points: int = 400,
    dose_override: float | None = None,
) -> pd.DataFrame:
    """
    Compare repeated-dose regimen metrics across selected drugs.
    """
    db = DrugDatabase(dataset)
    selected = _parse_drug_list(drugs) or db.list_drugs()

    rows = []
    for name in selected:
        drug = db.get_drug(name)
        dose = float(dose_override) if dose_override is not None else float(drug.dose)
        pk = PKModel(**drug.pk_kwargs)
        res = simulate_regimen(
            pk=pk,
            dose=dose,
            interval_h=interval_h,
            n_doses=n_doses,
            t_end=t_end,
            n_points=n_points,
        )
        auc = float(np.trapezoid(res["conc"], res["t"]))
        rows.append(
            {
                "drug": str(drug.name),
                "dose": dose,
                "interval_h": float(interval_h),
                "n_doses": int(n_doses),
                "cmax": float(res["cmax"]),
                "trough_last": float(res["trough_last"]),
                "auc_0_tend": auc,
            }
        )

    df = pd.DataFrame(rows).sort_values("cmax", ascending=False).reset_index(drop=True)
    return df


def write_benchmark_csv(df: pd.DataFrame, output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return str(out)
