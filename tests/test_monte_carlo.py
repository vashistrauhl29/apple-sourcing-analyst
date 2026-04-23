import numpy as np

from sourcing.data.catalog import Catalog
from sourcing.engine.monte_carlo import MonteCarloInputs, run_monte_carlo
from sourcing.engine.tco import TCOInputs


def test_monte_carlo_shape_and_stats():
    c = Catalog.load()
    q = next(x for x in c.quotes_for("P_IPH15P") if x.supplier_id == "S_FOXCONN")
    res = run_monte_carlo(
        c, q, "Ocean", TCOInputs(volume=10_000_000), MonteCarloInputs(trials=5000, seed=7)
    )
    assert res.distribution.shape == (5000,)
    assert res.p5 < res.p50 < res.p95
    assert res.mean > 0


def test_monte_carlo_deterministic_seed():
    c = Catalog.load()
    q = next(x for x in c.quotes_for("P_IPH15P") if x.supplier_id == "S_FOXCONN")
    r1 = run_monte_carlo(
        c, q, "Ocean", TCOInputs(volume=10_000_000), MonteCarloInputs(trials=3000, seed=123)
    )
    r2 = run_monte_carlo(
        c, q, "Ocean", TCOInputs(volume=10_000_000), MonteCarloInputs(trials=3000, seed=123)
    )
    assert np.allclose(r1.distribution, r2.distribution)


def test_tornado_returns_ordered_bars():
    from sourcing.engine.sensitivity import tornado

    c = Catalog.load()
    q = next(x for x in c.quotes_for("P_IPH15P") if x.supplier_id == "S_FOXCONN")
    bars = tornado(c, q, "Ocean", TCOInputs(volume=10_000_000))
    swings = [b.swing for b in bars]
    assert swings == sorted(swings, reverse=True)
