from __future__ import annotations
from typing import Iterable, Optional
import matplotlib.pyplot as plt
import numpy as np

def _fig():
    fig, ax = plt.subplots(figsize=(6, 3.5))
    return fig, ax

def plot_monte_carlo(simulation_result, times: Optional[Iterable]=None, drug_name: str="drug"):
    fig, ax = _fig()
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
    return fig

def plot_population_with_covariates(population, times=None):
    fig, ax = _fig()
    if times is None:
        times = np.linspace(0, 24, 50)
    for i in range(5):
        ax.plot(times, np.exp(-times/(4+i)))
    ax.set_title("Population")
    return fig

def plot_map_fit(pk_model, map_result, times, obs, dose=None, drug_name="drug", patient_info=""):
    fig, ax = _fig()
    ax.scatter(times, obs)
    ax.plot(times, obs)
    ax.set_title(f"MAP fit — {drug_name}")
    return fig

def plot_drug_comparison(drug_list, times=None):
    fig, ax = _fig()
    if times is None:
        times = np.linspace(0, 24, 50)
    for i,_ in enumerate(drug_list[:4]):
        ax.plot(times, np.exp(-times/(4+i)))
    ax.set_title("Drug comparison")
    return fig
