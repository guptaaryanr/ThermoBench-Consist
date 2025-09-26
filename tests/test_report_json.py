import json
from pathlib import Path
import numpy as np

from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.checks import (
    check_monotonic_rho_isotherm,
    check_compressibility,
    check_clapeyron,
)
from thermobench.score import aggregate_checks_to_summary
from thermobench.report import generate_report


def test_json_and_markdown_created(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    adapter = CoolPropAdapter(fluid="CO2")
    T = 280.0
    p = np.linspace(1e5, 5e5, 20)
    r1 = check_monotonic_rho_isotherm(adapter, "CO2", T, p)
    r2 = check_compressibility(adapter, "CO2", T, p)
    r3 = check_clapeyron(adapter, "CO2", [230.0, 260.0])
    summary = aggregate_checks_to_summary(
        adapter_name=adapter.__class__.__name__,
        fluid="CO2",
        grid="T=220:300:20,p=1e5:5e6:5e5",
        results_monotonic=[r1],
        results_compress=[r2],
        results_clapeyron=[r3],
        tol_monotonic=1e-6,
        tol_clap=0.1,
    )
    json_path = out / "report.json"
    md_path = out / "report.md"
    html_path = out / "report.html"
    json_path.write_text(json.dumps(summary))
    generate_report(summary, md_out=str(md_path), html_out=str(html_path), out_dir=str(out))
    assert json_path.exists()
    assert md_path.exists()
    assert html_path.exists()
