import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from opendose_poppk import (
    DrugDatabase,
    MAPEstimator,
    PDModel,
    PKModel,
    PopulationSimulator,
    CovariateModel,
    plot_drug_comparison,
    plot_map_fit,
    plot_monte_carlo,
    plot_population_with_covariates,
)


def test_plot_monte_carlo_with_pk_model():
    pk = PKModel(F=1.0, ka=1.2, ke=0.25, Vd=60.0)
    fig = plot_monte_carlo(pk, dose=1000.0, n_subjects=20, t_max=12.0, drug_name="TestDrug")
    assert fig is not None
    plt.close(fig)


def test_plot_population_with_covariates_from_result():
    pk = PKModel(F=1.0, ka=1.1, ke=0.2, Vd=55.0)
    pd = PDModel(EC50=20.0, n=1.3)
    cov = CovariateModel(pk)
    sim = PopulationSimulator(pk=pk, pd=pd, covariate_model=cov, dose=500.0)
    result = sim.run(n_subjects=20, t_max=12.0, n_points=50, seed=42)

    fig = plot_population_with_covariates(result, drug_name="TestDrug", dose=500.0)
    assert fig is not None
    plt.close(fig)


def test_plot_map_fit_with_map_result():
    db = DrugDatabase("datasets/drugs_parameters.csv")
    drug = db.get_drug("Paracetamol")
    pk = PKModel(**drug.pk_kwargs)
    cov = CovariateModel(pk)
    est = MAPEstimator(pk, covariate_model=cov, sigma_obs=0.8)

    t_obs = np.array([0.5, 1.0, 2.0, 4.0, 6.0])
    c_obs = np.array([4.2, 6.7, 7.4, 5.8, 4.0])
    result = est.fit(t_obs, c_obs, {"weight": 80.0, "crcl": 70.0, "age": 55.0}, dose=drug.dose)

    fig = plot_map_fit(pk, result, t_obs, c_obs, dose=drug.dose, drug_name=drug.name)
    assert fig is not None
    plt.close(fig)


def test_plot_drug_comparison_with_dict_input():
    db = DrugDatabase("datasets/drugs_parameters.csv")
    names = ["Paracetamol", "Ibuprofen", "Diazepam", "Metformin"]
    panel = {name: db.get_drug(name) for name in names}

    fig = plot_drug_comparison(panel, t_max=24.0)
    assert fig is not None
    plt.close(fig)


def test_plot_monte_carlo_with_array_inputs_and_fallback():
    times = np.linspace(0.0, 12.0, 20)
    arr_2d = np.tile(np.linspace(1.0, 0.2, 20), (4, 1))
    fig = plot_monte_carlo(arr_2d, times=times, drug_name="Array2D")
    assert fig is not None
    plt.close(fig)

    arr_1d = np.linspace(1.0, 0.1, 20)
    fig = plot_monte_carlo(arr_1d, times=times, drug_name="Array1D")
    assert fig is not None
    plt.close(fig)

    fig = plot_monte_carlo(arr_1d, times=None, drug_name="Array1DNoTimes")
    assert fig is not None
    plt.close(fig)

    fig = plot_monte_carlo("not-an-array-like-profile", times=times, drug_name="Fallback")
    assert fig is not None
    plt.close(fig)


def test_plot_population_with_covariates_fallback_branch():
    times = np.linspace(0.0, 10.0, 15)
    fig = plot_population_with_covariates(population=[1, 2, 3], times=times)
    assert fig is not None
    plt.close(fig)

    fig = plot_population_with_covariates(population=[1, 2, 3], times=None)
    assert fig is not None
    plt.close(fig)


def test_plot_map_fit_without_params_map_and_with_patient_info():
    pk = PKModel(F=1.0, ka=1.0, ke=0.2, Vd=40.0)
    t_obs = np.array([1.0, 2.0, 4.0])
    c_obs = np.array([4.0, 3.0, 1.5])

    fig = plot_map_fit(
        pk_model=pk,
        map_result={"any": "value"},
        times=t_obs,
        obs=c_obs,
        dose=500.0,
        drug_name="TestDrug",
        patient_info="age=60",
    )
    assert fig is not None
    plt.close(fig)


def test_plot_drug_comparison_list_and_exception_branch(monkeypatch):
    class _DrugLike:
        pk_kwargs = {"F": 1.0, "ka": 1.0, "ke": 0.2, "Vd": 20.0}
        dose = 100.0

    class _BadPK:
        def __init__(self, **kwargs):
            raise RuntimeError("boom")

    import opendose_poppk.plotting as plotting_mod

    monkeypatch.setattr(plotting_mod, "PKModel", _BadPK, raising=False)
    fig = plot_drug_comparison([_DrugLike()], t_max=12.0)
    assert fig is not None
    plt.close(fig)

    class _BadDrugLike:
        pk_kwargs = {"F": "bad-value", "ka": 1.0, "ke": 0.2, "Vd": 20.0}
        dose = 100.0

    fig = plot_drug_comparison([_BadDrugLike()], t_max=12.0)
    assert fig is not None
    plt.close(fig)

    fig = plot_drug_comparison([1, 2, 3], t_max=12.0)
    assert fig is not None
    plt.close(fig)
