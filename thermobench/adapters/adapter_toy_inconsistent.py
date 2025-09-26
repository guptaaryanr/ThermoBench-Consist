from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from CoolProp.CoolProp import PropsSI  # for p_sat baseline only
from ..api import Capabilities, SurrogateAdapter


@dataclass
class ToyInconsistentAdapter:
    """Deliberately inconsistent surrogate.

    - Density has a small region with negative dρ/dp near p ≈ 2 MPa.
    - Enthalpy jump across VLE is spuriously small -> fails Clapeyron.
    """

    fluid: str

    def capabilities(self) -> Capabilities:
        return Capabilities(supports_rho=True, supports_h=True, supports_phase_split=True)

    def rho(self, T: float, p: float, x=None) -> float:
        """Toy density [kg/m³]; mostly linear in p with a local wiggle."""
        T = float(T)
        p = float(p)
        base = 0.8e-6 * p + 1.2  # linear trend (arbitrary units but positive)
        wiggle = -0.2 * (p / 2e6 - 1.0) * (p / 2e6 - 1.2)  # creates a small non-monotone region
        temp_mod = 1.0 + 0.001 * (T - 273.15) / 100.0
        rho = abs(base + wiggle) * 100.0 * temp_mod  # scale to ~ realistic kg/m3
        return float(rho)

    def h(self, T: float, p: float, x=None) -> float:
        """Toy enthalpy [J/kg]; weakly varying to remain plausible."""
        T = float(T)
        p = float(p)
        return 1.0e3 * T + 5.0e-4 * p  # mild p dependence

    def phase_split_at_T(self, T: float) -> Tuple[float, Dict[str, float], Dict[str, float]]:
        """Use CoolProp p_sat(T) but inject inconsistent Δh."""
        T = float(T)
        p_sat = float(PropsSI("P", "T", T, "Q", 0, self.fluid))
        # Fabricate densities: take CoolProp densities (for plausibility)
        rho_l = float(PropsSI("D", "T", T, "Q", 0, self.fluid))
        rho_v = float(PropsSI("D", "T", T, "Q", 1, self.fluid))
        # Make enthalpy jump spuriously small (violates Clapeyron)
        h_l = float(1.0e3 * T)  # ~ T kJ/kg
        h_v = h_l + 100.0  # only 100 J/kg of latent heat (nonsense small)
        return p_sat, {"rho": rho_l, "h": h_l}, {"rho": rho_v, "h": h_v}
