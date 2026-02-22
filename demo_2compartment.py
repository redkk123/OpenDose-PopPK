#!/usr/bin/env python3
"""
Demo — Modelo PopPK de 2 Compartimentos
========================================

Este script demonstra a refatoração do PKModel de 1 para 2 compartimentos:
- Compartimento Central (V1)
- Compartimento Periférico (V2)
- Parâmetros inter-compartimental: Q (clearance entre compartimentos)

A dose (AMT) é sempre aplicada no compartimento central.

Nomenclatura padrão:
  V1 (ou Vd) : volume central (L)
  V2         : volume periférico (L)
  Q          : clearance inter-compartimental (L/h)
  CL         : clearance total do corpo (L/h)
  ke = CL/V1 : taxa de eliminação do compartimento central (h⁻¹)
"""

import numpy as np
import matplotlib.pyplot as plt
from scripts.project_paths import paths
from opendose_poppk import PKModel, PopulationSimulator, PDModel

# ════════════════════════════════════════════════════════════════════════════
# 1. Criar modelo com 2 compartimentos
# ════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("MODELO PK — 2 COMPARTIMENTOS (CENTRAL + PERIFÉRICO)")
print("=" * 80)
print()

# Parâmetros clássicos de 1 compartimento (compatibilidade)
F   = 0.80          # biodisponibilidade (%)
ka  = 1.80          # constante de absorção (h⁻¹)
ke  = 0.28          # eliminação (h⁻¹)
Vd  = 65.0          # volume de distribuição (L)

# Novos parâmetros: inter-compartimento
Q   = 10.0          # clearance inter-compartimental (L/h)
V2  = 20.0          # volume periférico (L)

# Criar o modelo
pk = PKModel(
    F=F, ka=ka, ke=ke, Vd=Vd,  # compatível com modelo legado
    Q=Q, V2=V2                  # novos parâmetros
)

print(f"✓ Modelo criado: {pk}")
print(f"  • F   = {F:.2f}      (biodisponibilidade)")
print(f"  • ka  = {ka:.2f}     (absorção, h⁻¹)")
print(f"  • CL  = {pk.CL:.2f}  (clearance total, L/h)")
print(f"  • V1  = {pk.V1:.2f}  (volume central, L)")
print(f"  • ke  = {pk.ke:.2f}  (eliminação, h⁻¹)")
print(f"  • Q   = {Q:.2f}      (inter-compartimental, L/h)")
print(f"  • V2  = {V2:.2f}     (volume periférico, L)")
print()

# ════════════════════════════════════════════════════════════════════════════
# 2. Simular perfil individual com dose no compartimento central
# ════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("SIMULAÇÃO — PERFIL INDIVIDUAL")
print("=" * 80)
print()

dose = 1000.0  # mg
t = np.linspace(0, 24, 300)

# A dose é aplicada automaticamente no compartimento central (A1_0 = F·D)
C = pk.concentration(t, D=dose)

cmax, tmax = pk.cmax(D=dose)
auc = pk.auc(D=dose)

print(f"Dose: {dose:.0f} mg → Compartimento Central (V1)")
print(f"• Cmax  = {cmax:.4f} µg/mL  (em t = {tmax:.2f} h)")
print(f"• AUC   = {auc:.4f} µg·h/mL")
print()

# ════════════════════════════════════════════════════════════════════════════
# 3. Análise de espaço de estados
# ════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ANÁLISE — ESPAÇO DE ESTADOS")
print("=" * 80)
print()

ss = pk.state_space()

print("Modelo em espaço de estados (quantidades: A1, A2):")
print()
print("  dA₁   = -(k₁₀ + k₁₂)·A₁ + k₂₁·A₂")
print("  dA₂   = k₁₂·A₁ - k₂₁·A₂")
print()
print("  onde:")
print(f"    k₁₀ = CL/V1 = {pk.CL:.2f}/{pk.V1:.2f} = {pk.CL/pk.V1:.4f} h⁻¹  (eliminação central)")
print(f"    k₁₂ = Q/V1  = {Q:.2f}/{pk.V1:.2f} = {Q/pk.V1:.4f} h⁻¹  (saída do central)")
print(f"    k₂₁ = Q/V2  = {Q:.2f}/{V2:.2f}  = {Q/V2:.4f} h⁻¹  (volta ao central)")
print()
print(f"Matriz A (dinâmica):")
print(ss["A"])
print()
print(f"Autovalores (estabilidade):")
for i, ev in enumerate(ss["eigenvalues"]):
    print(f"  λ_{i+1} = {ev:.6f} {'✓ estável' if ev < 0 else '✗ instável'}")
