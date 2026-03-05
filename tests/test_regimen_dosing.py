import pytest

from opendose_poppk import (
    PKModel,
    recommend_regimen_dose_for_target_cmax,
    recommend_regimen_dose_for_target_trough,
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
