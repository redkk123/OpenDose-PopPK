from pathlib import Path

import pandas as pd
import pytest

from opendose_poppk import load_tdm_csv, summarize_tdm


def test_load_tdm_csv_and_summary(tmp_path):
    csv_path = tmp_path / "tdm.csv"
    csv_path.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,1.0,4.2,1000\n"
        "P1,2.0,6.8,1000\n"
        "P2,1.5,5.1,750\n",
        encoding="utf-8",
    )

    df = load_tdm_csv(csv_path)
    summary = summarize_tdm(df)

    assert df.shape[0] == 3
    assert summary["rows"] == 3
    assert summary["patients"] == 2
    assert summary["time_min_h"] == 1.0
    assert summary["time_max_h"] == 2.0


def test_load_tdm_csv_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("patient_id,time_h,conc\nP1,1,2.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required TDM columns"):
        load_tdm_csv(csv_path)


def test_load_tdm_csv_rejects_invalid_ranges(tmp_path):
    csv_path = tmp_path / "bad_ranges.csv"
    csv_path.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,-1.0,2.0,1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="time_h must be non-negative"):
        load_tdm_csv(csv_path)

    csv_path.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,1.0,-2.0,1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conc must be non-negative"):
        load_tdm_csv(csv_path)

    csv_path.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,1.0,2.0,0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dose_mg must be positive"):
        load_tdm_csv(csv_path)


def test_summarize_tdm_empty():
    df = pd.DataFrame(columns=["patient_id", "time_h", "conc", "dose_mg"])
    summary = summarize_tdm(df)
    assert summary["rows"] == 0
    assert summary["patients"] == 0
    assert summary["time_min_h"] is None
