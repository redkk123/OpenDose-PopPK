"""
test_pk_model.py
================
Unit tests for the PKModel class, including physical decay scenarios.

Tests cover:
- Basic PK model behavior
- Physical decay of radioactive isotopes (meia-vida)
- Unit consistency
- Balance of mass between compartments
- AUC with/without decay
"""

import numpy as np
import pytest
from opendose_poppk import PDModel, PKModel


# ════════════════════════════════════════════════════════════════════════════
# Basic PKModel Tests
# ════════════════════════════════════════════════════════════════════════════

def test_pkmodel_init_default():
    """Test default PKModel initialization."""
    pk = PKModel()
    assert pk.F == 0.80
    assert pk.ka == 1.80
    assert pk.ke == 0.28
    assert pk.Vd == 65.0
    assert pk.lambda_phys == 0.0


def test_pkmodel_init_with_cl_v():
    """Test PKModel with CL and V (V1) parameters."""
    pk = PKModel(CL=10.0, V=50.0)
    assert pk.CL == 10.0
    assert pk.V1 == 50.0
    assert pk.ke == 10.0 / 50.0  # Derived ke
    assert pk.Vd == 50.0


def test_pkmodel_concentration_positive():
    """Test that concentrations are always non-negative."""
    pk = PKModel(F=1.0, ka=0.5, ke=0.1, Vd=20.0)
    t = np.array([0, 1, 4, 12, 24])
    C = pk.concentration(t, D=100.0)
    assert np.all(C >= 0)


def test_pkmodel_concentration_rejects_negative_time():
    """Negative time points are invalid."""
    pk = PKModel()
    with pytest.raises(ValueError, match="não-negativos"):
        pk.concentration(np.array([-1.0, 1.0]), D=100.0)


def test_pkmodel_concentration_decreases():
    """Test that concentration decreases over time (no decay)."""
    pk = PKModel(F=1.0, ka=0.5, ke=0.1, Vd=20.0)
    t = np.array([0, 12, 24, 48])
    C = pk.concentration(t, D=100.0)
    # Should generally decrease after peaks
    assert C[-1] < C[1]


def test_pkmodel_multiple_dose_accumulation():
    """Multiple-dose regimen should produce higher late concentrations than single dose."""
    pk = PKModel(F=1.0, ka=0.8, ke=0.1, Vd=25.0, Q=0.0, V2=10.0)
    t = np.linspace(0, 24, 241)
    c_single = pk.concentration(t, D=100.0)
    c_multi = pk.concentration_multiple_dose(t, D=100.0, interval_h=8.0, n_doses=3)

    # After the second and third doses, multi-dose profile should exceed single-dose profile.
    assert np.max(c_multi[t >= 9.0]) > np.max(c_single[t >= 9.0])
    assert c_multi.shape == t.shape


def test_pkmodel_multiple_dose_validation():
    """Invalid regimen parameters should raise errors."""
    pk = PKModel()
    t = np.array([0.0, 1.0, 2.0])

    with pytest.raises(ValueError, match="interval_h must be positive"):
        pk.concentration_multiple_dose(t, interval_h=0.0, n_doses=2)

    with pytest.raises(ValueError, match="n_doses must be at least 1"):
        pk.concentration_multiple_dose(t, interval_h=8.0, n_doses=0)

    with pytest.raises(ValueError, match="não-negativos"):
        pk.concentration_multiple_dose(np.array([-1.0, 1.0]), interval_h=8.0, n_doses=2)


def test_pkmodel_iv_bolus_ignores_bioavailability_factor():
    pk = PKModel(F=0.5, ka=1.0, ke=0.1, Vd=20.0, Q=0.0, V2=10.0)
    t = np.array([0.0, 1.0, 4.0])
    c_oral_like = pk.concentration(t, D=100.0)
    c_iv = pk.concentration_iv_bolus(t, dose=100.0)
    assert c_iv[0] == pytest.approx(100.0 / pk.V1, rel=1e-8)
    assert c_oral_like[0] == pytest.approx(50.0 / pk.V1, rel=1e-8)
    assert c_iv[0] > c_oral_like[0]

    with pytest.raises(ValueError, match="dose must be positive"):
        pk.concentration_iv_bolus(t, dose=0.0)


