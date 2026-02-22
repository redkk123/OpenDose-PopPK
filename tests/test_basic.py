import numpy as np
from opendose import PKModel

def test_concentration_positive():

    pk = PKModel(CL=5, V=50)

    t = np.linspace(0,10,100)

    C = pk.concentration(t, D=100)

    assert (C >= 0).all()


def test_concentration_decreases():

    pk = PKModel(CL=5, V=50)

    c0 = pk.concentration(0, D=100)
    c1 = pk.concentration(10, D=100)

    assert c1 < c0