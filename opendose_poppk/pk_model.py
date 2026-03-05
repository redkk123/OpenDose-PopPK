"""
opendose_poppk.pk_model
=======================
Core pharmacokinetic and pharmacodynamic models.

Classes
-------
PKModel  : 1-compartment PK model with first-order absorption
PDModel  : Emax pharmacodynamic model with Hill equation
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp, trapezoid
from typing import Optional




class PKModel:
    """
    1-compartment pharmacokinetic model with first-order absorption.

    Supports 2-compartment system with inter-compartmental flows and radioactive decay.

    Parameters
    ----------
    F  : bioavailability (0–1)
    ka : absorption rate constant (h⁻¹)
    ke : elimination rate constant (h⁻¹)
    Vd : volume of distribution (L)
    Q  : inter-compartmental flow (L/h)
    V2 : peripheral compartment volume (L)
    CL : systemic clearance (L/h) - alternative to ke
    V  : central volume (L) - alternative to Vd
    phys_half_life_h : physical decay half-life (h) for radioactive isotopes
    """

    def __init__(self, F: float = 0.80, ka: float = 1.80,
                 ke: float = 0.28, Vd: float = 65.0,
                 Q: float = 10.0, V2: float = 20.0,
                 CL: float | None = None, V: float | None = None,
                 phys_half_life_h: float | None = None):
        """
        Initialize PKModel with classic parameters (F, ka, ke, Vd) or 
        alternative parameters (CL, V). Supports radioactive decay.
        """
        self.F  = float(F)
        self.ka = float(ka)

        # Suporte a parâmetros alternativos: CL e V (V1)
        if CL is not None and V is not None:
            self.CL = float(CL)
            self.V1 = float(V)
            # derivado para compatibilidade
            self.ke = float(self.CL / self.V1)
            self.Vd = float(self.V1)
        else:
            # comportamento legado: ke e Vd fornecidos
            self.ke = float(ke)
            self.Vd = float(Vd)
            self.CL = float(self.ke * self.Vd)
            self.V1 = float(self.Vd)


        self.Q  = float(Q)
        self.V2 = float(V2)

        if phys_half_life_h is not None:
            if phys_half_life_h <= 0:
                raise ValueError("phys_half_life_h must be positive if provided")
            self.phys_half_life_h = float(phys_half_life_h)
            self.lambda_phys = float(np.log(2.0) / self.phys_half_life_h)
        else:
            self.phys_half_life_h = None
            self.lambda_phys = 0.0

    # ── Equação analítica ────────────────────────────────────────────────────

    def concentration(self, t: np.ndarray, D: float = 1000.0) -> np.ndarray:
        """
        Concentração plasmática C(t).

        Parâmetros
        ----------
                t : array de tempos (h)
                D : dose/atividade administrada (por exemplo: mg ou MBq)

                Observações de unidades
                -----------------------
                - Tempo é esperado em horas (h).
                - Se `D` representa atividade radioativa (MBq), então `A1`/`A2`
                    e as concentrações serão em MBq e MBq/L, respectivamente.
                - `CL` deve estar em L/h, `Q` em L/h, `V1`/`V2` em L.
        """
        # Integra numericamente o sistema 2-compartimentos (quantidades)
        t = np.atleast_1d(np.asarray(t, dtype=float))

        CL = self.CL
        V1 = self.V1
        Q  = self.Q
        V2 = self.V2

        def rhs(ti, y):
            A1, A2 = y
            # Taxas inter-compartimentais
            k10 = CL / V1      # eliminação biológica do central (h^-1)
            k12 = Q  / V1      # central -> periférico (h^-1)
            k21 = Q  / V2      # periférico -> central (h^-1)

            # Perda física (decaimento) age sobre a atividade em todos
            # os compartimentos e é adicionada às taxas de saída.
            lam = self.lambda_phys

            # dA1/dt: saída por clearance biológico, distribuição e decaimento
            dA1 = - (k10 + k12 + lam) * A1 + (k21) * A2
            # dA2/dt: troca com central e decaimento físico no periférico
            dA2 = (k12) * A1 - (k21 + lam) * A2
            return [dA1, dA2]

        # Aplicar a dose no compartimento central (AMT no central)
        A1_0 = self.F * D
        A2_0 = 0.0

        if np.any(t < 0):
            raise ValueError("Tempos t devem ser não-negativos")

        # Caso com um único tempo pedido: tratar separadamente para evitar
        # t_span com t0 == tf, o que falha em solve_ivp.
        if t.size == 1:
            if t[0] == 0.0:
                A1 = np.array([A1_0])
            else:
                sol = solve_ivp(rhs, (0.0, float(t[0])), [A1_0, A2_0],
                                t_eval=[float(t[0])], vectorized=False,
                                rtol=1e-6, atol=1e-8)
                A1 = sol.y[0]
        else:
            # Integra uma vez com pontos requisitados
            sol = solve_ivp(rhs, (t.min(), t.max()), [A1_0, A2_0], t_eval=t,
                            vectorized=False, rtol=1e-6, atol=1e-8)
            A1 = sol.y[0]
        C  = A1 / V1
        return np.maximum(C, 0.0)

    def cmax(self, D: float = 1000.0) -> tuple[float, float]:
        """Retorna (Cmax, Tmax) numéricos usando `concentration`."""
        # procura o máximo numericamente em um intervalo razoável
        t = np.linspace(0, 24.0, 1000)
        C = self.concentration(t, D=D)
        idx = np.nanargmax(C)
        return float(C[idx]), float(t[idx])

    def concentration_multiple_dose(
        self,
        t: np.ndarray,
        D: float = 1000.0,
        interval_h: float = 8.0,
        n_doses: int = 3,
    ) -> np.ndarray:
        """
        Concentração para regime de múltiplas doses em intervalos fixos.

        A dose é aplicada nos tempos: 0, interval_h, 2*interval_h, ...
        """
        if interval_h <= 0:
            raise ValueError("interval_h must be positive")
        if n_doses < 1:
            raise ValueError("n_doses must be at least 1")

        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        if np.any(t_arr < 0):
            raise ValueError("Tempos t devem ser não-negativos")

        total = np.zeros_like(t_arr, dtype=float)
        for k in range(n_doses):
            shifted = t_arr - (k * interval_h)
            mask = shifted >= 0
            if np.any(mask):
                total[mask] += self.concentration(shifted[mask], D=D)
        return np.maximum(total, 0.0)

    def auc(self, D: float = 1000.0) -> float:
        """AUC₀→∞ analítica para modelo linear: AUC = F·D / CL."""
        # Se não há decaimento físico, a expressão analítica é válida
        if self.lambda_phys == 0.0:
            return self.F * D / self.CL

        # Se existe decaimento físico, o AUC é reduzido pela perda física.
        # Para o sistema multi-compartimento, usamos integração numérica
        # do perfil de concentração para obter AUC₀→∞ de forma robusta.
        t_end = max(24.0, 10.0 / max(self.ke, 1e-6), 10.0 / max(self.lambda_phys, 1e-6))
        t = np.linspace(0.0, t_end, 2000)
        C = self.concentration(t, D=D)
        return float(trapezoid(C, t))

    # ── Monte Carlo (sem covariáveis) ────────────────────────────────────────

    def simulate_population(
        self,
        t: np.ndarray,
        D: float = 1000.0,
        n_subjects: int = 1000,
        cv_ke: float = 0.30,
        cv_ka: float = 0.25,
        cv_Vd: float = 0.30,
        cv_Q: float = 0.25,
        cv_V2: float = 0.25,
        seed: int = 42,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Simulação Monte Carlo de IIV sem covariáveis.

        Cada parâmetro é amostrado log-normalmente:
            param_i = param_pop · exp(η_i),  η_i ~ N(0, cv²)

        Retorna
        -------
        (mediana, p5, p95) : percentis do perfil populacional
        """
        rng      = np.random.default_rng(seed)
        t        = np.asarray(t, dtype=float)
        profiles = np.zeros((n_subjects, len(t)))

        for i in range(n_subjects):
            ke_i = self.ke * np.exp(rng.normal(0, cv_ke))
            ka_i = self.ka * np.exp(rng.normal(0, cv_ka))
            Vd_i = self.Vd * np.exp(rng.normal(0, cv_Vd))
            Q_i   = self.Q  * np.exp(rng.normal(0, cv_Q))
            V2_i  = self.V2 * np.exp(rng.normal(0, cv_V2))

            ke_i = max(ke_i, 1e-6)
            ka_i = max(ka_i, 1e-6)
            Vd_i = max(Vd_i, 1e-3)
            Q_i   = max(Q_i, 1e-6)
            V2_i  = max(V2_i, 1e-3)

            if abs(ka_i - ke_i) < 1e-4:
                ke_i *= 0.99

            m = PKModel(F=self.F, ka=ka_i, ke=ke_i, Vd=Vd_i, Q=Q_i, V2=V2_i)
            profiles[i] = m.concentration(t, D=D)

        return (np.percentile(profiles, 50, axis=0),
                np.percentile(profiles,  5, axis=0),
                np.percentile(profiles, 95, axis=0))

    # ── Espaço de estados ────────────────────────────────────────────────────

    def state_space(self) -> dict:
        """
        Retorna as matrizes do sistema em espaço de estados.

        Retorna
        -------
        dict com A, B, eigenvalues, is_stable
        """
        # Utilizamos quantidades (A1 = amount central, A2 = amount periférico)
        k10 = self.CL / self.V1
        k12 = self.Q  / self.V1
        k21 = self.Q  / self.V2

        # Incluir decaimento físico nas entradas diagonais (se aplicável):
        lam = self.lambda_phys
        A = np.array([[-(k10 + k12 + lam),  k21],
                  [ k12,               -(k21 + lam)]])
        B = np.array([[1.0], [0.0]])
        ev = np.linalg.eigvals(A)
        return {"A": A, "B": B, "eigenvalues": ev,
            "is_stable": bool(np.all(np.real(ev) < 0))}

    def __repr__(self) -> str:
        if self.phys_half_life_h is not None:
            return (f"PKModel(F={self.F}, ka={self.ka}, CL={self.CL}, V1={self.V1}, Q={self.Q}, V2={self.V2}, t_half_h={self.phys_half_life_h})")
        return (f"PKModel(F={self.F}, ka={self.ka}, CL={self.CL}, V1={self.V1}, Q={self.Q}, V2={self.V2})")


