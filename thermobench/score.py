from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from .checks import ClapeyronResult, CompressibilityResult, MonotonicResult, SpeedOfSoundResult


@dataclass
class CheckSummary:
    name: str
    supported: bool
    passed: bool
    pass_ratio: float  # for collections (single result -> 1.0 if passed)
    details: dict[str, Any]
    severity: str  # "info" | "warn" | "fail"


def _severity_from_flags(passed: bool, warn_flag: bool) -> str:
    if passed and not warn_flag:
        return "info"
    if passed and warn_flag:
        return "warn"
    return "fail"


def _summarize_monotonic(results: list[MonotonicResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    warn_flag = any(getattr(r, "near_spinodal", False) for r in results)
    detail = {
        "per_T": [
            {
                "T": r.T,
                "fraction_positive": r.fraction_positive,
                "min_derivative": r.min_derivative,
                "passed": r.passed,
                "near_spinodal": r.near_spinodal,
                "p": r.p,
                "drho_dp": r.drho_dp,
            }
            for r in results
        ]
    }
    return CheckSummary(
        "C1_monotonic",
        supported,
        all(passes) if passes else False,
        ratio,
        detail,
        _severity_from_flags(all(passes) if passes else False, warn_flag),
    )


def _summarize_compress(results: list[CompressibilityResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    warn_flag = any(getattr(r, "near_spinodal", False) for r in results)
    detail = {
        "per_T": [
            {
                "T": r.T,
                "passed": r.passed,
                "min_kappa": min(r.kappa_T) if r.kappa_T else None,
                "near_spinodal": r.near_spinodal,
                "p": r.p,
                "kappa_T": r.kappa_T,
            }
            for r in results
        ]
    }
    return CheckSummary(
        "C2_compressibility",
        supported,
        all(passes) if passes else False,
        ratio,
        detail,
        _severity_from_flags(all(passes) if passes else False, warn_flag),
    )


def _summarize_clapeyron(results: list[ClapeyronResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    med_errs = [
        float(np.median([e for e in r.rel_errors if np.isfinite(e)] or [float("inf")]))
        for r in results
    ]
    detail = {
        "per_run": [
            {
                "T_list": r.T_list,
                "median_rel_error": float(
                    np.median([e for e in r.rel_errors if np.isfinite(e)] or [float("inf")])
                ),
                "passed": r.passed,
                "lhs": r.lhs_values,
                "rhs": r.rhs_values,
            }
            for r in results
        ],
        "median_errors_all": med_errs,
    }
    # No warn flag for C3—either passes tolerance or not
    sev = "info" if (all(passes) if passes else False) else "fail"
    return CheckSummary(
        "C3_clapeyron", supported, all(passes) if passes else False, ratio, detail, sev
    )


def _summarize_c4(results: list[SpeedOfSoundResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    detail = {
        "per_run": [
            {
                "T_list": r.T_list,
                "p_ref": r.p_ref,
                "median_rel_error": float(
                    np.median([e for e in r.rel_errors if np.isfinite(e)] or [float("inf")])
                ),
                "passed": r.passed,
                "a2_ref": r.a2_ref,
                "a2_sur": r.a2_sur,
            }
            for r in results
        ]
    }
    sev = "info" if (all(passes) if passes else False) else ("warn" if supported else "info")
    return CheckSummary(
        "C4_speed_of_sound", supported, all(passes) if passes else False, ratio, detail, sev
    )


def aggregate_checks_to_summary(
    adapter_name: str,
    fluid: str,
    grid: str,
    results_monotonic: list[MonotonicResult],
    results_compress: list[CompressibilityResult],
    results_clapeyron: list[ClapeyronResult],
    tol_monotonic: float,
    tol_clap: float,
    results_c4: list[SpeedOfSoundResult] | None = None,
) -> dict[str, Any]:
    """Aggregate per-check results and compute composite score in [0, 100]."""
    c1 = _summarize_monotonic(results_monotonic)
    c2 = _summarize_compress(results_compress)
    c3 = _summarize_clapeyron(results_clapeyron)
    c4 = _summarize_c4(results_c4 or [])

    ratios = [c.pass_ratio for c in [c1, c2, c3] if c.supported]
    composite = float(100.0 * np.mean(ratios)) if ratios else 0.0

    # Badges: Core (C1–C3) and Plus (C4)
    core = [c for c in [c1, c2, c3] if c.supported]
    plus = [c4] if c4.supported else []
    badges = {
        "Core": float(np.mean([c.pass_ratio for c in core])) if core else 0.0,
        "Plus": float(np.mean([c.pass_ratio for c in plus])) if plus else 0.0,
    }

    summary = {
        "schema_version": "1.1",
        "datetime_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),  # timezone-aware ISO8601 in UTC with 'Z' suffix
        "system": {"python": platform.python_version(), "platform": platform.platform()},
        "adapter": adapter_name,
        "fluid": fluid,
        "grid": grid,
        "tolerances": {"monotonic": tol_monotonic, "clapeyron_rel": tol_clap},
        "checks": {
            c1.name: {
                "supported": c1.supported,
                "passed": c1.passed,
                "pass_ratio": c1.pass_ratio,
                "details": c1.details,
                "severity": c1.severity,
            },
            c2.name: {
                "supported": c2.supported,
                "passed": c2.passed,
                "pass_ratio": c2.pass_ratio,
                "details": c2.details,
                "severity": c2.severity,
            },
            c3.name: {
                "supported": c3.supported,
                "passed": c3.passed,
                "pass_ratio": c3.pass_ratio,
                "details": c3.details,
                "severity": c3.severity,
            },
            c4.name: {
                "supported": c4.supported,
                "passed": c4.passed,
                "pass_ratio": c4.pass_ratio,
                "details": c4.details,
                "severity": c4.severity,
            },
        },
        "badges": badges,
        "composite_score": composite,
    }
    return summary
