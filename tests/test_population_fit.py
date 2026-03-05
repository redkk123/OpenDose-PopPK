import numpy as np
import pandas as pd
import pytest

from opendose_poppk import PKModel, fit_population_pk
import opendose_poppk.population_fit as population_fit_mod


def test_fit_population_pk_basic():
    true = PKModel(F=0.8, ka=1.6, ke=0.25, Vd=60.0)
    times = np.array([0.5, 1.0, 2.0, 4.0, 6.0, 8.0])
    doses = np.array([1000.0] * len(times))
    conc = true.concentration(times, D=1000.0)

    df = pd.DataFrame(
        {
            "patient_id": ["P1"] * len(times),
            "time_h": times,
            "conc": conc,
            "dose_mg": doses,
        }
    )

    res = fit_population_pk(df, maxiter=1000)
    assert "params" in res
    assert res["n_obs"] == len(times)
    assert res["objective_mse"] >= 0.0
    assert res["params"]["Vd"] > 0
    assert res["params"]["ke"] > 0


def test_fit_population_pk_with_init_and_two_doses():
    true = PKModel(F=0.7, ka=1.2, ke=0.22, Vd=55.0)
    times1 = np.array([0.5, 1.0, 2.0, 4.0])
    times2 = np.array([0.5, 1.5, 3.0, 6.0])
    conc1 = true.concentration(times1, D=500.0)
    conc2 = true.concentration(times2, D=1000.0)

    df = pd.DataFrame(
        {
            "patient_id": ["P1"] * len(times1) + ["P2"] * len(times2),
            "time_h": np.concatenate([times1, times2]),
            "conc": np.concatenate([conc1, conc2]),
            "dose_mg": np.array([500.0] * len(times1) + [1000.0] * len(times2)),
        }
    )
    init = {"F": 0.9, "ka": 1.5, "ke": 0.3, "Vd": 70.0}
    res = fit_population_pk(df, init=init, maxiter=1200)
    assert res["n_obs"] == df.shape[0]
    assert 0.01 <= res["params"]["F"] <= 1.0


def test_fit_population_pk_validation_errors():
    with pytest.raises(ValueError, match="empty"):
        fit_population_pk(pd.DataFrame())

    with pytest.raises(ValueError, match="Missing required columns"):
        fit_population_pk(pd.DataFrame({"time_h": [1.0], "conc": [2.0]}))


def test_fit_population_pk_penalizes_ka_equal_ke(monkeypatch):
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1"],
            "time_h": [1.0, 2.0],
            "conc": [2.0, 1.0],
            "dose_mg": [1000.0, 1000.0],
        }
    )

    captured = {}

    class _FakeResult:
        x = np.array([np.log(0.8), np.log(0.5), np.log(0.5), np.log(65.0)])
        success = True
        fun = 1e8

    def _fake_minimize(obj, x0, method=None, options=None):
        x_penalty = np.array([np.log(0.8), np.log(0.5), np.log(0.5), np.log(65.0)])
        captured["penalty"] = obj(x_penalty)
        return _FakeResult()

    monkeypatch.setattr(population_fit_mod, "minimize", _fake_minimize)
    out = fit_population_pk(df, maxiter=20)
    assert captured["penalty"] == 1e8
    assert out["objective_mse"] == 1e8
