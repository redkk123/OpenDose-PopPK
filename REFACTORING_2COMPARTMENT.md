# OpenDose-PopPK — Modelo de 2 Compartimentos

## 🎯 Visão Geral

O `PKModel` foi **refatorado de um modelo de 1 compartimento para 2 compartimentos** (central + periférico), mantendo **compatibilidade total com a API legada**.

### Novo Modelo

```
        Absorption (ka)
              ↓
    ┌─────────────────┐
    │  Compartimento  │
    │    Central      │  V1 = Vd
    │    (Sangue)     │  CL = ke·V1
    └────────┬────────┘
             │
        ┌────┴────┐
        │QQ       │Q
        │12  ↔ 21 │
        ↓         ↑
    ┌─────────────────┐
    │  Compartimento  │
    │   Periférico    │  V2
    │   (Tecidos)     │
    └─────────────────┘
        Elimination (CL)
```

## 📋 Parâmetros

### Originais (1 Compartimento) — **Mantidos para compatibilidade**
- `F` : Biodisponibilidade (0–1)
- `ka` : Constante de absorção (h⁻¹)
- `ke` : Constante de eliminação (h⁻¹)
- `Vd` : Volume de distribuição (L)

### Novos (2 Compartimentos)
- **`Q`** : Clearance inter-compartimental (L/h)
  - Descreve a taxa de transferência entre central e periférico
  - Alterna entre os compartimentos (Q12, Q21)
  
- **`V2`** : Volume do compartimento periférico (L)
  - Representa tecidos periféricos (músculos, gordura, etc.)

### Derivados Internamente
- `CL = ke · Vd` : Clearance total
- `V1 = Vd` : Volume central (alias para compatibilidade)

## 🔧 Equações do Sistema

Em espaço de estados, usando **quantidades de massa** (A1, A2):

$$\begin{align}
\frac{dA_1}{dt} &= -\left(\frac{\text{CL}}{V_1} + \frac{Q}{V_1}\right) \cdot A_1 + \frac{Q}{V_2} \cdot A_2 \\
\frac{dA_2}{dt} &= \frac{Q}{V_1} \cdot A_1 - \frac{Q}{V_2} \cdot A_2
\end{align}$$

Concentração no compartimento central: $C(t) = \frac{A_1(t)}{V_1}$

Ou em termos de constantes cinéticas:
- $k_{10} = \frac{\text{CL}}{V_1}$ : taxa de eliminação
- $k_{12} = \frac{Q}{V_1}$ : taxa de saída do central
- $k_{21} = \frac{Q}{V_2}$ : taxa de retorno do periférico

## 💊 Aplicação da Dose

A dose é **sempre aplicada no compartimento central**:
$$A_1(0) = F \cdot D \quad | \quad A_2(0) = 0$$

Esta é a configuração padrão em farmacologia (via IV, oral com absorção GI).

## ✅ Compatibilidade

### 1️⃣ **API Legada Mantida**
```python
# Forma original ainda funciona
pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
C = pk.concentration(t, D=1000)
```

### 2️⃣ **Novos Parâmetros Opcionais**
```python
# Adicionar inter-compatimental
pk = PKModel(
    F=0.8, ka=1.8, ke=0.28, Vd=65.0,
    Q=10.0, V2=20.0  # novo
)
```

### 3️⃣ **Sintaxe Alternativa (CL/V)**
```python
# Usar CL e V diretamente (compatível com testes legados)
pk = PKModel(CL=5.0, V=50.0)
```

## 📊 Variabilidade Inter-Individual (IIV)

`simulate_population()` agora inclui IIV nos novos parâmetros:

```python
c_med, c_p5, c_p95 = pk.simulate_population(
    t, 
    D=1000.0, 
    n_subjects=1000,
    cv_ke=0.30,   # original
    cv_ka=0.25,   # original
    cv_Vd=0.30,   # original
    cv_Q=0.25,    # novo
    cv_V2=0.25,   # novo
    seed=42
)
```

Cada parâmetro é amostrado log-normalmente:
$$\text{param}_i = \text{param}_{\text{pop}} \cdot \exp(\eta_i), \quad \eta_i \sim \mathcal{N}(0, \text{CV}^2)$$

## 🧪 Integração Numérica

- **Método**: `scipy.integrate.solve_ivp` (RK45)
- **Tolerância**: rtol=1e-6, atol=1e-8
- **Robustez**: Tratamento especial para casos com 1 ponto temporal

## 📖 Nomenclatura Padrão

Segue convenção **NONMEM/Stan/R**:

| Parâmetro | NONMEM | Stan/R | Significado |
|-----------|--------|--------|-------------|
| `V1` / `Vd` | VC | V1 | Volume central |
| `V2` | VP | V2 | Volume periférico |
| `CL` | CL | CL | Clearance sistêmico |
| `Q` | Q, Q12, Q23 | Q | Inter-compartimental |
| `ke` | — | k10 | Taxa de eliminação |
| `ka` | KA | ka | Taxa de absorção |

## 🔍 Exemplo Prático

```python
from opendose_poppk import PKModel
import numpy as np

# Criar modelo
pk = PKModel(
    F=0.80, ka=1.80, ke=0.28, Vd=65.0,
    Q=10.0, V2=20.0
)

# Simular concentração-tempo
t = np.linspace(0, 24, 300)
C = pk.concentration(t, D=1000.0)

# Parâmetros cinéticos
cmax, tmax = pk.cmax(D=1000.0)
auc = pk.auc(D=1000.0)

print(f"Cmax = {cmax:.2f} µg/mL em t = {tmax:.2f} h")
print(f"AUC  = {auc:.2f} µg·h/mL")

# Estabilidade
ss = pk.state_space()
print(f"Sistema estável: {ss['is_stable']}")
```

## 🧬 Análise de Estabilidade

Autovalores da matriz `A` (todas dinâmicas devem ter $\text{Re}(\lambda) < 0$):

```python
pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0, Q=10.0, V2=20.0)
ss = pk.state_space()

print("Autovalores:", ss['eigenvalues'])
print("Estável:", ss['is_stable'])
```

## 🚀 Executar a Demonstração

```bash
python demo_2compartment.py
```

Gera:
- Resumo dos parâmetros
- Análise cinética (Cmax, AUC, Tmax)
- Espaço de estados com autovalores
- Simulação de 1000 indivíduos (Monte Carlo)
- Gráfico: `figures/demo_2compartment.png`

## ✔️ Testes

Todos os 4 testes passam:

```bash
python -m pytest -q
# ....  [100%]
```

### Casos Testados
1. `test_concentration_positive` : Concentração ≥ 0
2. `test_concentration_decreases` : Decaimento monótono
3. `test_map_runs` : Estimador MAP sem erro
4. `test_population_runs` : PopulationSimulator sem erro

## 📝 Resumo das Mudanças

| Arquivo | Mudança |
|---------|---------|
| `opendose_poppk/pk_model.py` | **PKModel**: Adiciona campos `Q`, `V2`, `CL`, `V1`; integração ODE; espaço de estados 2x2; compatibilidade com legacy API |
| `opendose_poppk/__init__.py` | Exporta `PDModel` |
| `tests/` | Todos passam ✅ |
| `demo_2compartment.py` | **Novo**: Demonstração interativa |
| `opendose.py` | **Novo**: Shim de compatibilidade |

## 🎓 Referências

- Gabrielsson & Weiner (2000): "Pharmacokinetic & Pharmacodynamic Data Analysis"
- NONMEM Documentation
- Stan PharmacoKinetics User Guide
- scipy.integrate.solve_ivp

---

**Última atualização**: Fevereiro 2026
