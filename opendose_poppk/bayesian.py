"""
opendose_poppk.bayesian
=======================
Bayesian individual parameter estimation.

Classes
-------
MAPEstimator : Maximum A Posteriori individual parameter estimation
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from typing import Optional

from .pk_model import PKModel
from .covariate import CovariateModel


class MAPEstimator:
    """
    Bayesian individual parameter estimation (Maximum A Posteriori).

    Finds individual etas that minimize:
        obj = Σ[(C_obs − C_pred)² / σ²]  +  Σ[ηᵢ² / ωᵢ²]
              └─ data fidelity ──────┘    └─ population prior ─┘

    Example
    -------
    >>> est = MAPEstimator(pk, covariate_model=cov)
    >>> res = est.fit(
    ...     times=np.array([1, 2, 4, 6]),
    ...     obs  =np.array([6.8, 7.5, 5.9, 4.1]),
    ...     patient_covariates={"weight": 90, "crcl": 50},
    ...     dose=1000.0
    ... )
    >>> print(res["params_map"])
    """

    def __init__(self, pk: Optional[PKModel] = None,
                 covariate_model: Optional[CovariateModel] = None,
                 sigma_obs: float = 1.0):
        self.pk    = pk or PKModel()
        self.cov   = covariate_model or CovariateModel(self.pk)
        self.sigma = sigma_obs

    def fit(self, times: np.ndarray, obs: np.ndarray,
            patient_covariates: dict, dose: float,
            n_iter: int = 3000) -> dict:
        """
        Fit individual parameters for a patient.

        Parameters
        ----------
        times : observation times (h)
        obs : observed concentrations
        patient_covariates : patient's covariate values
        dose : administered dose
        n_iter : maximum optimizer iterations

        Returns
        -------
        dict with params_map, eta_map, pop_adjusted, converged, obj_value
        """
        omega   = self.cov.omega
        pop_adj = {
            p: self.cov._adjust(getattr(self.pk, p), p,
                                patient_covariates, eta=0.0)
            for p in ("F", "ka", "ke", "Vd")
        }

        def obj(eta_vec):
            eta = dict(zip(("Vd", "ke", "ka", "F"), eta_vec))
            p   = {k: pop_adj[k] * np.exp(eta[k]) for k in pop_adj}
            p["F"] = np.clip(p["F"], 0.01, 1.0)
            if abs(p["ka"] - p["ke"]) < 1e-4:
                return 1e8
            C     = PKModel(**p).concentration(times, D=dose)
            resid = ((obs - C) ** 2 / self.sigma ** 2).sum()
            prior = sum((eta[k] / omega[k]) ** 2 for k in ("Vd", "ke", "ka", "F"))
            return 0.5 * (resid + prior)

        res     = minimize(obj, np.zeros(4), method="Nelder-Mead",
                           options={"maxiter": n_iter, "xatol": 1e-6, "fatol": 1e-6})
        eta_map = res.x
        params  = {k: pop_adj[k] * np.exp(eta_map[i])
                   for i, k in enumerate(("Vd", "ke", "ka", "F"))}

        return {
            "params_map":   params,
            "eta_map":      dict(zip(("Vd", "ke", "ka", "F"), eta_map)),
            "pop_adjusted": pop_adj,
            "converged":    res.success,
            "obj_value":    res.fun,
        }
