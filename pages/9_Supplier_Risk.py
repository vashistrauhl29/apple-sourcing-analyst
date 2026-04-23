"""Wave 3 — Supplier Risk panel."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.risk import score_supplier


st.set_page_config(page_title="Supplier Risk", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Supplier Risk Panel")
st.markdown(
    "_Who could go dark on us, and how fast could we recover? Combines financial health "
    "(Altman-Z), geopolitical exposure, Time-to-Recover, and ESG audit status into one "
    "risk score per supplier plus a portfolio-level view._"
)

with st.expander("Glossary — open if you're new to these terms"):
    st.markdown(
        "- **Altman-Z**: public-data financial health score. **>3 = Safe**, 1.8–3 = Grey zone, <1.8 = Distress.\n"
        "- **Geopolitical risk (0–1)**: 0 = stable & friendly, 1 = high trade-action / sanction exposure. Seeded from internal assessment.\n"
        "- **Time-to-Recover (TTR, weeks)**: estimated weeks to restore shipments after a major disruption at the worst site.\n"
        "- **Overall score**: weighted blend (40% financial + 35% geo + 15% TTR + 10% ESG). Higher = riskier.\n"
        "- **ESG audit**: supplier's last Apple Supplier Responsibility audit outcome."
    )


def _band_color(val: str) -> str:
    return {
        "Safe": "background-color: #d1fae5",
        "Grey": "background-color: #fef3c7",
        "Distress": "background-color: #fee2e2",
    }.get(val, "")


def _score_color(val: float) -> str:
    if val >= 0.6:
        return "background-color: #fecaca"
    if val >= 0.4:
        return "background-color: #fed7aa"
    return "background-color: #d1fae5"


cards = [score_supplier(c, s) for s in c.suppliers]
df = pd.DataFrame(
    [
        {
            "Supplier": r.supplier_name,
            "Country": r.country,
            "Altman-Z": r.altman_z,
            "Financial band": r.financial_risk,
            "Geo risk (0-1)": r.geopolitical_risk,
            "Time-to-Recover (wk)": r.ttr_weeks,
            "ESG audit": r.esg_status,
            "Overall score": r.overall_score,
        }
        for r in cards
    ]
).sort_values("Overall score", ascending=False)

st.subheader("Supplier risk cards")
st.caption("Sorted highest-risk → lowest. Green = OK, amber = watch, red = escalate.")
styled = (
    df.style.format(
        {
            "Altman-Z": "{:.2f}",
            "Geo risk (0-1)": "{:.2f}",
            "Overall score": "{:.2f}",
        }
    )
    .map(_band_color, subset=["Financial band"])
    .map(_score_color, subset=["Overall score"])
)
st.dataframe(
    styled,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Supplier": st.column_config.TextColumn(width="medium"),
        "Country": st.column_config.TextColumn(width="small"),
        "Financial band": st.column_config.TextColumn(width="small"),
        "ESG audit": st.column_config.TextColumn(width="small"),
    },
)

st.subheader("Country concentration — parts with single country of sourcing")
st.caption("Any row with 1 country is a geopolitical single point of failure.")
conc_rows = []
for part_id, part in c.parts.items():
    qs = c.quotes_for(part_id)
    if not qs:
        continue
    countries = {c.suppliers[q.supplier_id].country for q in qs}
    conc_rows.append(
        {
            "Part": part.name,
            "Qualified suppliers": len(qs),
            "Countries represented": ", ".join(sorted(countries)),
            "# countries": len(countries),
        }
    )
cdf = pd.DataFrame(conc_rows).sort_values("# countries")
st.dataframe(
    cdf,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Countries represented": st.column_config.TextColumn(width="large"),
        "Part": st.column_config.TextColumn(width="medium"),
    },
)

st.subheader("Financial vs geopolitical scatter")
st.caption(
    "Bottom-right quadrant is dangerous (low Altman-Z + high geo risk). "
    "Bubble size = Time-to-Recover weeks — bigger bubble = slower to bounce back."
)
fig = px.scatter(
    df,
    x="Geo risk (0-1)",
    y="Altman-Z",
    size="Time-to-Recover (wk)",
    color="Country",
    hover_name="Supplier",
    title="Bubble size = Time-to-Recover (weeks)",
)
fig.add_hline(y=3.0, line_dash="dot", annotation_text="Altman-Z safe threshold (3.0)")
fig.add_vline(x=0.5, line_dash="dot", annotation_text="Geo risk yellow line")
fig.update_layout(height=480)
st.plotly_chart(fig, use_container_width=True)

red_flags = [r for r in cards if r.overall_score > 0.6]
if red_flags:
    st.error(
        "Portfolio red flags (overall score > 0.6): "
        + ", ".join(r.supplier_name for r in red_flags)
        + " — qualify an alternate source."
    )
else:
    st.success("No suppliers above the 0.6 overall-score threshold today.")
