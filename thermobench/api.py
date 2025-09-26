from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pint

ureg = pint.UnitRegistry()
Q_ = ureg.Quantity


@dataclass(frozen=True)
class Capabilities:
    """Flags indicating which checks are supported by a surrogate.

    Attributes
    ----------
    supports_rho : bool
        Whether density rho(T, p) is implemented (required).
    supports_h : bool
        Whether enthalpy h(T, p) is implemented.
    supports_phase_split : bool
        Whether VLE split at T is implemented (provides p_sat and (rho,h) for liq/vap).
    """

    supports_rho: bool = True
    supports_h: bool = False
    supports_phase_split: bool = False


class SurrogateAdapter(Protocol):
    """Protocol for property surrogate adapters (pure fluids).

    Required
    --------
    rho(T, p, x=None) -> float
        Density ρ [kg/m³] given temperature T [K] and pressure p [Pa].

    Optional
    --------
    h(T, p, x=None) -> float
        Specific enthalpy h [J/kg].

    phase_split_at_T(T) -> (p_sat, props_liq, props_vap)
        Saturation split at temperature T [K]. Returns:
        - p_sat [Pa]
        - props_liq: {"rho": ρ_liq [kg/m³], "h": h_liq [J/kg]}
        - props_vap: {"rho": ρ_vap [kg/m³], "h": h_vap [J/kg]}

    capabilities() -> Capabilities
        Capability flags.

    Notes
    -----
    * Units are SI; callers pass floats in base SI units.
    * Surrogates may ignore `x` (composition) in v0.1; it is kept for future mixtures.
    """

    fluid: str

    def rho(self, T: float, p: float, x: Any | None = None) -> float: ...

    def h(self, T: float, p: float, x: Any | None = None) -> float: ...

    def phase_split_at_T(self, T: float) -> tuple[float, dict[str, float], dict[str, float]]: ...

    def capabilities(self) -> Capabilities: ...


class FiniteDiff:
    """Finite-difference helpers with explicit unit guidance.

    All inputs are floats in SI (K, Pa). Steps are in Pa or K as documented.
    """

    @staticmethod
    def drho_dp_at_T(adapter: SurrogateAdapter, T: float, p: float, dp: float = 1e3) -> float:
        """Centered finite difference for (∂ρ/∂p)|_T.

        Parameters
        ----------
        adapter : SurrogateAdapter
        T : float
            Temperature [K].
        p : float
            Pressure [Pa].
        dp : float, default 1e3
            Pressure step [Pa].

        Returns
        -------
        float
            Approximate derivative (kg/m³)/Pa.
        """
        p1, p2 = p - 0.5 * dp, p + 0.5 * dp
        rho1 = float(adapter.rho(T, p1))
        rho2 = float(adapter.rho(T, p2))
        return (rho2 - rho1) / dp

    @staticmethod
    def dP_sat_dT_coolprop(fluid: str, T: float, dT: float = 1e-2) -> float:
        """Finite difference of saturation pressure using CoolProp baseline.

        Returns dP_sat/dT evaluated by a symmetric difference around T.

        Parameters
        ----------
        fluid : str
        T : float [K]
        dT : float [K], small

        Returns
        -------
        float
            dP_sat/dT [Pa/K]
        """
        from CoolProp.CoolProp import PropsSI

        Pp = float(PropsSI("P", "T", T + 0.5 * dT, "Q", 0, fluid))
        Pm = float(PropsSI("P", "T", T - 0.5 * dT, "Q", 0, fluid))
        return (Pp - Pm) / dT
