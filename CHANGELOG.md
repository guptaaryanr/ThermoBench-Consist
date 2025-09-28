# Changelog

## v1.0.0 — 2025-09-28
- New check **C4: Speed of sound / isentropic compressibility sanity** (CFD-relevant).
- Spinodal/critical **guardrails**: `near_spinodal` flags in C1/C2 and optional `--critical_guard`.
- Reports: real plots with data bands; badges for **Core** (C1–C3) and **Plus** (C4); severity labels.
- CLI ergonomics: `inspect` subcommand, `--seed`, `--random_grid`, `--critical_guard`.
- Micro-caching for repeated CoolProp calls; one **convergence smoke test**.
- Docs & paper updated for v1.0; version bumps and release checklist updates.

## v0.1.0 — 2025-09-26
- First public release of **ThermoBench-Consist**.
- Python package `thermobench` with:
  - Adapter protocol and CoolProp + Toy adapters.
  - Checks: C1 Monotonic density, C2 Compressibility sign, C3 Clapeyron slope along VLE.
  - Report (Markdown/HTML) and JSON score/summary.
  - CLI with `run`, `score`, `plot`.
- Tiny reference grids for CO₂ (220–300 K) and N₂ (80–120 K).
- Colab-ready quickstart notebook.
- Tests + GitHub Actions CI (ruff, black, pytest).
