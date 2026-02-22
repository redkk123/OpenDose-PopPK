"""
main.py — OpenDose-PopPK
========================
Pipeline principal. Gera todas as figuras do projeto.

Uso
---
    python main.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts.project_paths import paths
from opendose_poppk import (
    DrugDatabase,
    PKModel, PDModel,
    CovariateModel,
    PopulationSimulator,
    MAPEstimator,
    plot_monte_carlo,
    plot_drug_comparison,
    plot_population_with_covariates,
    plot_map_fit,
)

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

# Usar projeto_paths para garantir caminhos relativos
CSV_PATH = paths.raw_data("drugs_parameters.csv")
OUT_DIR  = paths.figures()
OUT_DIR.mkdir(parents=True, exist_ok=True)  # Garantir que a pasta existe


def main():
    print("=" * 60)
    print("  OpenDose-PopPK — Main Pipeline")
    print("=" * 60)

    db = DrugDatabase(CSV_PATH)
    print(f"\nDrugs loaded: {db.list_drugs()}\n")

    # ── Figura 1: Monte Carlo — Paracetamol ──────────────────────────────────
    print("[1] Monte Carlo simulation — Paracetamol...")
    para = db.get_drug("Paracetamol")
    pk   = PKModel(**para.pk_kwargs)
    pd   = PDModel(para.EC50, para.n_hill)

    fig1 = plot_monte_carlo(pk, pd, dose=para.dose, t_max=12.0,
                             n_subjects=1000, drug_name=para.name)
    fig1.savefig(paths.figures("monte_carlo_paracetamol.png"),
                 dpi=150, bbox_inches="tight")
    plt.close(fig1)

    cmax, tmax = pk.cmax(D=para.dose)
    auc        = pk.auc(D=para.dose)
    ss         = pk.state_space()
    print(f"   Cmax = {cmax:.2f} µg/mL  at Tmax = {tmax:.2f} h")
    print(f"   AUC₀→∞ = {auc:.1f} µg·h/mL")
    print(f"   Eigenvalues: {ss['eigenvalues']}  →  Stable: {ss['is_stable']}")

    # ── Figura 2: Painel comparativo ─────────────────────────────────────────
    print("\n[2] Drug comparison panel...")
    drug_panel = {name: db.get_drug(name)
                  for name in ["Ibuprofen", "Diazepam", "Metformin", "Amoxicillin"]}

    fig2 = plot_drug_comparison(drug_panel, t_max=25.0)
    fig2.savefig(paths.figures("drug_comparison_panel.png"),
                 dpi=150, bbox_inches="tight")
    plt.close(fig2)

    # ── Figura 3: Simulação com covariáveis ──────────────────────────────────
    print("\n[3] Covariate population simulation...")
    cov = CovariateModel(pk)
    sim = PopulationSimulator(pk, pd, cov, dose=para.dose)

    result = sim.run(
        n_subjects=1000,
        t_max=12.0,
        seed=42,
        covariates={
            "weight": ("normal", 70.0, 15.0),
            "crcl":   ("normal", 90.0, 30.0),
            "age":    ("normal", 45.0, 15.0),
        }
    )

    ppk = result["percentiles_pk"]
    print(f"   Median Cmax : {ppk[50].max():.2f} µg/mL")
    print(f"   PI90  Cmax  : {ppk[5].max():.2f} – {ppk[95].max():.2f} µg/mL")

    fig3 = plot_population_with_covariates(result, para.name, para.dose)
    fig3.savefig(paths.figures("covariate_simulation.png"),
                 dpi=150, bbox_inches="tight")
    plt.close(fig3)

    # ── Figura 4: Estimação MAP ───────────────────────────────────────────────
    print("\n[4] MAP estimation — individual patient...")
    t_obs  = np.array([0.5, 1.0, 2.0, 4.0, 6.0, 8.0])
    c_obs  = np.array([4.2, 6.8, 7.5, 5.9, 4.1, 2.8])
    patient_covariates = {"weight": 95.0, "crcl": 45.0, "age": 68.0}

    est = MAPEstimator(pk, covariate_model=cov, sigma_obs=0.8)
    res = est.fit(t_obs, c_obs, patient_covariates, dose=para.dose)

    print(f"   Converged : {res['converged']}")
    print(f"   {'Param':6s}  {'Pop-adj':>12s}  {'MAP':>12s}  {'Eta':>8s}")
    print("   " + "─" * 46)
    for p in ("Vd", "ke", "ka", "F"):
        print(f"   {p:6s}  {res['pop_adjusted'][p]:12.4f}  "
              f"{res['params_map'][p]:12.4f}  {res['eta_map'][p]:+8.3f}")

    patient_str = (f"weight={patient_covariates['weight']}kg, "
                   f"CrCl={patient_covariates['crcl']}mL/min, "
                   f"age={patient_covariates['age']}yr")

    fig4 = plot_map_fit(pk, res, t_obs, c_obs, dose=para.dose,
                         drug_name=para.name, patient_info=patient_str)
    fig4.savefig(paths.figures("map_estimation.png"),
                 dpi=150, bbox_inches="tight")
    plt.close(fig4)

    print(f"\n✓ Done! All figures saved to: {OUT_DIR}")
    for f in sorted(OUT_DIR.iterdir()):
        print(f"   {f.name}")


if __name__ == "__main__":
    print(f"\n📍 Project root: {paths.root}\n")
    main()
