from sourcing.data.catalog import Catalog
from sourcing.engine.should_cost import compute_should_cost


def test_should_cost_iphone_foxconn_reasonable():
    c = Catalog.load()
    r = compute_should_cost(c, "P_IPH15P", "S_FOXCONN")
    assert r.should_cost > 0
    assert r.quoted > 0
    # Material line should dominate on an iPhone
    material = next(ln for ln in r.lines if ln.label.startswith("Material"))
    assert material.amount > r.should_cost * 0.4


def test_should_cost_variance_sign():
    c = Catalog.load()
    r = compute_should_cost(c, "P_IPH15P", "S_FOXCONN")
    assert r.variance == r.quoted - r.should_cost


def test_india_labor_cheaper_than_china():
    c = Catalog.load()
    r_cn = compute_should_cost(c, "P_IPH15P", "S_FOXCONN")
    r_in = compute_should_cost(c, "P_IPH15P", "S_FOXCONN_IN")
    labor_cn = next(ln.amount for ln in r_cn.lines if ln.label == "Direct labor")
    labor_in = next(ln.amount for ln in r_in.lines if ln.label == "Direct labor")
    assert labor_in < labor_cn
