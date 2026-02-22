"""
opendose_poppk.population
=========================
Population simulation with covariates.

Classes
-------
PopulationSimulator : Monte Carlo simulation of heterogeneous populations
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from .pk_model import PKModel, PDModel
from .covariate import CovariateModel


class PopulationSimulator:
    """
    Monte Carlo simulation of heterogeneous population with covariates.

    Integrates PKModel + PDModel + CovariateModel to generate individual
    PK/PD profiles with realistic covariate distributions.

    Example
    -------
    >>> pk  = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    >>> pd  = PDModel(EC50=10.0, n=1.5)
    >>> sim = PopulationSimulator(pk, pd, dose=1000.0)
    >>> res = sim.run(n_subjects=1000, t_max=12.0,
    ...               covariates={"weight": ("normal", 70, 15),
    ...                           "crcl":   ("normal", 90, 30)})
    """

    _BOUNDS = {
        "weight": (30,  200), "crcl": (10, 180),
        "age":    (18,  100), "alt":  ( 5, 500), "bmi": (15, 60),
    }

    def __init__(self, pk: Optional[PKModel] = None,
                 pd: Optional[PDModel] = None,
                 covariate_model: Optional[CovariateModel] = None,
                 dose: float = 1000.0):
        self.pk   = pk or PKModel()
        self.pd   = pd
        self.cov  = covariate_model or CovariateModel(self.pk)
        self.dose = dose

    def run(self,
            n_subjects: int = 1000,
            t_max: float = 24.0,
            n_points: int = 200,
            covariates: dict | None = None,
            seed: int = 42) -> dict:
        """
        Execute Monte Carlo simulation.

        Parameters
        ----------
        n_subjects  : simulated population size
        t_max       : final time (h)
        n_points    : number of points in time curve
        covariates  : covariate distributions.
                      Format: {"name": ("type", p1, p2)}
                      Types: "normal", "uniform", "lognormal"
                      Example: {"weight": ("normal", 70, 15)}
        seed        : random seed

        Returns
        -------
        dict with t, pk_profiles, pd_profiles, percentiles_pk,
                 percentiles_pd, covariates_sim
        """
        rng = np.random.default_rng(seed)
        t   = np.linspace(0, t_max, n_points)

        if covariates is None:
            covariates = {
                "weight": ("normal", 70.0, 15.0),
                "crcl":   ("normal", 90.0, 25.0),
                "age":    ("normal", 40.0, 15.0),
            }

        # Simulate population covariates
        cov_sim = {}
        for name, spec in covariates.items():
            kind = spec[0]
            vals = (rng.normal(spec[1], spec[2], n_subjects)   if kind == "normal"    else
                    rng.uniform(spec[1], spec[2], n_subjects)  if kind == "uniform"   else
                    rng.lognormal(np.log(spec[1]), spec[2], n_subjects))
            lo, hi = self._BOUNDS.get(name, (1e-9, 1e9))
            cov_sim[name] = np.clip(vals, lo, hi)

        sexes = rng.choice(["M", "F"], n_subjects)

        pk_profiles = np.zeros((n_subjects, n_points))
        pd_profiles = np.zeros((n_subjects, n_points)) if self.pd else None

        for i in range(n_subjects):
            ind = {k: v[i] for k, v in cov_sim.items()}
            p   = self.cov.individualize(ind, sex=sexes[i], rng=rng)
            m   = PKModel(**p)
            pk_profiles[i] = m.concentration(t, D=self.dose)
            if self.pd:
                pd_profiles[i] = self.pd.effect(pk_profiles[i])

        pct = [5, 50, 95]
        return {
            "t":               t,
            "pk_profiles":     pk_profiles,
            "pd_profiles":     pd_profiles,
            "percentiles_pk":  {p: np.percentile(pk_profiles, p, axis=0) for p in pct},
            "percentiles_pd":  ({p: np.percentile(pd_profiles, p, axis=0) for p in pct}
                                if pd_profiles is not None else None),
            "covariates_sim":  cov_sim,
            "sexes":           sexes,
        }

    def simulate(self, n: int = 10) -> list[np.ndarray]:
        """
        Legacy compatibility method: returns list of profiles.
        
        This simplifies testing - just check the array size.
        """
        res = self.run(n_subjects=n, n_points=50)
        profiles = [res["pk_profiles"][i] for i in range(res["pk_profiles"].shape[0])]
        return profiles
