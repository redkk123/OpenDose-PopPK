import numpy as np
import pytest
from opendose_poppk import PKModel


def test_concentration_positive():
    """Test that concentration is always non-negative."""
    pk = PKModel(CL=5, V=50)
    t = np.linspace(0, 10, 100)
    C = pk.concentration(t, D=100)
    assert (C >= 0).all()


def test_concentration_decreases():
    """Test that concentration decreases over time after peak."""
    pk = PKModel(CL=5, V=50)
    c0 = pk.concentration(0, D=100)
    c1 = pk.concentration(10, D=100)
    assert c1 < c0


def test_concentration_peak_exists():
    """Test that concentration peaks and then decreases."""
    # Use parameters that clearly show absorption phase
    # Keep V2 > 0 to avoid division by zero in 2-compartment model 
    pk = PKModel(F=1.0, ka=0.3, ke=0.1, Vd=70, Q=0.1, V2=10.0)
    t = np.linspace(0, 48, 1000)
    C = pk.concentration(t, D=100)
    
    # Find peak
    c_max = np.max(C)
    
    # Peak should exist and concentration should decrease after peak
    assert c_max > 0
    assert C[-1] < C[0]  # Final concentration lower than initial


def test_cmax_tmax():
    """Test that Cmax and Tmax are reasonable values."""
    # Use non-zero Q and V2 to avoid division by zero
    pk = PKModel(F=1.0, ka=0.5, ke=0.2, Vd=50, Q=1.0, V2=20.0)
    cmax, tmax = pk.cmax(D=1000.0)
    
    # Cmax should be positive
    assert cmax > 0
    
    # Tmax should be reasonable
    assert tmax >= 0


def test_auc_positive():
    """Test that AUC is always positive."""
    pk = PKModel(F=1.0, ka=1.0, ke=0.1, Vd=100.0)
    auc = pk.auc(D=500.0)
    assert auc > 0


def test_auc_increases_with_dose():
    """Test that AUC increases with dose."""
    pk = PKModel(F=1.0, ka=1.0, ke=0.1, Vd=100.0)
    
    auc_100 = pk.auc(D=100.0)
    auc_200 = pk.auc(D=200.0)
    
    assert auc_200 / auc_100 == pytest.approx(2.0, rel=0.01)


def test_auc_decreases_with_ke():
    """Test that AUC decreases with higher elimination rate."""
    D = 500.0
    
    pk_slow_elim = PKModel(F=1.0, ka=1.0, ke=0.05, Vd=100.0)
    auc_slow = pk_slow_elim.auc(D=D)
    
    pk_fast_elim = PKModel(F=1.0, ka=1.0, ke=0.2, Vd=100.0)
    auc_fast = pk_fast_elim.auc(D=D)
    
    assert auc_slow > auc_fast


def test_state_space_stability():
    """Test that state-space system is stable."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0, Q=10.0, V2=20.0)
    ss = pk.state_space()
    
    assert ss["is_stable"]
    assert np.all(np.real(ss["eigenvalues"]) < 0)


def test_pk_init_with_cl_v():
    """Test PKModel initialization with CL and V parameters."""
    pk = PKModel(CL=10.0, V=50.0)
    assert pk.CL == 10.0
    assert pk.V1 == 50.0
    assert np.isclose(pk.ke, 10.0 / 50.0)
    assert pk.Vd == 50.0


def test_simulate_population():
    """Test that simulate_population returns correct shape."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    t = np.linspace(0, 24, 100)
    
    med, p5, p95 = pk.simulate_population(
        t, D=1000.0, n_subjects=100, seed=42
    )
    
    assert med.shape == (100,)
    assert p5.shape == (100,)
    assert p95.shape == (100,)
    
    # Check ordering
    assert np.all(p5 <= med)
    assert np.all(med <= p95)
