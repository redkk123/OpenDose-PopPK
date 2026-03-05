import pandas as pd
import pytest

from opendose_poppk import fit_tdm_mixed_by_drug, summarize_tdm_mixed_fit


def test_fit_tdm_mixed_by_drug_basic():
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2", "P2"],
            "drug": ["Paracetamol", "Paracetamol", "Ibuprofen", "Ibuprofen"],
            "time_h": [1.0, 2.0, 1.0, 2.0],
            "conc": [4.2, 6.8, 2.1, 3.4],
            "dose_mg": [1000.0, 1000.0, 500.0, 500.0],
            "weight": [80.0, 80.0, 65.0, 65.0],
        }
    )
    fit_df = fit_tdm_mixed_by_drug(
        df=df,
        dataset="datasets/drugs_parameters.csv",
        sigma_obs=0.8,
        n_iter=500,
    )
    assert fit_df.shape[0] == 2
    assert set(fit_df["drug"]) == {"Paracetamol", "Ibuprofen"}
    s = summarize_tdm_mixed_fit(fit_df)
    assert s["groups"] == 2
    assert s["patients"] == 2
    assert s["drugs"] == 2


def test_fit_tdm_mixed_by_drug_missing_columns():
    df = pd.DataFrame({"patient_id": ["P1"], "time_h": [1.0], "conc": [2.0], "dose_mg": [1000.0]})
    with pytest.raises(ValueError, match="Missing required mixed-TDM columns"):
        fit_tdm_mixed_by_drug(df, dataset="datasets/drugs_parameters.csv")


def test_summarize_tdm_mixed_fit_empty():
    fit_df = pd.DataFrame(columns=["patient_id", "drug", "converged"])
    s = summarize_tdm_mixed_fit(fit_df)
    assert s["groups"] == 0
    assert s["patients"] == 0
    assert s["drugs"] == 0
    assert s["converged"] == 0