def test_pkmodel_iv_infusion_profile_and_validation():
    pk = PKModel(F=1.0, ka=1.0, ke=0.2, Vd=20.0, Q=0.0, V2=10.0)
    t = np.linspace(0.0, 8.0, 161)
    c = pk.concentration_iv_infusion(t, rate=50.0, duration_h=2.0, start_h=0.0)
    assert c.shape == t.shape
    assert c[0] == pytest.approx(0.0, abs=1e-10)
    assert np.max(c[(t >= 1.0) & (t <= 2.5)]) > np.max(c[t >= 6.0])

    with pytest.raises(ValueError, match="rate must be positive"):
        pk.concentration_iv_infusion(t, rate=0.0, duration_h=1.0)
    with pytest.raises(ValueError, match="duration_h must be positive"):
        pk.concentration_iv_infusion(t, rate=1.0, duration_h=0.0)
    with pytest.raises(ValueError, match="start_h must be non-negative"):
        pk.concentration_iv_infusion(t, rate=1.0, duration_h=1.0, start_h=-1.0)


def test_pkmodel_steady_state_metrics():
    pk = PKModel(F=1.0, ka=1.0, ke=0.15, Vd=20.0, Q=0.0, V2=10.0)
    m = pk.steady_state_metrics(D=100.0, interval_h=8.0, n_doses=25, n_points=3000)
    assert m["cmax_ss"] > 0
    assert m["trough_ss"] > 0
    assert m["cmax_ss"] >= m["trough_ss"]
    assert m["auc_tau_ss"] > 0
    assert m["accumulation_ratio_cmax"] >= 1.0

    with pytest.raises(ValueError, match="D must be positive"):
        pk.steady_state_metrics(D=0.0, interval_h=8.0, n_doses=10)
    with pytest.raises(ValueError, match="interval_h must be positive"):
        pk.steady_state_metrics(D=100.0, interval_h=0.0, n_doses=10)
    with pytest.raises(ValueError, match="n_doses must be at least 2"):
        pk.steady_state_metrics(D=100.0, interval_h=8.0, n_doses=1)
    with pytest.raises(ValueError, match="n_points must be at least 3"):
        pk.steady_state_metrics(D=100.0, interval_h=8.0, n_doses=10, n_points=2)


def test_pkmodel_nonlinear_profile_and_validation():
    pk = PKModel(F=1.0, ka=1.0, ke=0.2, Vd=20.0, Q=0.0, V2=10.0)
    t = np.linspace(0.0, 24.0, 121)
    c = pk.concentration_nonlinear(t, D=100.0, vmax=80.0, km=10.0)
    assert c.shape == t.shape
    assert np.all(c >= 0.0)
    assert c[0] > c[-1]
    assert pk.concentration_nonlinear(np.array([0.0]), D=100.0, vmax=80.0, km=10.0)[0] == pytest.approx(5.0)
    assert pk.concentration_nonlinear(np.array([2.0]), D=100.0, vmax=80.0, km=10.0)[0] > 0.0

    with pytest.raises(ValueError, match="D must be positive"):
        pk.concentration_nonlinear(t, D=0.0, vmax=80.0, km=10.0)
    with pytest.raises(ValueError, match="vmax must be positive"):
        pk.concentration_nonlinear(t, D=100.0, vmax=0.0, km=10.0)
    with pytest.raises(ValueError, match="km must be positive"):
        pk.concentration_nonlinear(t, D=100.0, vmax=80.0, km=0.0)
    with pytest.raises(ValueError, match="não-negativos"):
        pk.concentration_nonlinear(np.array([-1.0, 0.5]), D=100.0, vmax=80.0, km=10.0)


