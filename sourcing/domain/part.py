from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    hts_code: str
    category: str
    weight_kg: float
    unit_of_measure: str = "each"
    description: str = ""


@dataclass(frozen=True)
class BOMLine:
    parent_part_id: str
    child_part_id: str
    quantity: float
    scrap_factor: float = 0.0
