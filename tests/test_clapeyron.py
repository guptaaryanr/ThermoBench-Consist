from thermobench.adapters.adapter_coolprop import CoolPropAdapter
from thermobench.adapters.adapter_toy_inconsistent import ToyInconsistentAdapter
from thermobench.checks import check_clapeyron


def test_clapeyron_matches_coolprop_for_reference():
    adapter = CoolPropAdapter(fluid="CO2")
    Ts = [230.0, 240.0, 260.0]
    res = check_clapeyron(adapter, "CO2", Ts, tol_rel=0.1)
    assert res.supported is True
    assert res.passed is True
    assert max(res.rel_errors) < 0.3  # some slack for numerics


def test_clapeyron_fails_for_toy_inconsistent():
    adapter = ToyInconsistentAdapter(fluid="CO2")
    Ts = [230.0, 240.0, 260.0]
    res = check_clapeyron(adapter, "CO2", Ts, tol_rel=0.1)
    assert res.supported is True  # toy implements phase split + h
    assert res.passed is False
