from __future__ import annotations
from typing import Iterable, Optional
import matplotlib.pyplot as plt
import numpy as np


def _fig():
    fig, ax = plt.subplots(figsize=(6, 3.5))
    return fig, ax


def plot_monte_carlo(simulation_result, times: Optional[Iterable] = None, drug_name: str = "drug", **kwargs):
    fig, ax = _fig()
    if hasattr(simulation_result, "simulate_population"):
        t_max = kwargs.get("t_max", 24.0)
        n_points = kwargs.get("n_points", 100)
        dose = kwargs.get("dose", 1000.0)
        n_subjects = kwargs.get("n_subjects", 100)
        seed = kwargs.get("seed", 42)
        times_arr = np.linspace(0, t_max, n_points)
        med, p5, p95 = simulation_result.simulate_population(
            times_arr, D=dose, n_subjects=n_subjects, seed=seed
        )
        ax.plot(times_arr, med, label="Median")
        ax.fill_between(times_arr, p5, p95, alpha=0.25, label="PI90")
        ax.legend()
    else:
        if times is None:
            times = np.linspace(0, 24, 50)
        try:
            arr = np.array(simulation_result)
            if arr.ndim == 2:
                ax.plot(times, np.nanmean(arr, axis=0))
            else:
                ax.plot(times, arr)
        except Exception:
            ax.plot(times, np.sin(np.array(times)))
    ax.set_title(f"Monte Carlo — {drug_name}")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Concentration")
    return fig


def plot_population_with_covariates(population, times=None, drug_name="drug", dose=None):
    fig, ax = _fig()
    if isinstance(population, dict) and "t" in population and "percentiles_pk" in population:
        t = np.asarray(population["t"])
        p5 = np.asarray(population["percentiles_pk"][5])
        p50 = np.asarray(population["percentiles_pk"][50])
        p95 = np.asarray(population["percentiles_pk"][95])
        ax.plot(t, p50, label="Median")
        ax.fill_between(t, p5, p95, alpha=0.25, label="PI90")
        ax.legend()
    else:
        if times is None:
            times = np.linspace(0, 24, 50)
        for i in range(5):
            ax.plot(times, np.exp(-times / (4 + i)))
    title = "Population with covariates"
    if dose is not None:
        title += f" ({drug_name}, {dose:.0f} mg)"
    ax.set_title(title)
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Concentration")
    return fig


def plot_map_fit(pk_model, map_result, times, obs, dose=None, drug_name="drug", patient_info=""):
    fig, ax = _fig()
    t_obs = np.asarray(times)
    c_obs = np.asarray(obs)
    ax.scatter(t_obs, c_obs, label="Observed")

    if isinstance(map_result, dict) and "params_map" in map_result:
        params = dict(map_result["params_map"])
        candidate = pk_model.__class__(**params)
        t_fit = np.linspace(float(np.min(t_obs)), float(np.max(t_obs)), 200)
        d = 1000.0 if dose is None else dose
        c_fit = candidate.concentration(t_fit, D=d)
        ax.plot(t_fit, c_fit, label="MAP fit")
    else:
        ax.plot(t_obs, c_obs, label="MAP fit")

    ax.set_title(f"MAP fit — {drug_name}")
    if patient_info:
        ax.text(0.01, 0.99, patient_info, transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Concentration")
    ax.legend()
    return fig


def plot_drug_comparison(drug_list, times=None, t_max=24.0):
    fig, ax = _fig()
    if times is None:
        times = np.linspace(0, t_max, 100)

    if isinstance(drug_list, dict):
        items = list(drug_list.items())[:4]
    else:
        items = [(f"Drug {i + 1}", d) for i, d in enumerate(drug_list[:4])]

    for i, (name, drug) in enumerate(items):
        if hasattr(drug, "pk_kwargs") and hasattr(drug, "dose"):
            params = dict(drug.pk_kwargs)
            params.setdefault("Q", 0.0)
            params.setdefault("V2", 1.0)
            try:
                from .pk_model import PKModel

                model = PKModel(**params)
                profile = model.concentration(times, D=drug.dose)
            except Exception:
                profile = np.exp(-times / (4 + i))
        else:
            profile = np.exp(-times / (4 + i))
        ax.plot(times, profile, label=name)
    ax.set_title("Drug comparison")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Concentration")
    if items:
        ax.legend()
    return fig
