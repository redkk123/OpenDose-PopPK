import opendose_poppk.benchmark as benchmark_mod
from opendose_poppk import benchmark_regimen_across_drugs, write_benchmark_csv


def test_parse_drug_list_helper():
    assert benchmark_mod._parse_drug_list(None) is None
    assert benchmark_mod._parse_drug_list("") is None
    assert benchmark_mod._parse_drug_list(" Paracetamol , Ibuprofen ") == ["Paracetamol", "Ibuprofen"]


def test_benchmark_regimen_default_and_override():
    df = benchmark_regimen_across_drugs(
        dataset="datasets/drugs_parameters.csv",
        drugs=None,
        interval_h=12.0,
        n_doses=3,
        n_points=150,
        dose_override=500.0,
    )
    assert df.shape[0] >= 1
    assert {"drug", "cmax", "trough_last", "auc_0_tend"}.issubset(set(df.columns))
    assert (df["dose"] == 500.0).all()


def test_benchmark_regimen_selected_and_write_csv(tmp_path):
    df = benchmark_regimen_across_drugs(
        dataset="datasets/drugs_parameters.csv",
        drugs="Paracetamol,Ibuprofen",
        interval_h=8.0,
        n_doses=4,
        t_end=36.0,
        n_points=120,
    )
    assert set(df["drug"]) == {"Paracetamol", "Ibuprofen"}
    out = tmp_path / "benchmark.csv"
    path = write_benchmark_csv(df, out)
    assert out.exists()
    assert str(out) == path
