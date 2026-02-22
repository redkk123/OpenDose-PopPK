"""
opendose_poppk.py
=================
OpenDose-PopPK — Core Library
Population Pharmacokinetic / Pharmacodynamic Modeling Framework

Classes
-------
DrugDatabase        : carrega parâmetros do CSV
PKModel             : modelo PK 1-compartimento + Monte Carlo + state-space
PDModel             : modelo PD Emax (Hill)
CovariateModel      : ajuste de parâmetros por covariáveis (power model)
PopulationSimulator : Monte Carlo completo com covariáveis
MAPEstimator        : estimação bayesiana individual

Funções de visualização
-----------------------
plot_monte_carlo()
plot_drug_comparison()
plot_population_with_covariates()
plot_map_fit()

Author : Angelo Gabriel C. Silva Gomes
         Federal Institute of Brasília (IFB)
Date   : 2026
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import minimize
from scipy.integrate import solve_ivp, trapezoid
from typing import Optional


# ════════════════════════════════════════════════════════════════════════════
# 1. DRUG DATABASE
# ════════════════════════════════════════════════════════════════════════════

class DrugDatabase:
    """
    Carrega e fornece parâmetros farmacológicos a partir de um arquivo CSV.

    Colunas esperadas no CSV
    ------------------------
    Drug, F, ka_h, ke_h, Vd_L, EC50_ugmL, n_hill, dose_mg, notes

    Exemplo
    -------
    >>> db   = DrugDatabase("datasets/drugs_parameters.csv")
    >>> info = db.get_drug("Paracetamol")
    >>> pk   = PKModel(**info.pk_kwargs)
    """

    def __init__(self, csv_path: str):
        self._df = pd.read_csv(csv_path)
        self._df.columns = [c.strip() for c in self._df.columns]

    # ── Acesso ──────────────────────────────────────────────────────────────

    def get_drug(self, name: str) -> "_DrugInfo":
        row = self._df[self._df["Drug"].str.lower() == name.lower()]
        if row.empty:
            raise ValueError(
                f"Droga '{name}' não encontrada. "
                f"Disponíveis: {self.list_drugs()}"
            )
        return _DrugInfo(row.iloc[0])

    def list_drugs(self) -> list[str]:
        return list(self._df["Drug"])

    def dataframe(self) -> pd.DataFrame:
        return self._df.copy()


class _DrugInfo:
    """Container retornado por DrugDatabase.get_drug()."""

    def __init__(self, row: pd.Series):
        self.name    = str(row["Drug"])
        self.F       = float(row["F"])
        self.ka      = float(row["ka_h"])
        self.ke      = float(row["ke_h"])
        self.Vd      = float(row["Vd_L"])
        self.dose    = float(row["dose_mg"])
        self.EC50    = None if pd.isna(row.get("EC50_ugmL", np.nan)) \
                       else float(row["EC50_ugmL"])
        self.n_hill  = None if pd.isna(row.get("n_hill", np.nan)) \
                       else float(row["n_hill"])
        self.notes   = str(row.get("notes", ""))

    @property
    def pk_kwargs(self) -> dict:
        return {"F": self.F, "ka": self.ka, "ke": self.ke, "Vd": self.Vd}

    @property
    def has_pd(self) -> bool:
        return self.EC50 is not None and self.n_hill is not None

    def __repr__(self) -> str:
        return (f"DrugInfo({self.name}: F={self.F}, ka={self.ka}, "
                f"ke={self.ke}, Vd={self.Vd})")


# ════════════════════════════════════════════════════════════════════════════
# 2. PK MODEL
# ════════════════════════════════════════════════════════════════════════════

class PKModel:
    """
    Modelo farmacocinético de 1 compartimento com absorção de 1ª ordem.

    Equação analítica (Eq. 1 do artigo)
    ------------------------------------
    C(t) = F·D·ka / [Vd·(ka − ke)] · (e^{−ke·t} − e^{−ka·t}),  ka ≠ ke

    Representação em espaço de estados (Seção 3 do artigo)
    -------------------------------------------------------
    ẋ = A·x + B·u
    A = [[-ka,  0 ],      B = [[1],
         [ ka, -ke]]           [0]]

    Autovalores: λ = {−ka, −ke} → estabilidade assintótica garantida.

    Parâmetros
    ----------
    F  : biodisponibilidade (0–1)
    ka : constante de absorção (h⁻¹)
    ke : constante de eliminação (h⁻¹)
    Vd : volume de distribuição (L)
    """

    def __init__(self, F: float = 0.80, ka: float = 1.80,
                 ke: float = 0.28, Vd: float = 65.0,
                 Q: float = 10.0, V2: float = 20.0,
                 CL: float | None = None, V: float | None = None,
                 phys_half_life_h: float | None = None):
        """
        Compat: aceita os parâmetros clássicos (F, ka, ke, Vd) e adiciona
        parâmetros de inter-compartimento `Q` e volume periférico `V2`.

        Internamente computamos `CL = ke * Vd` e `V1 = Vd` para manter
        compatibilidade com o código existente que usa `ke` e `Vd`.
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

        # novo: inter-compartimental
        self.Q  = float(Q)
        self.V2 = float(V2)

        # Parâmetros de decaimento físico (isótopos radioativos)
        # - `phys_half_life_h`: meia-vida física em horas (se fornecida)
        # - `lambda_phys`   : constante de decaimento (h^-1) = ln(2)/t_half
        # A decaimento físico atua sobre a atividade (quantidade) em todos
        # os compartimentos e deve ser somado às taxas de eliminação
        # biológicas para obter a perda total de atividade.
        if phys_half_life_h is not None:
            if phys_half_life_h <= 0:
                raise ValueError("phys_half_life_h deve ser positivo se fornecido")
            self.phys_half_life_h = float(phys_half_life_h)
            self.lambda_phys = float(np.log(2.0) / self.phys_half_life_h)
        else:
            self.phys_half_life_h = None
            self.lambda_phys = 0.0

        # Documentação técnica curta dos principais parâmetros (unidades)
        # - CL  : clearance sistêmico (L/h). Taxa de remoção biológica do
        #         compartimento central quando multiplicado por concentração
        #         (CL * C [L/h * MBq/L] -> MBq/h).
        # - V1  : volume do compartimento central (L). Usado para converter
        #         amount -> concentração: C = A1 / V1 (MBq/L).
        # - Q   : fluxo inter-compartimental (L/h). Controla transferência
        #         entre central e periférico (k12 = Q / V1, k21 = Q / V2).
        # - V2  : volume do compartimento periférico (L).

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


