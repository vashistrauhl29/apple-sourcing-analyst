import pytest

from sourcing.data.catalog import Catalog
from sourcing.engine.tco import TCOInputs, compute_tco


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


def _first_quote(catalog, part_id, supplier_id):
    for q in catalog.quotes_for(part_id):
        if q.supplier_id == supplier_id:
            return q
    raise LookupError


def test_tco_china_iphone_ocean_positive(catalog):
    q = _first_quote(catalog, "P_IPH15P", "S_FOXCONN")
    b = compute_tco(catalog, q, "Ocean", TCOInputs(volume=1_000_000))
    assert b.total > q.fob_usd
    assert b.fob == 450.0
    assert b.freight > 0
    assert b.inventory_carrying > 0


def test_tariff_override_short_circuits_table(catalog):
    q = next(
        x
        for x in catalog.quotes_for("P_IPH15P")
        if x.supplier_id == "S_FOXCONN"
    )
    b = compute_tco(catalog, q, "Ocean", TCOInputs(tariff_override_pct=0.25))
    assert b.base_duty == pytest.approx(q.fob_usd * 0.25)
    assert b.section_301 == 0.0


def test_usmca_zeroes_aluminum_chassis(catalog):
    q = next(
        x
        for x in catalog.quotes_for("P_CHAS_MBA")
        if x.supplier_id == "S_FOXCONN_MX"
    )
    b = compute_tco(catalog, q, "Truck")
    assert b.base_duty == 0.0
    assert b.section_301 == 0.0


def test_carbon_shadow_increases_total(catalog):
    q = _first_quote(catalog, "P_IPH15P", "S_FOXCONN")
    base = compute_tco(catalog, q, "Ocean", TCOInputs(carbon_shadow_usd_per_tonne=0))
    shadowed = compute_tco(
        catalog, q, "Ocean", TCOInputs(carbon_shadow_usd_per_tonne=100)
    )
    assert shadowed.total > base.total


def test_nre_amortization_decreases_with_volume(catalog):
    q = next(
        x
        for x in catalog.quotes_for("P_IPH15P")
        if x.supplier_id == "S_FOXCONN_IN"
    )
    assert q.nre_usd > 0
    low_vol = compute_tco(catalog, q, "Ocean", TCOInputs(volume=100_000))
    high_vol = compute_tco(catalog, q, "Ocean", TCOInputs(volume=100_000_000))
    assert low_vol.nre_per_unit > high_vol.nre_per_unit


def test_yield_loss_nonzero_for_known_supplier(catalog):
    q = _first_quote(catalog, "P_IPH15P", "S_WISTRON_IN")
    b = compute_tco(catalog, q, "Ocean")
    assert b.yield_loss > 0
