"""Wave 1 — Should-Cost Teardown."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.should_cost import compute_should_cost
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Should-Cost", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Should-Cost Teardown — is this quote fair?")
st.markdown(
    "_Builds the supplier's price from the ground up — Material + Labor + Overhead + SG&A + Target Margin — "
    "and compares it to what they quoted. Positive variance = negotiation headroom. Use before any QBR or "
    "cost-down review._"
)

with st.expander("What each line is built from"):
    st.markdown(
        "- **Material (BOM rollup)** — Sum of cheapest child-part quotes × quantity × (1 + scrap %). "
        "Pulled live from `sourcing/data/bom.csv` and `quotes.csv`.\n"
        "- **Direct labor** — Direct labor hours × country wage × overhead multiplier. Wages from "
        "BCG 2025 manufacturing wage study / BLS.\n"
        "- **Overhead (non-labor)** — Plant overhead as a multiplier on material cost.\n"
        "- **SG&A** — Selling, General & Administrative, typically 6–10% of cost base.\n"
        "- **Target margin** — Supplier's expected operating margin (8–15% for contract manufacturing, "
        "higher for silicon)."
    )

assemblies = [p for p in c.parts.values() if p.category != "Component"]
part_id = st.selectbox(
    "Assembly / Finished Good",
    options=[p.id for p in assemblies],
    format_func=lambda p: f"{c.parts[p].name} ({p})",
    help="Should-cost only meaningful for parts with a Bill of Materials.",
)

quotes = c.quotes_for(part_id)
if not quotes:
    st.warning("No quotes for this part.")
    st.stop()
supplier_id = st.selectbox(
    "Supplier whose quote you want to challenge",
    options=[q.supplier_id for q in quotes],
    format_func=lambda s: f"{c.suppliers[s].name} [{c.suppliers[s].country}]",
)

result = compute_should_cost(c, part_id, supplier_id)

k1, k2, k3 = st.columns(3)
k1.metric("Quoted (supplier ask)", usd(result.quoted))
k2.metric("Should-cost (our build-up)", usd(result.should_cost))
k3.metric(
    "Variance (quote minus should-cost)",
    usd(result.variance),
    delta=f"{result.variance_pct:+.1%}",
    delta_color="inverse",
)

st.subheader("Waterfall — how we got to should-cost")
labels = [ln.label for ln in result.lines] + ["Should-cost", "Quote"]
values = [ln.amount for ln in result.lines] + [result.should_cost, result.quoted]
measures = ["relative"] * len(result.lines) + ["total", "total"]

fig = go.Figure(
    go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        text=[f"${v:,.2f}" for v in values],
        connector={"line": {"color": "#888"}},
    )
)
fig.update_layout(height=480, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Line detail")
for ln in result.lines:
    with st.container(border=True):
        c1, c2 = st.columns([1, 3])
        c1.markdown(f"**{ln.label}**: {usd(ln.amount)}")
        c2.caption(ln.note)

# --- Negotiation Talking Points ---
st.subheader("Negotiation talking points — what to press the vendor on")
st.caption(
    "Auto-generated from this teardown and public benchmarks. Use as your QBR cheat-sheet; "
    "validate each with the commodity team before the meeting."
)

material = next((ln for ln in result.lines if ln.label.startswith("Material")), None)
labor = next((ln for ln in result.lines if ln.label == "Direct labor"), None)
overhead = next((ln for ln in result.lines if ln.label.startswith("Overhead")), None)
sga = next((ln for ln in result.lines if ln.label.startswith("SG&A")), None)
margin = next((ln for ln in result.lines if ln.label == "Target margin"), None)

part = c.parts[part_id]
supplier = c.suppliers[supplier_id]
labor_spec = c.labor[part_id]
wage = c.wages[supplier.country]

talking_points: list[str] = []

if result.variance > 0:
    talking_points.append(
        f"**Open with the headline:** quote is {usd(result.variance)}/unit "
        f"({result.variance_pct:+.1%}) over our bottoms-up build. Ask them to justify the gap line-by-line."
    )
else:
    talking_points.append(
        f"**They're quoting at or below build cost** ({usd(abs(result.variance))}, {result.variance_pct:+.1%}). "
        "Validate they're not absorbing a loss-leader to lock-in — request an updated quote in 6 months."
    )

if material:
    talking_points.append(
        f"**Material ({usd(material.amount)})** — cross-check against LME (metals) / spot commodity benchmarks. "
        "Ask supplier to share their sub-tier quote stack; if they refuse, push for open-book on material only. "
        "Raw-material cost drops should flow through within 60–90 days under most MFC terms."
    )

if labor:
    benchmark_wage = wage.usd_per_hour
    talking_points.append(
        f"**Labor ({usd(labor.amount)}; {labor_spec.direct_labor_hours:.2f} h × {usd(benchmark_wage)}/h × "
        f"{wage.overhead_multiplier:.1f} overhead multiplier in {supplier.country})** — validate hours against "
        "IE (industrial engineering) time study. If the supplier has automated steps, hours should come down "
        "YoY — demand a learning curve of 5–10% / year."
    )

if overhead:
    mult = labor_spec.overhead_material_multiplier - 1.0
    if mult > 0.40:
        talking_points.append(
            f"**Overhead multiplier at +{mult:.0%} of material is high** — industry norm is 15–35%. "
            "Ask for the overhead breakdown (utilities, depreciation, rent, indirect labor) and challenge each."
        )
    else:
        talking_points.append(
            f"**Overhead at +{mult:.0%} of material looks reasonable**, but still ask supplier to "
            "separate fixed vs variable — fixed overhead should decline per unit as volume scales."
        )

if sga:
    talking_points.append(
        f"**SG&A at {labor_spec.sga_margin_pct:.0%} of cost base** — check against supplier's public 10-K "
        "SG&A-to-revenue ratio (available for Foxconn, Luxshare, Pegatron). If they're charging more on our "
        "parts than their corporate average, push back."
    )

if margin:
    m = labor_spec.target_margin_pct
    if m > 0.15:
        talking_points.append(
            f"**Target margin at {m:.0%} is rich** — contract-manufacturing public norm is 3–8% operating margin. "
            f"Silicon/components earn higher (15–30%) but {part.name} isn't one of those. "
            "Counter with 10–12% as the ceiling."
        )
    else:
        talking_points.append(
            f"**Target margin at {m:.0%}** — in line with contract-manufacturing norms. "
            "Still validate against their public operating margin trend (up or down YoY?)."
        )

talking_points.append(
    "**Payment terms (DPO) as a lever** — offering 15 extra days of payment-terms gives supplier ~50bp of NPV "
    f"relief, which you can trade for a 0.3–0.6% price concession. {supplier.name} is currently at "
    f"{[q.payment_terms_days for q in c.quotes_for(part_id) if q.supplier_id == supplier_id][0]} days."
)

talking_points.append(
    "**Volume commitment as a lever** — longer-term commitments justify tooling / NRE amortization "
    "over more units. Ask for a tiered price: step-down at 2× volume, step-down at 3× volume."
)

talking_points.append(
    "**Yield improvement clause** — tie a portion of the next quote to a DPPM (Defective Parts Per Million) "
    "reduction target; if they beat the target, share the savings."
)

talking_points.append(
    "**Public-data sanity checks:** supplier 10-K segment margin, "
    "iFixit / TechInsights teardown cost estimates for this commodity, industry trade-press cost indices."
)

for i, t in enumerate(talking_points, 1):
    st.markdown(f"{i}. {t}")

if result.variance > 0:
    st.info(
        f"Potential headroom on table: **{usd(result.variance)}/unit × annual volume** = cost-down target."
    )
