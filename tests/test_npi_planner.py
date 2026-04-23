from datetime import date, timedelta

from sourcing.data.catalog import Catalog
from sourcing.engine.npi_planner import critical_path_slack, plan_program


def test_gates_ordered_by_latest_start():
    c = Catalog.load()
    gates = plan_program(c, "NPI_IPH16", today=date(2026, 1, 1))
    starts = [g.latest_start for g in gates]
    assert starts == sorted(starts)


def test_launch_date_used_in_offset():
    c = Catalog.load()
    gates = plan_program(c, "NPI_IPH16", today=date(2026, 1, 1))
    prog = c.npi_programs["NPI_IPH16"]
    ltb = next(g for g in gates if g.name == "LTB Raw Material")
    # offset 52 + buffer 3 = 55 weeks before launch
    expected = prog.launch_date - timedelta(weeks=55)
    assert ltb.latest_start == expected


def test_health_flags_past_due_gate():
    c = Catalog.load()
    # Today == right before launch — everything should be RED/past due
    gates = plan_program(c, "NPI_IPH16", today=date(2026, 9, 15))
    assert any(g.health == "RED" for g in gates)


def test_critical_path_slack_sign():
    c = Catalog.load()
    gates = plan_program(c, "NPI_IPH16", today=date(2025, 1, 1))
    slack = critical_path_slack(gates, today=date(2025, 1, 1))
    assert slack > 0
