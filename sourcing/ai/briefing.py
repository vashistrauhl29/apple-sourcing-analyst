"""Stakeholder briefing generator — same data, tailored narrative per persona."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from sourcing.data.catalog import Catalog
from sourcing.engine.optimizer import AllocationResult


PERSONAS = ["NPI PM", "Product Design", "Commodity Finance", "Trade Compliance", "Sustainability", "Executive"]


@dataclass(frozen=True)
class Briefing:
    persona: str
    markdown: str


def _top_line(res: AllocationResult) -> str:
    if not res.rows:
        return "**No allocation produced.**"
    top = res.rows[0]
    return (
        f"**Lead supplier:** {top.supplier_name} ({top.country}) at "
        f"{top.share:.0%} share, TCO \\${top.tco_per_unit:.2f}/unit."
    )


def _countries(res: AllocationResult) -> Iterable[str]:
    return sorted({r.country for r in res.rows})


def generate(
    catalog: Catalog,
    part_id: str,
    res: AllocationResult,
) -> List[Briefing]:
    part = catalog.parts[part_id]
    allocation_table = "\n".join(
        f"- {r.supplier_name} ({r.country}) — {r.share:.0%}, \\${r.tco_per_unit:.2f}/unit"
        for r in res.rows
    )
    total_spend = sum(r.spend_usd for r in res.rows)
    total_carbon = sum(r.carbon_g_per_unit * r.units for r in res.rows) / 1_000_000
    countries = _countries(res)

    briefings: List[Briefing] = []

    briefings.append(
        Briefing(
            "NPI PM",
            f"""### NPI briefing — {part.name}
{_top_line(res)}

Critical-path signals:
- Lead suppliers span **{len(countries)} countries**: {", ".join(countries)}.
- Single-country concentration risk: {'YES' if len(countries) == 1 else 'diversified'}.
- Pull-in buffer required for any off-China origin due to 2–3 wk transit delta.

Action: gate EVT/DVT readiness with qualified second source before locking tooling.
""",
        )
    )

    briefings.append(
        Briefing(
            "Product Design",
            f"""### Design briefing — {part.name}
Allocation:
{allocation_table}

Implication for design:
- Any material / spec swap (ECO) re-triggers qualification on every awarded supplier.
- If design targets aluminum-recycled content > 30%, verify supplier renewable-% is ≥ 40% to hit Apple 2030 gap < 60%.
""",
        )
    )

    briefings.append(
        Briefing(
            "Commodity Finance",
            f"""### Finance briefing — {part.name}
- **Total spend (annualised):** \\${total_spend:,.0f}
- **Weighted TCO/unit:** \\${total_spend / max(sum(r.units for r in res.rows), 1):.2f}
- **Objective (MILP):** {res.objective_value:.2f} (mixed cost + risk + carbon)

Binding constraints:
{chr(10).join(f"- {b}" for b in res.binding_constraints) if res.binding_constraints else "- none"}

Variance vs prior award, YoY cost-down delivery, PPV tracking should be verified before lock-in.
""",
        )
    )

    briefings.append(
        Briefing(
            "Trade Compliance",
            f"""### Trade briefing — {part.name} (HTS {part.hts_code})
Origins in the allocation: {", ".join(countries)}.

Per-origin duty exposure follows the loaded tariff table. Where Mexico is in the mix, USMCA must be documented (substantial transformation + ≥ 60 % regional content). Where China is in the mix, Section 301 exposure must be re-tested against the latest USTR list revision.
""",
        )
    )

    briefings.append(
        Briefing(
            "Sustainability",
            f"""### Sustainability briefing — {part.name}
- Annualised carbon (weighted): **{total_carbon:,.0f} tCO2e**.
- Supplier-level renewable-% and recycled-content % drive progress vs Apple 2030 trajectory.
- Carbon shadow price materially re-ranks suppliers; verify that the weight used in the optimizer reflects the corporate trajectory.
""",
        )
    )

    briefings.append(
        Briefing(
            "Executive",
            f"""### Executive one-pager — {part.name}
{_top_line(res)}

- Spend: **\\${total_spend:,.0f}**
- Diversification: **{len(countries)} countries**
- Carbon (annualised): **{total_carbon:,.0f} tCO2e**
- Status: {res.status}

Risks / decisions escalated:
{chr(10).join(f"- {b}" for b in res.binding_constraints[:4]) if res.binding_constraints else "- None material."}
""",
        )
    )
    return briefings
