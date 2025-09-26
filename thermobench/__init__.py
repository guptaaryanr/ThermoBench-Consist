"""
ThermoBench-Consist package.

Exposes:
- Adapter protocol and finite difference helper (see thermobench.api)
- Checks: C1/C2/C3 (see thermobench.checks)
- CLI entrypoint `thermobench` (see `cli_main` below)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path

from .checks import (
    check_clapeyron,
    check_compressibility,
    check_monotonic_rho_isotherm,
)
from .grid import parse_grid_string
from .report import generate_report
from .score import aggregate_checks_to_summary

# from dataclasses import asdict
# from typing import Any, Tuple

__all__ = [
    "cli_main",
    "parse_grid_string",
    "check_monotonic_rho_isotherm",
    "check_compressibility",
    "check_clapeyron",
    "aggregate_checks_to_summary",
    "generate_report",
]

__version__ = "0.1.0"


def _load_adapter(class_path: str, fluid: str):
    """
    Load an adapter given 'module:Class'. If 'module' has no dot, it's resolved
    relative to 'thermobench.adapters'.
    """
    if ":" not in class_path:
        raise ValueError("Adapter must be given as 'module:Class'")
    mod_name, cls_name = class_path.split(":")
    if "." not in mod_name:
        mod_name = f"thermobench.adapters.{mod_name}"
    module = import_module(mod_name)
    cls = getattr(module, cls_name)
    return cls(fluid=fluid)


def _parse_sat_T(arg: str) -> Sequence[float]:
    if not arg:
        return []
    return [float(x.strip()) for x in arg.split(",") if x.strip()]


def cli_main(argv: Sequence[str] | None = None) -> int:
    """
    CLI entrypoint implementing:
      thermobench run --surrogate ... --fluid --out --html --json
      thermobench score --json path
      thermobench plot --json path --outdir out/
    """
    parser = argparse.ArgumentParser(prog="thermobench", description="ThermoBench-Consist CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run checks and generate report")
    p_run.add_argument(
        "--surrogate", required=True, help="module:Class (e.g., adapter_coolprop:CoolPropAdapter)"
    )
    p_run.add_argument("--fluid", required=True, choices=["CO2", "N2"], help="Fluid")
    p_run.add_argument(
        "--grid",
        default="T=220:300:10,p=1e5:5e6:5e5",
        help='Grid string, e.g., "T=220:300:10,p=1e5:5e6:5e5"',
    )
    p_run.add_argument(
        "--sat_T", default="", help="Comma-separated saturation temperatures, e.g., 230,240,260,280"
    )
    p_run.add_argument(
        "--tol_monotonic", type=float, default=1e-6, help="Tolerance for C1/C2 derivative sign"
    )
    p_run.add_argument(
        "--tol_clap", type=float, default=0.1, help="Relative tolerance for C3 median error"
    )
    p_run.add_argument("--out", required=True, help="Markdown report path")
    p_run.add_argument("--html", required=True, help="HTML report path")
    p_run.add_argument("--json", required=True, help="JSON summary path")

    p_score = sub.add_parser("score", help="Print JSON summary to stdout")
    p_score.add_argument("--json", required=True, help="Path to JSON summary")

    p_plot = sub.add_parser("plot", help="Regenerate plots from an existing JSON summary")
    p_plot.add_argument("--json", required=True, help="Path to JSON summary")
    p_plot.add_argument("--outdir", default="out", help="Output directory for plots")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        adapter = _load_adapter(args.surrogate, args.fluid)
        T_vals, p_vals = parse_grid_string(args.grid)
        # choose a representative isotherm for C1/C2
        T0 = float(T_vals[len(T_vals) // 2])
        p_line = p_vals
        # C1 & C2
        r1 = check_monotonic_rho_isotherm(adapter, args.fluid, T0, p_line, tol=args.tol_monotonic)
        r2 = check_compressibility(adapter, args.fluid, T0, p_line, tol=args.tol_monotonic)
        # C3 Clapeyron on requested saturation T list (if any)
        Ts = _parse_sat_T(args.sat_T)
        results_c3 = []
        if Ts:
            r3 = check_clapeyron(adapter, args.fluid, Ts, tol_rel=args.tol_clap)
            results_c3 = [r3]
        summary = aggregate_checks_to_summary(
            adapter_name=adapter.__class__.__name__,
            fluid=args.fluid,
            grid=args.grid,
            results_monotonic=[r1],
            results_compress=[r2],
            results_clapeyron=results_c3,
            tol_monotonic=args.tol_monotonic,
            tol_clap=args.tol_clap,
        )
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.html).parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(summary, f, indent=2)
        generate_report(
            summary, md_out=args.out, html_out=args.html, out_dir=str(Path(args.out).parent)
        )
        print(f"Wrote: {args.json}\nWrote: {args.out}\nWrote: {args.html}")
        return 0

    if args.cmd == "score":
        with open(args.json) as f:
            data = json.load(f)
        print(json.dumps(data, indent=2))
        return 0

    if args.cmd == "plot":
        with open(args.json) as f:
            data = json.load(f)
        generate_report(data, md_out=None, html_out=None, out_dir=args.outdir, overwrite_figs=True)
        print(f"Regenerated figures in {args.outdir}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(cli_main())
