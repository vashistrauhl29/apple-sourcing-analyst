"""Vectorised Monte Carlo over TCO drivers.

Distributions (lognormal for strictly-positive quantities, normal for signed deltas):
    fob_mult        ~ LogNormal(μ = log(1), σ = fob_vol)
    fx_mult         ~ Normal(0, fx_vol) applied additively to FOB
    freight_mult    ~ LogNormal(μ = log(1), σ = freight_vol)
    yield_delta     ~ Normal(0, yield_vol) clipped to [-0.1, +0.05]
    tariff_adj_pp   ~ Triangular(low, mode, high) additive to total tariff rate
    demand_mult     ~ LogNormal(μ = log(1), σ = demand_vol)  -> triggers expedite premium if capacity < demand
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from sourcing.data.catalog import Catalog
from sourcing.domain import Quote
from sourcing.engine.tco import TCOInputs, compute_tco


@dataclass(frozen=True)
class MonteCarloInputs:
    trials: int = 10_000
    fob_vol: float = 0.03
    fx_vol: float = 0.05
    freight_vol: float = 0.10
    yield_vol: float = 0.01
    tariff_low_pp: float = -0.05
    tariff_mode_pp: float = 0.00
    tariff_high_pp: float = 0.15
    demand_vol: float = 0.12
    expedite_premium_per_unit: float = 35.0
    seed: int = 42


@dataclass(frozen=True)
class MonteCarloResult:
    base_tco: float
    mean: float
    std: float
    p5: float
    p50: float
    p90: float
    p95: float
    distribution: np.ndarray
    tariff_hits_pct: float
    expedite_hits_pct: float


def run_monte_carlo(
    catalog: Catalog,
    quote: Quote,
    mode: str,
    base_inputs: TCOInputs,
    mc: Optional[MonteCarloInputs] = None,
) -> MonteCarloResult:
    mc = mc or MonteCarloInputs()
    rng = np.random.default_rng(mc.seed)

    # Base TCO gives us the deterministic scaffold.
    base = compute_tco(catalog, quote, mode, base_inputs)
    base_tco = base.total

    n = mc.trials
    fob_mult = rng.lognormal(mean=0.0, sigma=mc.fob_vol, size=n)
    fx_add = rng.normal(0.0, mc.fx_vol, size=n)
    freight_mult = rng.lognormal(mean=0.0, sigma=mc.freight_vol, size=n)
    tariff_add = rng.triangular(mc.tariff_low_pp, mc.tariff_mode_pp, mc.tariff_high_pp, size=n)
    demand_mult = rng.lognormal(mean=0.0, sigma=mc.demand_vol, size=n)
    yield_delta = np.clip(rng.normal(0.0, mc.yield_vol, size=n), -0.1, 0.05)

    # Stochastic FOB
    fob_trial = base.fob * fob_mult + base.fob * fx_add
    # Duties ride on stochastic tariff rate
    current_tariff_rate = (
        (base.base_duty + base.section_301 + base.section_232 + base.adcvd - base.fta_savings)
        / max(base.fob, 1e-9)
    )
    duty_rate_trial = np.clip(current_tariff_rate + tariff_add, 0.0, 0.90)
    duties_trial = fob_trial * duty_rate_trial
    # Freight
    freight_trial = base.freight * freight_mult
    # Insurance scales with FOB
    insurance_trial = fob_trial * (base.insurance / max(base.fob, 1e-9))
    # Yield
    fpy_base = base.fob / (base.fob + base.yield_loss) if (base.fob + base.yield_loss) > 0 else 1.0
    fpy_trial = np.clip(fpy_base + yield_delta, 0.5, 0.9999)
    yield_loss_trial = fob_trial / fpy_trial - fob_trial
    # Inventory carry (invariant on base inputs for simplicity)
    inv_trial = np.full(n, base.inventory_carrying)
    # Constant: NRE per unit, warranty, carbon shadow, DPO benefit
    nre_trial = np.full(n, base.nre_per_unit)
    warranty_trial = np.full(n, base.warranty_reserve)
    carbon_trial = np.full(n, base.carbon_shadow)
    dpo_trial = np.full(n, base.dpo_benefit)
    # Demand > capacity triggers expedite premium
    annual_capacity = quote.capacity_monthly * 12.0
    demand_trial = base_inputs.volume * demand_mult
    expedite_hit = demand_trial > annual_capacity
    expedite_cost = np.where(expedite_hit, mc.expedite_premium_per_unit, 0.0)

    tco_trial = (
        fob_trial
        + freight_trial
        + insurance_trial
        + duties_trial
        + inv_trial
        + nre_trial
        + yield_loss_trial
        + warranty_trial
        + carbon_trial
        + expedite_cost
        - dpo_trial
    )

    return MonteCarloResult(
        base_tco=base_tco,
        mean=float(np.mean(tco_trial)),
        std=float(np.std(tco_trial)),
        p5=float(np.percentile(tco_trial, 5)),
        p50=float(np.percentile(tco_trial, 50)),
        p90=float(np.percentile(tco_trial, 90)),
        p95=float(np.percentile(tco_trial, 95)),
        distribution=tco_trial,
        tariff_hits_pct=float(np.mean(tariff_add > 0.05)),
        expedite_hits_pct=float(np.mean(expedite_hit)),
    )
