from __future__ import annotations

import numpy as np
import pandas as pd
from CoolProp.CoolProp import PhaseSI

from .api import FiniteDiff


def _parse_range(expr: str) -> np.ndarray:
    """Parse a range like '220:300:10' into an array [220,230,...,300]."""
    a, b, s = expr.split(":")
    start, stop, step = float(a), float(b), float(s)
    n = int(np.floor((stop - start) / step)) + 1
    vals = start + np.arange(n) * step
    # include stop if exactly on step
    if abs(vals[-1] - stop) > 1e-12:
        vals = np.append(vals, stop)
    return vals


def parse_grid_string(grid: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse grid string like 'T=220:300:10,p=1e5:5e6:5e5'.

    Returns
    -------
    T_vals : np.ndarray [K]
    p_vals : np.ndarray [Pa]
    """
    parts = {kv.split("=")[0].strip(): kv.split("=")[1].strip() for kv in grid.split(",")}
    T_vals = _parse_range(parts["T"])
    p_vals = _parse_range(parts["p"])
    return T_vals, p_vals


def apply_critical_guard(fluid: str, T_vals: np.ndarray, band_K: float = 2.0) -> np.ndarray:
    """Optionally shrink T grid to avoid ±band_K around T_c (informational guard)."""
    Tc = FiniteDiff.critical_temperature(fluid)
    keep = [float(T) for T in T_vals if not (Tc - band_K <= T <= Tc + band_K)]
    return np.array(keep, dtype=float) if keep else T_vals


def sample_single_phase_points(
    fluid: str, T_vals: np.ndarray, p_vals: np.ndarray, max_points: int | None = None
) -> pd.DataFrame:
    """Return a DataFrame of (T, p) points filtered to single-phase via CoolProp.

    We use CoolProp's PhaseSI; any 'two_phase' states are skipped.

    Columns: ['fluid', 'T_K', 'p_Pa'].
    """
    rows = []
    for T in T_vals:
        for p in p_vals:
            phase = PhaseSI("T", float(T), "P", float(p), fluid)  # returns string
            if "two_phase" in phase.lower():
                continue
            rows.append((fluid, float(T), float(p)))
            if max_points and len(rows) >= max_points:
                break
        if max_points and len(rows) >= max_points:
            break
    return pd.DataFrame(rows, columns=["fluid", "T_K", "p_Pa"])


def random_grid(
    fluid: str,
    T_vals: np.ndarray,
    p_vals: np.ndarray,
    seed: int | None,
    nT: int = 3,
    nP: int = 25,
    critical_guard: bool = False,
    guard_band_K: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Pick small random subsets of T and p (single-phase filter applied later by checks)."""
    rng = np.random.default_rng(seed)
    if critical_guard:
        T_vals = apply_critical_guard(fluid, T_vals, band_K=guard_band_K)
    Ts = np.sort(rng.choice(T_vals, size=min(nT, len(T_vals)), replace=False))
    Ps = np.sort(rng.choice(p_vals, size=min(nP, len(p_vals)), replace=False))
    return Ts, Ps


def default_saturation_T(fluid: str) -> list[float]:
    """Convenience: small saturation-T lists for CO2 and N2 examples."""
    if fluid.upper() == "CO2":
        return [230.0, 240.0, 260.0, 280.0]
    if fluid.upper() == "N2":
        return [85.0, 95.0, 105.0, 115.0]
    return []
