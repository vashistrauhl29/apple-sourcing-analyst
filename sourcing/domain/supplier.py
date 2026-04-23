from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    country: str
    tier: int
    altman_z: float
    esg_audit_status: str
    renewable_pct: float
    geopolitical_risk: float
    years_of_relationship: int


@dataclass(frozen=True)
class SupplierSite:
    id: str
    supplier_id: str
    city: str
    country: str
    monthly_capacity: int
    certifications: str
    time_to_recover_weeks: int
