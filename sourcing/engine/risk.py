"""Supplier risk scoring and portfolio concentration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sourcing.data.catalog import Catalog


@dataclass(frozen=True)
class SupplierRiskCard:
    supplier_id: str
    supplier_name: str
    country: str
    altman_z: float
    financial_risk: str
    geopolitical_risk: float
    ttr_weeks: int
    esg_status: str
    overall_score: float  # higher = riskier


def _financial_band(z: float) -> str:
    if z >= 3.0:
        return "Safe"
    if z >= 1.8:
        return "Grey"
    return "Distress"


def score_supplier(catalog: Catalog, supplier_id: str) -> SupplierRiskCard:
    sup = catalog.suppliers[supplier_id]
    sites = [s for s in catalog.sites.values() if s.supplier_id == supplier_id]
    ttr = max((s.time_to_recover_weeks for s in sites), default=8)
    # Weighted 0-1 overall score: higher = riskier.
    fin = max(0.0, min(1.0, (3.5 - sup.altman_z) / 3.0))
    geo = max(0.0, min(1.0, sup.geopolitical_risk))
    recovery = max(0.0, min(1.0, ttr / 14.0))
    esg_penalty = 0.0 if sup.esg_audit_status == "Pass" else 0.25
    overall = 0.4 * fin + 0.35 * geo + 0.15 * recovery + 0.10 * esg_penalty
    return SupplierRiskCard(
        supplier_id=sup.id,
        supplier_name=sup.name,
        country=sup.country,
        altman_z=sup.altman_z,
        financial_risk=_financial_band(sup.altman_z),
        geopolitical_risk=sup.geopolitical_risk,
        ttr_weeks=ttr,
        esg_status=sup.esg_audit_status,
        overall_score=overall,
    )


def portfolio_concentration(catalog: Catalog, part_id: str, shares: Dict[str, float]) -> Dict[str, float]:
    """Group a share-dict by country."""
    by_country: Dict[str, float] = {}
    for sid, share in shares.items():
        sup = catalog.suppliers.get(sid)
        if sup is None:
            continue
        by_country[sup.country] = by_country.get(sup.country, 0.0) + share
    return by_country
