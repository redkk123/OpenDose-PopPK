from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

REQUIRED_TDM_COLUMNS = ("patient_id", "time_h", "conc", "dose_mg")

_COLUMN_ALIASES = {
    "patient_id": ("patient_id", "patient", "patientid", "subject_id", "subject", "id"),
    "time_h": ("time_h", "time", "time_hr", "time_hours", "sampling_time_h", "sampling_time"),
    "conc": ("conc", "concentration", "conc_value", "concentration_value", "obs_conc"),
    "dose_mg": ("dose_mg", "dose", "dose_amount", "dose_amt", "amt", "dose_value"),
    "time_unit": ("time_unit", "time_units"),
    "conc_unit": ("conc_unit", "conc_units", "concentration_unit", "concentration_units"),
    "dose_unit": ("dose_unit", "dose_units"),
    "weight": ("weight", "weight_kg", "wt"),
    "crcl": ("crcl", "creatinine_clearance", "creatinine_clearance_ml_min"),
    "age": ("age", "age_years"),
    "sex": ("sex", "gender"),
    "drug": ("drug", "compound", "medication"),
}

_TIME_TO_H = {
    "h": 1.0,
    "min": 1.0 / 60.0,
    "day": 24.0,
}

_CONC_TO_UG_ML = {
    "ug/ml": 1.0,
    "mg/l": 1.0,
    "ng/ml": 1e-3,
    "mg/ml": 1e3,
    "ug/l": 1e-3,
    "g/l": 1e3,
}

_DOSE_TO_MG = {
    "mg": 1.0,
    "g": 1e3,
    "ug": 1e-3,
    "ng": 1e-6,
}

_VALUE_WITH_UNIT_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-zuUµμ/_]+)?\s*$"
)


def _normalize_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.strip().lower())


def _normalize_unit_token(unit: str | None) -> str | None:
    if unit is None:
        return None
    token = str(unit).strip().lower()
    if token == "" or token in {"nan", "none"}:
        return None

    token = token.replace("μ", "u").replace("µ", "u")
    token = token.replace(" ", "")
    token = token.replace("mcg", "ug")
    token = token.replace("hours", "h").replace("hour", "h").replace("hrs", "h").replace("hr", "h")
    token = token.replace("minutes", "min").replace("minute", "min").replace("mins", "min")
    token = token.replace("days", "day")
    token = token.replace("\\", "/")

    if token in {"h", "min", "day", "mg", "g", "ug", "ng", "ug/ml", "mg/l", "ng/ml", "mg/ml", "ug/l", "g/l"}:
        return token
    return token


def _parse_value_and_unit(value) -> tuple[float, str | None]:
    if pd.isna(value):
        return float("nan"), None
    if isinstance(value, (int, float)):
        return float(value), None

    text = str(value).strip()
    if text == "":
        return float("nan"), None

    normalized = text.replace(",", ".") if "," in text and "." not in text else text
    try:
        return float(normalized), None
    except ValueError:
        pass

    match = _VALUE_WITH_UNIT_RE.match(normalized)
    if match is None:
        return float("nan"), None

    number = float(match.group(1))
    unit = _normalize_unit_token(match.group(2))
    return number, unit


