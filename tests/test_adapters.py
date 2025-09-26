from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.adapters.adapter_toy_inconsistent import ToyInconsistentAdapter


def test_capabilities_flags():
    a = CoolPropAdapter(fluid="CO2")
    c = a.capabilities()
    assert c.supports_rho and c.supports_h and c.supports_phase_split

    b = ToyInconsistentAdapter(fluid="CO2")
    c2 = b.capabilities()
    assert c2.supports_rho and c2.supports_h and c2.supports_phase_split