# ════════════════════════════════════════════════════════════════════════════
# 4. COVARIATE MODEL
# ════════════════════════════════════════════════════════════════════════════

# Valores de referência (mediana da população)
_COV_REF = {
    "weight": 70.0,   # kg
    "age":    40.0,   # anos
    "crcl":   90.0,   # mL/min (clearance de creatinina)
    "alt":    30.0,   # U/L (função hepática)
    "bmi":    25.0,   # kg/m²
}

# Coeficientes beta: (covariável, parâmetro) → força do efeito
# 0 = sem efeito; positivo = aumenta; negativo = diminui
_COV_BETA = {
    #               Vd      ke      ka      F
    "weight": {"Vd": 1.00, "ke": 0.00, "ka": 0.00, "F": 0.00},
    "age":    {"Vd": 0.00, "ke":-0.40, "ka": 0.00, "F": 0.00},
    "crcl":   {"Vd": 0.00, "ke": 0.75, "ka": 0.00, "F": 0.00},
    "alt":    {"Vd": 0.00, "ke":-0.30, "ka": 0.00, "F":-0.10},
    "bmi":    {"Vd": 0.50, "ke": 0.00, "ka": 0.00, "F": 0.00},
}

# Variabilidade residual (após explicar covariáveis)
_OMEGA = {"Vd": 0.30, "ke": 0.20, "ka": 0.25, "F": 0.10}


