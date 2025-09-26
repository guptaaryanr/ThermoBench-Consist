from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from CoolProp.CoolProp import PropsSI
from ..api import Capabilities, SurrogateAdapter


@dataclass
class CoolPropAdapter:
    """Reference adapter using CoolProp (pure fluids)."""

    fluid: str

    def capabilities(self) -> Capabilities:
        return Capabilities(supports_rho=True, supports_h=True, supports_phase_split=True)

    # Required
    def rho(self, T: float, p: float, x=None) -> float:
        """Density ρ [kg/m³]."""
        return float(PropsSI("D", "T", float(T), "P", float(p), self.fluid))

    # Optional
    def h(self, T: float, p: float, x=None) -> float:
        """Specific enthalpy h [J/kg]."""
        return float(PropsSI("H", "T", float(T), "P", float(p), self.fluid))

    def phase_split_at_T(self, T: float) -> Tuple[float, Dict[str, float], Dict[str, float]]:
        """Return saturation at T: p_sat and (ρ,h) for liquid and vapor."""
        T = float(T)
        p_sat = float(PropsSI("P", "T", T, "Q", 0, self.fluid))
        rho_l = float(PropsSI("D", "T", T, "Q", 0, self.fluid))
        rho_v = float(PropsSI("D", "T", T, "Q", 1, self.fluid))
        h_l = float(PropsSI("H", "T", T, "Q", 0, self.fluid))
        h_v = float(PropsSI("H", "T", T, "Q", 1, self.fluid))
        return p_sat, {"rho": rho_l, "h": h_l}, {"rho": rho_v, "h": h_v}
