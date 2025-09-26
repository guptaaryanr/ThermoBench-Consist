from __future__ import annotations

from dataclasses import dataclass

from CoolProp.CoolProp import PropsSI  # for p_sat baseline only

from ..api import Capabilities


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
        """Toy density [kg/m³] with a deliberate negative dρ/dp region near ~2.0 MPa.

        Form:
            ρ(p) = a0 + a1*(p - p_ref) - B * ((p - p0)^2) / S + tiny T-mod
        so that:
            dρ/dp = a1 - 2B*(p - p0)/S
        which becomes negative for p > p0 if B is large enough.
        """
        T = float(T)
        p = float(p)

        a0 = 200.0  # baseline density level [kg/m^3]
        a1 = 8.0e-7  # small positive base slope [(kg/m^3)/Pa]
        p_ref = 1.0e5  # reference pressure [Pa]

        p0 = 2.0e6  # center of the "dent" [Pa]
        B = 8.0  # strength of non-monotonic term [unitless]
        S = 1.0e12  # scaling for the quadratic term to keep magnitudes reasonable

        rho = a0 + a1 * (p - p_ref) - B * ((p - p0) ** 2) / S
        rho += 0.001 * (T - 273.15)  # tiny T modulation (keeps values plausible)

        # keep strictly positive (clip very small values, avoid abs() which wrecks slope signs)
        if rho < 1.0:
            rho = 1.0
        return float(rho)

    def h(self, T: float, p: float, x=None) -> float:
        """Toy enthalpy [J/kg]; weakly varying to remain plausible."""
        T = float(T)
        p = float(p)
        return 1.0e3 * T + 5.0e-4 * p  # mild p dependence

    def phase_split_at_T(self, T: float) -> tuple[float, dict[str, float], dict[str, float]]:
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
