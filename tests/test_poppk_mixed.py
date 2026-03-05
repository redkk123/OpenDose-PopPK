import numpy as np
import pandas as pd
import pytest

from opendose_poppk import PKModel, eta_table_from_fit, fit_population_mixed_effects
import opendose_poppk.poppk_mixed as poppk_mixed_mod


def _build_synthetic_df():
    times = np.array([0.5, 1.0, 2.0, 4.0])
    p1 = PKModel(F=0.8, ka=1.4, ke=0.22, Vd=55.0, Q=0.0, V2=20.0).concentration(times, D=1000.0)
    p2 = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=70.0, Q=0.0, V2=20.0).concentration(times, D=750.0)
    return pd.DataFrame(
        {
            "patient_id": ["P1"] * len(times) + ["P2"] * len(times),
            "time_h": np.concatenate([times, times]),
            "conc": np.concatenate([p1, p2]),
            "dose_mg": np.array([1000.0] * len(times) + [750.0] * len(times)),
        }
    )


def test_fit_population_mixed_effects_basic():
    df = _build_synthetic_df()
    template = PKModel(F=0.8, ka=1.6, ke=0.25, Vd=60.0, Q=0.0, V2=20.0)
    fit = fit_population_mixed_effects(df, pk_template=template, sigma_obs=0.8, maxiter=120)

    assert fit["n_patients"] == 2
    assert fit["n_obs"] == 8
    assert fit["sigma_obs"] == pytest.approx(0.8)
    assert fit["theta"]["ka"] > 0
    assert fit["theta"]["ke"] > 0
    assert fit["theta"]["Vd"] > 0
    assert fit["omega"]["ka"] > 0
    assert fit["omega"]["ke"] > 0
    assert fit["omega"]["Vd"] > 0
    assert len(fit["eta"]) == 2

    eta_df = eta_table_from_fit(fit)
    assert eta_df.shape[0] == 2
    assert set(eta_df.columns) == {"patient_id", "eta_ka", "eta_ke", "eta_Vd", "ind_ka", "ind_ke", "ind_Vd"}


def test_fit_population_mixed_effects_decay_template_and_empty_eta_table():
    df = _build_synthetic_df()
    template = PKModel(F=0.8, ka=1.6, ke=0.25, Vd=60.0, Q=0.0, V2=20.0, phys_half_life_h=72.0)
    fit = fit_population_mixed_effects(df, pk_template=template, sigma_obs=0.8, maxiter=80)
    assert fit["n_patients"] == 2
    assert eta_table_from_fit({}).empty


def test_fit_population_mixed_effects_validation_errors():
    template = PKModel(F=0.8, ka=1.6, ke=0.25, Vd=60.0, Q=0.0, V2=20.0)
    df = _build_synthetic_df()

    with pytest.raises(ValueError, match="empty"):
        fit_population_mixed_effects(pd.DataFrame(), pk_template=template)
    with pytest.raises(ValueError, match="Missing required columns"):
        fit_population_mixed_effects(pd.DataFrame({"patient_id": ["P1"]}), pk_template=template)
    with pytest.raises(ValueError, match="sigma_obs must be positive"):
        fit_population_mixed_effects(df, pk_template=template, sigma_obs=0.0)
    with pytest.raises(ValueError, match="maxiter must be at least 1"):
        fit_population_mixed_effects(df, pk_template=template, maxiter=0)
    with pytest.raises(ValueError, match="init_theta\\[ka\\] must be positive"):
        fit_population_mixed_effects(
            df,
            pk_template=template,
            init_theta={"ka": 0.0, "ke": 0.25, "Vd": 60.0},
        )
    with pytest.raises(ValueError, match="init_omega\\[ke\\] must be positive"):
        fit_population_mixed_effects(
            df,
            pk_template=template,
            init_omega={"ka": 0.3, "ke": 0.0, "Vd": 0.3},
        )


def test_predict_one_compartment_handles_equal_rates():
    pred = poppk_mixed_mod._predict_one_compartment(
        times=np.array([0.5, 1.0, 2.0]),
        doses=np.array([1000.0, 1000.0, 1000.0]),
        F=0.8,
        ka=0.3,
        ke=0.3,
        vd=60.0,
        lambda_phys=0.0,
    )
    assert np.all(np.isfinite(pred))
    assert np.all(pred >= 0.0)


def test_fit_population_mixed_effects_objective_guards(monkeypatch):
    df = _build_synthetic_df()
    template = PKModel(F=0.8, ka=1.6, ke=0.25, Vd=60.0, Q=0.0, V2=20.0)
    captured = {}

    class _FakeResult:
        def __init__(self, x):
            self.x = x
            self.success = True
            self.fun = 123.0

    def _fake_minimize(obj, x0, method=None, options=None):
        x_penalty = np.array(x0, copy=True)
        x_penalty[0] = np.log(0.5)
        x_penalty[1] = np.log(0.5)
        captured["penalty"] = obj(x_penalty)
        captured["non_finite"] = obj(np.full_like(x0, np.nan))
        return _FakeResult(np.array(x0, copy=True))

    monkeypatch.setattr(poppk_mixed_mod, "minimize", _fake_minimize)
    out = fit_population_mixed_effects(df, pk_template=template, maxiter=10)

    assert captured["penalty"] == 1e8
    assert captured["non_finite"] == 1e12
    assert out["objective"] == pytest.approx(123.0)