def _find_column(lookup: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        key = _normalize_column_name(alias)
        if key in lookup:
            return lookup[key]
    return None


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    lookup = {_normalize_column_name(col): col for col in df.columns}
    mapped: dict[str, str] = {}
    for canonical_name, aliases in _COLUMN_ALIASES.items():
        col = _find_column(lookup, aliases)
        if col is not None:
            mapped[canonical_name] = col
    return mapped


def _convert_series_to_canonical(
    raw_values: pd.Series,
    *,
    unit_values: pd.Series | None,
    default_unit: str,
    factors: dict[str, float],
    field_name: str,
) -> pd.Series:
    converted = []
    fallback_unit = _normalize_unit_token(default_unit)
    for idx, raw in raw_values.items():
        value, inline_unit = _parse_value_and_unit(raw)
        if pd.isna(value):
            converted.append(float("nan"))
            continue

        explicit_unit = None
        if unit_values is not None:
            explicit_unit = _normalize_unit_token(unit_values.loc[idx])

        unit = explicit_unit or inline_unit or fallback_unit
        if unit not in factors:
            raise ValueError(f"Unsupported {field_name} unit: {unit}")
        converted.append(float(value) * factors[unit])

    return pd.Series(converted, index=raw_values.index, dtype=float)


def load_tdm_csv(
    csv_path: str | Path,
    dropna: bool = True,
    time_unit: str = "h",
    conc_unit: str = "ug/mL",
    dose_unit: str = "mg",
) -> pd.DataFrame:
    """
    Load and validate TDM observations from CSV.

    Required columns:
    - patient_id
    - time_h
    - conc
    - dose_mg
    """
    raw_df = pd.read_csv(csv_path)
    raw_df.columns = [c.strip() for c in raw_df.columns]

    mapped = _map_columns(raw_df)
    missing = [c for c in REQUIRED_TDM_COLUMNS if c not in mapped]
    if missing:
        raise ValueError(f"Missing required TDM columns: {missing}")

    df = pd.DataFrame(index=raw_df.index)
    df["patient_id"] = raw_df[mapped["patient_id"]].astype(str).str.strip()
    missing_pid = df["patient_id"].str.lower().isin({"", "nan", "none"})
    df.loc[missing_pid, "patient_id"] = pd.NA

    time_units = raw_df[mapped["time_unit"]] if "time_unit" in mapped else None
    conc_units = raw_df[mapped["conc_unit"]] if "conc_unit" in mapped else None
    dose_units = raw_df[mapped["dose_unit"]] if "dose_unit" in mapped else None

    df["time_h"] = _convert_series_to_canonical(
        raw_df[mapped["time_h"]],
        unit_values=time_units,
        default_unit=time_unit,
        factors=_TIME_TO_H,
        field_name="time",
    )
    df["conc"] = _convert_series_to_canonical(
        raw_df[mapped["conc"]],
        unit_values=conc_units,
        default_unit=conc_unit,
        factors=_CONC_TO_UG_ML,
        field_name="concentration",
    )
    df["dose_mg"] = _convert_series_to_canonical(
        raw_df[mapped["dose_mg"]],
        unit_values=dose_units,
        default_unit=dose_unit,
        factors=_DOSE_TO_MG,
        field_name="dose",
    )

    for cov_col in ("weight", "crcl", "age"):
        if cov_col in mapped:
            df[cov_col] = pd.to_numeric(raw_df[mapped[cov_col]], errors="coerce")

    if "sex" in mapped:
        df["sex"] = raw_df[mapped["sex"]].astype(str).str.strip()
    if "drug" in mapped:
        df["drug"] = raw_df[mapped["drug"]].astype(str).str.strip()

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
            "time_unit": "h",
            "conc_unit": "ug/mL",
            "dose_unit": "mg",
        }
    return {
        "rows": int(df.shape[0]),
        "patients": int(df["patient_id"].nunique()),
        "time_min_h": float(df["time_h"].min()),
        "time_max_h": float(df["time_h"].max()),
        "conc_min": float(df["conc"].min()),
        "conc_max": float(df["conc"].max()),
        "time_unit": "h",
        "conc_unit": "ug/mL",
        "dose_unit": "mg",
    }


def write_tdm_template_csv(output_path: str | Path, template_format: str = "basic") -> str:
    """
    Write an empty TDM CSV template with required and optional columns.
    """
    if template_format not in {"basic", "clinical"}:
        raise ValueError("template_format must be either 'basic' or 'clinical'")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if template_format == "clinical":
        header = "patient_id,time,time_unit,conc,conc_unit,dose,dose_unit,weight,crcl,age,sex,drug,notes\n"
    else:
        header = "patient_id,time_h,conc,dose_mg,weight,crcl,age\n"
    out.write_text(header, encoding="utf-8")
    return str(out)
