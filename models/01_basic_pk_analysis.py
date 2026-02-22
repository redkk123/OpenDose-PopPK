"""
models/01_basic_pk_analysis.py
==============================

Análise PK básica com a nova estrutura de pastas.

Este arquivo é um TEMPLATE que demonstra:
1. Como usar project_paths para acessar dados
2. Como salvar resultados em output/
3. Padrão de código recomendado

Executar com:
    python models/01_basic_pk_analysis.py
"""

import sys
from pathlib import Path

# Adicionar raiz do projeto ao path para imports relativos
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scripts.project_paths import paths
from opendose_poppk import PKModel, DrugDatabase


def main():
    """Pipeline de análise PK básica."""
    
    print("\n" + "=" * 70)
    print("  ANÁLISE PK BÁSICA — Usando Nova Estrutura")
    print("=" * 70 + "\n")
    
    # ══════════════════════════════════════════════════════════════════════════
    # 1. LEITURA DE DADOS (de data/raw/)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("[1] Carregando dados farmacológicos...")
    
    # Usar paths.raw_data() para acessar dados brutos
    csv_path = paths.raw_data("drugs_parameters.csv")
    print(f"    Arquivo: {csv_path}")
    print(f"    Existe?: {csv_path.exists()}\n")
    
    db = DrugDatabase(str(csv_path))  # Converter Path para string se necessário
    drugs = db.list_drugs()
    print(f"    Drogas carregadas: {drugs}\n")
    
    # ══════════════════════════════════════════════════════════════════════════
    # 2. ANÁLISE: Computar cinética para cada droga
    # ══════════════════════════════════════════════════════════════════════════
    
    print("[2] Computando cinética PK básica...")
    
    results = []
    for drug_name in drugs:
        drug_info = db.get_drug(drug_name)
        pk = PKModel(**drug_info.pk_kwargs)
        
        cmax, tmax = pk.cmax(D=drug_info.dose)
        auc = pk.auc(D=drug_info.dose)
        ss = pk.state_space()
        
        results.append({
            "Drug": drug_name,
            "F": pk.F,
            "ka (h-1)": pk.ka,
            "ke (h-1)": pk.ke,
            "Vd (L)": pk.Vd,
            "CL (L/h)": pk.CL,
            "Dose (mg)": drug_info.dose,
            "Cmax (µg/mL)": cmax,
            "Tmax (h)": tmax,
            "AUC (µg·h/mL)": auc,
            "Eigenvalue_1": ss["eigenvalues"][0],
            "Eigenvalue_2": ss["eigenvalues"][1],
            "Stable": ss["is_stable"],
        })
        
        print(f"    ✓ {drug_name}")
        print(f"      Cmax = {cmax:.2f} µg/mL @ {tmax:.2f} h")
        print(f"      AUC  = {auc:.2f} µg·h/mL")
        print(f"      Estável: {ss['is_stable']}")
    
    print()
    
    # ══════════════════════════════════════════════════════════════════════════
    # 3. RESULTADOS: Salvar em tabelas + criar visualização
    # ══════════════════════════════════════════════════════════════════════════
    
    print("[3] Salvando resultados...")
    
    # Converter para DataFrame
    df_results = pd.DataFrame(results)
    
    # Salvar em output/tables/ usando paths.tables()
    table_path = paths.tables("basic_pk_analysis.csv")
    df_results.to_csv(table_path, index=False)
    print(f"    ✓ Tabela: {table_path.relative_to(paths.root)}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # Criar visualização simples
    # ──────────────────────────────────────────────────────────────────────────
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Basic Pharmacokinetic Analysis", fontsize=14, fontweight="bold")
    
    # Cmax by drug
    ax = axes[0, 0]
    ax.bar(df_results["Drug"], df_results["Cmax (µg/mL)"], color="#1f77b4", alpha=0.7)
    ax.set_ylabel("Cmax (µg/mL)")
    ax.set_title("Maximum Concentration by Drug")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(alpha=0.3)
    
    # AUC by drug
    ax = axes[0, 1]
    ax.bar(df_results["Drug"], df_results["AUC (µg·h/mL)"], color="#ff7f0e", alpha=0.7)
    ax.set_ylabel("AUC (µg·h/mL)")
    ax.set_title("Area Under the Curve by Drug")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(alpha=0.3)
    
    # ke scatter
    ax = axes[1, 0]
    scatter = ax.scatter(df_results["CL (L/h)"], df_results["ke (h-1)"],
                        s=df_results["Vd (L)"]*2, alpha=0.6, c=range(len(df_results)),
                        cmap="viridis")
    for i, drug in enumerate(df_results["Drug"]):
        ax.text(df_results["CL (L/h)"].iloc[i], df_results["ke (h-1)"].iloc[i], 
               drug, fontsize=8, ha='center', va='bottom')
    ax.set_xlabel("CL (L/h)")
    ax.set_ylabel("ke (h-1)")
    ax.set_title("Clearance vs Elimination Rate (dot size = Vd)")
    ax.grid(alpha=0.3)
    
    # Properties summary
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = "Summary\n" + "=" * 30 + "\n"
    summary_text += f"Total Drugs: {len(df_results)}\n"
    summary_text += f"Mean Cmax: {df_results['Cmax (µg/mL)'].mean():.2f} µg/mL\n"
    summary_text += f"Mean AUC: {df_results['AUC (µg·h/mL)'].mean():.2f} µg·h/mL\n"
    summary_text += f"All Stable: {df_results['Stable'].all()}\n"
    ax.text(0.1, 0.5, summary_text, fontsize=10, family="monospace",
           verticalalignment='center')
    
    plt.tight_layout()
    
    # Salvar figura em output/figures/
    fig_path = paths.figures("basic_pk_analysis.png")
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    print(f"    ✓ Gráfico: {fig_path.relative_to(paths.root)}")
    
    plt.close(fig)
    
    # ══════════════════════════════════════════════════════════════════════════
    # 4. RESUMO FINAL
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("✓ ANÁLISE COMPLETA")
    print("=" * 70)
    print(f"\n📊 Resultados salvos em: {paths.output()}/")
    print(f"   • Tabelas: {paths.tables()}/")
    print(f"   • Gráficos: {paths.figures()}/")
    print(f"\n📍 Raiz do projeto: {paths.root}\n")
    
    return df_results


if __name__ == "__main__":
    df = main()
