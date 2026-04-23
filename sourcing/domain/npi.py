from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NPIGate:
    program_id: str
    gate_name: str
    default_offset_weeks_before_launch: int
    owner_role: str
    buffer_weeks: int
    description: str


@dataclass(frozen=True)
class NPIProgram:
    id: str
    product_name: str
    launch_date: date
    target_volume_y1: int
    ramp_start: date
    mp_start: date
    description: str
