import pytest

import opendose_poppk.project_report as report_mod
from opendose_poppk.project_report import build_project_report, render_project_report_markdown


def test_build_project_report_success(tmp_path):
    csv = tmp_path / "drugs.csv"
    csv.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\n"
        "Paracetamol,0.8,1.8,0.28,65,1000,10,1.5\n",
        encoding="utf-8",
    )

    report = build_project_report(dataset=str(csv), drug="Paracetamol")
    assert report["report_ok"] is True
    assert report["dataset_ok"] is True
    assert report["pk_smoke_ok"] is True
    assert report["sensitivity_ok"] is True
    assert report["failures"] == []
    assert report["sensitivity"]["drug"] == "Paracetamol"
    assert len(report["sensitivity"]["results"]) == 4

    md = render_project_report_markdown(report)
    assert "# OpenDose Project Report" in md
    assert "| Parameter | Sensitivity Cmax | Sensitivity AUC |" in md


def test_build_project_report_dataset_failure_renders(tmp_path):
    missing = tmp_path / "missing.csv"
    report = build_project_report(dataset=str(missing), drug="Paracetamol")
    assert report["report_ok"] is False
    assert report["dataset_ok"] is False
    assert report["sensitivity_ok"] is False
    assert any("dataset_validation:" in item for item in report["failures"])

    md = render_project_report_markdown(report)
    assert "Sensitivity section not available." in md


def test_build_project_report_sensitivity_failure(tmp_path):
    csv = tmp_path / "drugs.csv"
    csv.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n"
        "Paracetamol,0.8,1.8,0.28,65,1000\n",
        encoding="utf-8",
    )
    report = build_project_report(dataset=str(csv), drug="Paracetamol", rel_step=1.0)
    assert report["dataset_ok"] is True
    assert report["sensitivity_ok"] is False
    assert any("sensitivity:" in item for item in report["failures"])


def test_build_project_report_pk_smoke_failure(monkeypatch, tmp_path):
    csv = tmp_path / "drugs.csv"
    csv.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n"
        "Paracetamol,0.8,1.8,0.28,65,1000\n",
        encoding="utf-8",
    )

    class _BadPK:
        def __init__(self, *args, **kwargs):
            pass

        def concentration(self, t, D=1000.0):
            raise RuntimeError("pk smoke failed")

    monkeypatch.setattr(report_mod, "PKModel", _BadPK)
    report = build_project_report(dataset=str(csv), drug="Paracetamol")
    assert report["pk_smoke_ok"] is False
    assert any("pk_smoke:" in item for item in report["failures"])
