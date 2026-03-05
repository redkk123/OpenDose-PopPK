from pathlib import Path

import pandas as pd
import pytest

import opendose_poppk.tdm as tdm_mod
from opendose_poppk import load_tdm_csv, summarize_tdm, write_tdm_template_csv


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


def test_load_tdm_csv_aliases_and_unit_columns(tmp_path):
    csv_path = tmp_path / "tdm_units.csv"
    csv_path.write_text(
        "patient,time,concentration,dose,time_unit,conc_unit,dose_unit,gender\n"
        "P1,60,4200,1,min,ng/mL,g,M\n"
        "P2,2,5,750,h,mg/L,mg,F\n",
        encoding="utf-8",
    )

    df = load_tdm_csv(csv_path)
    assert list(df.columns[:4]) == ["patient_id", "time_h", "conc", "dose_mg"]
    assert df.shape[0] == 2
    assert df.loc[0, "time_h"] == pytest.approx(1.0)
    assert df.loc[0, "conc"] == pytest.approx(4.2)
    assert df.loc[0, "dose_mg"] == pytest.approx(1000.0)
    assert df.loc[1, "time_h"] == pytest.approx(2.0)
    assert df.loc[1, "conc"] == pytest.approx(5.0)
    assert df.loc[1, "dose_mg"] == pytest.approx(750.0)
    assert df.loc[0, "sex"] == "M"
    assert df.loc[1, "sex"] == "F"


def test_load_tdm_csv_inline_units(tmp_path):
    csv_path = tmp_path / "tdm_inline_units.csv"
    csv_path.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,90 min,2500 ng/mL,0.5 g\n"
        "P1,2 h,5 mg/L,750 mg\n",
        encoding="utf-8",
    )

    df = load_tdm_csv(csv_path)
    assert df.shape[0] == 2
    assert df.loc[0, "time_h"] == pytest.approx(1.5)
    assert df.loc[0, "conc"] == pytest.approx(2.5)
    assert df.loc[0, "dose_mg"] == pytest.approx(500.0)
    assert df.loc[1, "time_h"] == pytest.approx(2.0)
    assert df.loc[1, "conc"] == pytest.approx(5.0)
    assert df.loc[1, "dose_mg"] == pytest.approx(750.0)


def test_load_tdm_csv_default_unit_overrides(tmp_path):
    csv_path = tmp_path / "tdm_default_units.csv"
    csv_path.write_text(
        "patient,time,conc,dose\n"
        "P1,90,2500,0.5\n",
        encoding="utf-8",
    )

    df = load_tdm_csv(
        csv_path,
        time_unit="min",
        conc_unit="ng/mL",
        dose_unit="g",
    )
    assert df.shape[0] == 1
    assert df.loc[0, "time_h"] == pytest.approx(1.5)
    assert df.loc[0, "conc"] == pytest.approx(2.5)
    assert df.loc[0, "dose_mg"] == pytest.approx(500.0)


def test_load_tdm_csv_rejects_unknown_units(tmp_path):
    csv_path = tmp_path / "tdm_bad_units.csv"
    csv_path.write_text(
        "patient,time,concentration,dose,time_unit,conc_unit,dose_unit\n"
        "P1,1,2,100,weeks,ug/mL,mg\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported time unit"):
        load_tdm_csv(csv_path)


def test_tdm_internal_parser_edges():
    assert tdm_mod._normalize_unit_token(None) is None
    assert tdm_mod._normalize_unit_token("") is None
    assert tdm_mod._normalize_unit_token("nan") is None

    v_nan, u_nan = tdm_mod._parse_value_and_unit(float("nan"))
    assert pd.isna(v_nan)
    assert u_nan is None

    v_empty, u_empty = tdm_mod._parse_value_and_unit("")
    assert pd.isna(v_empty)
    assert u_empty is None

    v_bad, u_bad = tdm_mod._parse_value_and_unit("abc")
    assert pd.isna(v_bad)
    assert u_bad is None

    converted = tdm_mod._convert_series_to_canonical(
        pd.Series([float("nan"), 120.0]),
        unit_values=None,
        default_unit="min",
        factors={"min": 1.0 / 60.0},
        field_name="time",
    )
    assert pd.isna(converted.iloc[0])
    assert converted.iloc[1] == pytest.approx(2.0)


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


def test_write_tdm_template_csv(tmp_path):
    out = tmp_path / "template.csv"
    path = write_tdm_template_csv(out)
    assert str(out) == path
    text = out.read_text(encoding="utf-8")
    assert text.strip() == "patient_id,time_h,conc,dose_mg,weight,crcl,age"


def test_write_tdm_template_csv_clinical(tmp_path):
    out = tmp_path / "template_clinical.csv"
    path = write_tdm_template_csv(out, template_format="clinical")
    assert str(out) == path
    text = out.read_text(encoding="utf-8")
    assert text.strip() == "patient_id,time,time_unit,conc,conc_unit,dose,dose_unit,weight,crcl,age,sex,drug,notes"


def test_write_tdm_template_csv_invalid_format(tmp_path):
    out = tmp_path / "template_invalid.csv"
    with pytest.raises(ValueError, match="template_format must be either"):
        write_tdm_template_csv(out, template_format="invalid")
