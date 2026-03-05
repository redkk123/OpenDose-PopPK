import matplotlib

matplotlib.use("Agg")

import pytest

from opendose_poppk import PKModel, simulate_regimen, summarize_regimen, write_regimen_csv, write_regimen_plot


def test_simulate_regimen_basic():
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    res = simulate_regimen(pk=pk, dose=1000.0, interval_h=12.0, n_doses=4, t_end=60.0, n_points=300)
    assert res["t"].shape == res["conc"].shape
    assert res["cmax"] > 0
    assert res["trough_last"] >= 0

    summary = summarize_regimen(res)
    assert summary["n_doses"] == 4
    assert summary["n_points"] == 300


def test_simulate_regimen_default_t_end_and_io(tmp_path):
    pk = PKModel()
    res = simulate_regimen(pk=pk, dose=500.0, interval_h=8.0, n_doses=3)
    assert res["t_end"] == pytest.approx(32.0)

    csv_path = write_regimen_csv(res, tmp_path / "regimen.csv")
    png_path = write_regimen_plot(res, tmp_path / "regimen.png")
    assert (tmp_path / "regimen.csv").exists()
    assert (tmp_path / "regimen.png").exists()
    assert str(tmp_path / "regimen.csv") == csv_path
    assert str(tmp_path / "regimen.png") == png_path

    # Cover branch when simulation horizon is before final scheduled dose time.
    short_res = simulate_regimen(pk=pk, dose=500.0, interval_h=8.0, n_doses=3, t_end=4.0, n_points=20)
    assert short_res["trough_last"] == pytest.approx(float(short_res["conc"].min()))


def test_simulate_regimen_validation_errors():
    pk = PKModel()
    with pytest.raises(ValueError, match="interval_h must be positive"):
        simulate_regimen(pk=pk, dose=100.0, interval_h=0.0, n_doses=3)
    with pytest.raises(ValueError, match="n_doses must be at least 1"):
        simulate_regimen(pk=pk, dose=100.0, interval_h=8.0, n_doses=0)
    with pytest.raises(ValueError, match="dose must be positive"):
        simulate_regimen(pk=pk, dose=0.0, interval_h=8.0, n_doses=3)
    with pytest.raises(ValueError, match="n_points must be at least 2"):
        simulate_regimen(pk=pk, dose=100.0, interval_h=8.0, n_doses=3, n_points=1)
    with pytest.raises(ValueError, match="t_end must be positive"):
        simulate_regimen(pk=pk, dose=100.0, interval_h=8.0, n_doses=3, t_end=0.0)
