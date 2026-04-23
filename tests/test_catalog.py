from sourcing.data.catalog import Catalog


def test_catalog_loads():
    c = Catalog.load()
    s = c.summary()
    assert s["parts"] >= 10
    assert s["suppliers"] >= 5
    assert s["quotes"] >= 20


def test_tariff_lookup_hits_china_301():
    c = Catalog.load()
    t = c.tariff_for("8531.20.00", "China", "USA")
    assert t is not None
    assert t.section_301 == 0.25


def test_tariff_lookup_vietnam_no_301():
    c = Catalog.load()
    t = c.tariff_for("8531.20.00", "Vietnam", "USA")
    assert t is not None
    assert t.section_301 == 0.0


def test_usmca_fta_100pct():
    c = Catalog.load()
    f = c.fta_for("Mexico", "USA", "7616.99.51")
    assert f is not None
    assert f.savings_pct == 1.0


def test_all_quotes_reference_valid_ids():
    c = Catalog.load()
    for q in c.quotes:
        assert q.part_id in c.parts
        assert q.supplier_id in c.suppliers
        assert q.site_id in c.sites
