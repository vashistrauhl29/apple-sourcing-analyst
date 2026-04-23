"""Pre-loaded what-if scenarios."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TariffShock:
    name: str
    description: str
    china_301_delta: float = 0.0
    mexico_duty_override: float = 0.0
    vietnam_duty_override: float = 0.0
    india_duty_override: float = 0.0
    applies_to_hts_prefix: str = "*"


@dataclass(frozen=True)
class DemandShock:
    name: str
    description: str
    volume_mult: float


TARIFF_SHOCKS: List[TariffShock] = [
    TariffShock(
        name="Baseline (current law)",
        description="No change. Tariff table as loaded.",
    ),
    TariffShock(
        name="Section 301 +25 pp on China",
        description="Hypothetical: China-origin 301 rate rises by 25 percentage points.",
        china_301_delta=0.25,
    ),
    TariffShock(
        name="Mexico 25% universal",
        description="USMCA partial suspension; Mexico-origin 25% across the board.",
        mexico_duty_override=0.25,
    ),
    TariffShock(
        name="Vietnam 10% reciprocal",
        description="Hypothetical reciprocal tariff on Vietnam-origin goods.",
        vietnam_duty_override=0.10,
    ),
    TariffShock(
        name="India trade-deal zero",
        description="US-India trade deal zeroes all India duty lines.",
        india_duty_override=0.0,
    ),
    TariffShock(
        name="China 301 repeal",
        description="301 fully removed; base duty only.",
        china_301_delta=-1.0,
    ),
]

DEMAND_SHOCKS: List[DemandShock] = [
    DemandShock("Plan", "At-plan volume.", 1.00),
    DemandShock("Demand +15%", "Holiday pull-in / viral hit.", 1.15),
    DemandShock("Demand +30%", "Supercycle.", 1.30),
    DemandShock("Demand -10%", "Macro drag.", 0.90),
    DemandShock("Demand -25%", "Recession / product miss.", 0.75),
]
