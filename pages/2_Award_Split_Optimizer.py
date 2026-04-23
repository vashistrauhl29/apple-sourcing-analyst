"""Wave 1 — Award-Split Optimizer (MILP)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.optimizer import (
    OptimizerInputs,
    build_supplier_options,
    solve_allocation,
)
from sourcing.engine.tco import TCOInputs
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Award-Split Optimizer", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Award-Split Optimizer — how to divide volume across suppliers")
st.markdown(
    "_You've decided to dual- or triple-source. This tool computes the specific % split "
    "that minimises your weighted objective (cost + risk + carbon) under real constraints "
    "(capacity, concentration, quality floor). Uses a Mixed-Integer Linear Program (**MILP** — "
    "a solver that picks the best allocation honoring every rule you set)._"
)

with st.expander("What the jargon means — open if new"):
    st.markdown(
        "- **Share** — % of your annual volume awarded to that supplier.\n"
        "- **DPPM (Defective Parts Per Million)** — supplier quality: 500 ≈ tight, 1000 ≈ loose, 2000 ≈ concerning.\n"
        "- **Max country share** — % cap on any single country. 65% is typical for China+1 strategies.\n"
        "- **Min # of suppliers** — floor on how many suppliers get awarded. 2–3 for resilience.\n"
        "- **Capacity** — supplier's monthly capacity × 12 caps their max share.\n"
        "- **Tariff override** — simulate a hypothetical duty rate instead of the loaded table (e.g. Section 301 +25pp)."
    )


# --- Decision presets ---
PRESETS: dict[str, dict] = {
    "Cheapest wins (pure cost)": {
        "desc": "Minimise TCO (Total Cost of Ownership). Ignore risk and carbon.",
        "w_cost": 1.0,
        "w_risk": 0.0,
        "w_carbon": 0.0,
    },
    "Balanced (cost + modest risk hedge)": {
        "desc": "Default GSSM stance: ~80% weight on cost, small risk premium, light carbon nudge.",
        "w_cost": 1.0,
        "w_risk": 0.2,
        "w_carbon": 0.1,
    },
    "De-risk (geopolitics + quality first)": {
        "desc": "Lean away from fragile / concentrated / high-DPPM suppliers even at modest cost premium.",
        "w_cost": 0.6,
        "w_risk": 0.8,
        "w_carbon": 0.1,
    },
    "Green (Apple-2030 path)": {
        "desc": "Bias toward cleaner-energy suppliers — still cost-aware but carbon weight is material.",
        "w_cost": 0.7,
        "w_risk": 0.2,
        "w_carbon": 0.7,
    },
    "Custom (show raw sliders)": {
        "desc": "Set your own weights. Ratio matters, not absolute values.",
        "w_cost": 1.0,
        "w_risk": 0.2,
        "w_carbon": 0.1,
    },
}

left, right = st.columns([1, 1])
with left:
    part_id = st.selectbox(
        "Part",
        options=list(c.parts.keys()),
        format_func=lambda p: f"{c.parts[p].name} ({p})",
        index=0,
    )
    volume = st.number_input(
        "Annual volume (units) — total buy to allocate",
        10_000, 200_000_000, 10_000_000, step=100_000,
    )
    ir = st.slider("Cost of capital (annual %) — what your money costs", 5.0, 25.0, 12.0) / 100.0
    carbon_px = st.slider(
        "Carbon shadow price (USD per tCO2e) — Apple uses ~50–100 internally",
        0, 300, 50, step=10,
    )

with right:
    st.markdown("**Decision style — pick the lens the exec would use**")
    preset_name = st.radio(
        "Preset",
        options=list(PRESETS.keys()),
        index=1,
        help="Each preset pre-fills the three objective weights with a realistic GSSM stance.",
    )
    preset = PRESETS[preset_name]
    st.caption(preset["desc"])
    if preset_name == "Custom (show raw sliders)":
        w_cost = st.slider("Cost weight", 0.0, 1.0, preset["w_cost"], step=0.05)
        w_risk = st.slider("Risk weight", 0.0, 1.0, preset["w_risk"], step=0.05)
        w_carbon = st.slider("Carbon weight", 0.0, 1.0, preset["w_carbon"], step=0.05)
    else:
        w_cost, w_risk, w_carbon = preset["w_cost"], preset["w_risk"], preset["w_carbon"]
        st.caption(
            f"Weights in use: cost={w_cost:.2f}  risk={w_risk:.2f}  carbon={w_carbon:.2f}"
        )

    st.markdown("**Portfolio constraints (the 'rules')**")
    max_country = st.slider(
        "Max share in any one country — concentration cap (65% typical for China+1)",
        0.20, 1.00, 0.70, step=0.05,
    )
    min_n = st.number_input(
        "Minimum # of suppliers — resilience floor (2–3 typical)",
        1, 6, 2,
    )
    quality_floor = st.number_input(
        "Max allowed DPPM (Defective Parts Per Million) — 0 = no floor; 900 = tight flagship-class",
        0, 5000, 900, step=50,
    )

tco_inputs = TCOInputs(
    annual_interest_rate=ir,
    volume=int(volume),
    carbon_shadow_usd_per_tonne=float(carbon_px),
)
options = build_supplier_options(c, part_id, tco_inputs)

st.subheader("Eligible suppliers (all qualified quotes for this part)")
opts_df = pd.DataFrame(
    [
        {
            "Supplier": o.supplier_name,
            "Country": o.country,
            "TCO / unit": o.tco_per_unit,
            "Carbon gCO2e / unit": o.carbon_gco2e_per_unit,
            "Risk (0-1)": o.risk_score,
            "Capacity / mo": o.monthly_capacity,
            "DPPM": o.dppm,
            "Lead (wk)": o.lead_time_weeks,
        }
        for o in options
    ]
)
st.dataframe(
    opts_df.style.format(
        {
            "TCO / unit": "${:,.2f}",
            "Carbon gCO2e / unit": "{:,.0f}",
            "Risk (0-1)": "{:.2f}",
            "Capacity / mo": "{:,}",
            "DPPM": "{:,}",
            "Lead (wk)": "{:.1f}",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Supplier": st.column_config.TextColumn(width="medium"),
    },
)

with st.expander("Per-supplier share bounds (advanced — force-minimums for strategic reasons)"):
    st.caption(
        "Example: set 'min' to 0.10 on a strategic India supplier to force at least 10% "
        "share regardless of cost. Leave blank (0 / 1) to let the optimizer decide."
    )
    min_shares: dict[str, float] = {}
    max_shares: dict[str, float] = {}
    for o in options:
        c1, c2 = st.columns(2)
        with c1:
            min_shares[o.supplier_id] = st.number_input(
                f"min % {o.supplier_name}",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.05,
                key=f"min_{o.supplier_id}",
            )
        with c2:
            max_shares[o.supplier_id] = st.number_input(
                f"max % {o.supplier_name}",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
                key=f"max_{o.supplier_id}",
            )

opt_inputs = OptimizerInputs(
    annual_volume=int(volume),
    w_cost=w_cost,
    w_risk=w_risk,
    w_carbon=w_carbon,
    max_country_share=max_country,
    min_num_suppliers=int(min_n),
    quality_floor_dppm=int(quality_floor) if quality_floor > 0 else None,
    min_shares=min_shares,
    max_shares=max_shares,
)

if st.button("Solve allocation", type="primary", use_container_width=True):
    res = solve_allocation(options, opt_inputs)
    st.subheader(f"Solver status: {res.status}")
    if res.infeasibility_reason:
        st.error(res.infeasibility_reason)

    if res.rows:
        alloc_df = pd.DataFrame(
            [
                {
                    "Supplier": r.supplier_name,
                    "Country": r.country,
                    "Share %": r.share * 100,
                    "Units": r.units,
                    "Spend (USD)": r.spend_usd,
                    "TCO / unit": r.tco_per_unit,
                    "Carbon g/unit": r.carbon_g_per_unit,
                    "Risk": r.risk_score,
                }
                for r in res.rows
            ]
        )
        st.dataframe(
            alloc_df.style.format(
                {
                    "Share %": "{:.1f}",
                    "Units": "{:,}",
                    "Spend (USD)": "${:,.0f}",
                    "TCO / unit": "${:,.2f}",
                    "Carbon g/unit": "{:,.0f}",
                    "Risk": "{:.2f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Supplier": st.column_config.TextColumn(width="medium"),
            },
        )

        pie = px.pie(alloc_df, values="Share %", names="Supplier", title="Allocation", hole=0.4)
        st.plotly_chart(pie, use_container_width=True)

        total_spend = alloc_df["Spend (USD)"].sum()
        total_units = alloc_df["Units"].sum()
        weighted_tco = total_spend / max(total_units, 1)
        k1, k2, k3 = st.columns(3)
        k1.metric("Total spend", usd(total_spend, 0))
        k2.metric("Weighted TCO / unit", usd(weighted_tco))
        country_share = alloc_df.groupby("Country")["Share %"].sum().max() / 100
        k3.metric("Max country concentration", f"{country_share:.0%}")

        if res.binding_constraints:
            with st.expander("Which constraints are biting (binding) — i.e. costing us money"):
                for b in res.binding_constraints:
                    st.write(f"- {b}")
