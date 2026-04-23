"""Carbon rollup + Apple-2030 progress."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sourcing.data.catalog import Catalog
from sourcing.engine.tco import pick_best_mode


APPLE2030_TARGET_GCO2E_PER_IPHONE = 3_500.0
APPLE2030_TARGET_GCO2E_PER_MBA = 14_000.0


@dataclass(frozen=True)
class CarbonLine:
    supplier_name: str
    part_name: str
    scope1: float
    scope2: float
    scope3: float
    transport: float
    total: float
    recycled_pct: float
    renewable_pct: float
    apple2030_gap_pct: float


def part_carbon_lines(catalog: Catalog, part_id: str) -> List[CarbonLine]:
    lines: List[CarbonLine] = []
    for q in catalog.quotes_for(part_id):
        cp = catalog.carbon.get((q.supplier_id, q.part_id))
        if cp is None:
            continue
        sup = catalog.suppliers[q.supplier_id]
        lane = catalog.lane_for(sup.country, q.destination_country, pick_best_mode(catalog, q))
        transport_g = 0.0
        if lane is not None:
            transport_g = catalog.parts[part_id].weight_kg * lane.distance_km * lane.carbon_g_per_kg_km
        total = cp.scope1_gco2e_per_unit + cp.scope2_gco2e_per_unit + cp.scope3_gco2e_per_unit + transport_g
        lines.append(
            CarbonLine(
                supplier_name=sup.name,
                part_name=catalog.parts[part_id].name,
                scope1=cp.scope1_gco2e_per_unit,
                scope2=cp.scope2_gco2e_per_unit,
                scope3=cp.scope3_gco2e_per_unit,
                transport=transport_g,
                total=total,
                recycled_pct=cp.recycled_content_pct,
                renewable_pct=cp.renewable_energy_pct,
                apple2030_gap_pct=cp.apple2030_gap_pct,
            )
        )
    lines.sort(key=lambda x: x.total)
    return lines


def apple2030_target_for(part_id: str) -> float:
    if part_id == "P_IPH15P":
        return APPLE2030_TARGET_GCO2E_PER_IPHONE
    if part_id == "P_MBA_M3":
        return APPLE2030_TARGET_GCO2E_PER_MBA
    return 0.0
