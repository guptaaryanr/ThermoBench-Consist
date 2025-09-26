from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime
import platform
import json
import numpy as np

from .checks import MonotonicResult, CompressibilityResult, ClapeyronResult


@dataclass
class CheckSummary:
    name: str
    supported: bool
    passed: bool
    pass_ratio: float  # for collections (single result -> 1.0 if passed)
    details: Dict[str, Any]


def _summarize_monotonic(results: List[MonotonicResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    detail = {
        "per_T": [
            {
                "T": r.T,
                "fraction_positive": r.fraction_positive,
                "min_derivative": r.min_derivative,
                "passed": r.passed,
            }
            for r in results
        ]
    }
    return CheckSummary("C1_monotonic", supported, all(passes) if passes else False, ratio, detail)


def _summarize_compress(results: List[CompressibilityResult]) -> CheckSummary:
    supported = any(r.supported for r in results)
    passes = [r.passed for r in results if r.supported]
    ratio = float(np.mean(passes)) if passes else 0.0
    detail = {
        "per_T": [
            {"T": r.T, "passed": r.passed, "min_kappa": min(r.kappa_T) if r.kappa_T else None}
            for r in results
        ]
    }
    return CheckSummary(
        "C2_compressibility", supported, all(passes) if passes else False, ratio, detail
    )


def _summarize_clapeyron(results: List[ClapeyronResult]) -> CheckSummary:
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
            }
            for r in results
        ],
        "median_errors_all": med_errs,
    }
    return CheckSummary("C3_clapeyron", supported, all(passes) if passes else False, ratio, detail)


def aggregate_checks_to_summary(
    adapter_name: str,
    fluid: str,
    grid: str,
    results_monotonic: List[MonotonicResult],
    results_compress: List[CompressibilityResult],
    results_clapeyron: List[ClapeyronResult],
    tol_monotonic: float,
    tol_clap: float,
) -> Dict[str, Any]:
    """Aggregate per-check results and compute composite score in [0, 100]."""
    c1 = _summarize_monotonic(results_monotonic)
    c2 = _summarize_compress(results_compress)
    c3 = _summarize_clapeyron(results_clapeyron)

    ratios = [c.pass_ratio for c in [c1, c2, c3] if c.supported]
    composite = float(100.0 * np.mean(ratios)) if ratios else 0.0

    summary = {
        "schema_version": "1.0",
        "datetime_utc": datetime.utcnow().isoformat() + "Z",
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
            },
            c2.name: {
                "supported": c2.supported,
                "passed": c2.passed,
                "pass_ratio": c2.pass_ratio,
                "details": c2.details,
            },
            c3.name: {
                "supported": c3.supported,
                "passed": c3.passed,
                "pass_ratio": c3.pass_ratio,
                "details": c3.details,
            },
        },
        "composite_score": composite,
    }
    return summary
