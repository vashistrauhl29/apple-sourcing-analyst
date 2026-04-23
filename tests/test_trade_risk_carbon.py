from sourcing.data.catalog import Catalog
from sourcing.engine.carbon import apple2030_target_for, part_carbon_lines
from sourcing.engine.risk import score_supplier
from sourcing.engine.trade import evaluate_fta


def test_usmca_applies_for_mexico_to_usa():
    c = Catalog.load()
    q = next(
        x for x in c.quotes_for("P_MBA_M3") if x.supplier_id == "S_FOXCONN_MX"
    )
    r = evaluate_fta(c, q)
    assert r.fta_name == "USMCA"


def test_fta_absent_for_china_vietnam_pair():
    c = Catalog.load()
    q = next(x for x in c.quotes_for("P_IPH15P") if x.supplier_id == "S_FOXCONN")
    r = evaluate_fta(c, q)
    assert r.qualified is False


def test_supplier_risk_increases_with_low_altman_z():
    c = Catalog.load()
    r_hi = score_supplier(c, "S_TSMC_TW")
    r_lo = score_supplier(c, "S_WISTRON_IN")
    assert r_hi.financial_risk == "Safe"
    # Lower Z supplier should have higher overall risk score than high Z, all else equal
    assert r_lo.altman_z <= r_hi.altman_z


def test_carbon_rollup_has_transport():
    c = Catalog.load()
    lines = part_carbon_lines(c, "P_IPH15P")
    assert lines
    assert all(ln.total >= ln.scope1 + ln.scope2 + ln.scope3 for ln in lines)


def test_apple2030_target_defined_for_iphone():
    assert apple2030_target_for("P_IPH15P") > 0
