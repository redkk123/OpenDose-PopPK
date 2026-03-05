import pytest

from opendose_poppk import PKModel, recommend_dose_for_target_auc, recommend_dose_for_target_cmax


def test_recommend_dose_for_target_cmax():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    target = 10.0
    res = recommend_dose_for_target_cmax(pk, target_cmax=target, t_end=24.0, n_points=500)
    assert res["mode"] == "cmax"
    assert res["target"] == target
    assert res["recommended_dose"] > 0
    assert res["predicted"] == pytest.approx(target, rel=1e-2)


def test_recommend_dose_for_target_auc():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    target = 50.0
    res = recommend_dose_for_target_auc(pk, target_auc=target)
    assert res["mode"] == "auc"
    assert res["recommended_dose"] > 0
    assert res["predicted"] == pytest.approx(target, rel=1e-8)


def test_recommend_dose_validation_errors(monkeypatch):
    pk = PKModel()
    with pytest.raises(ValueError, match="target_cmax must be positive"):
        recommend_dose_for_target_cmax(pk, target_cmax=0.0)
    with pytest.raises(ValueError, match="t_end must be positive"):
        recommend_dose_for_target_cmax(pk, target_cmax=1.0, t_end=0.0)
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        recommend_dose_for_target_cmax(pk, target_cmax=1.0, n_points=1)

    class _ZeroPK:
        def concentration(self, t, D=1.0):
            import numpy as np

            return np.zeros(len(t))

    with pytest.raises(ValueError, match="unit Cmax"):
        recommend_dose_for_target_cmax(_ZeroPK(), target_cmax=1.0)

    with pytest.raises(ValueError, match="target_auc must be positive"):
        recommend_dose_for_target_auc(pk, target_auc=0.0)

    class _ZeroAUC:
        def auc(self, D=1.0):
            return 0.0

    with pytest.raises(ValueError, match="unit AUC"):
        recommend_dose_for_target_auc(_ZeroAUC(), target_auc=1.0)
