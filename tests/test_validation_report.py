import pytest

from opendose_poppk.validation_report import build_validation_report, render_validation_report_markdown


def test_validation_report_success(tmp_path):
    dataset = tmp_path / "drugs.csv"
    dataset.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\n"
        "Paracetamol,0.8,1.8,0.28,65,1000,10,1.5\n",
        encoding="utf-8",
    )

    report = build_validation_report(
        dataset=str(dataset),
        drug="Paracetamol",
        n_subjects=30,
        t_end=12.0,
        n_points=120,
        seed=7,
    )
    assert report["report_ok"] is True
    assert report["dataset_summary"]["rows"] == 1
    assert report["internal"] is not None
    assert report["internal"]["population"]["n_subjects"] == 30
    assert report["external"] is None
    assert report["failures"] == []

    md = render_validation_report_markdown(report)
    assert "# OpenDose Validation Report" in md
    assert "## Protocol" in md
    assert "## Limitations" in md


def test_validation_report_with_external(tmp_path):
    dataset = tmp_path / "drugs.csv"
    external = tmp_path / "external.csv"
    dataset.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n"
        "Paracetamol,0.8,1.8,0.28,65,1000\n",
        encoding="utf-8",
    )
    external.write_text(
        "patient_id,time_h,dose_mg,obs_conc,ref_conc,study_id\n"
        "P1,1.0,1000,4.2,4.1,StudyA\n"
        "P1,2.0,1000,6.8,6.5,StudyA\n",
        encoding="utf-8",
    )

    report = build_validation_report(
        dataset=str(dataset),
        drug="Paracetamol",
        external_input=str(external),
        n_subjects=20,
        n_points=80,
    )
    assert report["report_ok"] is True
    assert report["external"] is not None
    assert report["external"]["with_reference"] is True
    md = render_validation_report_markdown(report)
    assert "Model vs Obs RMSE" in md


def test_validation_report_failure_paths(tmp_path):
    missing = tmp_path / "missing.csv"
    external = tmp_path / "external.csv"
    external.write_text(
        "patient_id,time_h,dose_mg,obs_conc,ref_conc,study_id\n"
        "P1,1.0,1000,4.2,4.1,StudyA\n",
        encoding="utf-8",
    )
    report = build_validation_report(
        dataset=str(missing),
        drug="Paracetamol",
        external_input=str(external),
    )
    assert report["report_ok"] is False
    assert report["internal"] is None
    assert any("dataset_validation:" in item for item in report["failures"])
    assert any("external_validation:" in item for item in report["failures"])

    md = render_validation_report_markdown(report)
    assert "Internal validation section unavailable." in md
    assert "External validation not provided." in md


def test_validation_report_internal_failure_branch(tmp_path):
    dataset = tmp_path / "drugs.csv"
    dataset.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg\n"
        "Paracetamol,0.8,1.8,0.28,65,1000\n",
        encoding="utf-8",
    )
    report = build_validation_report(
        dataset=str(dataset),
        drug="Paracetamol",
        n_points=0,
    )
    assert report["report_ok"] is False
    assert report["internal"] is None
    assert any("internal_validation:" in item for item in report["failures"])
