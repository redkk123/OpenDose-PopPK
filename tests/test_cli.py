import json
from pathlib import Path

from opendose_poppk.cli import main


def test_cli_list_drugs(capsys):
    code = main(["list-drugs"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Paracetamol" in out


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
    assert out_md.exists()
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
    assert out_json.exists()
