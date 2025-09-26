from __future__ import annotations

from typing import Tuple
import numpy as np
import pandas as pd
from CoolProp.CoolProp import PhaseSI


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


def parse_grid_string(grid: str) -> Tuple[np.ndarray, np.ndarray]:
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


def default_saturation_T(fluid: str) -> list[float]:
    """Convenience: small saturation-T lists for CO2 and N2 examples."""
    if fluid.upper() == "CO2":
        return [230.0, 240.0, 260.0, 280.0]
    if fluid.upper() == "N2":
        return [85.0, 95.0, 105.0, 115.0]
    return []