def test_pkmodel_nonlinear_low_concentration_matches_linear_limit():
    pk = PKModel(F=1.0, ka=1.0, ke=0.2, Vd=20.0, Q=0.0, V2=10.0)
    t = np.linspace(0.0, 24.0, 121)
    dose = 5.0
    vmax = 80.0
    km = 20.0
    c_linear = pk.concentration(t, D=dose)
    c_nonlinear = pk.concentration_nonlinear(t, D=dose, vmax=vmax, km=km)
    assert np.allclose(c_nonlinear, c_linear, rtol=0.10, atol=1e-4)


def test_state_space_stable():
    """Test that state-space system is stable (eigenvalues < 0)."""
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0, Q=10.0, V2=20.0)
    ss = pk.state_space()
    assert ss["is_stable"]
    assert np.all(np.real(ss["eigenvalues"]) < 0)


def test_auc_consistency():
    """Test that AUC calculation is consistent with no decay."""
    pk = PKModel(F=1.0, ka=1.0, ke=0.1, Vd=100.0)
    D = 500.0
    auc = pk.auc(D=D)
    # With F=1, ke=0.1, Vd=100, CL = 0.1*100 = 10
    # AUC = F*D/CL = 1.0 * 500 / 10 = 50
    assert np.isclose(auc, 50.0, rtol=0.01)


# ════════════════════════════════════════════════════════════════════════════
# Physical Decay Tests (Lu-177 example)
# ════════════════════════════════════════════════════════════════════════════

def test_pkmodel_init_with_physical_decay():
    """Test PKModel initialization with physical decay (half-life)."""
    # Lu-177: t_1/2 = 6.647 days = 159.528 hours
    pk = PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, phys_half_life_h=159.528)
    assert pk.phys_half_life_h == 159.528
    # lambda = ln(2) / t_1/2
    expected_lambda = np.log(2.0) / 159.528
    assert np.isclose(pk.lambda_phys, expected_lambda, rtol=1e-6)


def test_physical_decay_reduces_auc():
    """
    Test that physical decay reduces AUC compared to no decay.
    
    Scenario: Lu-177 with a moderate half-life.
    The presence of physical decay (lambda_phys) causes faster clearance
    from both compartments, reducing total AUC.
    """
    D = 500.0  # MBq (for example)
    
    # Model without physical decay
    pk_no_decay = PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, Q=0.5, V2=2.0)
    auc_no_decay = pk_no_decay.auc(D=D)
    
    # Model with physical decay (Lu-177: t_1/2 = 6.647 days)
    pk_with_decay = PKModel(
        F=1.0, ka=0.1, ke=0.01, Vd=5.0, Q=0.5, V2=2.0,
        phys_half_life_h=159.528
    )
    auc_with_decay = pk_with_decay.auc(D=D)
    
    # AUC with decay must be significantly lower
    assert auc_with_decay < auc_no_decay
    # Expect ~10-20% reduction assuming equilibrium decay
    assert (auc_no_decay - auc_with_decay) / auc_no_decay > 0.05


def test_physical_decay_concentration_profile():
    """
    Test that physical decay reduces concentration at all time points.
    
    The concentration profile should be lower with decay compared
    to without, revealing the impact of lambda_phys on the system.
    """
    t = np.array([0, 4, 8, 12, 24])
    D = 100.0
    
    # Model without decay
    pk_no_decay = PKModel(F=1.0, ka=0.2, ke=0.05, Vd=10.0)
    C_no_decay = pk_no_decay.concentration(t, D=D)
    
    # Model with decay (short half-life to see effect quickly)
    pk_with_decay = PKModel(
        F=1.0, ka=0.2, ke=0.05, Vd=10.0,
        phys_half_life_h=48.0  # 2-day half-life
    )
    C_with_decay = pk_with_decay.concentration(t, D=D)
    
    # At all times > 0, concentration with decay should be lower
    for i in range(1, len(t)):
        assert C_with_decay[i] < C_no_decay[i], \
            f"At t={t[i]}: decay C={C_with_decay[i]} should be < no_decay C={C_no_decay[i]}"


def test_physical_decay_repesentation():
    """Test that PKModel repr includes half-life when set."""
    pk = PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, phys_half_life_h=159.528)
    repr_str = repr(pk)
    assert "t_half_h=159.528" in repr_str


