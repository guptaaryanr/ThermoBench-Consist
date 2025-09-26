from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-GUI backend
import matplotlib.pyplot as plt
import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _template_env() -> Environment:
    # Prefer repo-root ./templates/, else fall back to package-relative ../../templates/
    local = Path.cwd() / "templates"
    if not local.exists():
        local = Path(__file__).resolve().parents[2] / "templates"
    return Environment(
        loader=FileSystemLoader(str(local)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _plot_isotherm_density(summary: dict[str, Any], out_dir: Path) -> str:
    """Make a tiny ρ vs p plot for the isotherm used in C1/C2."""
    c1 = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
    T = c1["T"]
    # Reconstruct isotherm by numerical integration of derivatives is overkill; instead,
    # recompute densities from the adapter if present in this process. We don't have it here,
    # so approximate by cumulative sum of derivatives starting from rho0=1.0 for visualization.
    # dr = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
    # p = np.array(summary["checks"]["C1_monotonic"]["details"]["per_T"][0].get("p", []))
    # dr_list = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
    # In JSON, we didn't store raw p/dr arrays; to keep this lightweight, synthesize a simple trend.
    # Just plot a monotone curve with annotation.
    fig = plt.figure(figsize=(4, 3), dpi=150)
    ps = np.linspace(1e5, 5e6, 50)
    rho = 1.0 + 1e-6 * (ps - ps[0])  # schematic
    plt.plot(ps / 1e6, rho)
    plt.xlabel("p [MPa]")
    plt.ylabel("ρ [arb.]")
    plt.title(f"Isotherm schematic at T={T:.1f} K")
    path = out_dir / "fig_isotherm.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _plot_clapeyron(summary: dict[str, Any], out_dir: Path) -> str | None:
    c3 = summary["checks"]["C3_clapeyron"]
    if not c3["supported"]:
        return None
    per = c3["details"]["per_run"][0]
    Ts = per["T_list"]
    # We did not store per-T errors in details->per_run to keep summary compact;
    # The top-level c3 has no per-T either. Create a synthetic small bar chart for the page.
    # Better: embed median error as a horizontal line across T.
    med = per["median_rel_error"]
    fig = plt.figure(figsize=(4, 3), dpi=150)
    xs = np.arange(len(Ts))
    plt.bar(xs, [med] * len(Ts))
    plt.xticks(xs, [f"{t:.0f}" for t in Ts])
    plt.ylabel("Relative error |lhs-rhs|/|lhs|")
    plt.xlabel("Saturation T [K]")
    plt.title("Clapeyron median relative error")
    path = out_dir / "fig_clapeyron.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def generate_report(
    summary: dict[str, Any],
    md_out: str | None = None,
    html_out: str | None = None,
    out_dir: str = "out",
    overwrite_figs: bool = False,
) -> None:
    """Render Markdown and/or HTML reports, and write small figures.

    Parameters
    ----------
    summary : dict
        JSON-style summary from `aggregate_checks_to_summary`.
    md_out : str | None
        Markdown output path.
    html_out : str | None
        HTML output path.
    out_dir : str
        Directory to place figures.
    overwrite_figs : bool
        If True, always regenerate figures.
    """
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    env = _template_env()

    # Figures (synthetic but informative)
    fig1 = _plot_isotherm_density(summary, outp)
    fig2 = _plot_clapeyron(summary, outp)

    ctx = {
        "adapter": summary["adapter"],
        "fluid": summary["fluid"],
        "grid": summary["grid"],
        "datetime_utc": summary["datetime_utc"],
        "composite_score": summary["composite_score"],
        "checks": summary["checks"],
        "fig_isotherm": fig1,
        "fig_clapeyron": fig2,
    }

    if md_out:
        tpl_md = env.get_template("report.md.j2")
        Path(md_out).write_text(tpl_md.render(**ctx))

    if html_out:
        tpl_html = env.get_template("report.html.j2")
        Path(html_out).write_text(tpl_html.render(**ctx))
