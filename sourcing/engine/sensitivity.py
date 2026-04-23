"""Tornado sensitivity — swing each input between low/high, re-compute TCO, rank."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from sourcing.data.catalog import Catalog
from sourcing.domain import Quote
from sourcing.engine.tco import TCOInputs, compute_tco


@dataclass(frozen=True)
class TornadoBar:
    driver: str
    low: float
    high: float
    swing: float


def tornado(
    catalog: Catalog,
    quote: Quote,
    mode: str,
    base: TCOInputs,
    fob_low_pct: float = -0.08,
    fob_high_pct: float = 0.08,
) -> List[TornadoBar]:
    base_tco = compute_tco(catalog, quote, mode, base).total

    def perturb(input_override: TCOInputs, fob_mult: float = 1.0) -> float:
        # Swap fob directly by copying the quote with mutated FOB.
        q = quote
        if fob_mult != 1.0:
            from dataclasses import replace

            q = replace(quote, fob_usd=quote.fob_usd * fob_mult)
        return compute_tco(catalog, q, mode, input_override).total

    bars: List[TornadoBar] = []

    # 1. Cost of capital
    lo = perturb(TCOInputs(**{**_to_dict(base), "annual_interest_rate": max(0.0, base.annual_interest_rate - 0.05)}))
    hi = perturb(TCOInputs(**{**_to_dict(base), "annual_interest_rate": base.annual_interest_rate + 0.05}))
    bars.append(TornadoBar("Cost of capital ±5pp", lo, hi, abs(hi - lo)))

    # 2. Tariff override ±10 pp
    if base.tariff_override_pct is not None:
        tp = base.tariff_override_pct
    else:
        tp = 0.0
    lo = perturb(TCOInputs(**{**_to_dict(base), "tariff_override_pct": max(0.0, tp - 0.10)}))
    hi = perturb(TCOInputs(**{**_to_dict(base), "tariff_override_pct": tp + 0.10}))
    bars.append(TornadoBar("Tariff ±10 pp", lo, hi, abs(hi - lo)))

    # 3. FOB ±8%
    lo = perturb(base, fob_mult=1.0 + fob_low_pct)
    hi = perturb(base, fob_mult=1.0 + fob_high_pct)
    bars.append(TornadoBar("FOB price ±8%", lo, hi, abs(hi - lo)))

    # 4. FX stress ±5%
    lo = perturb(TCOInputs(**{**_to_dict(base), "fx_stress_pct": base.fx_stress_pct - 0.05}))
    hi = perturb(TCOInputs(**{**_to_dict(base), "fx_stress_pct": base.fx_stress_pct + 0.05}))
    bars.append(TornadoBar("FX vs USD ±5%", lo, hi, abs(hi - lo)))

    # 5. Carbon shadow price ±50
    lo = perturb(TCOInputs(**{**_to_dict(base), "carbon_shadow_usd_per_tonne": max(0.0, base.carbon_shadow_usd_per_tonne - 50)}))
    hi = perturb(TCOInputs(**{**_to_dict(base), "carbon_shadow_usd_per_tonne": base.carbon_shadow_usd_per_tonne + 50}))
    bars.append(TornadoBar("Carbon shadow ±$50/tCO2e", lo, hi, abs(hi - lo)))

    # 6. Volume ±50% (affects NRE amort)
    vol_lo = max(1, int(base.volume * 0.5))
    vol_hi = int(base.volume * 1.5)
    lo = perturb(TCOInputs(**{**_to_dict(base), "volume": vol_lo}))
    hi = perturb(TCOInputs(**{**_to_dict(base), "volume": vol_hi}))
    bars.append(TornadoBar("Volume ±50% (NRE amort)", lo, hi, abs(hi - lo)))

    bars.sort(key=lambda b: b.swing, reverse=True)
    return bars


def _to_dict(x: TCOInputs) -> Dict:
    return {
        "annual_interest_rate": x.annual_interest_rate,
        "volume": x.volume,
        "carbon_shadow_usd_per_tonne": x.carbon_shadow_usd_per_tonne,
        "include_nre": x.include_nre,
        "include_carbon": x.include_carbon,
        "include_fta": x.include_fta,
        "tariff_override_pct": x.tariff_override_pct,
        "fx_stress_pct": x.fx_stress_pct,
    }
