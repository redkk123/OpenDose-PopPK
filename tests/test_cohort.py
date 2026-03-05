import pandas as pd
import pytest

from opendose_poppk import PKModel, load_cohort_csv, simulate_cohort, summarize_cohort


def test_load_cohort_csv_success_and_normalization(tmp_path):
    csv = tmp_path / "cohort.csv"
    csv.write_text(
        "patient_id,sex,weight,crcl,age,dose\n"
        "P1,f,80,70,55,900\n"
        "P2,,65,90,40,\n",
        encoding="utf-8",
    )
    df = load_cohort_csv(str(csv))
    assert df.shape[0] == 2
    assert df.loc[0, "sex"] == "F"
    assert pd.isna(df.loc[1, "sex"]) or df.loc[1, "sex"] == ""
    assert float(df.loc[0, "weight"]) == 80.0
    assert float(df.loc[0, "dose"]) == 900.0


def test_load_cohort_csv_validation_errors(tmp_path):
    csv_missing = tmp_path / "missing.csv"
    csv_missing.write_text("id,sex\n1,M\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required cohort columns"):
        load_cohort_csv(str(csv_missing))

    csv_empty = tmp_path / "empty.csv"
    csv_empty.write_text("patient_id,sex\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cohort dataset has no rows"):
        load_cohort_csv(str(csv_empty))

    csv_empty_pid = tmp_path / "empty_pid.csv"
    csv_empty_pid.write_text("patient_id,sex\n,M\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column 'patient_id' contains empty values"):
        load_cohort_csv(str(csv_empty_pid))

    csv_bad_weight = tmp_path / "bad_weight.csv"
    csv_bad_weight.write_text("patient_id,weight\nP1,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column 'weight' must be positive"):
        load_cohort_csv(str(csv_bad_weight))

    csv_bad_sex = tmp_path / "bad_sex.csv"
    csv_bad_sex.write_text("patient_id,sex\nP1,X\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column 'sex' has invalid values"):
        load_cohort_csv(str(csv_bad_sex))


def test_simulate_cohort_no_iiv_and_iiv_seeded():
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2"],
            "sex": ["M", "F"],
            "weight": [80.0, 65.0],
            "crcl": [70.0, 90.0],
            "age": [55.0, 40.0],
            "dose": [900.0, 1000.0],
        }
    )
    pk_template = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)

    out_a = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=False, seed=1)
    out_b = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=False, seed=99)
    assert out_a[["F", "ka", "ke", "Vd", "cmax", "auc"]].equals(out_b[["F", "ka", "ke", "Vd", "cmax", "auc"]])

    out_c = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=True, seed=42)
    out_d = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=True, seed=42)
    assert out_c[["F", "ka", "ke", "Vd", "cmax", "auc"]].equals(out_d[["F", "ka", "ke", "Vd", "cmax", "auc"]])

    out_e = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=True, seed=7)
    assert not out_c[["F", "ka", "ke", "Vd"]].equals(out_e[["F", "ka", "ke", "Vd"]])


def test_simulate_cohort_validation_and_summary():
    df = pd.DataFrame({"patient_id": ["P1"]})
    pk_template = PKModel()
    with pytest.raises(ValueError, match="default_dose must be positive"):
        simulate_cohort(df, pk_template=pk_template, default_dose=0.0)
    with pytest.raises(ValueError, match="t_end must be positive"):
        simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, t_end=0.0)
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, n_points=1)

    out = simulate_cohort(df, pk_template=pk_template, default_dose=1000.0, include_iiv=False)
    summary = summarize_cohort(out)
    assert summary["patients"] == 1
    assert summary["cmax_mean"] > 0
    assert summary["auc_mean"] > 0

    df_nan_sex = pd.DataFrame({"patient_id": ["P2"], "sex": ["nan"]})
    out_nan_sex = simulate_cohort(df_nan_sex, pk_template=pk_template, default_dose=1000.0, include_iiv=False)
    assert out_nan_sex.loc[0, "sex"] == "M"
