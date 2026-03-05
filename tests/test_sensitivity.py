import numpy as np
import pytest

from opendose_poppk import PKModel, local_pk_sensitivity


def test_local_pk_sensitivity_basic_behavior():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    res = local_pk_sensitivity(pk=pk, dose=1000.0, t_end=24.0, n_points=300, rel_step=0.1)
    assert res["baseline_cmax"] > 0
    assert res["baseline_auc"] > 0
    assert len(res["results"]) == 4

    by_param = {r["parameter"]: r for r in res["results"]}
    assert by_param["F"]["sensitivity_cmax"] > 0
    assert by_param["F"]["sensitivity_auc"] > 0
    assert by_param["ke"]["sensitivity_auc"] < 0
    assert by_param["Vd"]["sensitivity_cmax"] < 0


def test_local_pk_sensitivity_validation_errors():
    pk = PKModel()
    with pytest.raises(ValueError, match="dose must be positive"):
        local_pk_sensitivity(pk=pk, dose=0.0)
    with pytest.raises(ValueError, match="t_end must be positive"):
        local_pk_sensitivity(pk=pk, t_end=0.0)
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        local_pk_sensitivity(pk=pk, n_points=1)
    with pytest.raises(ValueError, match="rel_step must be in"):
        local_pk_sensitivity(pk=pk, rel_step=1.0)

    class _ZeroCmaxPK:
        F = 1.0
        ka = 1.0
        ke = 0.2
        Vd = 10.0
        Q = 1.0
        V2 = 5.0
        phys_half_life_h = None

        def concentration(self, t, D=1000.0):
            return np.zeros(len(t))

        def auc(self, D=1000.0):
            return 1.0

    with pytest.raises(ValueError, match="baseline Cmax must be positive"):
        local_pk_sensitivity(_ZeroCmaxPK())

    class _ZeroAucPK:
        F = 1.0
        ka = 1.0
        ke = 0.2
        Vd = 10.0
        Q = 1.0
        V2 = 5.0
        phys_half_life_h = None

        def concentration(self, t, D=1000.0):
            return np.ones(len(t))

        def auc(self, D=1000.0):
            return 0.0

    with pytest.raises(ValueError, match="baseline AUC must be positive"):
        local_pk_sensitivity(_ZeroAucPK())

    class _BadParamPK:
        F = 0.0
        ka = 1.0
        ke = 0.2
        Vd = 10.0
        Q = 1.0
        V2 = 5.0
        phys_half_life_h = None

        def concentration(self, t, D=1000.0):
            return np.ones(len(t))

        def auc(self, D=1000.0):
            return 1.0

    with pytest.raises(ValueError, match="invalid perturbed values"):
        local_pk_sensitivity(_BadParamPK())
