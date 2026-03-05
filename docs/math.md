# Mathematical Notes

## One-compartment PK

For first-order absorption and elimination:

$$
C(t) = \frac{F \cdot D \cdot k_a}{V_d(k_a-k_e)}\left(e^{-k_e t} - e^{-k_a t}\right)
$$

Where:

- $F$ is bioavailability
- $D$ is dose
- $k_a$ is absorption rate
- $k_e$ is elimination rate
- $V_d$ is apparent volume of distribution

## AUC

Without physical decay, an analytical approximation is:

$$
\mathrm{AUC}_{0\to\infty} \approx \frac{F \cdot D}{CL}
$$

For scenarios with physical decay and/or multi-compartment dynamics, OpenDose-PopPK computes AUC numerically from the simulated profile.
