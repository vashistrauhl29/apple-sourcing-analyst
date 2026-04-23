from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Quote:
    supplier_id: str
    part_id: str
    site_id: str
    destination_country: str
    fob_usd: float
    currency: str
    moq: int
    capacity_monthly: int
    lead_time_weeks: float
    nre_usd: float
    tooling_usd: float
    payment_terms_days: int
    valid_until: date
    as_of: date
    source: str


@dataclass(frozen=True)
class YieldProfile:
    supplier_id: str
    part_id: str
    first_pass_yield: float
    dppm: int
    warranty_reserve_usd: float
    as_of: date
    source: str
