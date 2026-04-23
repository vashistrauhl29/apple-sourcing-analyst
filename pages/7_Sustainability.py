"""Wave 3 — Sustainability (Apple 2030)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.carbon import apple2030_target_for, part_carbon_lines
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Sustainability", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Sustainability — tracking each supplier vs Apple 2030")
st.markdown(
    "_Per-supplier carbon footprint broken down into Scope 1 / 2 / 3 plus transport, alongside "
    "recycled-content %, renewable-energy %, and the gap to Apple's 2030 carbon-neutral commitment. "
    "Use this before award decisions if carbon is on your scorecard._"
)

with st.expander("Scope 1 / 2 / 3 in plain English — open if new"):
    st.markdown(
        "- **Scope 1** — **direct** emissions the supplier controls (factory boilers, forklifts, "
        "on-site fuel combustion).\n"
        "- **Scope 2** — emissions from **purchased electricity / steam** the supplier buys. "
        "Shrinks as the supplier moves to renewable PPAs.\n"
        "- **Scope 3** — **upstream** emissions embedded in what the supplier buys from *their* suppliers "
        "(tier-2+). Biggest & hardest bucket.\n"
        "- **Transport** — outbound logistics to the destination factory.\n"
        "- **gCO2e** — grams of CO2-equivalent; 1,000,000 g = 1 tCO2e.\n"
        "- **Apple 2030 gap %** — how far the supplier is from being carbon-neutral per Apple's 2030 pledge."
    )

part_id = st.selectbox(
    "Part",
    options=list(c.parts.keys()),
    format_func=lambda p: c.parts[p].name,
)

lines = part_carbon_lines(c, part_id)
if not lines:
    st.warning("No carbon data for this part.")
    st.stop()

target = apple2030_target_for(part_id)
best = lines[0]
worst = lines[-1]

# Markdown cards avoid the st.metric label-overflow problem for long supplier names.
st.subheader("Headline")
cA, cB, cC = st.columns(3)
cA.markdown(
    f"**Lowest footprint**  \n"
    f"{best.total:,.0f} g CO2e/unit  \n"
    f"_{best.supplier_name}_"
)
cB.markdown(
    f"**Highest footprint**  \n"
    f"{worst.total:,.0f} g CO2e/unit  \n"
    f"_{worst.supplier_name}_"
)
if target > 0:
    pct_over = best.total / target - 1
    cC.markdown(
        f"**Best vs Apple-2030 target**  \n"
        f"{best.total:,.0f} / target {target:,.0f} g  \n"
        f"_{pct_over:+.0%} to go_"
    )
else:
    cC.markdown("_(No fixed Apple-2030 target in seed data for this part.)_")

df = pd.DataFrame(
    [
        {
            "Supplier": ln.supplier_name,
            "Scope 1 (direct)": ln.scope1,
            "Scope 2 (electricity)": ln.scope2,
            "Scope 3 (upstream)": ln.scope3,
            "Transport": ln.transport,
            "Total gCO2e": ln.total,
            "Recycled %": ln.recycled_pct * 100,
            "Renewable %": ln.renewable_pct * 100,
            "Apple-2030 gap %": ln.apple2030_gap_pct * 100,
        }
        for ln in lines
    ]
)

st.subheader("Emissions stack per supplier")
st.caption(
    "Each stacked bar = total gCO2e per unit shipped. Red dotted line is the Apple-2030 target for this part."
)
fig = go.Figure()
for col in ["Scope 1 (direct)", "Scope 2 (electricity)", "Scope 3 (upstream)", "Transport"]:
    fig.add_bar(name=col, x=df["Supplier"], y=df[col])
fig.update_layout(barmode="stack", height=440, yaxis_title="gCO2e / unit")
if target > 0:
    fig.add_hline(
        y=target,
        line_dash="dot",
        line_color="#dc2626",
        annotation_text=f"Apple 2030 target {target:,.0f}",
    )
st.plotly_chart(fig, use_container_width=True)

st.subheader("Per-supplier detail")
st.dataframe(
    df.style.format(
        {
            "Scope 1 (direct)": "{:,.0f}",
            "Scope 2 (electricity)": "{:,.0f}",
            "Scope 3 (upstream)": "{:,.0f}",
            "Transport": "{:,.0f}",
            "Total gCO2e": "{:,.0f}",
            "Recycled %": "{:.0f}",
            "Renewable %": "{:.0f}",
            "Apple-2030 gap %": "{:.0f}",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Supplier": st.column_config.TextColumn(width="medium"),
    },
)

st.subheader("Shadow carbon price — what if carbon were priced?")
st.caption(
    "Pick a price per tonne of CO2e (Apple uses ~USD 50–100 internally). "
    "This tab shows the per-unit cost in USD the shadow price would add. "
    "Copy this price into the Optimizer's 'Carbon shadow price' slider to see allocation shift."
)
shadow = st.slider("Shadow price (USD per tCO2e)", 0, 300, 75, step=5)
df["Carbon cost (USD/unit)"] = df["Total gCO2e"] / 1_000_000 * shadow
fig2 = px.bar(df, x="Supplier", y="Carbon cost (USD/unit)", color="Supplier")
fig2.update_layout(height=360, showlegend=False)
st.plotly_chart(fig2, use_container_width=True)
