# Changelog

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
