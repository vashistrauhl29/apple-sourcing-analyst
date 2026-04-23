from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarbonProfile:
    supplier_id: str
    part_id: str
    scope1_gco2e_per_unit: float
    scope2_gco2e_per_unit: float
    scope3_gco2e_per_unit: float
    recycled_content_pct: float
    renewable_energy_pct: float
    apple2030_gap_pct: float
    as_of: str
    source: str
