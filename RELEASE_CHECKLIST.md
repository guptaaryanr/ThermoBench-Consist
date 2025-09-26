# Release checklist (v0.1.0)

1. Bump version in `thermobench/__init__.py`, `pyproject.toml`, and `CITATION.cff`.
2. Update `CHANGELOG.md`.
3. Run CI locally: `ruff`, `black --check`, `pytest -q`.
4. Rebuild tiny figures & regenerate example reports (CO2 & N2) with the CLI.
5. Tag the release:
```bash
git tag -a v0.1.0 -m "ThermoBench-Consist v0.1.0"
git push origin v0.1.0
```
6. Create a GitHub Release and attach example artifacts (out/*.md, out/*.html, out/*.json, out/*.png).
7. **Zenodo**: Enable GitHub-Zenodo integration and mint a DOI. Add DOI badge to README and CITATION.cff.
8. Announce the release.