from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TariffSchedule:
    hts_code: str
    origin_country: str
    destination_country: str
    base_duty_rate: float
    section_301: float
    section_232: float
    adcvd: float
    effective_from: date
    source: str


@dataclass(frozen=True)
class FTARule:
    fta_name: str
    origin_country: str
    destination_country: str
    hts_prefix: str
    savings_pct: float
    substantial_transformation_required: bool
    min_regional_content_pct: float
    source: str
