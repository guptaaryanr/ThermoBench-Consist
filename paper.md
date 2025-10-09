---
title: ThermoBench-Consist v1.0: A Tiny Benchmark for Thermodynamic Consistency of ML EOS/VLE Surrogates
authors:
  - Aryan Gupta
date: 2025-10-08
---

# Abstract
Machine-learned surrogates for equations of state (EOS) and vapor–liquid equilibrium (VLE) are increasingly used in design, optimization, and simulation pipelines. Beyond pointwise accuracy, **thermodynamic consistency** is a prerequisite for stable downstream usage. This work presents **ThermoBench-Consist v1.0**, a CPU-only benchmark focused on four low-level consistency checks: (C1) monotonicity of density along isotherms $\left(\frac{\partial \rho}{\partial p}\right)_T > 0$, (C2) positivity of the isothermal compressibility $\kappa_T$, (C3) Clapeyron relation along saturation, and (C4) a **CFD-relevant** sanity check for speed of sound $a^2=\left(\frac{\partial p}{\partial \rho}\right)_s$. The benchmark adds lightweight **guardrails** (near-spinodal flagging and optional critical-band avoidance) that stabilize interpretation near delicate regions. ThermoBench emits compact Markdown/HTML reports, tolerance-band plots, and a machine-readable JSON summary for CI and artifact evaluation. The suite ships with a reference CoolProp adapter, a deliberately inconsistent toy surrogate, tiny grids for $CO_2/N_2$, and runs in $<1$ minute on CPU.

# 1. Motivation
Surrogates for thermophysical properties are attractive for speed and differentiability, but solvers (flowsheet, optimization, and especially CFD) rely on **physically consistent** state functions to remain well-posed. Density must increase with pressure in single-phase regions, compressibility must not be negative, phase equilibrium must respect Clapeyron, and the speed of sound must be plausible to avoid CFL violations and spurious acoustics in compressible simulations [2,3,4]. Failing these basic conditions often causes solver divergence or unstable time stepping even when conventional error metrics (e.g., MAE) look acceptable. The benchmark targets these physics sanity checks with a CPU-only design suitable for CI.

# 2. Related Work
**Property libraries** such as CoolProp provide reference-quality EOS/VLE calculations for pure fluids [1]. **Thermodynamics texts** and EOS monographs summarize stability, Clapeyron, and critical behavior [2,5,6]. In **ML for physics**, physics-informed or constrained training (e.g., PINNs) encodes governing laws into learning objectives to improve generalization and physical plausibility [7]. The goal is orthogonal: instead of constraining training, the suite provides a **post-hoc consistency benchmark** for any surrogate.

# 3. Methods

## 3.1 Adapter API
A surrogate implements:
- `rho(T,p)` $\rightarrow$ density $\rho$ [$kg·m^{-3}$] (**required**),
- `h(T,p)` $\rightarrow$ specific enthalpy $h$ [$J·kg^{-1}$] (optional),
- `phase_split_at_T(T)` $\rightarrow$ ($p_\text{sat}$, $\text{props}_\ell$, $\text{props}_v$) with `rho` and `h` for each branch (optional),
- `speed_of_sound(T,p)` $\rightarrow$ $a$ [$m·s^{-1}$] (optional, used by C4).

A capability structure declares which checks are supported; unsupported checks are **skipped** in scoring. Finite differences compute $\left(\frac{\partial \rho}{\partial p}\right)_T$ where needed. Units are SI.

## 3.2 Checks (Core and Plus)

### C1 - Monotonic density (Core)
In a single phase, mechanical stability implies $\left(\frac{\partial \rho}{\partial p}\right)_T > 0$. Centered finite differences along an isotherm are computed; the check passes if all slopes exceed $-\text{tol}$.

### C2 - Isothermal compressibility (Core)
The isothermal compressibility is $\kappa_T \equiv \frac{1}{\rho}\left(\frac{\partial \rho}{\partial p}\right)_T$ and stability requires $\kappa_T > 0$. The C1 derivative is reused; slightly negative values within tolerance are treated as numerical noise.

### C3 - Clapeyron along VLE (Core)
The Clapeyron relation connects the slope of the saturation curve and phase property differences: $\frac{dP_{\mathrm{sat}}}{dT} \;=\; \frac{\Delta h}{T\,\Delta v}, \qquad \Delta h = h_v - h_\ell, \qquad \Delta v = \frac{1}{\rho_v} - \frac{1}{\rho_\ell}$. $\frac{dP_{\mathrm{sat}}}{dT}$ is taken from a **CoolProp** finite-difference baseline and the RHS is computed from the surrogate’s phase-split (if available). The $\text{per}-T$ relative error $\varepsilon_\text{rel}(T) \;=\; \frac{\left|\text{LHS}(T) - \text{RHS}(T)\right|}{\left|\text{LHS}(T)\right|}$ feeds a **median**-over-$T$ decision with a default tolerance of $0.1$.

