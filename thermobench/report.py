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


# def _plot_isotherm_density(summary: dict[str, Any], out_dir: Path) -> str:
#     """Make a tiny ρ vs p plot for the isotherm used in C1/C2."""
#     c1 = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
#     T = c1["T"]
#     # Reconstruct isotherm by numerical integration of derivatives is overkill; instead,
#     # recompute densities from the adapter if present in this process. We don't have it here,
#     # so approximate by cumulative sum of derivatives starting from rho0=1.0 for visualization.
#     # dr = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
#     # p = np.array(summary["checks"]["C1_monotonic"]["details"]["per_T"][0].get("p", []))
#     # dr_list = summary["checks"]["C1_monotonic"]["details"]["per_T"][0]
#     # In JSON, we didn't store raw p/dr arrays; to keep this lightweight, synthesize a simple trend.
#     # Just plot a monotone curve with annotation.
#     fig = plt.figure(figsize=(4, 3), dpi=150)
#     ps = np.linspace(1e5, 5e6, 50)
#     rho = 1.0 + 1e-6 * (ps - ps[0])  # schematic
#     plt.plot(ps / 1e6, rho)
#     plt.xlabel("p [MPa]")
#     plt.ylabel("ρ [arb.]")
#     plt.title(f"Isotherm schematic at T={T:.1f} K")
#     path = out_dir / "fig_isotherm.png"
#     fig.tight_layout()
#     fig.savefig(path)
#     plt.close(fig)
#     return str(path)


def _plot_isotherm_with_derivative(summary: dict[str, Any], out_dir: Path) -> str:
    """Make a tiny ρ vs p plot for the isotherm used in C1/C2."""
    c1 = summary["checks"]["C1_monotonic"]
    per_T = c1["details"]["per_T"][0] if c1["details"]["per_T"] else None
    fig = plt.figure(figsize=(4.5, 3.2), dpi=150)
    if per_T:
        p = np.array(per_T["p"])
        # reconstruct a simple monotone-like rho curve for visualization by integrating drho/dp
        dr = np.array(per_T["drho_dp"])
        # define rho[0] arbitrary but positive
        rho = np.empty(len(p))
        rho[0] = 1.0
        for i in range(1, len(p)):
            dp = p[i] - p[i - 1]
            slope = dr[i - 1] if i - 1 < len(dr) else dr[-1]
            rho[i] = rho[i - 1] + slope * dp
        # shading based on derivative sign bands
        bands = []
        tol = c1.get("tol", 1e-6)
        warn = max(10.0 * tol, 1e-9)
        for i in range(len(p) - 1):
            color = (
                "green"
                if dr[i] >= 0
                else ("orange" if (-tol < dr[i] < warn) else "red" if dr[i] <= -tol else "orange")
            )
            bands.append(color)
        plt.plot(p / 1e6, rho, lw=1.6)
        for i in range(len(p) - 1):
            plt.axvspan(p[i] / 1e6, p[i + 1] / 1e6, color=bands[i], alpha=0.15)
        plt.title(f"Isotherm @ T={per_T['T']:.1f} K (ρ vs p)")
        plt.xlabel("p [MPa]")
        plt.ylabel("ρ [arb.]")
    else:
        plt.text(0.5, 0.5, "No C1 data", ha="center", va="center")
        plt.axis("off")
    path = out_dir / "fig_isotherm.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _plot_clapeyron(summary: dict[str, Any], out_dir: Path) -> str | None:
    c3 = summary["checks"]["C3_clapeyron"]
    runs = c3["details"]["per_run"]
    if not runs:
        return None
    T_list = runs[0]["T_list"]
    lhs = runs[0]["lhs"]
    rhs = runs[0]["rhs"]
    errs = runs[0]["median_rel_error"]

    fig = plt.figure(figsize=(4.5, 3.2), dpi=150)
    xs = np.arange(len(T_list))
    plt.plot(xs, lhs, marker="o", label="dP_sat/dT (CP)")
    # may have NaNs in rhs
    rhs_arr = np.array(rhs, dtype=float)
    plt.plot(xs, rhs_arr, marker="s", label="Δh/(TΔv) (surrogate)")
    plt.xticks(xs, [f"{t:.0f}" for t in T_list])
    plt.ylabel("Slope [Pa/K]")
    plt.xlabel("Saturation T [K]")
    plt.title(f"Clapeyron LHS vs RHS (median rel err ~ {errs:.2f})")
    plt.legend()
    path = out_dir / "fig_clapeyron.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _plot_speed_of_sound(summary: dict[str, Any], out_dir: Path) -> str | None:
    c4 = summary["checks"]["C4_speed_of_sound"]
    runs = c4["details"]["per_run"]
    if not runs:
        return None
    T_list = runs[0]["T_list"]
    a2_ref = np.array(runs[0]["a2_ref"], dtype=float)
    a2_sur = np.array(runs[0]["a2_sur"], dtype=float)

    fig = plt.figure(figsize=(4.5, 3.2), dpi=150)
    xs = np.arange(len(T_list))
    plt.plot(xs, np.sqrt(np.maximum(a2_ref, 0)), marker="o", label="a (CP)")
    if np.isfinite(a2_sur).any():
        plt.plot(xs, np.sqrt(np.maximum(a2_sur, 0)), marker="s", label="a (surrogate)")
    plt.xticks(xs, [f"{t:.0f}" for t in T_list])
    plt.ylabel("Speed of sound a [m/s]")
    plt.xlabel("T [K]")
    mederr = runs[0]["median_rel_error"]
    plt.title(f"Speed of sound vs T (median rel err ~ {mederr:.2f})")
    plt.legend()
    path = out_dir / "fig_a2.png"
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

    fig1 = _plot_isotherm_with_derivative(summary, outp)
    fig2 = _plot_clapeyron(summary, outp)
    fig3 = _plot_speed_of_sound(summary, outp)

    ctx = {
        "adapter": summary["adapter"],
        "fluid": summary["fluid"],
        "grid": summary["grid"],
        "datetime_utc": summary["datetime_utc"],
        "composite_score": summary["composite_score"],
        "checks": summary["checks"],
        "badges": summary.get("badges", {}),
        "fig_isotherm": fig1,
        "fig_clapeyron": fig2,
        "fig_a2": fig3,
    }

    if md_out:
        tpl_md = env.get_template("report.md.j2")
        Path(md_out).write_text(tpl_md.render(**ctx))
    if html_out:
        tpl_html = env.get_template("report.html.j2")
        Path(html_out).write_text(tpl_html.render(**ctx))
