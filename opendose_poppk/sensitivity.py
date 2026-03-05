from __future__ import annotations

import numpy as np

from .pk_model import PKModel


def local_pk_sensitivity(
    pk: PKModel,
    dose: float = 1000.0,
    t_end: float = 24.0,
    n_points: int = 400,
    rel_step: float = 0.10,
) -> dict:
    """
    Local one-at-a-time sensitivity analysis for PK parameters.

    Parameters perturbed: F, ka, ke, Vd.
    """
    if dose <= 0:
        raise ValueError("dose must be positive")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 2:
        raise ValueError("n_points must be at least 2")
    if rel_step <= 0 or rel_step >= 1:
        raise ValueError("rel_step must be in (0, 1)")

    t = np.linspace(0.0, float(t_end), int(n_points))
    base_profile = pk.concentration(t, D=float(dose))
    base_cmax = float(np.max(base_profile))
    base_auc = float(pk.auc(D=float(dose)))
    if base_cmax <= 0:
        raise ValueError("baseline Cmax must be positive")
    if base_auc <= 0:
        raise ValueError("baseline AUC must be positive")

    base_params = {
        "F": float(pk.F),
        "ka": float(pk.ka),
        "ke": float(pk.ke),
        "Vd": float(pk.Vd),
    }

    results = []
    for param_name in ("F", "ka", "ke", "Vd"):
        value = base_params[param_name]
        minus_value = value * (1.0 - rel_step)
        plus_value = value * (1.0 + rel_step)
        if minus_value <= 0 or plus_value <= 0:
            raise ValueError(f"invalid perturbed values for parameter '{param_name}'")

        p_minus = dict(base_params)
        p_plus = dict(base_params)
        p_minus[param_name] = minus_value
        p_plus[param_name] = plus_value

        model_minus = PKModel(
            F=p_minus["F"],
            ka=p_minus["ka"],
            ke=p_minus["ke"],
            Vd=p_minus["Vd"],
            Q=float(pk.Q),
            V2=float(pk.V2),
            phys_half_life_h=pk.phys_half_life_h,
        )
        model_plus = PKModel(
            F=p_plus["F"],
            ka=p_plus["ka"],
            ke=p_plus["ke"],
            Vd=p_plus["Vd"],
            Q=float(pk.Q),
            V2=float(pk.V2),
            phys_half_life_h=pk.phys_half_life_h,
        )

        cmax_minus = float(np.max(model_minus.concentration(t, D=float(dose))))
        cmax_plus = float(np.max(model_plus.concentration(t, D=float(dose))))
        auc_minus = float(model_minus.auc(D=float(dose)))
        auc_plus = float(model_plus.auc(D=float(dose)))

        sens_cmax = (cmax_plus - cmax_minus) / (2.0 * rel_step * base_cmax)
        sens_auc = (auc_plus - auc_minus) / (2.0 * rel_step * base_auc)

        results.append(
            {
                "parameter": param_name,
                "base_value": value,
                "minus_value": minus_value,
                "plus_value": plus_value,
                "cmax_minus": cmax_minus,
                "cmax_plus": cmax_plus,
                "auc_minus": auc_minus,
                "auc_plus": auc_plus,
                "sensitivity_cmax": float(sens_cmax),
                "sensitivity_auc": float(sens_auc),
            }
        )

    return {
        "dose": float(dose),
        "t_end": float(t_end),
        "n_points": int(n_points),
        "rel_step": float(rel_step),
        "baseline_cmax": base_cmax,
        "baseline_auc": base_auc,
        "results": results,
    }
