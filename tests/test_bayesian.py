import numpy as np
import pytest
from opendose_poppk import MAPEstimator, PKModel, CovariateModel
import opendose_poppk.bayesian as bayesian_mod


def test_map_runs():
    """Test that MAPEstimator can be instantiated and runs without error."""
    estimator = MAPEstimator()
    assert estimator is not None
    assert estimator.sigma == 1.0


def test_map_fit_basic():
    """Test that MAP estimator fits to synthetic observation data."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    estimator = MAPEstimator(pk=pk)
    
    # Generate synthetic data from the model
    times = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
    true_conc = pk.concentration(times, D=1000.0)
    obs = true_conc + np.random.normal(0, 0.5, len(times))  # Add noise
    
    result = estimator.fit(
        times=times,
        obs=obs,
        patient_covariates={"weight": 70, "crcl": 90},
        dose=1000.0
    )
    
    assert "params_map" in result
    assert "eta_map" in result
    assert "pop_adjusted" in result
    assert "converged" in result
    assert "obj_value" in result
    
    # Check that estimated parameters are positive
    for key in ["F", "ka", "ke", "Vd"]:
        assert result["params_map"][key] > 0


def test_map_fit_convergence():
    """Test that MAP estimator converges to solution."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    estimator = MAPEstimator(pk=pk, sigma_obs=0.5)
    
    times = np.array([0.5, 1.0, 2.0, 4.0, 8.0])
    obs = np.array([10.0, 12.0, 11.0, 8.0, 4.0])
    
    result = estimator.fit(
        times=times,
        obs=obs,
        patient_covariates={},
        dose=1000.0,
        n_iter=2000
    )
    
    # At least for basic cases, should converge
    assert result["obj_value"] < 100  # Should achieve reasonable fit


def test_map_with_covariates():
    """Test MAP estimator with covariate-adjusted population parameters."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    cov = CovariateModel(pk)
    estimator = MAPEstimator(pk=pk, covariate_model=cov)
    
    times = np.array([1.0, 2.0, 4.0, 6.0])
    obs = np.array([15.0, 14.0, 10.0, 6.0])
    
    # Test with patient covariates
    result = estimator.fit(
        times=times,
        obs=obs,
        patient_covariates={"weight": 85, "crcl": 75, "age": 65},
        dose=1000.0
    )
    
    assert "params_map" in result
    assert all(p > 0 for p in result["params_map"].values())


def test_map_eta_values():
    """Test that eta values represent deviations from population."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    estimator = MAPEstimator(pk=pk)
    
    times = np.array([1.0, 2.0, 4.0, 8.0])
    obs = pk.concentration(times, D=1000.0)  # Perfect fit
    
    result = estimator.fit(
        times=times,
        obs=obs,
        patient_covariates={},
        dose=1000.0
    )
    
    # With perfect fit to population model, etas should be close to zero
    eta_values = result["eta_map"].values()
    assert all(abs(eta) < 0.5 for eta in eta_values)


def test_map_objective_penalizes_ka_equal_ke(monkeypatch):
    """Cover the objective penalty branch when ka == ke."""
    pk = PKModel(F=0.8, ka=0.3, ke=0.3, Vd=65.0)
    estimator = MAPEstimator(pk=pk)

    captured = {}

    class _FakeResult:
        x = np.zeros(4)
        success = True
        fun = 1e8

    def _fake_minimize(obj, x0, method=None, options=None):
        captured["obj_at_zero"] = obj(np.zeros(4))
        return _FakeResult()

    monkeypatch.setattr(bayesian_mod, "minimize", _fake_minimize)

    times = np.array([1.0, 2.0, 4.0])
    obs = np.array([2.0, 1.5, 1.0])
    result = estimator.fit(times=times, obs=obs, patient_covariates={}, dose=100.0, n_iter=10)

    assert captured["obj_at_zero"] == 1e8
    assert result["obj_value"] == 1e8
