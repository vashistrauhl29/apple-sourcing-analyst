"""Trade-compliance helpers — FTA qualifier, substantial-transformation heuristic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sourcing.data.catalog import Catalog
from sourcing.domain import FTARule, Quote


@dataclass(frozen=True)
class FTAResult:
    fta_name: Optional[str]
    qualified: bool
    reason: str
    savings_usd_per_unit: float
    savings_pct: float
    regional_content_est_pct: float


def evaluate_fta(catalog: Catalog, quote: Quote) -> FTAResult:
    part = catalog.parts[quote.part_id]
    sup = catalog.suppliers[quote.supplier_id]
    rule = catalog.fta_for(sup.country, quote.destination_country, part.hts_code)
    if rule is None:
        return FTAResult(
            fta_name=None,
            qualified=False,
            reason=f"No FTA rule for {sup.country} → {quote.destination_country} / {part.hts_code}.",
            savings_usd_per_unit=0.0,
            savings_pct=0.0,
            regional_content_est_pct=0.0,
        )
    tariff = catalog.tariff_for(part.hts_code, sup.country, quote.destination_country)
    full_duty = 0.0
    if tariff is not None:
        full_duty = (
            tariff.base_duty_rate
            + tariff.section_301
            + tariff.section_232
            + tariff.adcvd
        ) * quote.fob_usd

    # Regional content heuristic: share of BOM material sourced from same country.
    same_country_value = 0.0
    total_material = 0.0
    for bl in catalog.bom:
        if bl.parent_part_id != part.id:
            continue
        child_quotes = catalog.quotes_for(bl.child_part_id)
        if not child_quotes:
            continue
        cheapest = min(child_quotes, key=lambda q: q.fob_usd)
        val = cheapest.fob_usd * bl.quantity * (1 + bl.scrap_factor)
        total_material += val
        child_sup = catalog.suppliers[cheapest.supplier_id]
        if child_sup.country == sup.country or child_sup.country == quote.destination_country:
            same_country_value += val

    regional_content = (
        same_country_value / total_material if total_material > 0 else 0.0
    )

    if rule.substantial_transformation_required and regional_content < rule.min_regional_content_pct:
        return FTAResult(
            fta_name=rule.fta_name,
            qualified=False,
            reason=(
                f"{rule.fta_name}: regional content {regional_content:.0%} "
                f"< required {rule.min_regional_content_pct:.0%}."
            ),
            savings_usd_per_unit=0.0,
            savings_pct=0.0,
            regional_content_est_pct=regional_content,
        )
    savings = full_duty * rule.savings_pct
    return FTAResult(
        fta_name=rule.fta_name,
        qualified=True,
        reason=f"{rule.fta_name}: qualified (regional content {regional_content:.0%}).",
        savings_usd_per_unit=savings,
        savings_pct=rule.savings_pct,
        regional_content_est_pct=regional_content,
    )
