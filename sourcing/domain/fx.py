from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FXRate:
    currency: str
    usd_per_unit: float
    forward_3m: float
    forward_12m: float
    volatility_annual: float
    as_of: date
    source: str
