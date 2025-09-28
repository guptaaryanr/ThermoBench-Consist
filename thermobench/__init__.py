"""
ThermoBench-Consist package (v1.0).

CLI:
  thermobench run --surrogate ... --fluid ... [--critical_guard] [--random_grid --seed 42]
  thermobench score --json path
  thermobench plot --json path --outdir out/
  thermobench inspect --surrogate ... --fluid ...
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path

from .checks import (
    check_clapeyron,
    check_compressibility,
    check_monotonic_rho_isotherm,
    check_speed_of_sound,
)
from .grid import apply_critical_guard, parse_grid_string, random_grid
from .report import generate_report
from .score import aggregate_checks_to_summary

__all__ = ["cli_main"]
__version__ = "1.0.0"


def _load_adapter(class_path: str, fluid: str):
    if ":" not in class_path:
        raise ValueError("Adapter must be given as 'module:Class'")
    mod_name, cls_name = class_path.split(":")
    if "." not in mod_name:
        mod_name = f"thermobench.adapters.{mod_name}"
    module = import_module(mod_name)
    cls = getattr(module, cls_name)
    return cls(fluid=fluid)


def _parse_sat_T(arg: str):
    if not arg:
        return []
    return [float(x.strip()) for x in arg.split(",") if x.strip()]


def cli_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thermobench", description="ThermoBench-Consist CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run checks and generate report")
    p_run.add_argument("--surrogate", required=True)
    p_run.add_argument("--fluid", required=True, choices=["CO2", "N2"])
    p_run.add_argument("--grid", default="T=220:300:10,p=1e5:5e6:5e5")
    p_run.add_argument("--sat_T", default="")
    p_run.add_argument("--tol_monotonic", type=float, default=1e-6)
    p_run.add_argument("--tol_clap", type=float, default=0.1)
    p_run.add_argument("--tol_c4", type=float, default=0.2)
    p_run.add_argument("--out", required=True)
    p_run.add_argument("--html", required=True)
    p_run.add_argument("--json", required=True)
    # ergonomics
    p_run.add_argument("--critical_guard", action="store_true", help="avoid ±ΔT band around Tc")
    p_run.add_argument("--seed", type=int, default=None, help="random seed for --random_grid")
    p_run.add_argument(
        "--random_grid", action="store_true", help="sample small random subset of grid"
    )

    p_score = sub.add_parser("score", help="Print JSON summary to stdout")
    p_score.add_argument("--json", required=True)

    p_plot = sub.add_parser("plot", help="Regenerate figures from an existing JSON summary")
    p_plot.add_argument("--json", required=True)
    p_plot.add_argument("--outdir", default="out")

    p_inspect = sub.add_parser("inspect", help="Print adapter capability table and reasons")
    p_inspect.add_argument("--surrogate", required=True)
    p_inspect.add_argument("--fluid", required=True, choices=["CO2", "N2"])

    args = parser.parse_args(argv)

    if args.cmd == "inspect":
        adapter = _load_adapter(args.surrogate, args.fluid)
        caps = adapter.capabilities()
        rows = [
            ("C1_monotonic", "supported" if caps.supports_rho else "unsupported (rho)"),
            ("C2_compressibility", "supported" if caps.supports_rho else "unsupported (rho)"),
            (
                "C3_clapeyron",
                (
                    "supported"
                    if (caps.supports_phase_split and caps.supports_h and caps.supports_rho)
                    else "unsupported (phase_split/h/rho)"
                ),
            ),
            (
                "C4_speed_of_sound",
                (
                    "supported"
                    if getattr(caps, "supports_speed_of_sound", False)
                    else "unsupported (speed_of_sound)"
                ),
            ),
        ]
        print("Capability inspection for", adapter.__class__.__name__, "fluid", args.fluid)
        print("{:<20}{}".format("Check", "Status"))
        print("-" * 36)
        for k, v in rows:
            print(f"{k:<20}{v}")
        return 0

    if args.cmd == "run":
        adapter = _load_adapter(args.surrogate, args.fluid)
        T_vals, p_vals = parse_grid_string(args.grid)
        if args.critical_guard:
            T_vals = apply_critical_guard(args.fluid, T_vals)
        if args.random_grid:
            T_vals, p_vals = random_grid(args.fluid, T_vals, p_vals, seed=args.seed)

        # representative isotherm for C1/C2
        T0 = float(T_vals[len(T_vals) // 2])
        p_line = p_vals
        r1 = check_monotonic_rho_isotherm(adapter, args.fluid, T0, p_line, tol=args.tol_monotonic)
        r2 = check_compressibility(adapter, args.fluid, T0, p_line, tol=args.tol_monotonic)

        # C3
        Ts = _parse_sat_T(args.sat_T)
        results_c3 = []
        if Ts:
            r3 = check_clapeyron(adapter, args.fluid, Ts, tol_rel=args.tol_clap)
            results_c3 = [r3]

        # C4: use three temperatures across grid if not provided
        T_list_c4 = [float(T_vals[0]), float(T_vals[len(T_vals) // 2]), float(T_vals[-1])]
        r4 = check_speed_of_sound(adapter, args.fluid, T_list_c4, p_ref=1e5, tol_rel=args.tol_c4)

        summary = aggregate_checks_to_summary(
            adapter_name=adapter.__class__.__name__,
            fluid=args.fluid,
            grid=args.grid,
            results_monotonic=[r1],
            results_compress=[r2],
            results_clapeyron=results_c3,
            tol_monotonic=args.tol_monotonic,
            tol_clap=args.tol_clap,
            results_c4=[r4],
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