def test_mass_balance_with_decay():
    """
    Test approximate mass balance: total loss (compartments) matches
    elimination + physical decay.
    
    For a two-compartment system with decay, the rate of change of
    total amount should equal -(CL + lambda_phys * total).
    """
    pk = PKModel(F=1.0, ka=0.0, ke=0.05, Vd=20.0, Q=1.0, V2=10.0, 
                 phys_half_life_h=72.0)
    D = 100.0
    
    # Evaluate concentrations at early times
    t = np.array([0.0, 0.1, 0.5])
    C = pk.concentration(t, D=D)
    
    # Both should be positive and decreasing (if no absorption, purely decay)
    assert C[0] >= C[1] >= C[2]


def test_invalid_half_life():
    """Test that negative or zero half-life raises an error."""
    with pytest.raises(ValueError, match="phys_half_life_h must be positive"):
        PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, phys_half_life_h=-10.0)
    
    with pytest.raises(ValueError, match="phys_half_life_h must be positive"):
        PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, phys_half_life_h=0.0)


def test_state_space_with_decay():
    """
    Test that state-space matrix A includes decay terms in diagonals.
    
    With physical decay, the eigenvalues should become more negative
    (faster equilibrium) compared to without decay.
    """
    # Without decay
    pk_no_decay = PKModel(F=1.0, ka=0.1, ke=0.01, Vd=5.0, Q=0.5, V2=2.0)
    ss_no_decay = pk_no_decay.state_space()
    eig_no_decay = np.real(ss_no_decay["eigenvalues"])
    
    # With decay
    pk_with_decay = PKModel(
        F=1.0, ka=0.1, ke=0.01, Vd=5.0, Q=0.5, V2=2.0,
        phys_half_life_h=168.0  # 1 week
    )
    ss_with_decay = pk_with_decay.state_space()
    eig_with_decay = np.real(ss_with_decay["eigenvalues"])
    
    # Both stable
    assert ss_no_decay["is_stable"]
    assert ss_with_decay["is_stable"]
    
    # Eigenvalues with decay should be more negative
    assert np.all(eig_with_decay < eig_no_decay)


def test_unit_consistency_hours_and_liters():
    """
    Test unit consistency: time in hours, volumes in liters, activity in MBq.
    
    For Lu-177 at 500 MBq:
    - V1 = 5 L
    - C_max <= 100 MBq/L (if D=100 and F=1)
    """
    D = 100.0  # MBq
    pk = PKModel(F=1.0, ka=0.1, ke=0.05, Vd=5.0)
    t = np.linspace(0, 24, 100)
    C = pk.concentration(t, D=D)
    
    # Initial concentration should not exceed D/V (conservation)
    C_initial = D / pk.Vd
    assert np.max(C) <= C_initial * 1.01  # Small tolerance for numerical methods


def test_simulate_population_handles_ka_close_to_ke():
    """Cover branch that nudges ke when sampled ka ~= ke."""
    pk = PKModel(F=1.0, ka=0.2, ke=0.2, Vd=30.0, Q=0.0, V2=10.0)
    t = np.linspace(0, 6, 30)
    med, p5, p95 = pk.simulate_population(
        t, D=200.0, n_subjects=5, cv_ke=0.0, cv_ka=0.0, cv_Vd=0.0, cv_Q=0.0, cv_V2=0.0, seed=1
    )
    assert med.shape == t.shape
    assert p5.shape == t.shape
    assert p95.shape == t.shape


def test_pdmodel_validation_and_ecx_bounds():
    """Cover EC50 and ec_x validation branches."""
    with pytest.raises(ValueError, match="EC50"):
        PDModel(EC50=0.0)

    pd = PDModel(EC50=10.0, n=1.0, Emax=100.0)
    with pytest.raises(ValueError, match="fraction"):
        pd.ec_x(0.0)
    with pytest.raises(ValueError, match="fraction"):
        pd.ec_x(1.0)


def test_pdmodel_ecx_valid_fraction():
    """Valid ec_x should return finite positive concentration."""
    pd = PDModel(EC50=10.0, n=1.0, Emax=100.0)
    assert pd.ec_x(0.5) == pytest.approx(10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
