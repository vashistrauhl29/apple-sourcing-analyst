import pytest

from sourcing.data.catalog import Catalog
from sourcing.engine.optimizer import (
    OptimizerInputs,
    build_supplier_options,
    solve_allocation,
)
from sourcing.engine.tco import TCOInputs


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


def test_single_supplier_all_share(catalog):
    options = build_supplier_options(catalog, "P_IPH15P", TCOInputs(volume=1_000_000))
    options = options[:1]
    res = solve_allocation(
        options, OptimizerInputs(annual_volume=1_000_000, min_num_suppliers=1)
    )
    assert res.status == "Optimal"
    assert len(res.rows) == 1
    assert res.rows[0].share == pytest.approx(1.0, abs=1e-4)


def test_shares_sum_to_one(catalog):
    options = build_supplier_options(catalog, "P_IPH15P", TCOInputs(volume=10_000_000))
    res = solve_allocation(
        options,
        OptimizerInputs(annual_volume=10_000_000, min_num_suppliers=2, max_country_share=0.7),
    )
    assert res.status == "Optimal"
    total = sum(r.share for r in res.rows)
    assert total == pytest.approx(1.0, abs=1e-4)


def test_country_concentration_honored(catalog):
    options = build_supplier_options(catalog, "P_IPH15P", TCOInputs(volume=10_000_000))
    res = solve_allocation(
        options, OptimizerInputs(annual_volume=10_000_000, max_country_share=0.5)
    )
    assert res.status == "Optimal"
    # Group by country
    by_country: dict[str, float] = {}
    for r in res.rows:
        by_country[r.country] = by_country.get(r.country, 0.0) + r.share
    assert max(by_country.values()) <= 0.5 + 1e-4


def test_quality_floor_excludes_high_dppm(catalog):
    options = build_supplier_options(catalog, "P_IPH15P", TCOInputs(volume=10_000_000))
    # Use a tight floor that must exclude S_WISTRON_IN (DPPM 940) or S_FOXCONN_IN (780)
    res = solve_allocation(
        options,
        OptimizerInputs(annual_volume=10_000_000, quality_floor_dppm=500, min_num_suppliers=1),
    )
    picked = {r.supplier_id for r in res.rows}
    assert "S_WISTRON_IN" not in picked
    assert "S_FOXCONN_IN" not in picked


def test_min_suppliers_respected(catalog):
    options = build_supplier_options(catalog, "P_IPH15P", TCOInputs(volume=10_000_000))
    res = solve_allocation(
        options, OptimizerInputs(annual_volume=10_000_000, min_num_suppliers=3)
    )
    assert res.status == "Optimal"
    assert len(res.rows) >= 3
