---
title: ThermoBench-Consist v1.0: A Tiny Benchmark for Thermodynamic Consistency of ML EOS/VLE Surrogates
authors:
  - Aryan Gupta
date: 2025-10-08
---

# Abstract
Machine-learned surrogates for equations of state (EOS) and vapor–liquid equilibrium (VLE) are increasingly used in design, optimization, and simulation pipelines. Beyond pointwise accuracy, **thermodynamic consistency** is a prerequisite for stable downstream usage. We present **ThermoBench-Consist v1.0**, a tiny CPU-only benchmark and diagnostics suite focused on four low-level consistency checks: (C1) monotonicity of density along isotherms $\left(\frac{\partial \rho}{\partial p}\right)_T > 0$, (C2) positivity of the isothermal compressibility $\kappa_T$, (C3) Clapeyron relation along saturation, and (C4) a **CFD-relevant** sanity check for **speed of sound** $a^2=\left(\frac{\partial p}{\partial \rho}\right)_s$. We add lightweight **guardrails** (near-spinodal flagging and optional critical-band avoidance) that stabilize interpretation near delicate regions. ThermoBench emits compact Markdown/HTML reports, plots with tolerance bands, and a machine-readable JSON summary suitable for CI and artifact evaluation. The suite ships with a reference CoolProp adapter, a deliberately inconsistent toy surrogate, tiny grids for CO$_2$/N$_2$, and runs in $<1$ minute on CPU.

# 1. Motivation
Surrogates for thermophysical properties are attractive for speed and differentiability, but solvers (flowsheet, optimization, and especially CFD) rely on **physically consistent** state functions to remain well-posed: density must increase with pressure in single-phase regions, compressibility must not be negative, phase equilibrium must respect Clapeyron, and the **speed of sound** must be plausible to avoid CFL violations and spurious acoustics in compressible simulations \cite{kundu2015, moran2018, callen1985}. Failing these basic conditions often causes solver divergence or unstable time stepping even when conventional error metrics (e.g., MAE) look acceptable. **ThermoBench-Consist** targets these “physics sanity” checks with a small, CPU-only, CI-friendly toolkit.

# 2. Related Work
**Property libraries** such as CoolProp provide reference-quality EOS/VLE calculations for pure fluids \cite{bell2014coolprop}. **Thermodynamics texts** and EOS monographs summarize stability, Clapeyron, and critical behavior \cite{callen1985, smithvan2017, kontogeorgis2010}. In **ML for physics**, physics-informed or constrained training (e.g., PINNs) encodes governing laws into learning objectives to improve generalization and physical plausibility \cite{raissi2019}. Our goal is orthogonal: instead of constraining training, we provide a **post-hoc consistency benchmark** for any surrogate.

# 3. Methods

## 3.1 Adapter API
A surrogate implements:
- `rho(T,p)` $\rightarrow$ density $\rho$ [kg·m$^{-3}$] (**required**),
- `h(T,p)` $\rightarrow$ specific enthalpy $h$ [J·kg$^{-1}$] (optional),
- `phase_split_at_T(T)` $\rightarrow$ $(p_\text{sat}, \text{props}_\ell, \text{props}_v)$ with `rho` and `h` for each branch (optional),
- `speed_of_sound(T,p)` $\rightarrow$ $a$ [m·s$^{-1}$] (optional, used by C4).

A capability structure declares which checks are supported; unsupported checks are **skipped** in scoring. Finite differences compute $\left(\frac{\partial \rho}{\partial p}\right)_T$ where needed. Units are SI.

## 3.2 Checks (Core and Plus)

### C1 — Monotonic density (Core)
In a single phase, mechanical stability implies $\left(\frac{\partial \rho}{\partial p}\right)_T > 0$. We compute centered finite differences along an isotherm; the check passes if all slopes exceed $-\text{tol}$.

### C2 — Isothermal compressibility (Core)
The isothermal compressibility is $\kappa_T \equiv \frac{1}{\rho}\left(\frac{\partial \rho}{\partial p}\right)_T$ and stability requires $\kappa_T > 0$. We reuse the C1 derivative; slightly negative values within tolerance are treated as numerical noise.

