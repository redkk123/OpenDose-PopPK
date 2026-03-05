import pandas as pd
import pytest

from opendose_poppk.database import DrugDatabase, validate_drug_csv, validate_drug_dataframe


def _write_csv(path, content: str):
    path.write_text(content)


def test_get_drug_and_pk_kwargs(tmp_path):
    csv = tmp_path / "drugs.csv"
    _write_csv(csv, """Drug,F,ka_h,ke_h,Vd_L,EC50_ugmL,n_hill,dose_mg,notes
Paracetamol,0.8,1.8,0.28,65,10,1.5,1000,common
""")

    db = DrugDatabase(str(csv))
    info = db.get_drug("paracetamol")

    assert info.name == "Paracetamol"
    assert info.pk_kwargs == {"F": 0.8, "ka": 1.8, "ke": 0.28, "Vd": 65.0}
    assert info.has_pd is True
    assert isinstance(db.dataframe(), pd.DataFrame)
    assert "Paracetamol" in db.list_drugs()


def test_missing_drug_raises(tmp_path):
    csv = tmp_path / "drugs.csv"
    _write_csv(csv, """Drug,F,ka_h,ke_h,Vd_L,EC50_ugmL,n_hill,dose_mg,notes
Aspirin,1.0,1.0,0.1,10,,,500,old
""")

    db = DrugDatabase(str(csv))
    with pytest.raises(ValueError):
        db.get_drug("Paracetamol")


def test_has_pd_false_when_missing(tmp_path):
    csv = tmp_path / "drugs.csv"
    _write_csv(csv, """Drug,F,ka_h,ke_h,Vd_L,EC50_ugmL,n_hill,dose_mg,notes
NoPD,1.0,1.0,0.1,10,,,100,none
""")

    db = DrugDatabase(str(csv))
    info = db.get_drug("NoPD")
    assert info.has_pd is False


def test_validate_drug_dataframe_success():
    df = pd.DataFrame(
        {
            "Drug": ["A", "B"],
            "F": [0.8, 1.0],
            "ka_h": [1.8, 1.2],
            "ke_h": [0.3, 0.2],
            "Vd_L": [50.0, 60.0],
            "dose_mg": [500, 1000],
            "EC50_ugmL": [10.0, None],
            "n_hill": [1.4, None],
            "notes": ["x", "y"],
        }
    )
    out, summary = validate_drug_dataframe(df)
    assert out.shape[0] == 2
    assert summary["rows"] == 2
    assert summary["drugs"] == 2
    assert summary["pd_complete_rows"] == 1
    assert summary["pd_partial_rows"] == 0
    assert "notes" in summary["optional_columns_present"]


def test_validate_drug_csv_and_validation_errors(tmp_path):
    csv_ok = tmp_path / "ok.csv"
    _write_csv(
        csv_ok,
        """Drug,F,ka_h,ke_h,Vd_L,dose_mg
Paracetamol,0.8,1.8,0.28,65,1000
""",
    )
    out, summary = validate_drug_csv(str(csv_ok))
    assert out.shape[0] == 1
    assert summary["drugs"] == 1

    csv_missing = tmp_path / "missing.csv"
    _write_csv(csv_missing, "Drug,F,ka_h,ke_h,Vd_L\nA,1,1,0.1,10\n")
    with pytest.raises(ValueError, match="Missing required drug columns"):
        validate_drug_csv(str(csv_missing))

    csv_dup = tmp_path / "dup.csv"
    _write_csv(csv_dup, "Drug,F,ka_h,ke_h,Vd_L,dose_mg\nA,1,1,0.1,10,100\nA,1,1,0.1,11,100\n")
    with pytest.raises(ValueError, match="duplicate drug names"):
        validate_drug_csv(str(csv_dup))

    csv_bad_positive = tmp_path / "bad_positive.csv"
    _write_csv(csv_bad_positive, "Drug,F,ka_h,ke_h,Vd_L,dose_mg\nA,0,1,0.1,10,100\n")
    with pytest.raises(ValueError, match="column 'F' must be positive"):
        validate_drug_csv(str(csv_bad_positive))

    csv_empty = tmp_path / "empty.csv"
    _write_csv(csv_empty, "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n")
    with pytest.raises(ValueError, match="drug dataset has no rows"):
        validate_drug_csv(str(csv_empty))

    csv_empty_drug = tmp_path / "empty_drug.csv"
    _write_csv(csv_empty_drug, "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n,1,1,0.1,10,100\n")
    with pytest.raises(ValueError, match="column 'Drug' contains empty values"):
        validate_drug_csv(str(csv_empty_drug))

    csv_non_numeric = tmp_path / "non_numeric.csv"
    _write_csv(csv_non_numeric, "Drug,F,ka_h,ke_h,Vd_L,dose_mg\nA,abc,1,0.1,10,100\n")
    with pytest.raises(ValueError, match="missing/non-numeric values"):
        validate_drug_csv(str(csv_non_numeric))

    csv_pd_partial = tmp_path / "pd_partial.csv"
    _write_csv(
        csv_pd_partial,
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\nA,1,1,0.1,10,100,10,\n",
    )
    with pytest.raises(ValueError, match="PD columns must be both filled or both empty"):
        validate_drug_csv(str(csv_pd_partial))

    csv_ec50_bad = tmp_path / "pd_ec50_bad.csv"
    _write_csv(
        csv_ec50_bad,
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\nA,1,1,0.1,10,100,0,1.5\n",
    )
    with pytest.raises(ValueError, match="column 'EC50_ugmL' must be positive"):
        validate_drug_csv(str(csv_ec50_bad))

    csv_nhill_bad = tmp_path / "pd_nhill_bad.csv"
    _write_csv(
        csv_nhill_bad,
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\nA,1,1,0.1,10,100,10,0\n",
    )
    with pytest.raises(ValueError, match="column 'n_hill' must be positive"):
        validate_drug_csv(str(csv_nhill_bad))