print()
print(f"Sistema estável: {ss['is_stable']}")
print()

# ════════════════════════════════════════════════════════════════════════════
# 4. Variabilidade inter-individual (Monte Carlo)
# ════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("SIMULAÇÃO — MONTE CARLO (N=1000)")
print("=" * 80)
print()

t_mc = np.linspace(0, 24, 200)
med, p5, p95 = pk.simulate_population(
    t_mc, D=dose, n_subjects=1000,
    cv_ke=0.30, cv_ka=0.25, cv_Vd=0.30,
    cv_Q=0.25, cv_V2=0.25,  # novo: IIV em Q e V2
    seed=42
)

print(f"✓ Simulação com variabilidade inter-individual:")
print(f"  • CV(ke) = 30%   (eliminação)")
print(f"  • CV(ka) = 25%   (absorção)")
print(f"  • CV(Vd) = 30%   (volume central)")
print(f"  • CV(Q)  = 25%   (inter-compartimental)")
print(f"  • CV(V2) = 25%   (volume periférico)")
print()
print(f"Percentis da população em Cmax:")
print(f"  • 5º percentil  = {p5.max():.4f} µg/mL")
print(f"  • 50º percentil = {med.max():.4f} µg/mL")
print(f"  • 95º percentil = {p95.max():.4f} µg/mL")
print()

# ════════════════════════════════════════════════════════════════════════════
# 5. Gráfico: Perfil Individual vs. População
# ════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(11, 6))

# Perfil típico
ax.plot(t, C, color="#1f77b4", lw=2.5, label="Perfil Típico (mediana)")

# Intervalo de predição 90%
ax.fill_between(t_mc, p5, p95, alpha=0.2, color="#1f77b4",
                label="PI 90% (população simulada)")
ax.plot(t_mc, med, color="#1f77b4", ls="--", lw=1.5, alpha=0.8)

ax.axvline(tmax, color="red", ls=":", alpha=0.6, label=f"Tmax = {tmax:.2f} h")
ax.axhline(cmax, color="red", ls=":", alpha=0.6, label=f"Cmax = {cmax:.2f} µg/mL")

ax.set_xlabel("Tempo após dose (h)", fontsize=11, fontweight="bold")
ax.set_ylabel("Concentração plasmática (µg/mL)", fontsize=11, fontweight="bold")
ax.set_title(f"PopPK — 2 Compartimentos | {dose:.0f}mg | D→V1 (central)", 
             fontsize=12, fontweight="bold")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper right", fontsize=10)
ax.set_xlim(0, 24)
ax.set_ylim(0, cmax * 1.15)

plt.tight_layout()
plt.savefig(paths.figures("demo_2compartment.png"), dpi=150, bbox_inches="tight")
print(f"📊 Gráfico salvo: {paths.figures('demo_2compartment.png')}")
print()

# ════════════════════════════════════════════════════════════════════════════
# 6. Resumo de compatibilidade
# ════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("COMPATIBILIDADE")
print("=" * 80)
print()
print("✓ Modelo 2-compartimentos mantém compatibilidade com API legada:")
print("  • PKModel(F, ka, ke, Vd) funciona → derivar CL=ke*Vd, V1=Vd")
print("  • PKModel(CL=..., V=...) funciona → derivar ke=CL/V, Vd=V")
print("  • Novos parâmetros Q e V2 adicionados opcionalmente")
print()
print("✓ Nomenclatura padrão NONMEM/Stan:")
print("    Central  : V1 (ou Vd), CL, ke")
print("    Periférico: V2")
print("    Inter-comp: Q (Q12 = inter-compartimental, Q21 = k21)")
print()
print("✓ Dose sempre aplicada no compartimento central (AMT → A1_0 = F·D)")
print()
