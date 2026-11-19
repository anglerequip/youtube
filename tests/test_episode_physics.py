"""Physics behind the overnight episodes: the numbers the scripts quote must come from the models."""
from factory.simulation_engine.physics import chain_fountain as cf
from factory.simulation_engine.physics import spaghetti as sp


def test_chain_fountain_balance_and_scaling():
    checks = cf.self_checks()
    assert all(ok for ok, _ in checks.values()), checks
    assert round(cf.steady(1.0)["h1"] * 100) == 14          # "about fourteen centimetres"
    assert 4.5 < cf.steady(2.0)["v"] < 5.0                   # "almost five metres per second"


def test_spaghetti_untwisted_breaks_in_three_or_more():
    r = sp.run(0.0, 0.47, seed=1)
    assert r.n_pieces >= 3 and r.burst_ratio > 1.15


def test_spaghetti_twisted_breaks_in_two():
    r = sp.run(1.0, 0.5, seed=3, t_twist=2.0, t_bend=2.4)
    assert r.n_pieces == 2
