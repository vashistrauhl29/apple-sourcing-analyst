"""Wave 3 — NPI Backward Planner."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from sourcing.data.catalog import Catalog
from sourcing.engine.npi_planner import critical_path_slack, plan_program


st.set_page_config(page_title="NPI Backward Planner", layout="wide")


@st.cache_resource
def _load() -> Catalog:
    return Catalog.load()


c = _load()
st.title("NPI Backward Planner — are we on schedule to launch?")
st.markdown(
    "_Given a launch date, this walks backward through every NPI (New Product Introduction) gate "
    "and tells you the **latest** you can still start each one. Traffic-light flags any gate that's "
    "already past-due or inside the amber zone. Open this when tooling or LTB decisions are on your desk._"
)

with st.expander("What each gate means"):
    st.markdown(
        "- **LTB Raw Material (Last-Time Buy)** — committed purchase of long-lead wafers / rare earths / "
        "custom material that can't be reordered after a cutoff.\n"
        "- **Tooling Kickoff** — hard-tool release to supplier; dies, molds, fixtures start being cut.\n"
        "- **EVT (Engineering Validation Test)** — first build, 300–800 units, proves the design boots.\n"
        "- **DVT (Design Validation Test)** — 1.5–3k units, proves the design meets spec reliably.\n"
        "- **PVT (Production Validation Test)** — 5–10k units, proves the **process** runs at yield.\n"
        "- **MP Ramp (Mass Production)** — scale to weekly run rate.\n"
        "- **FCS (First Customer Ship)** — goods on shelves / on Apple.com."
    )
st.caption(
    "Latest-start date = launch − (owner's offset weeks + stage-margin buffer weeks). "
    "Buffers reflect historical slip by gate."
)

prog_id = st.selectbox(
    "Program",
    options=list(c.npi_programs.keys()),
    format_func=lambda p: f"{c.npi_programs[p].product_name} ({p})",
)
prog = c.npi_programs[prog_id]

c1, c2, c3 = st.columns(3)
c1.metric("Launch (First Customer Ship)", prog.launch_date.isoformat())
c2.metric("Target Year-1 volume", f"{prog.target_volume_y1:,}")
c3.metric("Mass Production start", prog.mp_start.isoformat())

today = st.date_input(
    "Assume today is…",
    value=date.today(),
    help="Drag this to see future or hypothetical 'what if we decide on this date?' views.",
)
gates = plan_program(c, prog_id, today=today)

df = pd.DataFrame(
    [
        {
            "Gate": g.name,
            "Owner": g.owner,
            "Latest start": g.latest_start.isoformat(),
            "Buffer (wk)": g.buffer_weeks,
            "Health": g.health,
            "What this gate is": g.description,
        }
        for g in gates
    ]
)


def _colour(row: pd.Series) -> list[str]:
    # Strong-contrast palette — readable on light + dark themes.
    bg = {
        "GREEN": "background-color: #047857; color: white; font-weight: 600",
        "AMBER": "background-color: #b45309; color: white; font-weight: 600",
        "RED": "background-color: #b91c1c; color: white; font-weight: 700",
    }.get(row["Health"], "")
    return [bg if col == "Health" else "" for col in row.index]


st.dataframe(
    df.style.apply(_colour, axis=1),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Gate": st.column_config.TextColumn(width="small"),
        "Owner": st.column_config.TextColumn(width="small"),
        "Latest start": st.column_config.TextColumn(width="small"),
        "Buffer (wk)": st.column_config.NumberColumn(width="small"),
        "Health": st.column_config.TextColumn(width="small"),
        "What this gate is": st.column_config.TextColumn(width="large"),
    },
)

slack = critical_path_slack(gates, today)
if slack < 0:
    st.error(f"Earliest gate is **{-slack} days past due** — escalate immediately.")
elif slack < 21:
    st.warning(f"Earliest gate has **{slack} days** of slack — amber zone.")
else:
    st.success(f"Earliest gate has **{slack} days** of slack — on track.")

st.subheader("Gantt view")
st.caption("Each bar spans from the gate's latest-start to launch date. Colour = current health.")
gantt_rows = []
for g in gates:
    gantt_rows.append(
        {"Gate": g.name, "Start": g.latest_start, "Finish": prog.launch_date, "Health": g.health}
    )
gantt_df = pd.DataFrame(gantt_rows)
fig = px.timeline(
    gantt_df,
    x_start="Start",
    x_end="Finish",
    y="Gate",
    color="Health",
    color_discrete_map={"GREEN": "#047857", "AMBER": "#b45309", "RED": "#b91c1c"},
)
fig.update_yaxes(autorange="reversed")
fig.update_layout(height=380)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Assumptions"):
    st.markdown(
        "- Each gate's **latest start** = launch − (offset_weeks + buffer_weeks).\n"
        "- Buffer weeks absorb qualification slip / supplier variability.\n"
        "- Health: RED = past due, AMBER = <21 days slack, GREEN otherwise.\n"
        "- Tune the gate table per program by editing `sourcing/data/npi_gates.csv`."
    )
