import numpy as np
import pytest
from opendose_poppk import PopulationSimulator, PKModel, PDModel


def test_population_runs():
    """Test that PopulationSimulator.simulate() returns correct shape."""
    sim = PopulationSimulator()
    result = sim.simulate(n=10)
    
    assert len(result) == 10
    assert all(isinstance(profile, np.ndarray) for profile in result)


def test_population_simulation_returns_correct_shape():
    """Test that run() returns correct data shape and structure."""
    sim = PopulationSimulator()
    result = sim.run(n_subjects=100, t_max=24.0, n_points=100, seed=42)
    
    assert result["t"].shape == (100,)
    assert result["pk_profiles"].shape == (100, 100)
    assert result["percentiles_pk"][50].shape == (100,)
    assert result["percentiles_pk"][5].shape == (100,)
    assert result["percentiles_pk"][95].shape == (100,)


def test_population_concentrations_always_positive():
    """Test that all simulated concentrations are non-negative."""
    pk = PKModel(F=1.0, ka=1.5, ke=0.3, Vd=70)
    sim = PopulationSimulator(pk=pk, dose=1000.0)
    result = sim.run(n_subjects=50, t_max=24.0, n_points=100, seed=42)
    
    assert np.all(result["pk_profiles"] >= 0)
    assert np.all(result["percentiles_pk"][5] >= 0)
    assert np.all(result["percentiles_pk"][50] >= 0)
    assert np.all(result["percentiles_pk"][95] >= 0)


def test_population_percentiles_order():
    """Test that percentiles are in correct order: p5 < p50 < p95."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    sim = PopulationSimulator(pk=pk)
    result = sim.run(n_subjects=100, t_max=12.0, n_points=50, seed=42)
    
    t = result["t"]
    p5 = result["percentiles_pk"][5]
    p50 = result["percentiles_pk"][50]
    p95 = result["percentiles_pk"][95]
    
    # All points should satisfy: p5 <= p50 <= p95
    assert np.all(p5 <= p50)
    assert np.all(p50 <= p95)


def test_population_with_pd_model():
    """Test PopulationSimulator with both PK and PD models."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    pd = PDModel(EC50=20.0, n=1.5, Emax=100.0)
    sim = PopulationSimulator(pk=pk, pd=pd)
    
    result = sim.run(n_subjects=50, t_max=12.0, n_points=50, seed=42)
    
    assert result["pd_profiles"] is not None
    assert result["pd_profiles"].shape == (50, 50)
    assert np.all(result["pd_profiles"] >= 0)
    assert np.all(result["pd_profiles"] <= 105)  # Allow small overshoot due to numerics


def test_population_covariates_within_bounds():
    """Test that simulated covariates stay within expected bounds."""
    pk = PKModel()
    sim = PopulationSimulator(pk=pk)
    
    result = sim.run(n_subjects=200, seed=42)
    cov = result["covariates_sim"]
    
    # Check weight bounds
    if "weight" in cov:
        assert np.all(cov["weight"] >= 30)
        assert np.all(cov["weight"] <= 200)
    
    # Check renal function bounds
    if "crcl" in cov:
        assert np.all(cov["crcl"] >= 10)
        assert np.all(cov["crcl"] <= 180)


def test_population_reproducibility():
    """Test that same seed produces same results."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    
    sim1 = PopulationSimulator(pk=pk)
    result1 = sim1.run(n_subjects=100, t_max=24.0, n_points=100, seed=12345)
    
    sim2 = PopulationSimulator(pk=pk)
    result2 = sim2.run(n_subjects=100, t_max=24.0, n_points=100, seed=12345)
    
    # Percentiles should be identical
    np.testing.assert_array_equal(result1["percentiles_pk"][50], result2["percentiles_pk"][50])
    np.testing.assert_array_equal(result1["percentiles_pk"][5], result2["percentiles_pk"][5])
    np.testing.assert_array_equal(result1["percentiles_pk"][95], result2["percentiles_pk"][95])