class CovariateModel:
    """
    Aplica covariáveis a parâmetros PK via Power Model.

    Fórmula
    -------
    θᵢ = θ_pop · ∏ (COVₖ / refₖ)^βₖ · exp(ηᵢ)

    Onde:
        θ_pop → parâmetro típico da população
        COVₖ  → valor da covariável do paciente
        refₖ  → valor de referência (mediana)
        βₖ    → coeficiente de efeito (beta)
        ηᵢ    → desvio aleatório ~ N(0, ω²)

    Exemplo
    -------
    >>> pk  = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65)
    >>> cov = CovariateModel(pk)
    >>> p   = cov.individualize({"weight": 90, "crcl": 50}, sex="M")
    >>> print(p)  # {"F": ..., "ka": ..., "ke": ..., "Vd": ...}
    """

    _SEX_Vd = {"M": 1.00, "F": 0.90}

    def __init__(self, pk: PKModel,
                 omega: dict = None,
                 betas: dict = None,
                 references: dict = None):
        self.pk    = pk
        self.omega = dict(_OMEGA)         if omega      is None else omega
        self.betas = {k: dict(v) for k, v
                      in _COV_BETA.items()} if betas is None else betas
        self.refs  = dict(_COV_REF)       if references is None else references

    # ── Ajuste de um parâmetro ───────────────────────────────────────────────

    def _adjust(self, theta: float, param: str,
                covariates: dict, eta: float = 0.0) -> float:
        """Aplica power model para um parâmetro."""
        mult = 1.0
        for cov, val in covariates.items():
            beta = self.betas.get(cov, {}).get(param, 0.0)
            if beta != 0.0 and cov in self.refs:
                mult *= (val / self.refs[cov]) ** beta
        return theta * mult * np.exp(eta)

    # ── Parâmetros individuais ───────────────────────────────────────────────

    def individualize(self, covariates: dict,
                      sex: str = "M",
                      rng: np.random.Generator = None) -> dict:
        """
        Gera parâmetros PK individuais com covariáveis + IIV.

        Parâmetros
        ----------
        covariates : {"weight": 85.0, "crcl": 60.0, "age": 65.0, ...}
        sex        : "M" ou "F" (afeta Vd)
        rng        : gerador aleatório (para reprodutibilidade)

        Retorna
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

    # ── Configuração ─────────────────────────────────────────────────────────

    def set_beta(self, covariate: str, param: str, beta: float):
        """Atualiza o coeficiente beta de uma covariável."""
        self.betas.setdefault(covariate, {})[param] = beta

    def add_covariate(self, name: str, reference: float, betas: dict):
        """
        Registra uma covariável nova.

        Exemplo
        -------
        >>> cov.add_covariate("albumin", reference=4.0, betas={"Vd": 0.30})
        """
        self.refs[name]  = reference
        self.betas[name] = betas


# ════════════════════════════════════════════════════════════════════════════
# 5. POPULATION SIMULATOR
# ════════════════════════════════════════════════════════════════════════════

class PopulationSimulator:
    """
    Simulação Monte Carlo de população heterogênea com covariáveis.

    Integra PKModel + PDModel + CovariateModel para gerar perfis
    PK/PD individuais com distribuições reais de covariáveis.

    Exemplo
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
            covariates: dict = None,
            seed: int = 42) -> dict:
        """
        Executa a simulação Monte Carlo.

        Parâmetros
        ----------
        n_subjects  : tamanho da população simulada
        t_max       : tempo final (h)
        n_points    : pontos na curva temporal
        covariates  : distribuições das covariáveis.
                      Formato: {"nome": ("tipo", p1, p2)}
                      Tipos: "normal", "uniform", "lognormal"
                      Ex.: {"weight": ("normal", 70, 15)}
        seed        : semente aleatória

        Retorna
        -------
        dict com t, pk_profiles, pd_profiles, percentiles_pk,
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

        # Simula covariáveis populacionais
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

    # Compatibilidade com API legada: `simulate(n=...)` retorna uma lista de
    # perfis (um por indivíduo). Isso facilita testes simples que apenas
    # verificam o tamanho da amostra.
    def simulate(self, n: int = 10):
        res = self.run(n_subjects=n, n_points=50)
        profiles = [res["pk_profiles"][i] for i in range(res["pk_profiles"].shape[0])]
        return profiles


# ════════════════════════════════════════════════════════════════════════════
# 6. MAP ESTIMATOR
# ════════════════════════════════════════════════════════════════════════════

class MAPEstimator:
    """
    Estimação bayesiana individual (Maximum A Posteriori).

    Encontra os etas individuais que minimizam:
        obj = Σ[(C_obs − C_pred)² / σ²]  +  Σ[ηᵢ² / ωᵢ²]
              └─ fidelidade aos dados ──┘    └─ prior populacional ─┘

    Exemplo
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
        # permitir construção sem argumento para compatibilidade com testes
        self.pk    = pk or PKModel()
        self.cov   = covariate_model or CovariateModel(self.pk)
        self.sigma = sigma_obs

    def fit(self, times: np.ndarray, obs: np.ndarray,
            patient_covariates: dict, dose: float,
            n_iter: int = 3000) -> dict:
        """
        Ajusta parâmetros individuais para um paciente.

        Retorna
        -------
        dict com params_map, eta_map, pop_adjusted, converged
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


# ════════════════════════════════════════════════════════════════════════════
# 7. VISUALIZAÇÃO
# ════════════════════════════════════════════════════════════════════════════

_BLUE  = "#1f77b4"
_RED   = "#d62728"
_GREEN = "#2ca02c"


def plot_monte_carlo(pk: PKModel, pd: Optional[PDModel] = None,
                     dose: float = 1000.0, t_max: float = 12.0,
                     n_subjects: int = 1000, drug_name: str = "",
                     seed: int = 42) -> plt.Figure:
    """Figura 1 do artigo — Monte Carlo PK/PD com PI 90%."""
    t = np.linspace(0, t_max, 300)
    c_med, c_p5, c_p95 = pk.simulate_population(
        t, D=dose, n_subjects=n_subjects, seed=seed)

    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    ax1.fill_between(t, c_p5, c_p95, color=_BLUE, alpha=0.2,
                     label="90% Prediction Interval (PK)")
    ax1.plot(t, c_med, color=_BLUE, lw=2, label="Median Plasma Conc.")
    ax1.set_xlabel("Time Post-Dose (h)")
    ax1.set_ylabel("Plasma Concentration (µg/mL)", color=_BLUE)
    ax1.tick_params(axis="y", labelcolor=_BLUE)

    if pd is not None:
        ax2 = ax1.twinx()
        ax2.plot(t, pd.effect(c_med), color=_RED, ls="--", lw=2,
                 label="Median PD Effect (Hill)")
        ax2.set_ylabel("Effect Magnitude (% of Emax)", color=_RED)
        ax2.tick_params(axis="y", labelcolor=_RED)
        ax2.set_ylim(0, 105)

    title = f"PopPK/PD Monte Carlo Simulation"
    if drug_name:
        title += f": {drug_name} {dose:.0f}mg (N={n_subjects})"
    plt.title(title)
    fig.legend(loc="upper right",
               bbox_to_anchor=(0.90, 0.85), bbox_transform=ax1.transAxes)
    fig.tight_layout()
    return fig


def plot_drug_comparison(drugs: dict, t_max: float = 25.0,
                          n_points: int = 500) -> plt.Figure:
    """
    Figura 2 do artigo — painel comparativo PK/PD de múltiplas drogas.

    Parâmetros
    ----------
    drugs : {"DrugName": DrugInfo, ...}  ou  {"DrugName": {"F":..., ...}}
    """
    n     = len(drugs)
    ncols = 2
    nrows = (n + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(13, nrows * 4.5),
                              facecolor="white")
    axes = axes.flatten()
    t    = np.linspace(0, t_max, n_points)

    for i, (name, info) in enumerate(drugs.items()):
        # Aceita DrugInfo ou dict puro
        if isinstance(info, _DrugInfo):
            pk   = PKModel(**info.pk_kwargs)
            dose = info.dose
            pd   = PDModel(info.EC50, info.n_hill) if info.has_pd else None
        else:
            pk   = PKModel(F=info["F"], ka=info["ka"],
                           ke=info["ke"], Vd=info["Vd"])
            dose = info.get("dose", 1000.0)
            pd   = (PDModel(info["EC50"], info["n"])
                    if info.get("EC50") and info.get("n") else None)

        ax1 = axes[i]
        c   = pk.concentration(t, D=dose)
        ax1.plot(t, c, color=_BLUE, lw=2)
        ax1.set_title(f"{name} ({dose:.0f}mg)", fontweight="bold")
        ax1.set_xlabel("Time (h)")
        ax1.set_ylabel("Conc. (µg/mL)", color=_BLUE)
        ax1.tick_params(axis="y", labelcolor=_BLUE)
        ax1.grid(True, alpha=0.2)

        if pd is not None:
            ax2 = ax1.twinx()
            ax2.plot(t, pd.effect(c), color=_RED, lw=1.5, ls="--")
            ax2.set_ylabel("Effect (%)", color=_RED)
            ax2.set_ylim(0, 105)
            ax2.tick_params(axis="y", labelcolor=_RED)
        elif "Amoxicillin" in name:
            ax1.text(0.55, 0.55, "T > MIC Model\n(Antibiotic)",
                     transform=ax1.transAxes, fontsize=9,
                     color="gray", ha="center")

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle("OpenDose-PopPK — Comparative Drug Profiles",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_population_with_covariates(result: dict, drug_name: str,
                                     dose: float) -> plt.Figure:
    """Painel de 4 gráficos — simulação PopPK com covariáveis."""
    fig = plt.figure(figsize=(14, 10), facecolor="#F8F9FA")
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.38)

    t   = result["t"]
    ppk = result["percentiles_pk"]
    ppd = result["percentiles_pd"]
    cov = result["covariates_sim"]
    n   = result["pk_profiles"].shape[0]

    # ── PK / PD ─────────────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.fill_between(t, ppk[5], ppk[95], alpha=0.2, color=_BLUE, label="PI 90%")
    ax1.plot(t, ppk[50], color=_BLUE, lw=2, label="Median PK")
    ax1.set_xlabel("Time Post-Dose (h)", fontsize=9)
    ax1.set_ylabel("Conc. (µg/mL)", fontsize=9)
    ax1.set_title(f"PopPK — {drug_name} {dose:.0f}mg  (N={n})",
                  fontsize=10, fontweight="bold")
    ax1.legend(fontsize=8); ax1.set_facecolor("#FAFAFA"); ax1.grid(alpha=0.3)

    if ppd:
        ax1b = ax1.twinx()
        ax1b.plot(t, ppd[50], color=_RED, lw=2, ls="--", label="Median PD")
        ax1b.fill_between(t, ppd[5], ppd[95], alpha=0.10, color=_RED)
        ax1b.set_ylabel("Effect (% Emax)", fontsize=9, color=_RED)
        ax1b.tick_params(axis="y", colors=_RED)
        ax1b.legend(fontsize=8, loc="upper right")

    # ── Distribuição de peso ─────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    if "weight" in cov:
        ax2.hist(cov["weight"], bins=40, color=_BLUE, alpha=0.75,
                 edgecolor="white", lw=0.5)
        ax2.axvline(70, color=_RED, lw=2, ls="--", label="Ref (70 kg)")
        ax2.set_xlabel("Body Weight (kg)", fontsize=9)
        ax2.set_ylabel("Count", fontsize=9)
        ax2.set_title("Covariate Distribution — Weight", fontsize=10, fontweight="bold")
        ax2.legend(fontsize=8); ax2.set_facecolor("#FAFAFA"); ax2.grid(alpha=0.3)

    # ── Distribuição de ClCr com zonas ──────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    if "crcl" in cov:
        ax3.hist(cov["crcl"], bins=40, color=_GREEN, alpha=0.75,
                 edgecolor="white", lw=0.5)
        ax3.axvline(90, color=_RED, lw=2, ls="--", label="Ref (90 mL/min)")
        for lo, hi, lbl, clr in [(0,30,"Severe","#FCA5A5"),(30,60,"Moderate","#FDE68A"),
                                  (60,90,"Mild","#A7F3D0"),(90,180,"Normal","#BFDBFE")]:
            ax3.axvspan(lo, hi, alpha=0.15, color=clr, label=lbl)
        ax3.set_xlabel("Creatinine Clearance (mL/min)", fontsize=9)
        ax3.set_ylabel("Count", fontsize=9)
        ax3.set_title("Covariate Distribution — Renal Function", fontsize=10, fontweight="bold")
        ax3.legend(fontsize=7, ncol=2); ax3.set_facecolor("#FAFAFA"); ax3.grid(alpha=0.3)

    # ── Cmax por estrato renal ───────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    if "crcl" in cov:
        crcl = cov["crcl"]
        cmax = result["pk_profiles"].max(axis=1)
        for mask, lbl, clr in [
            (crcl < 30,                       "Severe (<30)",   "#EF4444"),
            ((crcl>=30)&(crcl<60),            "Moderate (30–60)","#F59E0B"),
            ((crcl>=60)&(crcl<90),            "Mild (60–90)",   "#10B981"),
            (crcl >= 90,                       "Normal (≥90)",   "#3B82F6"),
        ]:
            if mask.sum() > 0:
                ax4.hist(cmax[mask], bins=30, alpha=0.65, color=clr,
                         label=f"{lbl} (n={mask.sum()})",
                         edgecolor="white", lw=0.3)
        ax4.set_xlabel("Cmax (µg/mL)", fontsize=9)
        ax4.set_ylabel("Count", fontsize=9)
        ax4.set_title("Cmax by Renal Stratum", fontsize=10, fontweight="bold")
        ax4.legend(fontsize=7); ax4.set_facecolor("#FAFAFA"); ax4.grid(alpha=0.3)

    fig.suptitle(f"OpenDose-PopPK — Covariate Simulation | {drug_name}",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_map_fit(pk_pop: PKModel, map_result: dict,
                 times: np.ndarray, obs: np.ndarray,
                 dose: float, drug_name: str = "",
                 patient_info: str = "") -> plt.Figure:
    """Gráfico de ajuste MAP — perfil individual vs. população."""
    t_full  = np.linspace(0, times.max() * 1.4, 300)
    pk_map  = PKModel(**map_result["params_map"])
    pk_adj  = PKModel(**map_result["pop_adjusted"])

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t_full, pk_pop.concentration(t_full, D=dose),
            color=_BLUE, ls=":", lw=1.5, label="Population (no covariates)")
    ax.plot(t_full, pk_adj.concentration(t_full, D=dose),
            color=_GREEN, ls="--", lw=1.8, label="Population (covariate-adjusted)")
    ax.plot(t_full, pk_map.concentration(t_full, D=dose),
            color=_RED, lw=2.2, label="MAP Individual Fit")
    ax.scatter(times, obs, color=_RED, zorder=5, s=60, label="Observed")

    title = f"MAP Estimation — {drug_name} {dose:.0f}mg"
    if patient_info:
        title += f"\n{patient_info}"
    ax.set_xlabel("Time Post-Dose (h)")
    ax.set_ylabel("Conc. (µg/mL)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig
