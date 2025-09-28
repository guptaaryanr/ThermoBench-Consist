from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from CoolProp.CoolProp import PropsSI

from .api import FiniteDiff, SurrogateAdapter


@dataclass
class MonotonicResult:
    name: str
    fluid: str
    T: float
    p: list[float]
    drho_dp: list[float]
    fraction_positive: float
    min_derivative: float
    tol: float
    supported: bool
    passed: bool
    near_spinodal: bool = False


@dataclass
class CompressibilityResult:
    name: str
    fluid: str
    T: float
    p: list[float]
    kappa_T: list[float]
    tol: float
    supported: bool
    passed: bool
    near_spinodal: bool = False


@dataclass
class ClapeyronResult:
    name: str
    fluid: str
    T_list: list[float]
    rel_errors: list[float]
    tol_rel: float
    supported: bool
    passed: bool
    rhs_values: list[float]  # Δh/(T·Δv)
    lhs_values: list[float]  # dP_sat/dT baseline


@dataclass
class SpeedOfSoundResult:
    name: str
    fluid: str
    T_list: list[float]
    p_ref: float
    rel_errors: list[float]  # surrogate vs CP a^2 per T
    tol_rel: float
    supported: bool
    passed: bool
    a2_ref: list[float]
    a2_sur: list[float]


def check_monotonic_rho_isotherm(
    adapter: SurrogateAdapter, fluid: str, T: float, p_vals: Sequence[float], tol: float = 1e-6
) -> MonotonicResult:
    """C1: ∂ρ/∂p|_T > 0 along a single-phase isotherm.

    We compute centered FD derivatives on the `p_vals` grid.

    Returns a MonotonicResult with fraction of positive steps and min derivative.
    """
    if not adapter.capabilities().supports_rho:
        return MonotonicResult(
            name="C1_monotonic",
            fluid=fluid,
            T=T,
            p=list(map(float, p_vals)),
            drho_dp=[],
            fraction_positive=0.0,
            min_derivative=float("nan"),
            tol=tol,
            supported=False,
            passed=False,
        )

    p_vals = np.asarray(p_vals, dtype=float)
    # derivatives at midpoints between p[k] and p[k+1]
    dr = []
    for p1, p2 in zip(p_vals[:-1], p_vals[1:], strict=False):
        pmid = 0.5 * (p1 + p2)
        dp = p2 - p1
        d = FiniteDiff.drho_dp_at_T(adapter, T, pmid, dp=dp)
        dr.append(d)
    dr = np.asarray(dr)
    frac_pos = float(np.mean(dr > -tol)) if dr.size > 0 else 0.0
    min_d = float(np.min(dr)) if dr.size > 0 else float("nan")
    passed = bool(np.all(dr > -tol))
    # guardrail: near-spinodal when small positive
    eps_guard = max(10.0 * tol, 1e-9)
    near_spinodal = bool(np.any((dr >= 0) & (dr < eps_guard)))
    return MonotonicResult(
        name="C1_monotonic",
        fluid=fluid,
        T=float(T),
        p=list(map(float, p_vals)),
        drho_dp=list(map(float, dr)),
        fraction_positive=frac_pos,
        min_derivative=min_d,
        tol=tol,
        supported=True,
        passed=passed,
        near_spinodal=near_spinodal,
    )


def check_compressibility(
    adapter: SurrogateAdapter, fluid: str, T: float, p_vals: Sequence[float], tol: float = 1e-6
) -> CompressibilityResult:
    """C2: κ_T = (1/ρ)(∂ρ/∂p)|_T > 0.

    Derivative estimated via centered FD on isotherm samples.
    """
    if not adapter.capabilities().supports_rho:
        return CompressibilityResult(
            name="C2_compressibility",
            fluid=fluid,
            T=T,
            p=list(map(float, p_vals)),
            kappa_T=[],
            tol=tol,
            supported=False,
            passed=False,
        )

    p_vals = np.asarray(p_vals, dtype=float)
    kappas = []
    for p1, p2 in zip(p_vals[:-1], p_vals[1:], strict=False):
        pmid = 0.5 * (p1 + p2)
        dp = p2 - p1
        drdp = FiniteDiff.drho_dp_at_T(adapter, T, pmid, dp=dp)
        rho_mid = float(adapter.rho(T, pmid))
        kappa = drdp / max(rho_mid, 1e-30)
        kappas.append(kappa)
    kappas = np.asarray(kappas)
    passed = bool(np.all(kappas > -tol))
    eps_guard = max(10.0 * tol, 1e-9)
    near_spinodal = bool(np.any((kappas >= 0) & (kappas < eps_guard)))
    return CompressibilityResult(
        name="C2_compressibility",
        fluid=fluid,
        T=float(T),
        p=list(map(float, p_vals)),
        kappa_T=list(map(float, kappas)),
        tol=tol,
        supported=True,
        passed=passed,
        near_spinodal=near_spinodal,
    )


