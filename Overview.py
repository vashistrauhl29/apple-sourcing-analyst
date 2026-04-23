"""Apple Global Sourcing Command Center — landing / overview page.

File is named `Overview.py` so the Streamlit sidebar reads "Overview" instead of "app".
Run with: `python3 -m streamlit run Overview.py`.
"""
from __future__ import annotations

import streamlit as st

from sourcing.data.catalog import Catalog


st.set_page_config(
    page_title="🍎 Apple Global Sourcing — Overview",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()

st.title("🍎 Apple Global Sourcing Command Center")
st.caption(
    "Decision-support workbench for Global Supply Sourcing Managers — BOM-level should-cost, "
    "n-way award splits, what-if scenarios, NPI gate planning, sustainability, trade compliance, "
    "and stakeholder briefings."
)

s = c.summary()
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Parts", s["parts"])
m2.metric("Suppliers", s["suppliers"])
m3.metric("Quotes", s["quotes"])
m4.metric("Tariff rows", s["tariffs"])
m5.metric("NPI gates", s["npi_gates"])

st.markdown("---")
st.subheader("What each module does")

MODULES = [
    ("Portfolio Comparator",
     "Rank every qualified supplier for one part on a single landed-cost basis. First-thing-in-the-morning check."),
    ("Award-Split Optimizer",
     "Compute the % split across suppliers that minimises your weighted cost + risk + carbon objective under real constraints."),
    ("Should-Cost Teardown",
     "Build the supplier price from the ground up (material + labor + overhead + SG&A + margin) and generate negotiation talking points."),
    ("What-If Scenarios",
     "Tariff & demand shocks, tornado sensitivity, 10k-trial Monte Carlo giving you P50 / P90 / P95 budget numbers."),
    ("NPI Backward Planner",
     "From launch date, walk back through LTB → tooling → EVT → DVT → PVT → MP with stage buffers. Traffic-light gate health."),
    ("Sustaining Ops",
     "Post-launch tools: second-source status, Engineering Change Order (ECO) cost impact, Last-Time Buy (LTB) sizing."),
    ("Sustainability (Apple 2030)",
     "Scope 1 / 2 / 3 carbon per unit per supplier vs Apple 2030 target + optional carbon shadow price."),
    ("Trade Compliance",
     "Free-Trade-Agreement qualifier (USMCA etc.), HTS browser, loaded tariff schedule with date-stamped sources."),
    ("Supplier Risk",
     "Financial health (Altman-Z), geopolitical exposure, Time-to-Recover, ESG audit — rolled into one risk score."),
    ("AI Sourcing Analyst",
     "Natural-language queries over the catalog, quote anomaly detection, and QBR-ready briefings tailored to each stakeholder."),
    ("Executive Dashboard",
     "Portfolio rollup: best TCO per part, country exposure, single-source red flags, supplier resilience."),
]

cols = st.columns(3)
for i, (title, blurb) in enumerate(MODULES):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.write(blurb)

st.markdown("---")
st.markdown(
    "Navigate via the left sidebar. Data is seeded synthetic — see "
    "`sourcing/data/*.csv` and stamped `as_of` fields. Engines live under "
    "`sourcing/engine/`; UI pages are thin."
)