### C4 - Speed of sound sanity (Plus)
For a fixed reference pressure $p_{\mathrm{ref}}$ (default $10^5$ Pa), $a^2 \;=\; \left(\frac{\partial p}{\partial \rho}\right)_s$ is compared between the surrogate (if it exposes `speed_of_sound`) and CoolProp’s reference across a small set of $T$ values. The check reports $\text{per}-T$ relative errors in $a^2$ and **passes if the median error $< 0.2$** by default. This targets CFL stability and acoustics relevance in CFD [3,4].

### Tolerances and severity
Each check produces `passed` and also a qualitative **severity** (`info`, `warn`, `fail`). Slightly negative finite-difference slopes within tolerance or very small positive values (near spinodal) trigger `warn` without flipping `passed` if the tolerance criterion holds.

## 3.3 Guardrails
Two light guardrails are implemented (flags; **not** auto-fails):

1. **Near-spinodal flag.** During C1/C2 the guardrail flags `near_spinodal=true` if any computed derivative (or $\kappa_T$) lies in ($0$, $\varepsilon_{\text{guard}}$) with $\varepsilon_{\text{guard}}$ small (by default max($10·\text{tol}$, $10^{-9}$)). This warns about fragile states where tiny perturbations might invert signs.

2. **Critical-band avoidance.** An optional CLI switch `--critical_guard` removes a $\pm \Delta T$ band around $T_c$ (queried from the reference) from the isotherm set to prevent ambiguous regions; this is purely an **informational** filter for sampling.

## 3.4 Grids, datasets, and runtime
Tiny single-phase grids for **$CO_2$** (220–300 K) and **$N_2$** (80–120 K) are shipped, with utilities for parsing grid strings, randomized (seeded) subsets, single-phase filtering, and a critical-band guard. Everything is CPU-only and designed to finish in **$<30$ s** for CLI demos and **$<60$ s** for the provided notebook.

# 4. Scoring and Reporting
Per-check pass/fail is aggregated; unsupported checks are excluded from the mean. A composite **0–100** score plus **badges** are reported: **Core** (C1–C3) and **Plus** (C4) pass ratios. The report includes: (i) an isotherm $\rho–p$ plot with sign-aware shading, (ii) Clapeyron LHS vs RHS with a median-error title, and (iii) a speed-of-sound vs $T$ plot (reference and surrogate, if supported). A JSON summary encodes all metrics (including raw arrays) for CI.

# 5. Results Snapshot
The reference **CoolProp adapter** passes Core and Plus checks across small grids; the **toy inconsistent adapter** deliberately violates monotonicity near $\sim$ 2 MPa and injects an unrealistically small $\Delta h$ across VLE, causing clear failures in C1 and C3, and a sizable error in C4 (by construction). These behaviors are reflected consistently in JSON, Markdown, and HTML outputs.

# 6. Limitations
- **Scope.** Pure fluids only in **v1.0** ($CO_2$, $N_2$ reference grids). Mixtures and composition derivatives are future work.
- **Numerics.** Finite differences and small grids are fast but imperfect; overly tight tolerances can cause false negatives. A small convergence smoke test and micro-caching for repeated lookups are included.
- **Baselines.** CoolProp is used as the classical reference; cross-baseline comparisons are out of scope.

# 7. Reproducibility and Artifacts
The repository contains the package, tests, datasets, CLI, and a Colab-ready notebook. All runs are CPU-only and complete within the stated budgets. Each CLI run emits a reproducible JSON summary and compact Markdown/HTML reports.

# 8. Availability
Code (MIT), tests, datasets, and the quickstart notebook are available at the project repository. Example CLI commands generate the artifacts used in this paper. A Zenodo DOI can be minted at release time to fix artifact references.

# Acknowledgments
Thank you to the CoolProp community for a reference implementation and the open-source thermodynamics community for foundational texts and tools.

# References
[1] Bell, I. H., Wronski, J., Quoilin, S., & Lemort, V. (2014). CoolProp: An Open-Source Reference-Quality Thermophysical Property Library. *Industrial & Engineering Chemistry Research*, 53(6), 2498–2508. https://doi.org/10.1021/ie4033999
[2] Callen, H. B. (1985). *Thermodynamics and an Introduction to Thermostatistics* (2nd ed.). Wiley.
[3] Moran, M. J., Shapiro, H. N., Boettner, D. D., & Bailey, M. B. (2018). *Fundamentals of Engineering Thermodynamics* (9th ed.). Wiley.
[4] Kundu, P. K., Cohen, I. M., & Dowling, D. R. (2015). *Fluid Mechanics* (6th ed.). Academic Press.
[5] Smith, J. M., Van Ness, H. C., & Abbott, M. M. (2017). *Introduction to Chemical Engineering Thermodynamics* (8th ed.). McGraw-Hill.
[6] Kontogeorgis, G. M., & Folas, G. K. (2010). *Thermodynamic Models for Industrial Applications: From Classical and Advanced Mixing Rules to Association Theories*. Wiley.
[7] Raissi, M., Perdikaris, P., & Karniadakis, G. E. (2019). Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations. *Journal of Computational Physics*, 378, 686–707.
