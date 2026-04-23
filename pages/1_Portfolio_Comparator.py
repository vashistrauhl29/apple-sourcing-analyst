"""Wave 0/1 — N-way Portfolio Comparator."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.tco import TCOInputs, compute_tco, pick_best_mode
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Portfolio Comparator", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()

st.title("Portfolio Comparator — landed cost on one page")
st.markdown(
    "_Pick one part and see every qualified supplier ranked by landed cost (**TCO — Total Cost of Ownership**: "
    "FOB + freight + duty + inventory carry + yield loss + NRE amortization + optional carbon shadow). "
    "Use this first thing in the morning to sanity-check the incumbent._"
)

with st.expander("What the cost lines mean — open if new to this"):
    st.markdown(
        "- **FOB** — Free On Board, the supplier's quoted ex-factory price before any freight or duty.\n"
        "- **Freight + Insurance** — lane rate × part weight, plus insurance as % of FOB.\n"
        "- **Duties** — base tariff + Section 301 (China) + Section 232 (metals) + AD/CVD, minus any FTA savings.\n"
        "- **Inventory carry** — cost of capital tied up in goods during lead time.\n"
        "- **NRE / unit** — one-time tooling & engineering cost amortized over committed volume.\n"
        "- **Yield loss + Warranty** — cost of scrap + warranty reserve adjusted by First Pass Yield.\n"
        "- **Carbon shadow** — optional \\$ per tCO2e applied to the supplier's Scope 1/2/3 + transport."
    )

# --- Controls ---
left, right = st.columns([1, 2])
with left:
    part_id = st.selectbox(
        "Part",
        options=list(c.parts.keys()),
        format_func=lambda p: f"{c.parts[p].name} ({p})",
        help="Pick the part you're sourcing.",
    )
    volume = st.number_input(
        "Annual Volume (units)",
        min_value=1_000,
        max_value=200_000_000,
        value=10_000_000,
        step=100_000,
        help="Expected annual buy. Drives NRE amortization — higher volume → lower per-unit tooling cost.",
    )
    ir = st.slider(
        "Cost of Capital (annual %) — what your money costs the company",
        5.0, 25.0, 12.0, step=0.5,
    ) / 100.0
    carbon_px = st.slider(
        "Carbon Shadow Price (USD per tCO2e) — 0 = ignore carbon; Apple uses ~50–100 internally",
        0, 300, 50, step=10,
    )
    tariff_override_on = st.checkbox(
        "Simulate a hypothetical tariff rate (overrides the loaded tariff table)",
        help="Useful for 'what if Section 301 +25pp passes next month?' scenarios.",
    )
    tariff_override_pct = (
        st.slider("Hypothetical total duty rate (%)", 0.0, 0.60, 0.25, step=0.01)
        if tariff_override_on
        else None
    )
    include_nre = st.checkbox(
        "Include NRE / tooling amortization (one-time supplier setup cost spread per unit)",
        value=True,
    )
    include_fta = st.checkbox(
        "Honor FTA savings (USMCA etc.) — untick to see 'no deal' baseline",
        value=True,
    )
    fx_stress = st.slider(
        "FX stress on FOB (±%) — simulate currency shift against USD",
        -15.0, 15.0, 0.0, step=0.5,
    ) / 100.0

quotes = c.quotes_for(part_id)
if not quotes:
    st.warning("No quotes for this part.")
    st.stop()

with right:
    supplier_ids = [q.supplier_id for q in quotes]
    picked = st.multiselect(
        "Suppliers in comparison (tick / untick to include)",
        options=supplier_ids,
        default=supplier_ids,
        format_func=lambda sid: f"{c.suppliers[sid].name} [{c.suppliers[sid].country}]",
    )

# --- Compute ---
inputs = TCOInputs(
    annual_interest_rate=ir,
    volume=int(volume),
    carbon_shadow_usd_per_tonne=float(carbon_px),
    include_nre=include_nre,
    include_fta=include_fta,
    tariff_override_pct=tariff_override_pct,
    fx_stress_pct=fx_stress,
)


rows: list[dict] = []
breakdowns: dict[str, dict[str, float]] = {}
for q in quotes:
    if q.supplier_id not in picked:
        continue
    sup = c.suppliers[q.supplier_id]
    mode = pick_best_mode(c, q)
    b = compute_tco(c, q, mode, inputs)
    rows.append(
        {
            "Supplier": sup.name,
            "Country": sup.country,
            "Mode": mode,
            "FOB": b.fob,
            "Freight+Ins": b.freight + b.insurance,
            "Duties": b.base_duty + b.section_301 + b.section_232 + b.adcvd - b.fta_savings,
            "Inventory": b.inventory_carrying,
            "NRE/Unit": b.nre_per_unit,
            "Yield Loss": b.yield_loss + b.warranty_reserve,
            "Carbon": b.carbon_shadow,
            "FX Adj": b.fx_adjustment,
            "DPO Benefit": -b.dpo_benefit,
            "TCO": b.total,
            "LeadWk": q.lead_time_weeks,
            "Capacity/mo": q.capacity_monthly,
        }
    )
    breakdowns[sup.name] = b.positive_lines()

if not rows:
    st.info("Pick at least one supplier.")
    st.stop()

df = pd.DataFrame(rows).sort_values("TCO").reset_index(drop=True)
best = df.iloc[0]
df["vs Best"] = df["TCO"] - best["TCO"]

st.subheader("Landed TCO Ranking (lowest-cost first)")
st.dataframe(
    df.style.format(
        {
            "FOB": "${:,.2f}",
            "Freight+Ins": "${:,.2f}",
            "Duties": "${:,.2f}",
            "Inventory": "${:,.2f}",
            "NRE/Unit": "${:,.2f}",
            "Yield Loss": "${:,.2f}",
            "Carbon": "${:,.2f}",
            "FX Adj": "${:,.2f}",
            "DPO Benefit": "${:,.2f}",
            "TCO": "${:,.2f}",
            "vs Best": "${:,.2f}",
            "LeadWk": "{:.1f}",
            "Capacity/mo": "{:,}",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Supplier": st.column_config.TextColumn(width="medium"),
        "Country": st.column_config.TextColumn(width="small"),
        "Mode": st.column_config.TextColumn(width="small"),
    },
)

st.subheader("Cost Structure (Stacked)")
cat_order = [
    "FOB",
    "Freight",
    "Insurance",
    "Base Duty",
    "Section 301",
    "Section 232",
    "AD/CVD",
    "Inventory Carry",
    "NRE Amort.",
    "Yield Loss",
    "Warranty Reserve",
    "Carbon Shadow",
    "FX Adjustment",
]
exclude_fob = st.checkbox(
    "Focus View — hide FOB so the smaller deltas are visible",
    value=True,
    help="FOB usually dominates the bar; hiding it lets duties / freight / yield stand out.",
)
shown = [x for x in cat_order if not (exclude_fob and x == "FOB")]

fig = go.Figure()
for cat in shown:
    fig.add_bar(
        name=cat,
        x=list(breakdowns.keys()),
        y=[breakdowns[s].get(cat, 0.0) for s in breakdowns.keys()],
    )
fig.update_layout(barmode="stack", height=480, legend_title_text="Cost line")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Quick Read")
second = df.iloc[1] if len(df) > 1 else None
lines = [
    f"- **Best TCO:** {best['Supplier']} ({best['Country']}) at {usd(best['TCO'])}/unit.",
]
if second is not None:
    gap = second["TCO"] - best["TCO"]
    lines.append(
        f"- **Runner-up:** {second['Supplier']} at +{usd(gap)}/unit — "
        f"{'marginal (<1%)' if gap < best['TCO']*0.01 else 'meaningful gap'}."
    )
concentration = df.groupby("Country")["TCO"].count().to_dict()
if any(v == len(df) for v in concentration.values()):
    lines.append("- ⚠️ **All options in one country** — concentration risk. Qualify a second country.")
st.markdown("\n".join(lines))
