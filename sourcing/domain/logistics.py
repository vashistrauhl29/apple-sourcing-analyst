from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogisticsLane:
    origin_country: str
    destination_country: str
    mode: str
    transit_days: int
    usd_per_kg: float
    insurance_pct: float
    carbon_g_per_kg_km: float
    distance_km: float
    as_of: str
    source: str
