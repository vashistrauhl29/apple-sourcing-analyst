"""Wave 3 — Sustaining Ops console."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Sustaining Ops", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Sustaining Ops Console — keeping legacy SKUs healthy")
st.markdown(
    "_Tools for running the back-catalog after launch: am I single-sourced anywhere? What's the cost "
    "impact of a design change (**ECO — Engineering Change Order**)? How many units should I Last-Time-Buy "
    "(**LTB**) before a component goes End-of-Life?_"
)

tabs = st.tabs(
    ["Second-source tracker", "ECO cost impact", "LTB (Last-Time Buy) recommender"]
)

# ---- Second-source tracker ----
with tabs[0]:
    st.subheader("Second-source qualification status")
    st.caption(
        "Any part with only 1 supplier is a continuity risk. Any part with 2+ suppliers "
        "in the same country is still a geopolitical single point of failure."
    )
    rows = []
    for part_id, part in c.parts.items():
        qs = c.quotes_for(part_id)
        if not qs:
            continue
        countries = {c.suppliers[q.supplier_id].country for q in qs}
        sup_count = len(qs)
        status = "✅ Qualified" if sup_count >= 2 else "🟡 Single-sourced"
        if sup_count >= 2 and len(countries) >= 2:
            status = "✅✅ Multi-country"
        rows.append(
            {
                "Part": part.name,
                "Category": part.category,
                "Suppliers": sup_count,
                "Countries": len(countries),
                "Status": status,
                "Qualified suppliers": ", ".join(
                    f"{c.suppliers[q.supplier_id].name} [{c.suppliers[q.supplier_id].country}]"
                    for q in qs
                ),
            }
        )
    df = pd.DataFrame(rows).sort_values("Suppliers")
    st.dataframe(df, hide_index=True, use_container_width=True)

# ---- ECO cost impact ----
with tabs[1]:
    st.subheader("Engineering Change Order (ECO) impact")
    st.caption(
        "An ECO is a design/spec/supplier change after launch. Pick the 'before' and 'after' "
        "quote and this tab tells you how much the change costs per unit, how big the one-time NRE "
        "hit is, and how many weeks of existing inventory runs out before the new part has to cut in."
    )
    part_id = st.selectbox(
        "Affected part",
        options=list(c.parts.keys()),
        format_func=lambda p: c.parts[p].name,
    )
    base_quote = st.selectbox(
        "Current quote (baseline)",
        options=[q.supplier_id for q in c.quotes_for(part_id)],
        format_func=lambda s: c.suppliers[s].name,
    )
    alt_quote = st.selectbox(
        "Proposed quote (post-ECO)",
        options=[q.supplier_id for q in c.quotes_for(part_id)],
        format_func=lambda s: c.suppliers[s].name,
    )
    base = next(q for q in c.quotes_for(part_id) if q.supplier_id == base_quote)
    alt = next(q for q in c.quotes_for(part_id) if q.supplier_id == alt_quote)

    st.markdown("**Baseline vs proposed (FOB basis)**")
    df = pd.DataFrame(
        [
            {
                "Line": "FOB",
                "Baseline": base.fob_usd,
                "Proposed": alt.fob_usd,
                "Δ": alt.fob_usd - base.fob_usd,
            },
            {
                "Line": "NRE (one-time)",
                "Baseline": base.nre_usd + base.tooling_usd,
                "Proposed": alt.nre_usd + alt.tooling_usd,
                "Δ": (alt.nre_usd + alt.tooling_usd) - (base.nre_usd + base.tooling_usd),
            },
            {
                "Line": "Lead time (wk)",
                "Baseline": base.lead_time_weeks,
                "Proposed": alt.lead_time_weeks,
                "Δ": alt.lead_time_weeks - base.lead_time_weeks,
            },
        ]
    )
    st.dataframe(
        df.style.format(
            {"Baseline": "{:,.2f}", "Proposed": "{:,.2f}", "Δ": "{:+,.2f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    inventory_units_on_hand = st.number_input(
        "On-hand + WIP units (will run out before ECO cut-in if short)",
        min_value=0,
        value=250_000,
        step=10_000,
    )
    weeks_cover = inventory_units_on_hand / max(base.capacity_monthly / 4.33, 1)
    st.info(
        f"Current inventory covers approximately **{weeks_cover:.1f} weeks** of runout "
        f"(at {base.capacity_monthly:,}/mo throughput)."
    )

# ---- LTB recommendations ----
with tabs[2]:
    st.subheader("Last-Time Buy (LTB) recommender")
    st.caption(
        "When a component is going end-of-life, you buy a final lifetime supply. This tab sizes "
        "the LTB quantity from weekly demand × remaining service life × shrinkage allowance, and "
        "tells you when to cut the PO."
    )
    part_id = st.selectbox(
        "Legacy part",
        options=list(c.parts.keys()),
        format_func=lambda p: c.parts[p].name,
        key="ltb_part",
    )
    weeks_remaining_in_life = st.slider("Remaining service life (weeks)", 4, 260, 104, step=4)
    weekly_runrate = st.number_input(
        "Weekly demand (units)", min_value=0, value=25_000, step=1_000
    )
    shrinkage_pct = st.slider("Shrinkage / yield loss (%)", 0.0, 10.0, 2.5, step=0.5)
    ltb_units = int(weeks_remaining_in_life * weekly_runrate * (1 + shrinkage_pct / 100))
    q = next(iter(c.quotes_for(part_id)), None)
    ltb_cost = ltb_units * (q.fob_usd if q else 0.0)
    storage_cost = ltb_cost * 0.05
    c1, c2, c3 = st.columns(3)
    c1.metric("LTB quantity", f"{ltb_units:,}")
    c2.metric("Commit value", usd(ltb_cost, 0))
    c3.metric("Est. storage over life (5%/yr prorated)", usd(storage_cost, 0))
    rec_date = date.today() + timedelta(weeks=max(0, weeks_remaining_in_life - 26))
    st.info(f"Recommended PO cut date: **{rec_date.isoformat()}** (26 weeks before end of life).")
