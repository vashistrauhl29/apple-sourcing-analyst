"""Award-Split Optimizer — Mixed Integer Linear Program over supplier allocation.

Objective:
    min  Σ_i share_i * (w_cost*tco_i + w_risk*risk_i + w_carbon*carbon_i)

Constraints:
    Σ share_i = 1
    share_i ∈ [min_share_i, max_share_i] (continuous)
    use_i ∈ {0, 1} ; share_i ≤ max_share_i * use_i
    share_i * annual_volume ≤ 12 * monthly_capacity_i
    Σ_{i in country} share_i ≤ max_country_share
    Σ use_i ≥ min_num_suppliers
    dppm_i > quality_floor ⇒ use_i = 0
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pulp

from sourcing.data.catalog import Catalog
from sourcing.engine.tco import TCOInputs, compute_tco, pick_best_mode


@dataclass(frozen=True)
class SupplierOption:
    supplier_id: str
    supplier_name: str
    country: str
    tco_per_unit: float
    risk_score: float
    carbon_gco2e_per_unit: float
    monthly_capacity: int
    dppm: int
    lead_time_weeks: float


@dataclass(frozen=True)
class OptimizerInputs:
    annual_volume: int
    w_cost: float = 1.0
    w_risk: float = 0.0
    w_carbon: float = 0.0
    min_share_default: float = 0.0
    max_share_default: float = 1.0
    max_country_share: float = 1.0
    min_num_suppliers: int = 1
    quality_floor_dppm: Optional[int] = None
    min_shares: Optional[Dict[str, float]] = None
    max_shares: Optional[Dict[str, float]] = None
    force_include: Optional[List[str]] = None
    force_exclude: Optional[List[str]] = None


@dataclass(frozen=True)
class AllocationRow:
    supplier_id: str
    supplier_name: str
    country: str
    share: float
    units: int
    spend_usd: float
    tco_per_unit: float
    carbon_g_per_unit: float
    risk_score: float


@dataclass(frozen=True)
class AllocationResult:
    status: str
    objective_value: float
    rows: List[AllocationRow]
    binding_constraints: List[str]
    infeasibility_reason: Optional[str] = None


def build_supplier_options(
    catalog: Catalog,
    part_id: str,
    tco_inputs: TCOInputs,
) -> List[SupplierOption]:
    options: List[SupplierOption] = []
    for q in catalog.quotes_for(part_id):
        sup = catalog.suppliers[q.supplier_id]
        mode = pick_best_mode(catalog, q)
        b = compute_tco(catalog, q, mode, tco_inputs)
        cp = catalog.carbon.get((q.supplier_id, q.part_id))
        yp = catalog.yields.get((q.supplier_id, q.part_id))
        carbon_g = 0.0
        if cp is not None:
            carbon_g = (
                cp.scope1_gco2e_per_unit
                + cp.scope2_gco2e_per_unit
                + cp.scope3_gco2e_per_unit
            )
        risk = (
            0.45 * sup.geopolitical_risk
            + 0.35 * (1.0 - min(sup.altman_z / 4.0, 1.0))
            + 0.20 * (q.lead_time_weeks / 12.0)
        )
        options.append(
            SupplierOption(
                supplier_id=q.supplier_id,
                supplier_name=sup.name,
                country=sup.country,
                tco_per_unit=b.total,
                risk_score=risk,
                carbon_gco2e_per_unit=carbon_g,
                monthly_capacity=q.capacity_monthly,
                dppm=yp.dppm if yp else 1000,
                lead_time_weeks=q.lead_time_weeks,
            )
        )
    return options


def _normalize(values: List[float]) -> List[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def solve_allocation(
    options: List[SupplierOption],
    inputs: OptimizerInputs,
) -> AllocationResult:
    if not options:
        return AllocationResult(
            status="No options",
            objective_value=0.0,
            rows=[],
            binding_constraints=[],
            infeasibility_reason="No eligible suppliers.",
        )

    # Pre-filter on quality floor and explicit exclusions.
    filtered: List[SupplierOption] = []
    excluded: List[str] = []
    for o in options:
        if inputs.force_exclude and o.supplier_id in inputs.force_exclude:
            excluded.append(f"{o.supplier_name} (excluded by user)")
            continue
        if inputs.quality_floor_dppm is not None and o.dppm > inputs.quality_floor_dppm:
            excluded.append(
                f"{o.supplier_name} (DPPM {o.dppm} > floor {inputs.quality_floor_dppm})"
            )
            continue
        filtered.append(o)
    if not filtered:
        return AllocationResult(
            status="Infeasible",
            objective_value=0.0,
            rows=[],
            binding_constraints=excluded,
            infeasibility_reason="All suppliers filtered out by quality/force rules.",
        )

    # Normalise risk & carbon so the weighted objective is comparable.
    tco = [o.tco_per_unit for o in filtered]
    risk = _normalize([o.risk_score for o in filtered])
    carbon = _normalize([o.carbon_gco2e_per_unit for o in filtered])

    # Scale: push cost onto $ axis, risk & carbon expressed in cost-equivalent proxies.
    tco_range = max(tco) - min(tco) if len(tco) > 1 else 1.0
    unit_obj = [
        inputs.w_cost * tco[i]
        + inputs.w_risk * risk[i] * (tco_range if tco_range > 0 else 1.0)
        + inputs.w_carbon * carbon[i] * (tco_range if tco_range > 0 else 1.0)
        for i in range(len(filtered))
    ]

    prob = pulp.LpProblem("AwardSplit", pulp.LpMinimize)
    share = {
        o.supplier_id: pulp.LpVariable(f"s_{o.supplier_id}", lowBound=0, upBound=1)
        for o in filtered
    }
    use = {
        o.supplier_id: pulp.LpVariable(f"u_{o.supplier_id}", cat="Binary")
        for o in filtered
    }

    prob += pulp.lpSum(
        share[filtered[i].supplier_id] * unit_obj[i] for i in range(len(filtered))
    )

    prob += pulp.lpSum(share[o.supplier_id] for o in filtered) == 1, "SumShares"

    mins = inputs.min_shares or {}
    maxs = inputs.max_shares or {}
    # Epsilon so "use_i = 1" is distinguishable from share_i = 0.
    eps = 0.01
    for o in filtered:
        lo = max(mins.get(o.supplier_id, inputs.min_share_default), eps)
        hi = maxs.get(o.supplier_id, inputs.max_share_default)
        prob += share[o.supplier_id] >= lo * use[o.supplier_id], f"MinShare_{o.supplier_id}"
        prob += share[o.supplier_id] <= hi * use[o.supplier_id], f"MaxShare_{o.supplier_id}"
        cap_frac = (
            min(1.0, (o.monthly_capacity * 12.0) / max(inputs.annual_volume, 1))
            if inputs.annual_volume > 0
            else 1.0
        )
        prob += share[o.supplier_id] <= cap_frac, f"Capacity_{o.supplier_id}"

    # Country-level concentration.
    countries: Dict[str, list] = {}
    for o in filtered:
        countries.setdefault(o.country, []).append(o.supplier_id)
    for country, sids in countries.items():
        prob += pulp.lpSum(share[s] for s in sids) <= inputs.max_country_share, f"CCap_{country}"

    prob += pulp.lpSum(use[o.supplier_id] for o in filtered) >= inputs.min_num_suppliers, "MinSup"

    if inputs.force_include:
        for sid in inputs.force_include:
            if sid in use:
                prob += use[sid] == 1, f"Force_{sid}"

    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]

    rows: List[AllocationRow] = []
    binding: List[str] = list(excluded)
    if status == "Optimal":
        total_units = inputs.annual_volume
        for o in filtered:
            s = share[o.supplier_id].value() or 0.0
            if s <= 1e-5:
                continue
            u = int(round(s * total_units))
            rows.append(
                AllocationRow(
                    supplier_id=o.supplier_id,
                    supplier_name=o.supplier_name,
                    country=o.country,
                    share=float(s),
                    units=u,
                    spend_usd=u * o.tco_per_unit,
                    tco_per_unit=o.tco_per_unit,
                    carbon_g_per_unit=o.carbon_gco2e_per_unit,
                    risk_score=o.risk_score,
                )
            )
        for c in prob.constraints.values():
            try:
                slack = c.value()
            except Exception:  # pragma: no cover - defensive
                slack = None
            if slack is not None and abs(slack) < 1e-6:
                binding.append(c.name)
        rows.sort(key=lambda r: r.share, reverse=True)

    return AllocationResult(
        status=status,
        objective_value=float(pulp.value(prob.objective) or 0.0),
        rows=rows,
        binding_constraints=binding,
        infeasibility_reason=None if status == "Optimal" else f"Solver status: {status}",
    )
