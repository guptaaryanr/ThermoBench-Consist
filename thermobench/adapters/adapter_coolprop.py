from __future__ import annotations

import functools
from dataclasses import dataclass

from CoolProp.CoolProp import PropsSI

from ..api import Capabilities


def _lru(maxsize=1024):
    return functools.lru_cache(maxsize=maxsize)


@_lru()
def _cp_D(fluid: str, T: float, p: float) -> float:
    return float(PropsSI("D", "T", T, "P", p, fluid))


@_lru()
def _cp_H(fluid: str, T: float, p: float) -> float:
    return float(PropsSI("H", "T", T, "P", p, fluid))


@_lru()
def _cp_QD(fluid: str, T: float, Q: int) -> float:
    return float(PropsSI("D", "T", T, "Q", Q, fluid))


@_lru()
def _cp_QH(fluid: str, T: float, Q: int) -> float:
    return float(PropsSI("H", "T", T, "Q", Q, fluid))


@_lru()
def _cp_QP(fluid: str, T: float, Q: int) -> float:
    return float(PropsSI("P", "T", T, "Q", Q, fluid))


@_lru()
def _cp_A(fluid: str, T: float, p: float) -> float:
    return float(PropsSI("A", "T", T, "P", p, fluid))


@dataclass
class CoolPropAdapter:
    """Reference adapter using CoolProp (pure fluids)."""

    fluid: str

    def capabilities(self) -> Capabilities:
        return Capabilities(
            supports_rho=True,
            supports_h=True,
            supports_phase_split=True,
            supports_speed_of_sound=True,
        )

    def rho(self, T: float, p: float, x=None) -> float:
        return _cp_D(self.fluid, float(T), float(p))

    def h(self, T: float, p: float, x=None) -> float:
        return _cp_H(self.fluid, float(T), float(p))

    def speed_of_sound(self, T: float, p: float, x=None) -> float:
        return _cp_A(self.fluid, float(T), float(p))

    def phase_split_at_T(self, T: float) -> tuple[float, dict[str, float], dict[str, float]]:
        T = float(T)
        p_sat = _cp_QP(self.fluid, T, 0)
        rho_l = _cp_QD(self.fluid, T, 0)
        rho_v = _cp_QD(self.fluid, T, 1)
        h_l = _cp_QH(self.fluid, T, 0)
        h_v = _cp_QH(self.fluid, T, 1)
        return p_sat, {"rho": rho_l, "h": h_l}, {"rho": rho_v, "h": h_v}
