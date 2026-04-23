"""Wave 3 — Trade Compliance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.trade import evaluate_fta


st.set_page_config(page_title="Trade Compliance", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("Trade Compliance — where can I duty-engineer savings?")
st.markdown(
    "_Three lenses on tariffs: (1) do my suppliers qualify for any Free Trade Agreement, "
    "and what's the savings in USD? (2) what HTS code does each part carry? (3) what's the full "
    "loaded tariff schedule? Use this before finalising any award — an FTA swing can outweigh a FOB gap._"
)

with st.expander("Trade jargon cheat-sheet"):
    st.markdown(
        "- **HTS (Harmonized Tariff Schedule)** — global 6–10 digit classification that decides duty. "
        "Every part has one; wrong HTS = wrong duty.\n"
        "- **FTA (Free Trade Agreement)** — treaty that zeroes or lowers duty between signatory countries "
        "(e.g. **USMCA** between US/Mexico/Canada; **CPTPP** for Pacific Rim).\n"
        "- **Substantial transformation** — legal test: an imported component must be *transformed* into a "
        "new good in the origin country for FTA to apply (otherwise you're just rebadging).\n"
        "- **Regional content %** — the share of the product's value sourced from the FTA region. USMCA "
        "typically requires ≥60% regional content.\n"
        "- **Section 301** — US tariffs specifically on China-origin goods (List 1–4).\n"
        "- **Section 232** — US tariffs on steel / aluminum / specific strategic metals.\n"
        "- **AD/CVD** — Anti-Dumping / Countervailing Duty assessed on specific goods found to be dumped."
    )

tabs = st.tabs(["FTA qualifier", "HTS browser", "Tariff schedule"])

with tabs[0]:
    st.caption(
        "For each qualified quote, we test whether an FTA applies and estimate whether the supplier "
        "meets the regional-content floor via a BOM-based heuristic. '❌' doesn't always mean no deal — "
        "it often means the tier-2 sourcing needs restructuring to qualify (e.g. pull more components "
        "to Mexico to hit USMCA's 60% floor)."
    )
    part_id = st.selectbox(
        "Part",
        options=list(c.parts.keys()),
        format_func=lambda p: c.parts[p].name,
    )
    quotes = c.quotes_for(part_id)
    if not quotes:
        st.warning("No quotes.")
        st.stop()
    rows = []
    for q in quotes:
        res = evaluate_fta(c, q)
        sup = c.suppliers[q.supplier_id]
        rows.append(
            {
                "Supplier": sup.name,
                "Origin": sup.country,
                "Dest": q.destination_country,
                "FTA": res.fta_name or "—",
                "Qualified": "✅" if res.qualified else "❌",
                "Regional content": res.regional_content_est_pct * 100,
                "Savings USD/unit": res.savings_usd_per_unit,
                "Savings %": res.savings_pct * 100,
                "Reason": res.reason,
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format(
            {
                "Regional content": "{:.0f}%",
                "Savings USD/unit": "${:,.2f}",
                "Savings %": "{:.0f}%",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

with tabs[1]:
    st.subheader("Parts by HTS (Harmonized Tariff Schedule) code")
    st.caption("Reclassifying a part to a different HTS is a classic duty-engineering lever.")
    rows = []
    for p in c.parts.values():
        rows.append(
            {
                "Part": p.name,
                "HTS": p.hts_code,
                "Category": p.category,
                "Weight (kg)": p.weight_kg,
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with tabs[2]:
    st.subheader("Tariff schedule (currently loaded)")
    st.caption(
        "All figures in %. Base duty = statutory HTS rate. Section 301 = US-China. "
        "Section 232 = metals. AD/CVD = anti-dumping / countervailing."
    )
    t_rows = []
    for t in c.tariffs:
        t_rows.append(
            {
                "HTS": t.hts_code,
                "Origin": t.origin_country,
                "Dest": t.destination_country,
                "Base": t.base_duty_rate * 100,
                "301": t.section_301 * 100,
                "232": t.section_232 * 100,
                "AD/CVD": t.adcvd * 100,
                "Effective": t.effective_from.isoformat(),
                "Source": t.source,
            }
        )
    df = pd.DataFrame(t_rows)
    st.dataframe(
        df.style.format(
            {"Base": "{:.1f}%", "301": "{:.1f}%", "232": "{:.1f}%", "AD/CVD": "{:.1f}%"}
        ),
        hide_index=True,
        use_container_width=True,
    )
