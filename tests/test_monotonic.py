import numpy as np
from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.adapters.adapter_toy_inconsistent import ToyInconsistentAdapter
from thermobench.checks import check_monotonic_rho_isotherm


def test_monotonic_positive_for_coolprop():
    adapter = CoolPropAdapter(fluid="CO2")
    T = 280.0  # K
    p = np.linspace(1e5, 5e5, 40)
    res = check_monotonic_rho_isotherm(adapter, "CO2", T, p, tol=1e-7)
    assert res.supported is True
    assert res.passed is True
    assert res.fraction_positive >= 0.9


def test_monotonic_detects_violation_in_toy():
    adapter = ToyInconsistentAdapter(fluid="CO2")
    T = 270.0
    # include the wiggle region near ~2 MPa to induce negative slope
    p = np.linspace(1.5e6, 2.5e6, 60)
    res = check_monotonic_rho_isotherm(adapter, "CO2", T, p, tol=1e-8)
    assert res.supported is True
    assert res.passed is False
    assert res.fraction_positive < 1.0
