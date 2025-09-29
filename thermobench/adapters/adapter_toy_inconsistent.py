from __future__ import annotations

from dataclasses import dataclass

import numpy as np
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
        return Capabilities(
            supports_rho=True,
            supports_h=True,
            supports_phase_split=True,
            supports_speed_of_sound=True,
        )

    def rho(self, T: float, p: float, x=None) -> float:
        """Toy density [kg/m³] with a controlled non-monotone region around 2 MPa.

        Strategy: a mild positive base slope plus a *sufficiently strong* Gaussian dip
        centered at 2.0 MPa. The left shoulder of the dip makes ∂ρ/∂p negative
        over ~1.8–2.0 MPa, which the tests probe.
        """

        T = float(T)
        p = float(p)

        # Base trend ~ realistic magnitude and positive slope
        # base' = d(base)/dp = 100 * 0.8e-6 = 8e-5 (kg/m^3)/Pa
        temp_mod = 1.0 + 0.001 * (T - 273.15) / 100.0
        base = 100.0 * (0.8e-6 * p + 1.2) * temp_mod  # ~ O(10^2) kg/m^3

        # Gaussian dip parameters chosen so that |d(dip)/dp| > base' near the left shoulder:
        # derivative magnitude ~ (A/σ)*exp(-0.5)
        # choose A=30 kg/m^3, σ=1.5e5 Pa  -> (30/1.5e5)*0.607 ≈ 1.2e-4 > 8e-5
        p0 = 2.0e6  # center of dip [Pa]
        sigma = 1.5e5  # width [Pa]
        A = 30.0  # amplitude [kg/m^3]
        dip = A * np.exp(-((p - p0) ** 2) / (2.0 * sigma**2))

        rho = base - dip
        return float(max(rho, 1e-6))

    def h(self, T: float, p: float, x=None) -> float:
        """Toy enthalpy [J/kg]; weak p-dependence."""
        T = float(T)
        p = float(p)
        return 1.0e3 * T + 5.0e-4 * p

    def phase_split_at_T(self, T: float) -> tuple[float, dict[str, float], dict[str, float]]:
        """Use CoolProp p_sat(T) but inject inconsistent Δh."""
        T = float(T)
        p_sat = float(PropsSI("P", "T", T, "Q", 0, self.fluid))
        rho_l = float(PropsSI("D", "T", T, "Q", 0, self.fluid))
        rho_v = float(PropsSI("D", "T", T, "Q", 1, self.fluid))
        # spuriously tiny latent heat so Clapeyron fails badly
        h_l = 1.0e3 * T
        h_v = h_l + 100.0
        return p_sat, {"rho": rho_l, "h": h_l}, {"rho": rho_v, "h": h_v}

    def speed_of_sound(self, T: float, p: float, x=None) -> float:
        """Bias the speed of sound low to make C4 fail in a controlled way."""
        a_ref = float(PropsSI("A", "T", float(T), "P", float(p), self.fluid))
        return max(1.0, 0.6 * a_ref)  # ~40% low
