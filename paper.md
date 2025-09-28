---
title: ThermoBench-Consist: A Tiny Benchmark for Thermodynamic Consistency of ML EOS/VLE Surrogates
authors:
  - Aryan Gupta
date: 2025-09-26
---

# Abstract
Machine-learned surrogates for equations of state (EOS) and vapor–liquid equilibrium (VLE) are increasingly used for design and optimization. While pointwise accuracy is easy to report, most downstream failures arise from **inconsistency** with basic thermodynamic principles. We present **ThermoBench-Consist**, a tiny, CPU-only benchmark and diagnostics suite focused on three low-level consistency checks: (i) monotonicity of density along an isotherm $\frac{\partial\rho}{\partial p}|_T > 0$, (ii) the sign of the isothermal compressibility $\kappa_T$, and (iii) the Clapeyron relation along saturation, $\frac{dP_{sat}}{dT} \approx \frac{\Delta h}{T \cdot \Delta v}$. The suite provides an adapter API to wrap surrogates, a CoolProp reference, a toy inconsistent baseline, and a composite score with compact Markdown/HTML reports and a JSON summary suitable for CI.

# 1. Motivation
ML EOS/VLE surrogates—neural state functions, differentiable regressors, and emulator hybrids—promise substantial speedups. However, downstream flowsheets and optimizers require **stable** state functions: densities must not decrease with pressure in a single phase, compressibility must be positive, and VLE branches must satisfy Clapeyron. Violations lead to non-physical predictions, solver divergence, or infeasible designs. Benchmarks should therefore include **consistency** tests beyond mean absolute error. ThermoBench-Consist aims to be a minimal, practical baseline for such diagnostics.

# 2. Related Work
Consistency in ML thermodynamics has been approached via physics-constrained loss functions, convexity regularization, and integrability constraints in Helmholtz-based EOS neural models. Libraries such as **CoolProp** provide authoritative classical property calculations and were used here as a baseline reference for pure fluids [^coolprop]. Open-source efforts like Clapeyron.jl focus on EOS model fitting and analysis.

# 3. Methods

## 3.1 Adapter API
Surrogates implement:
- `rho(T, p)` → density ρ [kg·m⁻³] (required).
- `h(T, p)` → specific enthalpy h [J·kg⁻¹] (optional).
- `phase_split_at_T(T)` → returns `(p_sat, props_liq, props_vap)` with `rho` and `h` for each (optional).

A `FiniteDiff` helper estimates $\frac{\partial\rho}{\partial p}|_T$ with centered differences.

## 3.2 Checks

### C1 Monotonic density
**Principle.** In a mechanically stable single phase, ρ increases with p along an isotherm: $\frac{\partial\rho}{\partial p}|_T > 0$. We sample an isotherm `p` grid, compute finite-difference slopes, and report the fraction of positive steps, a minimum slope, and a boolean pass if all slopes exceed `-tol`.

### C2 Stability proxy (compressibility)
Isothermal compressibility is $\kappa_T = \frac{1}{\rho}\frac{\partial\rho}{\partial p}|_T > 0$. We compute κ_T from finite-difference $\frac{\partial\rho}{\partial p}|_T$ and require $\kappa_T$ > −`tol`. This proxies mechanical stability.

### C3 Clapeyron slope along VLE
The Clapeyron equation relates the slope of the saturation curve to phase property differences: $\frac{dP_{sat}}{dT} \approx \frac{\Delta h}{T \cdot \Delta v}$, $\Delta h = h_{vap} - h_{liq}$, $\Delta v = v_{vap} - v_{liq} = \frac{1}{\rho_{vap}} - \frac{1}{\rho_{liq}}$. We (i) evaluate a **CoolProp** baseline by numerically differentiating $P_{sat}(T)$, and (ii) compute the right-hand side from the surrogate’s VLE branches if available. We report per-T relative errors and a pass if the median error is below a tolerance. If the surrogate does not provide the needed branches and enthalpy, the check is marked **unsupported** and excluded from the composite score.

### C4 Speed of sound (CFD-relevant)
We sanity-check the **speed of sound** (or isentropic compressiblity) via $a^2 = \frac{\partial p}{\partial \rho}|_s$, using CoolProp's $a$ as the reference and comparing a surrogate's $a^2$ if provided. We report per-T relative errors and pass if the median error is below a tolerance (default 0.2). This is critical for CFL stability and acoustics in CFD.

## Guardrails
We expose `near_spinodal` flags when finite-difference derivatives or CoolProp $a^2$ are very small but positive, and provide an optional `--critical_guard` that shrinks isotherms away from a $\pm\Delta T$ band around the critical temperature to avoid ambiguous states. These are **flags** (not auto-fails) intended to stabilize interpretation of borderline cases.

## 3.3 Grids and datasets
We ship small single-phase grids for CO₂ (220–300 K) and N₂ (80–120 K) and utilities to sample new points while skipping two-phase regions via **CoolProp** phase detection.

# 4. Scoring and Reporting
Per-check pass/fail is aggregated across temperatures. The composite score averages the supported checks and is reported in [0, 100]. A compact Markdown/HTML report (with two small plots) and a JSON summary are emitted to enable both human and CI consumption.

# 5. Limitations
- Pure fluids only in v0.1; mixtures and cross-derivatives are future work.
- Numerical tolerances and finite difference steps are small but finite; tight tolerances may lead to false negatives.
- The Clapeyron test depends on availability and quality of surrogate enthalpy/VLE branches.

# 6. Availability
Code, tests, datasets, notebook, and a CLI are available in this repository. Everything runs on CPU in <1 minute.

# Acknowledgments
We thank the CoolProp community for an excellent reference implementation.

# References
[^coolprop]: Ian H. Bell et al., *CoolProp: An Open-Source Reference-Quality Thermophysical Property Library*, Ind. Eng. Chem. Res. 53, 2498–2508 (2014).
