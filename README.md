![tests](https://github.com/redkk123/OpenDose-PopPK/actions/workflows/tests.yml/badge.svg)

# OpenDose-PopPK 🔬💊

**A modular, open-source Python framework for Population Pharmacokinetic-Pharmacodynamic (PopPK/PD) modeling.**

The library bridges classical compartmental pharmacology and modern control theory by integrating state-space representation, stochastic Monte Carlo simulations, and Bayesian individual parameter estimation.

---

## ✨ Features

- **1-compartment PK model** — first-order analytical solution with state-space formalism
- **Emax Hill PD model** — sigmoidal pharmacodynamic effects
- **Monte Carlo simulation** — inter-individual variability with 90% prediction intervals
- **Covariate modeling** — weight, renal function (CrCl), age, hepatic markers (Power Model)
- **MAP estimation** — individual Bayesian fitting from sparse observed samples
- **DrugDatabase** — loads and manages parameters from CSV
- **Publication-ready figures** — all plots from the companion paper

---

## 📊 Results

### Population Simulation with Covariates
![Covariate Simulation](figures/covariate_simulation.png)

### Monte Carlo — Paracetamol 1000mg (N=1000)
![Monte Carlo](figures/monte_carlo_paracetamol.png)

### MAP Estimation — Individual Patient
![MAP Estimation](figures/map_estimation.png)

### Multi-Drug Comparison
![Drug Comparison](figures/drug_comparison_panel.png)

---

## 🛠️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/OpenDose-PopPK.git
cd OpenDose-PopPK
pip install -r requirements.txt
```

---

## 🚀 Quick Start

```python
from opendose_poppk import DrugDatabase, PKModel, PDModel
import numpy as np

# Load parameters from CSV
db   = DrugDatabase("datasets/drugs_parameters.csv")
drug = db.get_drug("Paracetamol")

# Build PK/PD models
pk = PKModel(**drug.pk_kwargs)
pd = PDModel(drug.EC50, drug.n_hill)

# Simulate
t = np.linspace(0, 12, 300)
C = pk.concentration(t, D=drug.dose)
E = pd.effect(C)

# Analytical metrics
cmax, tmax = pk.cmax(D=drug.dose)
auc        = pk.auc(D=drug.dose)
print(f"Cmax = {cmax:.2f} µg/mL at Tmax = {tmax:.2f} h")
print(f"AUC₀→∞ = {auc:.1f} µg·h/mL")
```

---

## 💊 Covariate-Adjusted Simulation

```python
from opendose_poppk import CovariateModel, PopulationSimulator

cov = CovariateModel(pk)
sim = PopulationSimulator(pk, pd, cov, dose=drug.dose)

result = sim.run(
    n_subjects=1000,
    t_max=12.0,
    covariates={
        "weight": ("normal", 70.0, 15.0),   # kg
        "crcl":   ("normal", 90.0, 30.0),   # mL/min — renal function
        "age":    ("normal", 45.0, 15.0),   # years
    }
)
```

---

## 🧑‍⚕️ Individual MAP Estimation

```python
from opendose_poppk import MAPEstimator
import numpy as np

t_obs = np.array([0.5, 1.0, 2.0, 4.0, 6.0, 8.0])
c_obs = np.array([4.2, 6.8, 7.5, 5.9, 4.1, 2.8])

est = MAPEstimator(pk, covariate_model=cov, sigma_obs=0.8)
res = est.fit(
    times=t_obs, obs=c_obs,
    patient_covariates={"weight": 95.0, "crcl": 45.0, "age": 68.0},
    dose=drug.dose
)

print(res["params_map"])
```

---

## 📐 Mathematical Background

### PK Model (Eq. 1)

$$C(t) = \frac{F \cdot D \cdot k_a}{V_d(k_a - k_e)}\left(e^{-k_e t} - e^{-k_a t}\right)$$

### State-Space Representation (Section 3)

$$\dot{\mathbf{x}} = \mathbf{A}\mathbf{x} + \mathbf{B}u, \quad
\mathbf{A} = \begin{bmatrix}-k_a & 0 \\ k_a & -k_e\end{bmatrix}$$

Eigenvalues $\lambda = \{-k_a, -k_e\}$ guarantee asymptotic stability.

### Covariate Power Model

$$\theta_i = \theta_{pop} \cdot \prod_k\left(\frac{COV_k}{ref_k}\right)^{\beta_k} \cdot e^{\eta_i}, \quad \eta_i \sim \mathcal{N}(0, \omega^2)$$

---

## 📁 Project Structure

```
OpenDose-PopPK/
├── opendose_poppk.py       ← Core library (all classes + plots)
├── main.py                 ← Full pipeline (generates all figures)
├── requirements.txt
├── .gitignore
├── datasets/
│   └── drugs_parameters.csv
├── notebooks/
│   └── demo_paracetamol.ipynb
└── figures/
    ├── monte_carlo_paracetamol.png
    ├── drug_comparison_panel.png
    ├── covariate_simulation.png
    └── map_estimation.png
```

---

## 📜 Citation

If you use this framework in your research, please cite:

```bibtex
@article{gomes2026opendose,
  title  = {OpenDose-PopPK: A Modular Open-Source Framework for
             Population Pharmacokinetic-Pharmacodynamic Modeling},
  author = {Gomes, Angelo Gabriel C. Silva},
  year   = {2026},
  note   = {arXiv preprint}
}
```

---

## 👤 Author

**Angelo Gabriel C. Silva Gomes**  
Federal Institute of Brasília (IFB)  
angelogabriel860@gmail.com
