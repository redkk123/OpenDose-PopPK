import pytest

from opendose_poppk import (
    PKModel,
    recommend_regimen_dose_for_target_cmax,
    recommend_regimen_dose_for_target_trough,
    recommend_regimen_dose_for_target_window,
)


def test_recommend_regimen_dose_for_target_cmax():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    target = 12.0
    res = recommend_regimen_dose_for_target_cmax(
        pk=pk, target_cmax=target, interval_h=12.0, n_doses=4, t_end=60.0, n_points=400
    )
    assert res["mode"] == "regimen_cmax"
    assert res["recommended_dose"] > 0
    assert res["predicted"] == pytest.approx(target, rel=1e-2)


def test_recommend_regimen_dose_for_target_trough():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    target = 1.0
    res = recommend_regimen_dose_for_target_trough(
        pk=pk, target_trough=target, interval_h=12.0, n_doses=4, t_end=60.0, n_points=400
    )
    assert res["mode"] == "regimen_trough"
    assert res["recommended_dose"] > 0
    assert res["predicted"] == pytest.approx(target, rel=1e-2)


def test_recommend_regimen_dose_validation():
    pk = PKModel()
    with pytest.raises(ValueError, match="target_cmax must be positive"):
        recommend_regimen_dose_for_target_cmax(pk, target_cmax=0.0, interval_h=12.0, n_doses=3)
    with pytest.raises(ValueError, match="target_trough must be positive"):
        recommend_regimen_dose_for_target_trough(pk, target_trough=0.0, interval_h=12.0, n_doses=3)
    with pytest.raises(ValueError, match="interval_h must be positive"):
        recommend_regimen_dose_for_target_cmax(pk, target_cmax=1.0, interval_h=0.0, n_doses=3)
    with pytest.raises(ValueError, match="n_doses must be at least 1"):
        recommend_regimen_dose_for_target_cmax(
            pk, target_cmax=1.0, interval_h=12.0, n_doses=0, t_end=24.0, n_points=100
        )
    with pytest.raises(ValueError, match="t_end must be positive"):
        recommend_regimen_dose_for_target_cmax(
            pk, target_cmax=1.0, interval_h=12.0, n_doses=3, t_end=0.0, n_points=100
        )
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        recommend_regimen_dose_for_target_cmax(
            pk, target_cmax=1.0, interval_h=12.0, n_doses=3, t_end=24.0, n_points=1
        )

    class _ZeroPK:
        def concentration_multiple_dose(self, t, D=1.0, interval_h=12.0, n_doses=3):
            import numpy as np

            return np.zeros(len(t))

    with pytest.raises(ValueError, match="unit regimen Cmax"):
        recommend_regimen_dose_for_target_cmax(_ZeroPK(), target_cmax=1.0, interval_h=12.0, n_doses=3)
    with pytest.raises(ValueError, match="unit regimen trough"):
        recommend_regimen_dose_for_target_trough(_ZeroPK(), target_trough=1.0, interval_h=12.0, n_doses=3)


def test_recommend_regimen_dose_window_feasible_and_midpoint():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    res_min = recommend_regimen_dose_for_target_window(
        pk=pk,
        target_trough_min=0.05,
        target_cmax_max=12.0,
        interval_h=12.0,
        n_doses=4,
        strategy="trough_min",
    )
    assert res_min["mode"] == "regimen_window"
    assert res_min["feasible"] is True
    assert res_min["recommended_dose"] == pytest.approx(res_min["dose_lower_bound"], rel=1e-8)
    assert res_min["predicted_trough"] == pytest.approx(0.05, rel=1e-4)
    assert res_min["predicted_cmax"] <= 12.0

    res_mid = recommend_regimen_dose_for_target_window(
        pk=pk,
        target_trough_min=0.05,
        target_cmax_max=12.0,
        interval_h=12.0,
        n_doses=4,
        strategy="midpoint",
    )
    assert res_mid["feasible"] is True
    assert res_mid["dose_lower_bound"] <= res_mid["recommended_dose"] <= res_mid["dose_upper_bound"]


def test_recommend_regimen_dose_window_infeasible_and_validation():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    res = recommend_regimen_dose_for_target_window(
        pk=pk,
        target_trough_min=5.0,
        target_cmax_max=6.0,
        interval_h=12.0,
        n_doses=4,
    )
    assert res["feasible"] is False
    assert res["recommended_dose"] is None
    assert res["predicted_cmax"] is None
    assert res["predicted_trough"] is None
    assert res["dose_lower_bound"] > res["dose_upper_bound"]

    with pytest.raises(ValueError, match="target_trough_min must be positive"):
        recommend_regimen_dose_for_target_window(
            pk=pk,
            target_trough_min=0.0,
            target_cmax_max=10.0,
            interval_h=12.0,
            n_doses=4,
        )
    with pytest.raises(ValueError, match="target_cmax_max must be positive"):
        recommend_regimen_dose_for_target_window(
            pk=pk,
            target_trough_min=1.0,
            target_cmax_max=0.0,
            interval_h=12.0,
            n_doses=4,
        )
    with pytest.raises(ValueError, match="target_trough_min must be lower than target_cmax_max"):
        recommend_regimen_dose_for_target_window(
            pk=pk,
            target_trough_min=10.0,
            target_cmax_max=5.0,
            interval_h=12.0,
            n_doses=4,
        )
    with pytest.raises(ValueError, match="strategy must be 'trough_min' or 'midpoint'"):
        recommend_regimen_dose_for_target_window(
            pk=pk,
            target_trough_min=1.0,
            target_cmax_max=10.0,
            interval_h=12.0,
            n_doses=4,
            strategy="invalid",
        )

    class _ZeroPK:
        def concentration_multiple_dose(self, t, D=1.0, interval_h=12.0, n_doses=3):
            import numpy as np

            return np.zeros(len(t))

    class _ZeroTroughPK:
        def concentration_multiple_dose(self, t, D=1.0, interval_h=12.0, n_doses=3):
            import numpy as np

            prof = np.ones(len(t))
            prof[t >= (n_doses - 1) * interval_h] = 0.0
            return prof

    with pytest.raises(ValueError, match="unit regimen Cmax"):
        recommend_regimen_dose_for_target_window(
            _ZeroPK(),
            target_trough_min=0.05,
            target_cmax_max=12.0,
            interval_h=12.0,
            n_doses=4,
        )
    with pytest.raises(ValueError, match="unit regimen trough"):
        recommend_regimen_dose_for_target_window(
            _ZeroTroughPK(),
            target_trough_min=0.05,
            target_cmax_max=12.0,
            interval_h=12.0,
            n_doses=4,
        )
