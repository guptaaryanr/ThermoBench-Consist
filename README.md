# ThermoBench-Consist
[![CI](https://img.shields.io/github/actions/workflow/status/guptaaryanr/ThermoBench-Consist/ci.yml?branch=main)](./.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**ThermoBench-Consist** is a tiny diagnostics/benchmark suite that checks **thermodynamic consistency** for ML-based EOS/VLE surrogates (pure fluids). It focuses on **signs and slopes** rather than absolute accuracy.

> **Positioning.** This is a small **diagnostics/benchmark**. It complements libraries like **CoolProp** and research code (e.g., Clapeyron.jl) and ML-EOS work. It is **not** an EOS or property library itself.

## What’s new in v1.0
- **C4 (CFD-relevant):** speed of sound sanity vs CoolProp baseline.
- **Guardrails:** near-spinodal flagging; optional `--critical_guard` to avoid a T band around $T_c$.
- **Reports:** real plots + badges (**Core** = C1–C3, **Plus** = C4), severity labels.
- **CLI:** `inspect` capabilities; `--seed`, `--random_grid` for reproducible small runs.
- **Speed:** tiny CoolProp caching; convergence smoke test in CI.

## Features
- Adapter protocol to wrap any surrogate (density and optional enthalpy & VLE split).
- Checks:
  - **C1 Monotonic density:** $\frac{\partial\rho}{\partial p}|_T > 0$ on isotherms.
  - **C2 Stability proxy (compressibility):** $\kappa_T = \frac{1}{\rho}\frac{\partial\rho}{\partial p}|_T > 0$.
  - **C3 Clapeyron slope along VLE:** $\frac{dP_{sat}}{dT} \approx \frac{\Delta h}{T \cdot \Delta v}$ vs CoolProp baseline.
- Graceful degradation: unsupported checks are skipped in the composite score.
- Reports: Markdown + HTML with small plots, plus a machine-readable JSON summary.
- CPU-only, tiny datasets (CO₂, N₂ grids).

## Install
```bash
# system req: libboost for CoolProp (on Ubuntu)
sudo apt-get update && sudo apt-get install -y libboost-all-dev

pip install -e .[dev]
```
Dependencies (pinned): numpy, scipy, pandas, matplotlib, coolprop, pint, jinja2, pytest, ruff, black (and optional pydantic).

## Quickstart (CLI)
```bash
# Example: CoolProp as the surrogate (reference)
thermobench run \
  --surrogate adapter_coolprop:CoolPropAdapter \
  --fluid CO2 \
  --grid "T=220:300:10,p=1e5:5e6:5e5" \
  --sat_T 230,240,260,280 \
  --out out/report_CO2.md \
  --html out/report_CO2.html \
  --json out/report_CO2.json

# Print the summary JSON to stdout
thermobench score --json out/report_CO2.json

# Regenerate plots from JSON
thermobench plot --json out/report_CO2.json --outdir out/

# Inspect capabilities of an adapter
thermobench inspect --surrogate adapter_coolprop:CoolPropAdapter --fluid CO2

# Randomized grid (reproducible)
thermobench run \
  --surrogate adapter_coolprop:CoolPropAdapter --fluid N2 \
  --grid "T=80:120:10,p=1e5:3e6:1.5e5" \
  --random_grid --seed 42 --critical_guard \
  --out out/report_N2.md --html out/report_N2.html --json out/report_N2.json
```

## Notebook
See notebooks/ThermoBench_Quickstart.ipynb (Colab-ready, CPU, <60 s). It wraps both adapters, runs checks for CO₂ & N₂, and saves a one-page report with two small figures.

## CFD context (why C4?)
RANS/LES, combustion, and compressible flows require speed of sound (or equivalently isentropic compressibility) for CFL limits, acoustics, and stability. Unphysical $a^2$ (negative or wildly off) leads to timestep blow-ups and spurious waves; C4 sanity-checks $a^2$ vs a trusted baseline (CoolProp).

## What the checks mean
- **C1 Monotonic density**: Along a single-phase isotherm, density must increase with pressure ($\frac{\partial\rho}{\partial p}|_T > 0$). We estimate the derivative via centered finite differences over a small isotherm pressure grid and count the fraction of positive steps.
- **C2 Stability proxy ($\kappa_T$)**: The isothermal compressibility $\kappa_T = \frac{1}{\rho}\frac{\partial\rho}{\partial p}|_T$ must be positive in mechanically stable single-phase states. We compute $\kappa_T$ from finite differences of $\rho$ with respect to p. Small negative values within a tolerance are treated as numerical noise.
- **C3 Clapeyron slope**: Along the saturation line, the slope of saturation pressure vs temperature satisfies $\frac{dP_{sat}}{dT} \approx \frac{\Delta h}{T \cdot \Delta v}$. We compare the surrogate’s $\Delta h$ and $\Delta v$ (from its liquid/vapor branches) against a CoolProp numeric derivative of $P_{sat}(T)$. We report per-T relative error and pass if the median error is below a tolerance.
- **C4 Speed of sound**: Speed of sound sanity $a^2 = \frac{\partial p}{\partial \rho}|_s$ vs CoolProp.

Guardrails: We flag near_spinodal=true if derivatives or $a^2$ fall in a tiny positive band (not an automatic fail). --critical_guard shrinks grids away from a $\pm\Delta T$ band around $T_c$.

## Scope & limitations
- v0.1 supports **pure fluids** (CO₂, N₂ reference grids). Mixtures are future work.
- If a surrogate does not expose VLE branches or enthalpy, C3 is marked **unsupported** (and excluded from the composite score).
- Units are **SI** (Kelvin, Pascal, kg/m³, J/kg). We use pint to document units and keep code explicit.

## Reference data
- Tiny single-phase grids for CO₂ (220–300 K) and N₂ (80–120 K) ship under thermobench/datasets/. You can also generate them from code via thermobench.grid.sample_single_phase_points(...).

## Development
Run CI locally:
```bash
ruff check .
black --check .
pytest -q
```

## Citation
If this benchmark is useful, please cite the short preprint included as paper.md/paper.bib.

## License
MIT - see LICENSE.