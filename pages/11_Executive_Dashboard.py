"""Wave 6 — Executive Dashboard."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.carbon import part_carbon_lines
from sourcing.engine.risk import score_supplier
from sourcing.engine.tco import TCOInputs, compute_tco, pick_best_mode
from sourcing.ui_fmt import usd


st.set_page_config(page_title="Executive Dashboard", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Executive Dashboard — one screen, whole portfolio")
st.markdown(
    "_Roll-up across every part and supplier: lowest-available landed cost per part, country exposure, "
    "single-source red flags, and Time-to-Recover (TTR — how many weeks to restore supply after a disruption) "
    "per supplier. Screenshot this for QBRs._"
)

# --- Portfolio TCO (lowest-cost per part across available suppliers) ---
rows = []
for part_id, part in c.parts.items():
    qs = c.quotes_for(part_id)
    if not qs:
        continue
    best = None
    best_tco = float("inf")
    best_country = ""
    for q in qs:
        sup = c.suppliers[q.supplier_id]
        mode = pick_best_mode(c, q)
        try:
            b = compute_tco(c, q, mode, TCOInputs(volume=5_000_000))
        except Exception:
            continue
        if b.total < best_tco:
            best_tco = b.total
            best = q
            best_country = sup.country
    if best is not None:
        rows.append(
            {
                "Part": part.name,
                "Category": part.category,
                "Best supplier": c.suppliers[best.supplier_id].name,
                "Best country": best_country,
                "Best TCO": best_tco,
                "Num quotes": len(qs),
                "Countries covered": len({c.suppliers[q.supplier_id].country for q in qs}),
            }
        )
df = pd.DataFrame(rows)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Parts tracked", len(df))
k2.metric("Avg TCO / part", usd(df["Best TCO"].mean()))
single_source = df[df["Num quotes"] < 2]
k3.metric("Single-sourced parts (1 supplier)", len(single_source))
single_country = df[df["Countries covered"] < 2]
k4.metric("Single-country parts (1 origin)", len(single_country))

st.subheader("Best-available supplier per part")
st.caption("'Best' = lowest landed TCO across qualified quotes at 5M-unit reference volume.")
st.dataframe(
    df.style.format({"Best TCO": "${:,.2f}"}),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Part": st.column_config.TextColumn(width="medium"),
        "Best supplier": st.column_config.TextColumn(width="medium"),
    },
)

st.subheader("Portfolio exposure by country (count of parts sourced)")
country_rows = []
for _, row in df.iterrows():
    country_rows.append({"Country": row["Best country"], "Parts": 1})
cdf = pd.DataFrame(country_rows).groupby("Country").sum().reset_index()
fig = px.bar(cdf, x="Country", y="Parts", color="Country")
fig.update_layout(showlegend=False, height=360)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Red flags")
reds: list[str] = []
for _, row in single_source.iterrows():
    reds.append(f"**{row['Part']}** — single-sourced ({row['Best supplier']}, {row['Best country']}).")
for _, row in single_country.iterrows():
    reds.append(f"**{row['Part']}** — all qualified suppliers in one country.")
# Supplier risk rollup
high_risk = [s for s in c.suppliers if score_supplier(c, s).overall_score > 0.6]
for s in high_risk:
    reds.append(f"Supplier **{c.suppliers[s].name}** ({c.suppliers[s].country}) — risk score > 0.6.")
if reds:
    for r in reds:
        st.warning(r)
else:
    st.success("No red flags at current thresholds.")

st.subheader("Supplier resilience — Time-to-Recover (TTR, weeks)")
st.caption(
    "TTR = estimated weeks to restore shipments from the supplier's worst-case site after a major "
    "disruption. Longer bar = slower bounce-back; qualify a faster alternate."
)
ttr_rows = []
for s in c.suppliers.values():
    sites = [st_ for st_ in c.sites.values() if st_.supplier_id == s.id]
    ttr_rows.append(
        {
            "Supplier": s.name,
            "Country": s.country,
            "Max Time-to-Recover (wk)": max((si.time_to_recover_weeks for si in sites), default=8),
        }
    )
ttr_df = pd.DataFrame(ttr_rows).sort_values("Max Time-to-Recover (wk)", ascending=False)
fig = px.bar(ttr_df, x="Supplier", y="Max Time-to-Recover (wk)", color="Country")
fig.update_layout(height=380)
st.plotly_chart(fig, use_container_width=True)
