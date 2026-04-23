"""NPI backward planner — from launch date → latest-start for every gate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from sourcing.data.catalog import Catalog
from sourcing.domain import NPIGate


HEALTH_GREEN = "GREEN"
HEALTH_AMBER = "AMBER"
HEALTH_RED = "RED"


@dataclass(frozen=True)
class PlannedGate:
    name: str
    owner: str
    latest_start: date
    buffer_weeks: int
    health: str
    description: str


def _status(latest_start: date, today: date) -> str:
    days_out = (latest_start - today).days
    if days_out < 0:
        return HEALTH_RED
    if days_out < 21:
        return HEALTH_AMBER
    return HEALTH_GREEN


def plan_program(
    catalog: Catalog, program_id: str, today: date | None = None
) -> List[PlannedGate]:
    prog = catalog.npi_programs[program_id]
    today = today or date.today()
    rows: List[PlannedGate] = []
    for g in [gt for gt in catalog.npi_gates if gt.program_id == program_id]:
        latest = prog.launch_date - timedelta(weeks=g.default_offset_weeks_before_launch + g.buffer_weeks)
        rows.append(
            PlannedGate(
                name=g.gate_name,
                owner=g.owner_role,
                latest_start=latest,
                buffer_weeks=g.buffer_weeks,
                health=_status(latest, today),
                description=g.description,
            )
        )
    rows.sort(key=lambda r: r.latest_start)
    return rows


def critical_path_slack(
    gates: List[PlannedGate], today: date | None = None
) -> int:
    """Days between today and the earliest latest-start (negative = past due)."""
    today = today or date.today()
    if not gates:
        return 0
    earliest = min(g.latest_start for g in gates)
    return (earliest - today).days
