"""Total Cost of Ownership engine.

Replaces the ad-hoc country switch in the legacy app.py. Every cost line is
explicit, attributable, and unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional

from sourcing.data.catalog import Catalog
from sourcing.domain import (
    CarbonProfile,
    FTARule,
    FXRate,
    LogisticsLane,
    Part,
    Quote,
    TariffSchedule,
    YieldProfile,
)


@dataclass(frozen=True)
class TCOInputs:
    annual_interest_rate: float = 0.12
    volume: int = 1_000_000
    carbon_shadow_usd_per_tonne: float = 0.0
    include_nre: bool = True
    include_carbon: bool = True
    include_fta: bool = True
    tariff_override_pct: Optional[float] = None
    fx_stress_pct: float = 0.0


@dataclass(frozen=True)
class TCOBreakdown:
    fob: float
    freight: float
    insurance: float
    base_duty: float
    section_301: float
    section_232: float
    adcvd: float
    fta_savings: float
    inventory_carrying: float
    nre_per_unit: float
    yield_loss: float
    warranty_reserve: float
    carbon_shadow: float
    fx_adjustment: float
    dpo_benefit: float
    total: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def positive_lines(self) -> Dict[str, float]:
        return {
            "FOB": self.fob,
            "Freight": self.freight,
            "Insurance": self.insurance,
            "Base Duty": self.base_duty,
            "Section 301": self.section_301,
            "Section 232": self.section_232,
            "AD/CVD": self.adcvd,
            "Inventory Carry": self.inventory_carrying,
            "NRE Amort.": self.nre_per_unit,
            "Yield Loss": self.yield_loss,
            "Warranty Reserve": self.warranty_reserve,
            "Carbon Shadow": self.carbon_shadow,
            "FX Adjustment": self.fx_adjustment,
        }


def _freight_and_insurance(
    quote: Quote, part: Part, lane: LogisticsLane
) -> tuple[float, float]:
    freight = part.weight_kg * lane.usd_per_kg
    insurance = quote.fob_usd * lane.insurance_pct
    return freight, insurance


def _duty_lines(
    quote: Quote,
    part: Part,
    tariff: Optional[TariffSchedule],
    override_pct: Optional[float],
) -> tuple[float, float, float, float]:
    if override_pct is not None:
        total_override = quote.fob_usd * override_pct
        return total_override, 0.0, 0.0, 0.0
    if tariff is None:
        return 0.0, 0.0, 0.0, 0.0
    base = quote.fob_usd * tariff.base_duty_rate
    s301 = quote.fob_usd * tariff.section_301
    s232 = quote.fob_usd * tariff.section_232
    adcvd = quote.fob_usd * tariff.adcvd
    return base, s301, s232, adcvd


def _fta_savings(
    base: float,
    s301: float,
    s232: float,
    adcvd: float,
    fta: Optional[FTARule],
    include_fta: bool,
) -> float:
    if not include_fta or fta is None:
        return 0.0
    total_duty = base + s301 + s232 + adcvd
    return total_duty * fta.savings_pct


def _inventory_carrying(fob: float, rate_annual: float, lead_time_weeks: float) -> float:
    return fob * (rate_annual / 52.0) * lead_time_weeks


def _nre_amortized(quote: Quote, volume: int, include_nre: bool) -> float:
    if not include_nre or volume <= 0:
        return 0.0
    total = quote.nre_usd + quote.tooling_usd
    return total / float(volume)


def _yield_loss(fob: float, yp: Optional[YieldProfile]) -> tuple[float, float]:
    if yp is None:
        return 0.0, 0.0
    fpy = max(min(yp.first_pass_yield, 0.9999), 0.0001)
    cost_per_good = fob / fpy
    yield_loss = cost_per_good - fob
    return yield_loss, yp.warranty_reserve_usd


def _carbon_shadow(
    carbon: Optional[CarbonProfile],
    lane: LogisticsLane,
    part_weight_kg: float,
    shadow_usd_per_tonne: float,
    include_carbon: bool,
) -> float:
    if not include_carbon or shadow_usd_per_tonne <= 0:
        return 0.0
    mfg_g = 0.0
    if carbon is not None:
        mfg_g = (
            carbon.scope1_gco2e_per_unit
            + carbon.scope2_gco2e_per_unit
            + carbon.scope3_gco2e_per_unit
        )
    transport_g = part_weight_kg * lane.distance_km * lane.carbon_g_per_kg_km
    tonnes = (mfg_g + transport_g) / 1_000_000.0
    return tonnes * shadow_usd_per_tonne


def _fx_adjustment(
    fob: float, fx: Optional[FXRate], stress_pct: float, currency: str
) -> float:
    if stress_pct == 0.0 or fx is None or currency == "USD":
        return 0.0
    return fob * stress_pct


def _dpo_benefit(fob: float, payment_terms_days: int, rate_annual: float) -> float:
    return fob * (rate_annual / 365.0) * payment_terms_days


_MODE_PREFERENCE = ("Ocean", "Truck", "Air")


def pick_best_mode(catalog: Catalog, quote: Quote) -> str:
    """Return the cheapest / most-sensible lane mode available for a quote.

    Preference order: Ocean (long-haul) → Truck (same-country / NAFTA) → Air (fallback).
    Raises ValueError only if no lane exists at all between the countries.
    """
    origin_country = catalog.suppliers[quote.supplier_id].country
    dest = quote.destination_country
    # Domestic (same country) skips Ocean — prefer Truck.
    if origin_country == dest:
        order = ("Truck", "Ocean", "Air")
    else:
        order = _MODE_PREFERENCE
    for mode in order:
        if catalog.lane_for(origin_country, dest, mode) is not None:
            return mode
    raise ValueError(
        f"No lane of any mode found: {origin_country} → {dest}. "
        f"Add a row to sourcing/data/lanes.csv."
    )


def compute_tco(
    catalog: Catalog,
    quote: Quote,
    mode: str,
    inputs: Optional[TCOInputs] = None,
) -> TCOBreakdown:
    """Compute landed TCO for a single quote + lane-mode combination."""
    inputs = inputs or TCOInputs()
    part = catalog.parts[quote.part_id]
    supplier = catalog.suppliers[quote.supplier_id]
    lane = catalog.lane_for(supplier.country, quote.destination_country, mode)
    if lane is None:
        raise ValueError(
            f"No lane found: {supplier.country} -> {quote.destination_country} ({mode})"
        )
    tariff = catalog.tariff_for(part.hts_code, supplier.country, quote.destination_country)
    fta = catalog.fta_for(supplier.country, quote.destination_country, part.hts_code)
    yp = catalog.yields.get((quote.supplier_id, quote.part_id))
    cp = catalog.carbon.get((quote.supplier_id, quote.part_id))
    fx = catalog.fx.get(quote.currency)

    freight, insurance = _freight_and_insurance(quote, part, lane)
    base, s301, s232, adcvd = _duty_lines(quote, part, tariff, inputs.tariff_override_pct)
    fta_savings = _fta_savings(base, s301, s232, adcvd, fta, inputs.include_fta)
    inv = _inventory_carrying(
        quote.fob_usd, inputs.annual_interest_rate, quote.lead_time_weeks
    )
    nre = _nre_amortized(quote, inputs.volume, inputs.include_nre)
    yl, warranty = _yield_loss(quote.fob_usd, yp)
    carbon_shadow = _carbon_shadow(
        cp, lane, part.weight_kg, inputs.carbon_shadow_usd_per_tonne, inputs.include_carbon
    )
    fx_adj = _fx_adjustment(quote.fob_usd, fx, inputs.fx_stress_pct, quote.currency)
    dpo = _dpo_benefit(quote.fob_usd, quote.payment_terms_days, inputs.annual_interest_rate)

    total = (
        quote.fob_usd
        + freight
        + insurance
        + base
        + s301
        + s232
        + adcvd
        - fta_savings
        + inv
        + nre
        + yl
        + warranty
        + carbon_shadow
        + fx_adj
        - dpo
    )
    return TCOBreakdown(
        fob=quote.fob_usd,
        freight=freight,
        insurance=insurance,
        base_duty=base,
        section_301=s301,
        section_232=s232,
        adcvd=adcvd,
        fta_savings=fta_savings,
        inventory_carrying=inv,
        nre_per_unit=nre,
        yield_loss=yl,
        warranty_reserve=warranty,
        carbon_shadow=carbon_shadow,
        fx_adjustment=fx_adj,
        dpo_benefit=dpo,
        total=total,
    )
