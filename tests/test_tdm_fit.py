import pandas as pd

from opendose_poppk import PKModel, fit_tdm_patients, summarize_fit_table


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
