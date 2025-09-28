from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.api import FiniteDiff


def test_convergence_drho_dp_two_steps():
    a = CoolPropAdapter("CO2")
    T = 260.0
    p = 3.0e6
    d1 = FiniteDiff.drho_dp_at_T(a, T, p, dp=5e3)
    d2 = FiniteDiff.drho_dp_at_T(a, T, p, dp=2e3)
    # agree within 5% (very loose; fast smoke test)
    rel = abs(d1 - d2) / max(abs(d1), 1e-12)
    assert rel < 0.05
