"""Wave 4 — AI Sourcing Analyst."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from sourcing.ai.anomaly import detect
from sourcing.ai.briefing import generate
from sourcing.ai.nl_query import query
from sourcing.data.catalog import Catalog
from sourcing.engine.optimizer import (
    OptimizerInputs,
    build_supplier_options,
    solve_allocation,
)
from sourcing.engine.tco import TCOInputs


st.set_page_config(page_title="AI Sourcing Analyst", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("AI Sourcing Analyst — ask the catalog, spot oddities, brief stakeholders")
st.markdown(
    "_Three tools in one: (1) type English questions and get a filtered dataset back, "
    "(2) auto-detect quotes that look suspicious vs peers or vs should-cost, "
    "(3) generate QBR-ready briefings tailored per stakeholder (NPI / Design / Finance / Trade / "
    "Sustainability / Exec)._"
)

tabs = st.tabs(["Natural-language query", "Anomaly detector", "Stakeholder briefings"])

with tabs[0]:
    st.subheader("Ask the catalog")
    st.caption(
        "Examples:"
        " `iphone suppliers with tariff > 10%` · "
        "`vietnam parts lead > 6 wk` · "
        "`top 5 cheapest components` · "
        "`parts with dppm > 700` · "
        "`macbook under \\$900` · "
        "`single-source parts`."
    )
    text = st.text_input("Query", value="iphone suppliers with tariff > 10%")
    if text:
        r = query(c, text)
        st.caption(f"Parsed filters: `{r.echo}` — {len(r.dataframe)} row(s)")
        st.dataframe(r.dataframe, hide_index=True, use_container_width=True)

with tabs[1]:
    st.subheader("Quote anomalies")
    st.caption(
        "Two checks run in parallel: (a) for each part, flag any quote whose FOB is > **z** standard "
        "deviations from the peer set — higher z = stricter; (b) for assemblies with a Bill of Materials, "
        "flag any quote that's > 20% off our bottoms-up should-cost. Use before any QBR."
    )
    z = st.slider(
        "Peer-set z-threshold (how many σ from peer mean before we flag)",
        1.0, 3.0, 1.5, step=0.1,
    )
    anomalies = detect(c, z_threshold=z)
    if not anomalies:
        st.success("No anomalies above threshold.")
    else:
        rows = []
        for a in anomalies:
            rows.append(
                {
                    "Part": c.parts[a.part_id].name,
                    "Supplier": c.suppliers[a.supplier_id].name,
                    "Kind": a.kind,
                    "Severity": a.severity,
                    "Message": a.message,
                }
            )
        st.dataframe(
            pd.DataFrame(rows).style.format({"Severity": "{:.2f}"}),
            hide_index=True,
            use_container_width=True,
        )

with tabs[2]:
    st.subheader("Stakeholder-tailored briefings")
    st.caption(
        "Same allocation decision — six different framings. Copy-paste into email / Slack / deck. "
        "All sections open by default so you can scan them at a glance."
    )
    part_id = st.selectbox(
        "Part",
        options=list(c.parts.keys()),
        format_func=lambda p: c.parts[p].name,
    )
    volume = st.number_input("Annual volume", 10_000, 200_000_000, 10_000_000, step=100_000)
    options = build_supplier_options(c, part_id, TCOInputs(volume=int(volume), carbon_shadow_usd_per_tonne=50))
    res = solve_allocation(
        options,
        OptimizerInputs(
            annual_volume=int(volume),
            w_cost=1.0,
            w_risk=0.2,
            w_carbon=0.1,
            max_country_share=0.7,
            min_num_suppliers=2,
        ),
    )
    briefings = generate(c, part_id, res)
    for b in briefings:
        with st.expander(b.persona, expanded=True):
            st.markdown(b.markdown)
