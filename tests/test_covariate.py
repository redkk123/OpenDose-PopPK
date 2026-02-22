import numpy as np

from opendose_poppk.covariate import CovariateModel


class _DummyPK:
    def __init__(self, F=1.0, ka=1.0, ke=0.5, Vd=10.0):
        self.F = F
        self.ka = ka
        self.ke = ke
        self.Vd = Vd


def test_adjust_power_model():
    pk = _DummyPK(Vd=50.0)
    cov = CovariateModel(pk)

    # weight has beta 1.0 for Vd (default ref 70.0)
    theta = pk.Vd
    result = cov._adjust(theta, "Vd", {"weight": 140.0}, eta=0.0)
    # doubling weight should double Vd when beta == 1.0
    assert abs(result - (theta * (140.0 / 70.0))) < 1e-8


def test_individualize_sex_and_limits():
    # deterministic: set omega to zeros
    pk = _DummyPK(F=1.5, ka=1.0, ke=1.0, Vd=0.05)
    cov = CovariateModel(pk, omega={"Vd": 0.0, "ke": 0.0, "ka": 0.0, "F": 0.0})

    # Female reduces Vd by factor 0.9; Vd should be clipped to minimum 0.10
    out = cov.individualize({}, sex="F")
    assert out["Vd"] >= 0.10

    # F should be clipped to 1.0 (was 1.5)
    assert out["F"] == 1.0

    # when ka == ke, ke should be multiplied by 0.99
    assert abs(out["ka"] - out["ke"]) > 1e-6


def test_set_beta_and_add_covariate():
    pk = _DummyPK(F=0.8, ka=1.0, ke=0.5, Vd=20.0)
    cov = CovariateModel(pk, omega={"Vd": 0.0, "ke": 0.0, "ka": 0.0, "F": 0.0})

    # add a new covariate and set its beta
    cov.add_covariate("albumin", reference=4.0, betas={"Vd": 0.5})
    out = cov.individualize({"albumin": 8.0}, sex="M")
    # albumin doubled -> Vd multiplied by (8/4)^0.5 = sqrt(2)
    assert abs(out["Vd"] - (pk.Vd * (8.0 / 4.0) ** 0.5)) < 1e-8

    # update an existing beta (weight -> ke)
    cov.set_beta("weight", "ke", 0.5)
    # now ke should respond to weight covariate
    out2 = cov.individualize({"weight": 140.0}, sex="M")
    assert out2["ke"] != pk.ke