def check_clapeyron(
    adapter: SurrogateAdapter, fluid: str, T_list: Sequence[float], tol_rel: float = 0.1
) -> ClapeyronResult:
    """C3: Clapeyron slope along the VLE line.

    For each T in T_list, compute:
      lhs (baseline): dP_sat/dT via CoolProp (finite difference),
      rhs (surrogate): Δh / (T · Δv), where Δv = 1/ρ_vap - 1/ρ_liq,
    using the adapter's `phase_split_at_T`. If the adapter cannot provide
    both ρ and h for both phases, mark supported=False (excluded from score).
    """
    caps = adapter.capabilities()
    supports = bool(caps.supports_phase_split and caps.supports_h and caps.supports_rho)
    lhs_vals, rhs_vals, rel_err = [], [], []

    # Guard: filter Ts to valid saturation range for the fluid
    try:
        T_triple = float(PropsSI("Ttriple", fluid))
        T_crit = float(PropsSI("Tcrit", fluid))
    except Exception:
        T_triple, T_crit = -float("inf"), float("inf")
    T_list = [float(T) for T in T_list if (T_triple < float(T) < T_crit)]
    if not T_list:
        # No valid temperatures -> mark unsupported (excluded from score)
        return ClapeyronResult(
            name="C3_clapeyron",
            fluid=fluid,
            T_list=[],
            rel_errors=[],
            tol_rel=tol_rel,
            supported=False,
            passed=False,
            rhs_values=[],
            lhs_values=[],
        )

    for T in T_list:
        # Baseline slope from CoolProp
        lhs = FiniteDiff.dP_sat_dT_coolprop(fluid, float(T), dT=1e-2)
        lhs_vals.append(float(lhs))

        rhs = float("nan")
        if supports:
            try:
                p_sat, liq, vap = adapter.phase_split_at_T(float(T))
                rho_l, rho_v = float(liq["rho"]), float(vap["rho"])
                h_l, h_v = float(liq["h"]), float(vap["h"])
                dv = 1.0 / rho_v - 1.0 / rho_l
                dh = h_v - h_l
                rhs = dh / (float(T) * dv)
            except Exception:
                supports = False  # degrade gracefully
        rhs_vals.append(float(rhs))

        # Avoid division by zero; still report a number
        rel = abs(lhs - rhs) / abs(lhs) if np.isfinite(rhs) and abs(lhs) > 0 else float("inf")
        rel_err.append(float(rel))

    med_err = np.median([x for x in rel_err if np.isfinite(x)]) if supports else float("inf")
    passed = bool(med_err < tol_rel) if supports else False
    return ClapeyronResult(
        name="C3_clapeyron",
        fluid=fluid,
        T_list=list(map(float, T_list)),
        rel_errors=list(map(float, rel_err)),
        tol_rel=tol_rel,
        supported=supports,
        passed=passed,
        rhs_values=list(map(float, rhs_vals)),
        lhs_values=list(map(float, lhs_vals)),
    )


def check_speed_of_sound(
    adapter: SurrogateAdapter,
    fluid: str,
    T_list: Sequence[float],
    p_ref: float = 1e5,
    tol_rel: float = 0.2,
) -> SpeedOfSoundResult:
    """C4: Compare surrogate a^2 against CoolProp reference at a fixed p_ref.

    If surrogate lacks a speed_of_sound method, mark unsupported but return reference arrays for plotting.
    """
    caps = adapter.capabilities()
    supports = bool(getattr(caps, "supports_speed_of_sound", False))

    a2_ref, a2_sur, rel = [], [], []
    for T in T_list:
        a_ref = FiniteDiff.a_coolprop(fluid, float(T), float(p_ref))
        a2_ref.append(a_ref * a_ref)
        if supports:
            try:
                a_sur = float(adapter.speed_of_sound(float(T), float(p_ref)))
                a2_sur.append(a_sur * a_sur)
                rel.append(abs((a_sur * a_sur) - (a_ref * a_ref)) / max(a_ref * a_ref, 1e-30))
            except Exception:
                supports = False
                a2_sur.append(float("nan"))
                rel.append(float("inf"))
        else:
            a2_sur.append(float("nan"))
            rel.append(float("inf"))

    med_err = np.median([x for x in rel if np.isfinite(x)]) if supports else float("inf")
    passed = bool(med_err < tol_rel) if supports else False
    return SpeedOfSoundResult(
        name="C4_speed_of_sound",
        fluid=fluid,
        T_list=list(map(float, T_list)),
        p_ref=float(p_ref),
        rel_errors=list(map(float, rel)),
        tol_rel=tol_rel,
        supported=supports,
        passed=passed,
        a2_ref=list(map(float, a2_ref)),
        a2_sur=list(map(float, a2_sur)),
    )
