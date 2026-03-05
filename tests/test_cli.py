import json
from pathlib import Path

import opendose_poppk.cli as cli_mod
import pytest
from opendose_poppk.cli import main


def test_cli_list_drugs(capsys):
    code = main(["list-drugs"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Paracetamol" in out


def test_cli_validate_dataset(tmp_path, capsys):
    input_csv = tmp_path / "drugs.csv"
    clean_csv = tmp_path / "drugs_clean.csv"
    input_csv.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\n"
        "Paracetamol,0.8,1.8,0.28,65,1000,10,1.5\n",
        encoding="utf-8",
    )

    code = main(
        [
            "--dataset",
            str(input_csv),
            "validate-dataset",
            "--output-clean",
            str(clean_csv),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "validate-dataset"
    assert payload["rows"] == 1
    assert payload["drugs"] == 1
    assert payload["pd_complete_rows"] == 1
    assert payload["pd_partial_rows"] == 0
    assert clean_csv.exists()


def test_cli_validate_dataset_error(capsys):
    code = main(["--dataset", "missing_drug_dataset.csv", "validate-dataset"])
    err = capsys.readouterr().err
    assert code == 1
    assert "No such file or directory" in err


def test_cli_simulate_writes_csv(tmp_path, capsys):
    out_csv = tmp_path / "sim.csv"
    code = main(
        [
            "simulate",
            "--drug",
            "Paracetamol",
            "--n-subjects",
            "20",
            "--n-points",
            "30",
            "--t-max",
            "12",
            "--output",
            str(out_csv),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 0
    assert payload["command"] == "simulate"
    assert payload["drug"] == "Paracetamol"
    assert out_csv.exists()
    assert out_csv.read_text(encoding="utf-8").startswith("time,p5,p50,p95")


def test_cli_sensitivity(tmp_path, capsys):
    out_csv = tmp_path / "sensitivity.csv"
    code = main(
        [
            "sensitivity",
            "--drug",
            "Paracetamol",
            "--dose",
            "1000",
            "--t-end",
            "24",
            "--n-points",
            "300",
            "--rel-step",
            "0.1",
            "--output-csv",
            str(out_csv),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 0
    assert payload["command"] == "sensitivity"
    assert payload["drug"] == "Paracetamol"
    assert payload["baseline_cmax"] > 0
    assert payload["baseline_auc"] > 0
    assert len(payload["results"]) == 4
    assert out_csv.exists()


def test_cli_sensitivity_validation(capsys):
    code = main(["sensitivity", "--drug", "Paracetamol", "--rel-step", "1.0"])
    err = capsys.readouterr().err
    assert code == 1
    assert "rel_step must be in (0, 1)" in err


def test_cli_simulate_regimen(tmp_path, capsys):
    out_csv = tmp_path / "regimen.csv"
    out_png = tmp_path / "regimen.png"
    code = main(
        [
            "simulate-regimen",
            "--drug",
            "Paracetamol",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
            "--n-points",
            "300",
            "--output-csv",
            str(out_csv),
            "--plot-png",
            str(out_png),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 0
    assert payload["command"] == "simulate-regimen"
    assert payload["drug"] == "Paracetamol"
    assert payload["n_doses"] == 4
    assert payload["n_points"] == 300
    assert out_csv.exists()
    assert out_png.exists()


def test_cli_fit_returns_json(capsys):
    code = main(
        [
            "fit",
            "--drug",
            "Paracetamol",
            "--times",
            "0.5,1.0,2.0,4.0",
            "--obs",
            "4.2,6.8,7.5,5.9",
            "--weight",
            "80",
            "--crcl",
            "70",
            "--age",
            "55",
            "--n-iter",
            "1000",
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 0
    assert payload["command"] == "fit"
    assert payload["drug"] == "Paracetamol"
    assert "params_map" in payload


def test_cli_fit_rejects_mismatched_vectors(capsys):
    code = main(
        [
            "fit",
            "--drug",
            "Paracetamol",
            "--times",
            "1,2,3",
            "--obs",
            "1,2",
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "same length" in err


def test_cli_fit_rejects_empty_vectors(capsys):
    code = main(
        [
            "fit",
            "--drug",
            "Paracetamol",
            "--times",
            ",,,",
            "--obs",
            ",,,",
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "cannot be empty" in err


def test_cli_validate_tdm(tmp_path, capsys):
    input_csv = tmp_path / "tdm.csv"
    clean_csv = tmp_path / "tdm_clean.csv"
    input_csv.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P2,2.0,5.0,750\n"
        "P1,1.0,4.0,1000\n",
        encoding="utf-8",
    )

    code = main(
        [
            "validate-tdm",
            "--input",
            str(input_csv),
            "--output-clean",
            str(clean_csv),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "validate-tdm"
    assert payload["rows"] == 2
    assert payload["patients"] == 2
    assert clean_csv.exists()


def test_cli_fit_tdm(tmp_path, capsys):
    input_csv = tmp_path / "tdm_fit.csv"
    out_csv = tmp_path / "fit_table.csv"
    pred_csv = tmp_path / "predictions.csv"
    plot_png = tmp_path / "obs_pred.png"
    out_md = tmp_path / "fit_report.md"
    input_csv.write_text(
        "patient_id,time_h,conc,dose_mg,weight\n"
        "P1,1.0,4.2,1000,80\n"
        "P1,2.0,6.8,1000,80\n"
        "P2,1.0,3.1,750,65\n"
        "P2,2.0,5.0,750,65\n",
        encoding="utf-8",
    )

    code = main(
        [
            "fit-tdm",
            "--drug",
            "Paracetamol",
            "--input",
            str(input_csv),
            "--n-iter",
            "500",
            "--output",
            str(out_csv),
            "--predictions-csv",
            str(pred_csv),
            "--plot-png",
            str(plot_png),
            "--report-md",
            str(out_md),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "fit-tdm"
    assert payload["patients"] == 2
    assert out_csv.exists()
    assert pred_csv.exists()
    assert plot_png.exists()
    assert out_md.exists()
    assert payload["predictions_csv"] == str(pred_csv)
    assert payload["plot_png"] == str(plot_png)
    assert payload["prediction_rows"] == 4
    assert payload["rmse"] is not None
    assert payload["mae"] is not None
    assert payload["report_md"] == str(out_md)


def test_cli_fit_population(tmp_path, capsys):
    input_csv = tmp_path / "tdm_population.csv"
    out_json = tmp_path / "pop_fit.json"
    input_csv.write_text(
        "patient_id,time_h,conc,dose_mg\n"
        "P1,0.5,4.2,1000\n"
        "P1,1.0,6.8,1000\n"
        "P2,0.5,2.1,500\n"
        "P2,1.0,3.4,500\n",
        encoding="utf-8",
    )

    code = main(
        [
            "fit-population",
            "--input",
            str(input_csv),
            "--maxiter",
            "500",
            "--init-F",
            "0.7",
            "--bootstrap-n",
            "3",
            "--bootstrap-seed",
            "11",
            "--output-json",
            str(out_json),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "fit-population"
    assert payload["n_obs"] == 4
    assert "params" in payload
    assert "bootstrap" in payload
    assert payload["bootstrap"]["n_boot"] == 3
    assert out_json.exists()


def test_cli_init_tdm_template(tmp_path, capsys):
    out_csv = tmp_path / "template.csv"
    code = main(["init-tdm-template", "--output", str(out_csv)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "init-tdm-template"
    assert out_csv.exists()


def test_cli_run_tdm_workflow(tmp_path, capsys):
    input_csv = tmp_path / "tdm_workflow.csv"
    outdir = tmp_path / "workflow_out"
    input_csv.write_text(
        "patient_id,time_h,conc,dose_mg,weight\n"
        "P1,1.0,4.2,1000,80\n"
        "P1,2.0,6.8,1000,80\n"
        "P2,1.0,3.1,750,65\n"
        "P2,2.0,5.0,750,65\n",
        encoding="utf-8",
    )

    code = main(
        [
            "run-tdm-workflow",
            "--drug",
            "Paracetamol",
            "--input",
            str(input_csv),
            "--outdir",
            str(outdir),
            "--n-iter",
            "500",
            "--maxiter-pop",
            "500",
            "--bootstrap-n",
            "2",
            "--bootstrap-seed",
            "13",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "run-tdm-workflow"
    assert payload["patients"] == 2
    assert payload["prediction_rows"] == 4
    assert Path(payload["clean_csv"]).exists()
    assert Path(payload["fit_csv"]).exists()
    assert Path(payload["predictions_csv"]).exists()
    assert Path(payload["report_md"]).exists()
    assert Path(payload["plot_png"]).exists()
    assert Path(payload["population_json"]).exists()


def test_cli_benchmark_regimen(tmp_path, capsys):
    out_csv = tmp_path / "benchmark.csv"
    code = main(
        [
            "benchmark-regimen",
            "--drugs",
            "Paracetamol,Ibuprofen",
            "--interval-h",
            "12",
            "--n-doses",
            "3",
            "--dose-override",
            "500",
            "--output-csv",
            str(out_csv),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "benchmark-regimen"
    assert payload["n_drugs"] == 2
    assert payload["output_csv"] == str(out_csv)
    assert payload["top_drug_by_cmax"] is not None
    assert out_csv.exists()


def test_cli_fit_tdm_mixed(tmp_path, capsys):
    input_csv = tmp_path / "tdm_mixed.csv"
    out_csv = tmp_path / "tdm_mixed_fit.csv"
    input_csv.write_text(
        "patient_id,drug,time_h,conc,dose_mg,weight\n"
        "P1,Paracetamol,1.0,4.2,1000,80\n"
        "P1,Paracetamol,2.0,6.8,1000,80\n"
        "P2,Ibuprofen,1.0,2.1,500,65\n"
        "P2,Ibuprofen,2.0,3.4,500,65\n",
        encoding="utf-8",
    )

    code = main(
        [
            "fit-tdm-mixed",
            "--input",
            str(input_csv),
            "--n-iter",
            "500",
            "--output",
            str(out_csv),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "fit-tdm-mixed"
    assert payload["groups"] == 2
    assert payload["patients"] == 2
    assert payload["drugs"] == 2
    assert out_csv.exists()


def test_cli_doctor_success(capsys):
    code = main(["doctor"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "doctor"
    assert payload["dataset_ok"] is True
    assert payload["pk_smoke_ok"] is True
    assert payload["failures"] == []


def test_cli_doctor_strict_failure_with_missing_dataset(capsys):
    code = main(["--dataset", "missing_file.csv", "doctor", "--strict"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["command"] == "doctor"
    assert payload["dataset_ok"] is False
    assert len(payload["failures"]) >= 1


def test_cli_doctor_pk_smoke_failure_non_strict(monkeypatch, capsys):
    class _BadPK:
        def concentration(self, t, D=1000.0):
            raise RuntimeError("pk smoke failed")

    monkeypatch.setattr(cli_mod, "PKModel", _BadPK)
    code = main(["doctor"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["pk_smoke_ok"] is False
    assert any("pk_smoke" in msg for msg in payload["failures"])


def test_cli_project_report_success(tmp_path, capsys):
    dataset_csv = tmp_path / "drugs.csv"
    report_md = tmp_path / "project_report.md"
    dataset_csv.write_text(
        "Drug,F,ka_h,ke_h,Vd_L,dose_mg,EC50_ugmL,n_hill\n"
        "Paracetamol,0.8,1.8,0.28,65,1000,10,1.5\n",
        encoding="utf-8",
    )

    code = main(
        [
            "--dataset",
            str(dataset_csv),
            "project-report",
            "--drug",
            "Paracetamol",
            "--output-md",
            str(report_md),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "project-report"
    assert payload["report_ok"] is True
    assert payload["dataset_ok"] is True
    assert payload["sensitivity_ok"] is True
    assert report_md.exists()
    assert "OpenDose Project Report" in report_md.read_text(encoding="utf-8")


def test_cli_project_report_strict_failure(capsys):
    code = main(["--dataset", "missing_drug_dataset.csv", "project-report", "--strict"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["command"] == "project-report"
    assert payload["report_ok"] is False
    assert payload["dataset_ok"] is False
    assert len(payload["failures"]) >= 1


def test_cli_recommend_dose_cmax(tmp_path, capsys):
    out_json = tmp_path / "dose_cmax.json"
    code = main(
        [
            "recommend-dose",
            "--drug",
            "Paracetamol",
            "--target-cmax",
            "10",
            "--weight",
            "80",
            "--crcl",
            "70",
            "--age",
            "55",
            "--sex",
            "M",
            "--output-json",
            str(out_json),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "recommend-dose"
    assert payload["mode"] == "cmax"
    assert payload["recommended_dose"] > 0
    assert out_json.exists()


def test_cli_recommend_dose_auc(capsys):
    code = main(["recommend-dose", "--drug", "Paracetamol", "--target-auc", "50"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["mode"] == "auc"
    assert payload["predicted"] == pytest.approx(50.0, rel=1e-8)


def test_cli_recommend_dose_validation_errors(capsys):
    code = main(["recommend-dose", "--drug", "Paracetamol"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Provide --target-cmax or --target-auc" in err

    code = main(["recommend-dose", "--drug", "Paracetamol", "--target-cmax", "10", "--target-auc", "50"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Use only one target mode" in err


def test_cli_recommend_regimen_dose_cmax(tmp_path, capsys):
    out_json = tmp_path / "regimen_dose_cmax.json"
    code = main(
        [
            "recommend-regimen-dose",
            "--drug",
            "Paracetamol",
            "--target-cmax",
            "12",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
            "--output-json",
            str(out_json),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "recommend-regimen-dose"
    assert payload["mode"] == "regimen_cmax"
    assert payload["recommended_dose"] > 0
    assert out_json.exists()


def test_cli_recommend_regimen_dose_trough(capsys):
    code = main(
        [
            "recommend-regimen-dose",
            "--drug",
            "Paracetamol",
            "--target-trough",
            "1.0",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["mode"] == "regimen_trough"


def test_cli_recommend_regimen_dose_with_covariates(capsys):
    code = main(
        [
            "recommend-regimen-dose",
            "--drug",
            "Paracetamol",
            "--target-cmax",
            "12",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
            "--weight",
            "80",
            "--crcl",
            "70",
            "--age",
            "55",
            "--sex",
            "M",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["mode"] == "regimen_cmax"
    assert payload["covariates"] == {"weight": 80.0, "crcl": 70.0, "age": 55.0}
    assert payload["sex"] == "M"


def test_cli_recommend_regimen_dose_validation(capsys):
    code = main(["recommend-regimen-dose", "--drug", "Paracetamol", "--interval-h", "12", "--n-doses", "4"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Provide --target-cmax or --target-trough" in err

    code = main(
        [
            "recommend-regimen-dose",
            "--drug",
            "Paracetamol",
            "--target-cmax",
            "10",
            "--target-trough",
            "1",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "Use only one target mode" in err


def test_cli_recommend_regimen_window_feasible(tmp_path, capsys):
    out_json = tmp_path / "regimen_window.json"
    code = main(
        [
            "recommend-regimen-window",
            "--drug",
            "Paracetamol",
            "--target-trough-min",
            "0.05",
            "--target-cmax-max",
            "12.0",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
            "--strategy",
            "midpoint",
            "--weight",
            "80",
            "--crcl",
            "70",
            "--age",
            "55",
            "--sex",
            "M",
            "--output-json",
            str(out_json),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["command"] == "recommend-regimen-window"
    assert payload["mode"] == "regimen_window"
    assert payload["feasible"] is True
    assert payload["strategy"] == "midpoint"
    assert payload["dose_lower_bound"] <= payload["recommended_dose"] <= payload["dose_upper_bound"]
    assert out_json.exists()


def test_cli_recommend_regimen_window_infeasible(capsys):
    code = main(
        [
            "recommend-regimen-window",
            "--drug",
            "Paracetamol",
            "--target-trough-min",
            "5.0",
            "--target-cmax-max",
            "6.0",
            "--interval-h",
            "12",
            "--n-doses",
            "4",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["mode"] == "regimen_window"
    assert payload["feasible"] is False
    assert payload["recommended_dose"] is None
