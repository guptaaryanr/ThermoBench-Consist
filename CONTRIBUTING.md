# Contributing Guide

Thanks for considering a contribution to **ThermoBench-Consist**!

## Development setup
```bash
git clone https://github.com/yourname/thermobench-consist
cd thermobench-consist
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Coding style
- **Black** for formatting and **Ruff** for linting.
- Keep functions small, with clear docstrings including **units**.
- Prefer **NumPy** for numerics; keep dependencies light.
- Run checks locally:
```bash
ruff check .
black --check .
pytest -q
```

## Tests
- Add/modify tests under tests/.
- Tests should complete in **<30 seconds** on CPU-only hardware.

## Pull requests
- One focused change per PR.
- Update CHANGELOG.md.
- If applicable, regenerate tiny figures and reports used in docs.

## Reporting issues
- Include OS, Python version, package version.
- Provide minimal repro scripts with the exact command-line you used.

Thanks! ♥