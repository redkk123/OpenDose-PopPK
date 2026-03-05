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
