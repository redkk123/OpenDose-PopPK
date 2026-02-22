"""
opendose_poppk.covariate
========================
Covariate modeling for population pharmacokinetics.

Classes
-------
CovariateModel : Apply covariates to PK parameters via Power Model
"""

from __future__ import annotations

import numpy as np
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .pk_model import PKModel


# Reference values (population median)
_COV_REF = {
    "weight": 70.0,   # kg
    "age":    40.0,   # years
    "crcl":   90.0,   # mL/min (creatinine clearance)
    "alt":    30.0,   # U/L (hepatic function)
    "bmi":    25.0,   # kg/m²
}

# Beta coefficients: (covariate, parameter) → effect strength
# 0 = no effect; positive = increases; negative = decreases
_COV_BETA = {
    #               Vd      ke      ka      F
    "weight": {"Vd": 1.00, "ke": 0.00, "ka": 0.00, "F": 0.00},
    "age":    {"Vd": 0.00, "ke":-0.40, "ka": 0.00, "F": 0.00},
    "crcl":   {"Vd": 0.00, "ke": 0.75, "ka": 0.00, "F": 0.00},
    "alt":    {"Vd": 0.00, "ke":-0.30, "ka": 0.00, "F":-0.10},
    "bmi":    {"Vd": 0.50, "ke": 0.00, "ka": 0.00, "F": 0.00},
}

# Residual variability (after explaining covariates)
_OMEGA = {"Vd": 0.30, "ke": 0.20, "ka": 0.25, "F": 0.10}


class CovariateModel:
    """
    Apply covariates to PK parameters via Power Model.

    Formula
    -------
    θᵢ = θ_pop · ∏ (COVₖ / refₖ)^βₖ · exp(ηᵢ)

    Where:
        θ_pop → typical population parameter
        COVₖ  → patient's covariate value
        refₖ  → reference value (median)
        βₖ    → effect coefficient (beta)
        ηᵢ    → random deviation ~ N(0, ω²)

    Example
    -------
    >>> pk  = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    >>> cov = CovariateModel(pk)
    >>> p   = cov.individualize({"weight": 90, "crcl": 50}, sex="M")
    >>> print(p)  # {"F": ..., "ka": ..., "ke": ..., "Vd": ...}
    """

    _SEX_Vd = {"M": 1.00, "F": 0.90}

    def __init__(self, pk: PKModel,
                 omega: dict | None = None,
                 betas: dict | None = None,
                 references: dict | None = None):
        self.pk    = pk
        self.omega = dict(_OMEGA) if omega is None else omega
        self.betas = {k: dict(v) for k, v
                      in _COV_BETA.items()} if betas is None else betas
        self.refs  = dict(_COV_REF) if references is None else references

    def _adjust(self, theta: float, param: str,
                covariates: dict, eta: float = 0.0) -> float:
        """Apply power model to a single parameter."""
        mult = 1.0
        for cov, val in covariates.items():
            beta = self.betas.get(cov, {}).get(param, 0.0)
            if beta != 0.0 and cov in self.refs:
                mult *= (val / self.refs[cov]) ** beta
        return theta * mult * np.exp(eta)

    def individualize(self, covariates: dict,
                      sex: str = "M",
                      rng: np.random.Generator | None = None) -> dict:
        """
        Generate individual PK parameters with covariates + IIV.

        Parameters
        ----------
        covariates : {"weight": 85.0, "crcl": 60.0, "age": 65.0, ...}
        sex        : "M" or "F" (affects Vd)
        rng        : random number generator (optional)

        Returns
        -------
        {"F": ..., "ka": ..., "ke": ..., "Vd": ...}
        """
        if rng is None:
            rng = np.random.default_rng()

        eta = {p: rng.normal(0.0, self.omega.get(p, 0.0))
               for p in ("Vd", "ke", "ka", "F")}

        Vd = self._adjust(self.pk.Vd, "Vd", covariates, eta["Vd"])
        ke = self._adjust(self.pk.ke, "ke", covariates, eta["ke"])
        ka = self._adjust(self.pk.ka, "ka", covariates, eta["ka"])
        F  = self._adjust(self.pk.F,  "F",  covariates, eta["F"])

        Vd *= self._SEX_Vd.get(sex, 1.0)
        F   = np.clip(F, 0.01, 1.00)
        ke  = max(ke, 1e-6)
        ka  = max(ka, 1e-6)
        Vd  = max(Vd, 0.10)
        if abs(ka - ke) < 1e-4:
            ke *= 0.99

        return {"F": F, "ka": ka, "ke": ke, "Vd": Vd}

    def set_beta(self, covariate: str, param: str, beta: float):
        """Update the beta coefficient of a covariate."""
        self.betas.setdefault(covariate, {})[param] = beta

    def add_covariate(self, name: str, reference: float, betas: dict):
        """
        Register a new covariate.

        Example
        -------
        >>> cov.add_covariate("albumin", reference=4.0, betas={"Vd": 0.30})
        """
        self.refs[name]  = reference
        self.betas[name] = betas