### C3 — Clapeyron along VLE (Core)
The Clapeyron relation connects the slope of the saturation curve and phase property differences:
$$
\frac{dP_{\mathrm{sat}}}{dT} \;=\; \frac{\Delta h}{T\,\Delta v}, 
\qquad \Delta h = h_v - h_\ell, 
\qquad \Delta v = \frac{1}{\rho_v} - \frac{1}{\rho_\ell}.
$$
We take $\frac{dP_{\mathrm{sat}}}{dT}$ from a **CoolProp** finite-difference baseline and compute the RHS from the surrogate’s phase-split (if available). The per-$T$ relative error 
$$
\varepsilon_\text{rel}(T) \;=\; \frac{\left|\text{LHS}(T) - \text{RHS}(T)\right|}{\left|\text{LHS}(T)\right|}
$$
feeds a **median**-over-$T$ decision with a default tolerance of $0.1$.

### C4 — Speed of sound sanity (Plus)
For a fixed reference pressure $p_{\mathrm{ref}}$ (default $10^5$ Pa), we compare
$$
a^2 \;=\; \left(\frac{\partial p}{\partial \rho}\right)_s
$$
between the surrogate (if it exposes `speed_of_sound`) and CoolProp’s reference across a small set of $T$ values. The check reports per-$T$ relative errors in $a^2$ and **passes if the median error $< 0.2$** by default. This targets CFL stability and acoustics relevance in CFD \cite{kundu2015, moran2018}.

### Tolerances and severity
Each check produces `passed` and also a qualitative **severity** (`info`, `warn`, `fail`). Slightly negative finite-difference slopes within tolerance or very small positive values (near spinodal) trigger `warn` without flipping `passed` if the tolerance criterion holds.

## 3.3 Guardrails
We implement two light guardrails (flags; **not** auto-fails):

1. **Near-spinodal flag.** During C1/C2 we set `near_spinodal=true` if any computed derivative (or $\kappa_T$) lies in $(0, \varepsilon_{\text{guard}})$ with $\varepsilon_{\text{guard}}$ small (by default $\max(10\,\text{tol}, 10^{-9})$). This warns about fragile states where tiny perturbations might invert signs.

2. **Critical-band avoidance.** An optional CLI switch `--critical_guard` removes a $\pm \Delta T$ band around $T_c$ (queried from the reference) from the isotherm set to prevent ambiguous regions; this is purely an **informational** filter for sampling.

## 3.4 Grids, datasets, and runtime
We ship tiny single-phase grids for **CO$_2$** (220–300 K) and **N$_2$** (80–120 K), with utilities for parsing grid strings, randomized (seeded) subsets, single-phase filtering, and a critical-band guard. Everything is CPU-only and designed to finish in **$<30$ s** for CLI demos and **$<60$ s** for the provided notebook.

# 4. Scoring and Reporting
Per-check pass/fail is aggregated; unsupported checks are excluded from the mean. We report a composite **0–100** score plus **badges**: **Core** (C1–C3) and **Plus** (C4) pass ratios. The report includes: (i) an isotherm $\rho$–$p$ plot with sign-aware shading, (ii) Clapeyron LHS vs RHS with a median-error title, and (iii) a speed-of-sound vs $T$ plot (reference and surrogate, if supported). A JSON summary encodes all metrics (including raw arrays) for CI.

# 5. Results Snapshot
The reference **CoolProp adapter** passes Core and Plus checks across small grids; the **toy inconsistent adapter** deliberately violates monotonicity near $\sim$2 MPa and injects an unrealistically small $\Delta h$ across VLE, causing clear failures in C1 and C3, and a sizable error in C4 (by construction). These behaviors are reflected consistently in JSON, Markdown, and HTML outputs.

# 6. Limitations
- **Scope.** Pure fluids only in **v1.0** (CO$_2$, N$_2$ reference grids). Mixtures and composition derivatives are future work.
- **Numerics.** Finite differences and small grids are fast but imperfect; overly tight tolerances can cause false negatives. We include a small convergence smoke test and micro-caching for repeated lookups.
- **Baselines.** We use CoolProp as the classical reference; cross-baseline comparisons are out of scope.

# 7. Reproducibility and Artifacts
The repository contains the package, tests, datasets, CLI, and a Colab-ready notebook. All runs are CPU-only and complete within the stated budgets. Each CLI run emits a reproducible JSON summary and compact Markdown/HTML reports.

# 8. Availability
Code (MIT), tests, datasets, and the quickstart notebook are available at the project repository. Example CLI commands generate the artifacts used in this paper. A Zenodo DOI can be minted at release time to fix
artifact references.

# Acknowledgments
We thank the CoolProp community for an excellent reference implementation and the open-source thermodynamics community for foundational texts and tools.

# References
Citations appear in the compiled version via `paper.bib`.
