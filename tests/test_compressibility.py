import numpy as np

from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.adapters.adapter_toy_inconsistent import ToyInconsistentAdapter
from thermobench.checks import check_compressibility


def test_compressibility_positive_for_coolprop():
    adapter = CoolPropAdapter(fluid="N2")
    T = 110.0
    p = np.linspace(1e5, 6e5, 30)
    res = check_compressibility(adapter, "N2", T, p, tol=1e-7)
    assert res.supported is True
    assert res.passed is True


def test_compressibility_negative_region_for_toy():
    adapter = ToyInconsistentAdapter(fluid="N2")
    T = 100.0
    p = np.linspace(1.8e6, 2.2e6, 40)  # range around the wiggle
    res = check_compressibility(adapter, "N2", T, p, tol=1e-10)
    assert res.supported is True
    assert res.passed is False
