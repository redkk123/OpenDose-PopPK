import pandas as pd
import pytest

from opendose_poppk.database import DrugDatabase


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