# ════════════════════════════════════════════════════════════════════════════
# 3. PD MODEL
# ════════════════════════════════════════════════════════════════════════════

class PDModel:
    """
    Modelo farmacodinâmico Emax com equação de Hill (sigmoidal).

        E(C) = Emax · C^n / (EC50^n + C^n)

    Parâmetros
    ----------
    EC50 : concentração de efeito meio-máximo (µg/mL)
    n    : coeficiente de Hill (1 = hiperbólico; >1 = sigmoidal)
    Emax : efeito máximo (default 100 %)
    """

    def __init__(self, EC50: float, n: float = 1.0, Emax: float = 100.0):
        if EC50 <= 0:
            raise ValueError("EC50 deve ser positivo.")
        self.EC50 = float(EC50)
        self.n    = float(n)
        self.Emax = float(Emax)

    def effect(self, C: np.ndarray) -> np.ndarray:
        """Efeito farmacodinâmico E(C) em % do Emax."""
        C     = np.maximum(np.asarray(C, dtype=float), 0.0)
        Cn    = C ** self.n
        EC50n = self.EC50 ** self.n
        return self.Emax * Cn / (EC50n + Cn)

    def ec_x(self, fraction: float) -> float:
        """
        Concentração que produz fração·Emax (inverso de Hill).

        Ex.: ec_x(0.5) → EC50, ec_x(0.9) → EC90
        """
        if not 0 < fraction < 1:
            raise ValueError("fraction deve estar entre 0 e 1.")
        return self.EC50 * (fraction / (1.0 - fraction)) ** (1.0 / self.n)

    def __repr__(self) -> str:
        return f"PDModel(EC50={self.EC50}, n={self.n}, Emax={self.Emax})"

