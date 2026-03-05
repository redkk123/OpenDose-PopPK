import pandas as pd

from opendose_poppk import build_tdm_fit_markdown_report, write_tdm_fit_markdown_report


def test_build_tdm_fit_markdown_report_with_rows():
    fit_df = pd.DataFrame(
        {
            "patient_id": ["P1"],
            "n_obs": [3],
            "dose_mg": [1000.0],
            "converged": [True],
            "obj_value": [12.3],
            "map_ke": [0.12],
            "map_Vd": [65.0],
        }
    )
    md = build_tdm_fit_markdown_report(fit_df, drug_name="Paracetamol")
    assert "# TDM MAP Fit Report - Paracetamol" in md
    assert "| P1 | 3 | 1000.0 | Yes |" in md


def test_build_tdm_fit_markdown_report_empty():
    fit_df = pd.DataFrame(columns=["patient_id", "n_obs", "dose_mg", "converged", "obj_value", "map_ke", "map_Vd"])
    md = build_tdm_fit_markdown_report(fit_df, drug_name="Paracetamol")
    assert "No patient rows were available." in md


def test_write_tdm_fit_markdown_report(tmp_path):
    fit_df = pd.DataFrame(
        {
            "patient_id": ["P1"],
            "n_obs": [2],
            "dose_mg": [500.0],
            "converged": [False],
            "obj_value": [20.1],
            "map_ke": [0.09],
            "map_Vd": [70.0],
        }
    )
    out = tmp_path / "report.md"
    path = write_tdm_fit_markdown_report(fit_df, drug_name="DrugX", output_path=out)
    assert out.exists()
    assert str(out) == path
    assert "TDM MAP Fit Report - DrugX" in out.read_text(encoding="utf-8")
