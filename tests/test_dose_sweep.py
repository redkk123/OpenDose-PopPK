import numpy as np
import pytest

from opendose_poppk import PKModel, sweep_dose_response


def test_sweep_dose_response_basic():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    res = sweep_dose_response(pk=pk, doses=[250, 500, 750, 1000], t_end=24.0, n_points=300)
    assert res["n_doses"] == 4
    assert res["dose_min"] == 250.0
    assert res["dose_max"] == 1000.0
    assert res["monotonic_cmax"] is True
    assert res["monotonic_auc"] is True
    assert len(res["rows"]) == 4

    cmax_values = [r["cmax"] for r in res["rows"]]
    auc_values = [r["auc"] for r in res["rows"]]
    assert np.all(np.diff(cmax_values) > 0)
    assert np.all(np.diff(auc_values) > 0)


def test_sweep_dose_response_validation():
    pk = PKModel()
    with pytest.raises(ValueError, match="doses cannot be empty"):
        sweep_dose_response(pk=pk, doses=[])
    with pytest.raises(ValueError, match="doses must be finite"):
        sweep_dose_response(pk=pk, doses=[100, np.nan])
    with pytest.raises(ValueError, match="doses must be positive"):
        sweep_dose_response(pk=pk, doses=[100, 0])
    with pytest.raises(ValueError, match="t_end must be positive"):
        sweep_dose_response(pk=pk, doses=[100], t_end=0.0)
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        sweep_dose_response(pk=pk, doses=[100], n_points=1)
