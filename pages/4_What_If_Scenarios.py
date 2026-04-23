"""Wave 2 — What-If: Monte Carlo, tornado, tariff/demand shocks."""
from __future__ import annotations

from dataclasses import replace

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.monte_carlo import MonteCarloInputs, run_monte_carlo
from sourcing.engine.scenarios import DEMAND_SHOCKS, TARIFF_SHOCKS
from sourcing.engine.sensitivity import tornado
from sourcing.engine.tco import TCOInputs, compute_tco, pick_best_mode
from sourcing.ui_fmt import usd


st.set_page_config(page_title="What-If Scenarios", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("What-If Scenarios — stress-test your TCO")
st.markdown(
    "_Four ways to ask 'what if the world changes?' — (1) plausible tariff shocks, "
    "(2) demand spikes / drops, (3) a tornado chart ranking every driver by how much it moves TCO, "
    "(4) a Monte Carlo simulation that runs thousands of random futures to give you P50/P90/P95 budget numbers._"
)

left, right = st.columns([1, 1])
with left:
    part_id = st.selectbox(
        "Part",
        options=list(c.parts.keys()),
        format_func=lambda p: f"{c.parts[p].name} ({p})",
    )
    quotes = c.quotes_for(part_id)
    supplier_id = st.selectbox(
        "Supplier",
        options=[q.supplier_id for q in quotes],
        format_func=lambda s: f"{c.suppliers[s].name} [{c.suppliers[s].country}]",
    )
    quote = next(q for q in quotes if q.supplier_id == supplier_id)
    sup = c.suppliers[supplier_id]
    mode = pick_best_mode(c, quote)

with right:
    volume = st.number_input("Planned volume (units)", 10_000, 200_000_000, 10_000_000, step=100_000)
    ir = st.slider("Cost of capital (%)", 5.0, 25.0, 12.0) / 100.0
    carbon_px = st.slider("Carbon shadow (USD per tCO2e)", 0, 300, 50, step=10)
    trials = st.slider("Monte Carlo trials", 1_000, 50_000, 10_000, step=1_000)

base_inputs = TCOInputs(
    annual_interest_rate=ir,
    volume=int(volume),
    carbon_shadow_usd_per_tonne=float(carbon_px),
)

tabs = st.tabs(["Tariff shocks", "Demand shocks", "Tornado", "Monte Carlo"])

# ---- Tariff shocks ----
with tabs[0]:
    st.caption(
        "Pre-loaded hypothetical duty changes. Each row re-computes your TCO as if that policy passed tomorrow. "
        "Useful for board-deck pages titled 'what's our exposure if tariff X happens?'"
    )
    rows = []
    for sh in TARIFF_SHOCKS:
        override: float | None = None
        if sup.country == "China" and sh.china_301_delta:
            override = max(
                0.0,
                (quote.fob_usd and 0.0)  # placeholder to clarify override path
            )
            override = None  # fall through to tariff table + delta
            # Compute by stressing via override: approximate by adding the delta to current 301
            tariff = c.tariff_for(c.parts[part_id].hts_code, "China", quote.destination_country)
            current_301 = tariff.section_301 if tariff else 0.0
            new_301 = max(0.0, current_301 + sh.china_301_delta) if sh.china_301_delta > -1.0 else 0.0
            override = (tariff.base_duty_rate if tariff else 0.0) + new_301
        if sup.country == "Mexico" and sh.mexico_duty_override > 0:
            override = sh.mexico_duty_override
        if sup.country == "Vietnam" and sh.vietnam_duty_override > 0:
            override = sh.vietnam_duty_override
        if sup.country == "India":
            override = sh.india_duty_override if sh.india_duty_override else None
        tco = compute_tco(
            c, quote, mode,
            replace(base_inputs, tariff_override_pct=override),
        ).total
        rows.append({"Scenario": sh.name, "Description": sh.description, "TCO/unit": tco})
    df = pd.DataFrame(rows)
    base_tco = df.loc[0, "TCO/unit"]
    df["Δ vs baseline"] = df["TCO/unit"] - base_tco
    st.dataframe(
        df.style.format({"TCO/unit": "${:,.2f}", "Δ vs baseline": "${:+,.2f}"}),
        hide_index=True,
        use_container_width=True,
    )

# ---- Demand shocks ----
with tabs[1]:
    st.caption(
        "±% demand swing. 'EXPEDITE' fires when demand exceeds supplier's annual capacity, "
        "which forces air-freight / spot-buy / overtime premiums (assumed \\$35/unit)."
    )
    cap_annual = quote.capacity_monthly * 12
    rows = []
    for sh in DEMAND_SHOCKS:
        d = int(volume * sh.volume_mult)
        over_capacity = d > cap_annual
        trig = "EXPEDITE" if over_capacity else "—"
        stress_tco = compute_tco(
            c, quote, mode, replace(base_inputs, volume=d)
        ).total
        if over_capacity:
            stress_tco += 35.0
        rows.append(
            {
                "Scenario": sh.name,
                "Volume": d,
                "Annual cap": cap_annual,
                "Trigger": trig,
                "TCO/unit": stress_tco,
            }
        )
    st.dataframe(
        pd.DataFrame(rows).style.format(
            {"Volume": "{:,}", "Annual cap": "{:,}", "TCO/unit": "${:,.2f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )

# ---- Tornado ----
with tabs[2]:
    st.caption(
        "Each bar = TCO swing when one driver moves between a low and high bound. "
        "Top = the driver that hurts most. Fix / hedge the top driver first."
    )
    bars = tornado(c, quote, mode, base_inputs)
    base_tco = compute_tco(c, quote, mode, base_inputs).total
    fig = go.Figure()
    for b in bars:
        fig.add_trace(
            go.Bar(
                y=[b.driver],
                x=[b.high - b.low],
                base=[min(b.low, b.high) - base_tco],
                orientation="h",
                name=b.driver,
                text=f"${b.swing:,.2f} swing",
            )
        )
    fig.update_layout(
        title=f"Tornado — base TCO ${base_tco:,.2f}",
        height=420,
        barmode="overlay",
        showlegend=False,
        xaxis_title="Δ TCO ($/unit)",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Monte Carlo ----
with tabs[3]:
    st.caption(
        "Runs thousands of simulated futures, each with randomised FOB / FX / freight / yield / tariff / demand. "
        "**P50** = median outcome, **P90** = 90% of futures come in at or below this (your stress-budget number), "
        "**P95** = value-at-risk / worst-realistic outcome. Use P90 when defending a budget ask to finance."
    )
    mc = MonteCarloInputs(trials=int(trials))
    res = run_monte_carlo(c, quote, mode, base_inputs, mc)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Base (deterministic)", usd(res.base_tco))
    m2.metric("P50 (median)", usd(res.p50))
    m3.metric("P90 (stress budget)", usd(res.p90))
    m4.metric("P95 (value-at-risk)", usd(res.p95))
    k1, k2 = st.columns(2)
    k1.metric("Mean ± stdev", f"{usd(res.mean)} ± {usd(res.std)}")
    k2.metric("Expedite-triggered trials", f"{res.expedite_hits_pct:.1%}")
    hist = px.histogram(
        res.distribution, nbins=60, title=f"TCO distribution ({trials:,} trials)"
    )
    hist.update_layout(showlegend=False, xaxis_title="TCO/unit ($)", yaxis_title="Count")
    hist.add_vline(x=res.p50, line_dash="dash", annotation_text="P50")
    hist.add_vline(x=res.p90, line_dash="dot", annotation_text="P90")
    st.plotly_chart(hist, use_container_width=True)
