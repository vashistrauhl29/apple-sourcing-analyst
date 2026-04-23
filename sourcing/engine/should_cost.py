"""Should-cost teardown — bottoms-up build vs the quoted price.

Model:
    material_cost   = Σ (child_qty * child_cost * (1 + scrap))
    labor_cost      = direct_hours * regional_wage * overhead_multiplier
    overhead        = material_cost * (overhead_material_multiplier - 1)
    sga             = (material + labor + overhead) * sga_margin_pct
    target_margin   = (material + labor + overhead + sga) * target_margin_pct
    should_cost     = material + labor + overhead + sga + target_margin
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sourcing.data.catalog import Catalog


@dataclass(frozen=True)
class ShouldCostLine:
    label: str
    amount: float
    note: str = ""


@dataclass(frozen=True)
class ShouldCostResult:
    part_id: str
    supplier_id: str
    lines: List[ShouldCostLine]
    should_cost: float
    quoted: float
    variance: float
    variance_pct: float

    def waterfall(self) -> Dict[str, float]:
        return {ln.label: ln.amount for ln in self.lines}


def _child_material_cost(
    catalog: Catalog, parent_part_id: str, preferred_suppliers: Optional[Dict[str, str]] = None
) -> float:
    preferred = preferred_suppliers or {}
    material = 0.0
    for line in catalog.bom:
        if line.parent_part_id != parent_part_id:
            continue
        child_quotes = catalog.quotes_for(line.child_part_id)
        if not child_quotes:
            continue
        preferred_id = preferred.get(line.child_part_id)
        chosen = None
        if preferred_id:
            chosen = next(
                (q for q in child_quotes if q.supplier_id == preferred_id), None
            )
        if chosen is None:
            chosen = min(child_quotes, key=lambda q: q.fob_usd)
        material += chosen.fob_usd * line.quantity * (1.0 + line.scrap_factor)
    return material


def compute_should_cost(
    catalog: Catalog,
    part_id: str,
    supplier_id: str,
    preferred_children: Optional[Dict[str, str]] = None,
) -> ShouldCostResult:
    sup = catalog.suppliers[supplier_id]
    labor_spec = catalog.labor.get(part_id)
    if labor_spec is None:
        raise ValueError(f"No labor spec for {part_id}")
    wage = catalog.wages[sup.country]

    material = _child_material_cost(catalog, part_id, preferred_children)

    labor = labor_spec.direct_labor_hours * wage.usd_per_hour * wage.overhead_multiplier
    overhead = material * (labor_spec.overhead_material_multiplier - 1.0)
    subtotal = material + labor + overhead
    sga = subtotal * labor_spec.sga_margin_pct
    pre_margin = subtotal + sga
    margin = pre_margin * labor_spec.target_margin_pct
    should = pre_margin + margin

    quote = next(
        (q for q in catalog.quotes_for(part_id) if q.supplier_id == supplier_id),
        None,
    )
    quoted = quote.fob_usd if quote else 0.0

    lines = [
        ShouldCostLine("Material (BOM rollup)", material, "Sum of cheapest child quotes × qty × (1+scrap)"),
        ShouldCostLine(
            "Direct labor",
            labor,
            f"{labor_spec.direct_labor_hours:.2f} h × ${wage.usd_per_hour:.2f} × {wage.overhead_multiplier:.1f} ({sup.country})",
        ),
        ShouldCostLine("Overhead (non-labor)", overhead, f"Material × ({labor_spec.overhead_material_multiplier - 1:.2f})"),
        ShouldCostLine("SG&A", sga, f"{labor_spec.sga_margin_pct:.0%} of subtotal"),
        ShouldCostLine("Target margin", margin, f"{labor_spec.target_margin_pct:.0%} target"),
    ]
    variance = quoted - should
    variance_pct = variance / should if should > 0 else 0.0
    return ShouldCostResult(
        part_id=part_id,
        supplier_id=supplier_id,
        lines=lines,
        should_cost=should,
        quoted=quoted,
        variance=variance,
        variance_pct=variance_pct,
    )
