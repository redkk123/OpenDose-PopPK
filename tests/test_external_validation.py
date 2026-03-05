import numpy as np
import pandas as pd
import pytest

from opendose_poppk import (
    PKModel,
    build_external_validation_table,
    load_external_validation_csv,
    summarize_external_validation,
    write_external_validation_template_csv,
)


def test_external_validation_load_build_summarize_with_reference(tmp_path):
    csv_path = tmp_path / "external.csv"
    pk = PKModel(F=0.8, ka=1.5, ke=0.25, Vd=60.0, Q=0.0, V2=20.0)
    t = np.array([0.5, 1.0, 2.0, 4.0])
    obs = pk.concentration(t, D=1000.0)
    ref = obs * 1.05
    csv_path.write_text(
        "patient_id,time_h,dose_mg,obs_conc,ref_conc,study_id\n"
        f"P1,0.5,1000,{obs[0]},{ref[0]},StudyA\n"
        f"P1,1.0,1000,{obs[1]},{ref[1]},StudyA\n"
        f"P2,2.0,1000,{obs[2]},{ref[2]},StudyA\n"
        f"P2,4.0,1000,{obs[3]},{ref[3]},StudyA\n",
        encoding="utf-8",
    )

    df = load_external_validation_csv(csv_path)
    table = build_external_validation_table(df, pk=pk)
    summary = summarize_external_validation(table)

    assert table.shape[0] == 4
    assert "model_pred_conc" in table.columns
    assert "model_residual" in table.columns
    assert "study_id" in table.columns
    assert summary["rows"] == 4
    assert summary["patients"] == 2
    assert summary["with_reference"] is True
    assert summary["model_vs_obs"]["rmse"] is not None
    assert summary["ref_vs_obs"]["rmse"] is not None
    assert summary["model_vs_ref"]["mae"] is not None
    assert len(summary["by_patient"]) == 2


def test_external_validation_summaries_without_reference_and_empty():
    empty = summarize_external_validation(pd.DataFrame())
    assert empty["rows"] == 0
    assert empty["with_reference"] is False
    assert empty["model_vs_obs"]["n"] == 0

    table = pd.DataFrame(
        {
            "patient_id": ["P1", "P1"],
            "time_h": [1.0, 2.0],
            "dose_mg": [1000.0, 1000.0],
            "obs_conc": [0.0, 0.0],
            "model_pred_conc": [0.0, 0.0],
            "model_residual": [0.0, 0.0],
        }
    )
    out = summarize_external_validation(table)
    assert out["with_reference"] is False
    assert out["model_vs_obs"]["mape_pct"] is None


def test_external_validation_validation_and_template(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("patient_id,time_h,dose_mg\nP1,1,1000\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required external-validation columns"):
        load_external_validation_csv(bad)

    bad.write_text("patient_id,time_h,dose_mg,obs_conc\nP1,-1,1000,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="time_h must be non-negative"):
        load_external_validation_csv(bad)

    bad.write_text("patient_id,time_h,dose_mg,obs_conc\nP1,1,0,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dose_mg must be positive"):
        load_external_validation_csv(bad)

    bad.write_text("patient_id,time_h,dose_mg,obs_conc\nP1,1,1000,-2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="obs_conc must be non-negative"):
        load_external_validation_csv(bad)

    bad.write_text("patient_id,time_h,dose_mg,obs_conc,ref_conc\nP1,1,1000,2,-1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ref_conc must be non-negative"):
        load_external_validation_csv(bad)

    with pytest.raises(ValueError, match="Missing required columns"):
        build_external_validation_table(pd.DataFrame({"patient_id": ["P1"]}), pk=PKModel())

    out = tmp_path / "external_template.csv"
    path = write_external_validation_template_csv(out)
    assert str(out) == path
    assert out.read_text(encoding="utf-8").strip() == "patient_id,time_h,dose_mg,obs_conc,ref_conc,study_id"
