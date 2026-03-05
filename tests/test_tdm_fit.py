import pandas as pd
import pytest

from opendose_poppk import (
    PKModel,
    build_tdm_prediction_table,
    fit_tdm_patients,
    summarize_fit_table,
    summarize_prediction_table,
)


def test_fit_tdm_patients_basic():
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2", "P2"],
            "time_h": [1.0, 2.0, 1.0, 2.0],
            "conc": [4.0, 6.0, 3.0, 5.0],
            "dose_mg": [1000.0, 1000.0, 750.0, 750.0],
            "weight": [80.0, 80.0, 65.0, 65.0],
        }
    )
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=0.8, n_iter=500)

    assert fit_df.shape[0] == 2
    assert list(fit_df["patient_id"]) == ["P1", "P2"]
    assert {"map_F", "map_ka", "map_ke", "map_Vd", "converged"}.issubset(set(fit_df.columns))
    assert fit_df["n_obs"].tolist() == [2, 2]


def test_fit_tdm_patients_without_optional_covariates():
    df = pd.DataFrame(
        {
            "patient_id": ["P3", "P3"],
            "time_h": [1.0, 3.0],
            "conc": [2.0, 1.2],
            "dose_mg": [500.0, 500.0],
        }
    )
    pk = PKModel()
    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=1.0, n_iter=300)
    assert fit_df.shape[0] == 1
    assert fit_df.iloc[0]["patient_id"] == "P3"


def test_fit_tdm_patients_with_optional_columns_all_nan():
    df = pd.DataFrame(
        {
            "patient_id": ["P4", "P4"],
            "time_h": [1.0, 2.0],
            "conc": [2.5, 1.5],
            "dose_mg": [600.0, 600.0],
            "weight": [None, None],
            "crcl": [None, None],
            "age": [None, None],
        }
    )
    pk = PKModel()
    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=1.0, n_iter=300)
    assert fit_df.shape[0] == 1
    assert fit_df.iloc[0]["patient_id"] == "P4"


def test_summarize_fit_table_empty_and_non_empty():
    empty = pd.DataFrame(columns=["patient_id", "converged"])
    s0 = summarize_fit_table(empty)
    assert s0["patients"] == 0
    assert s0["converged"] == 0
    assert s0["convergence_rate"] == 0.0

    non_empty = pd.DataFrame({"patient_id": ["P1", "P2"], "converged": [True, False]})
    s1 = summarize_fit_table(non_empty)
    assert s1["patients"] == 2
    assert s1["converged"] == 1
    assert s1["convergence_rate"] == 0.5


def test_build_tdm_prediction_table_and_summary():
    obs_df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2", "P2"],
            "time_h": [2.0, 1.0, 2.0, 1.0],  # intentionally unsorted
            "conc": [6.0, 4.0, 5.0, 3.0],
            "dose_mg": [1000.0, 1000.0, 750.0, 750.0],
        }
    )
    fit_df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2"],  # duplicate P1 triggers DataFrame branch in .loc
            "map_F": [0.8, 0.82, 0.8],
            "map_ka": [1.8, 1.7, 1.8],
            "map_ke": [0.28, 0.30, 0.28],
            "map_Vd": [65.0, 64.0, 65.0],
        }
    )
    pred = build_tdm_prediction_table(obs_df, fit_df)
    assert pred.shape[0] == 4
    assert {"obs_conc", "pred_conc", "residual"}.issubset(set(pred.columns))

    s = summarize_prediction_table(pred)
    assert s["prediction_rows"] == 4
    assert s["rmse"] is not None
    assert s["mae"] is not None


def test_build_tdm_prediction_table_validation_and_missing_patient():
    with pytest.raises(ValueError, match="Missing observation columns"):
        build_tdm_prediction_table(pd.DataFrame({"patient_id": ["P1"]}), pd.DataFrame())

    obs_df = pd.DataFrame(
        {
            "patient_id": ["P1"],
            "time_h": [1.0],
            "conc": [4.0],
            "dose_mg": [1000.0],
        }
    )
    fit_df_missing_cols = pd.DataFrame({"patient_id": ["P1"]})
    with pytest.raises(ValueError, match="Missing fit columns"):
        build_tdm_prediction_table(obs_df, fit_df_missing_cols)

    fit_df_other = pd.DataFrame(
        {
            "patient_id": ["P2"],
            "map_F": [0.8],
            "map_ka": [1.8],
            "map_ke": [0.28],
            "map_Vd": [65.0],
        }
    )
    with pytest.raises(ValueError, match="not found in fit table"):
        build_tdm_prediction_table(obs_df, fit_df_other)

    empty_pred = build_tdm_prediction_table(
        pd.DataFrame(columns=["patient_id", "time_h", "conc", "dose_mg"]), fit_df_other
    )
    s = summarize_prediction_table(empty_pred)
    assert s["prediction_rows"] == 0
    assert s["rmse"] is None
