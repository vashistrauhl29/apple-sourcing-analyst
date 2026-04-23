from sourcing.ai.anomaly import detect
from sourcing.ai.briefing import PERSONAS, generate
from sourcing.ai.nl_query import query
from sourcing.data.catalog import Catalog
from sourcing.engine.optimizer import (
    OptimizerInputs,
    build_supplier_options,
    solve_allocation,
)
from sourcing.engine.tco import TCOInputs


def test_nl_query_family_filter():
    c = Catalog.load()
    r = query(c, "iphone suppliers")
    assert len(r.dataframe) > 0
    assert (r.dataframe["Family"] == "iPhone").all()


def test_nl_query_country_tariff_filters():
    c = Catalog.load()
    r = query(c, "china parts with tariff > 10%")
    assert "origin=China" in r.echo
    assert (r.dataframe["Tariff %"] > 10).all()


def test_nl_query_top_cheapest():
    c = Catalog.load()
    r = query(c, "top 5 cheapest components")
    assert len(r.dataframe) <= 5
    fobs = list(r.dataframe["FOB"])
    assert fobs == sorted(fobs)


def test_nl_query_single_source():
    c = Catalog.load()
    r = query(c, "single-source parts")
    assert "single-source parts" in r.echo


def test_anomaly_detector_returns_records():
    c = Catalog.load()
    items = detect(c, z_threshold=0.9)
    assert isinstance(items, list)


def test_anomaly_detector_skips_parts_without_bom():
    """Should-cost variance only meaningful for parts with a real BOM rollup."""
    c = Catalog.load()
    items = detect(c, z_threshold=1.5)
    parts_with_bom = {bl.parent_part_id for bl in c.bom}
    for a in items:
        if a.kind == "should-cost-gap":
            assert a.part_id in parts_with_bom


def test_briefings_contain_all_personas():
    c = Catalog.load()
    options = build_supplier_options(c, "P_IPH15P", TCOInputs(volume=10_000_000))
    res = solve_allocation(
        options,
        OptimizerInputs(annual_volume=10_000_000, min_num_suppliers=2, max_country_share=0.7),
    )
    briefs = generate(c, "P_IPH15P", res)
    assert {b.persona for b in briefs} == set(PERSONAS)
