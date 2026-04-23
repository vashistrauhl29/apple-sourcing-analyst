# Apple Global Sourcing Command Center

A Streamlit decision workbench for a Global Supply Sourcing Manager (GSSM) at Apple. It reframes the legacy two-country TCO comparator into eleven working modules that cover the actual calls a commodity manager makes every week — award splits, should-cost negotiation, tariff what-ifs, NPI gate planning, Apple-2030 carbon tracking, trade compliance, supplier risk, and stakeholder briefings.

Synthetic seed data across 15 parts, 10 suppliers, 35 quotes, 34 tariff rows, 14 NPI gates. Swap in real RFQ data by overwriting the twelve CSVs under `sourcing/data/`.

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run Overview.py
```

Open the localhost URL Streamlit prints (usually http://localhost:8501). The left sidebar lists all eleven modules.

Run the test suite:
```bash
pytest -q
```
38 tests, ~1 second, covers the catalog, TCO engine, MILP optimizer, Monte Carlo, NPI planner, trade compliance, carbon rollup, and the AI layer.

---

## Module feature map

| # | Module | What it answers | Core engine |
|---|---|---|---|
| 0 | **Overview** | "What does this app do?" | Landing hub |
| 1 | **Portfolio Comparator** | "Of all my qualified suppliers for this part, who wins on landed cost?" | N-way TCO ranking with FOB, freight, duty, inventory carry, NRE amort, yield loss, carbon shadow |
| 2 | **Award-Split Optimizer** | "Given capacity + country + quality constraints, what's the optimal allocation across suppliers?" | Mixed-Integer Linear Program (PuLP) with four decision presets |
| 3 | **Should-Cost Teardown** | "Is this quote fair, and where can I push the supplier in the next QBR?" | Bottoms-up BOM + labor × wage + overhead + SG&A + margin; auto negotiation talking points |
| 4 | **What-If Scenarios** | "What happens if tariffs move / demand spikes?" | Pre-loaded tariff & demand shocks, 10,000-trial Monte Carlo, tornado sensitivity |
| 5 | **NPI Backward Planner** | "Am I on schedule to launch?" | Launch date → LTB → tooling → EVT → DVT → PVT → MP with stage-margin buffers; traffic-light gate health |
| 6 | **Sustaining Ops** | "Is anything single-sourced? What does this ECO cost me? When do I LTB?" | Second-source tracker, Engineering Change Order delta, Last-Time-Buy sizer |
| 7 | **Sustainability (Apple 2030)** | "Where are we vs the 2030 carbon-neutral target?" | Scope 1 / 2 / 3 + transport per supplier, recycled content %, renewable %, injectable carbon shadow price |
| 8 | **Trade Compliance** | "Can I duty-engineer savings through an FTA?" | USMCA / CPTPP qualifier with substantial-transformation heuristic, per-unit savings $ |
| 9 | **Supplier Risk** | "Who's my weakest link?" | Altman-Z financial + geopolitical + Time-to-Recover + ESG audit, rolled into one score |
| 10 | **AI Sourcing Analyst** | "Ask the catalog in plain English, catch anomalies, generate QBR briefings" | Rule-based NL query DSL, z-score anomaly detector, six persona-tailored briefings |
| 11 | **Executive Dashboard** | "One screen, whole portfolio" | Best TCO per part, country-exposure heatmap, single-source red flags, resilience rollup |

---

## Architecture

```
Overview.py                       landing / nav hub
pages/                            thin UI, one file per module
sourcing/
├── domain/                       immutable @dataclass(frozen=True) types
├── data/                         twelve seed CSVs + Catalog.load()
├── engine/                       pure-Python business logic (no Streamlit)
│   ├── tco.py                    total cost of ownership
│   ├── optimizer.py              MILP award split
│   ├── should_cost.py            bottoms-up build
│   ├── monte_carlo.py            vectorised numpy Monte Carlo
│   ├── sensitivity.py            tornado chart
│   ├── scenarios.py              pre-loaded tariff / demand shocks
│   ├── npi_planner.py            backward scheduling
│   ├── carbon.py                 Scope 1/2/3 rollup
│   ├── trade.py                  FTA qualifier
│   └── risk.py                   supplier risk scoring
└── ai/                           rule-based NL query, anomaly, briefings
tests/                            pytest, 38 cases
docs/
├── FEATURES.md                   full wave-by-wave spec
├── PLAN.md                       phased execution plan
├── ARCHITECTURE.md               module layout + conventions
└── CORRECTIONS.md                durable fix-up log
```

UI never computes, engines never render, domain never imports from either.

---

## Data model

Every record in the twelve seed CSVs carries an `as_of` date and `source` field:

| File | What it holds |
|---|---|
| `parts.csv` | 15 parts (finished goods + components) with HTS codes |
| `suppliers.csv` | 10 suppliers across China, India, Vietnam, Mexico, Thailand, Taiwan |
| `supplier_sites.csv` | factory-level capacity + Time-to-Recover weeks |
| `quotes.csv` | 35 supplier quotes with FOB, MOQ, capacity, lead time, NRE, tooling, payment terms |
| `bom.csv` | Bill of materials for iPhone and MacBook Air |
| `lanes.csv` | 20 freight lanes (Ocean / Truck / Air) with USD per kg + carbon g per kg km |
| `tariffs.csv` | 34 tariff schedules: base duty + Section 301 + Section 232 + AD/CVD |
| `fta.csv` | USMCA, CPTPP, India GSP rules with regional content floors |
| `fx.csv` | USD per unit for CNY, INR, VND, MXN, THB, TWD with 3m / 12m forward rates |
| `yield.csv` | First Pass Yield, DPPM, warranty reserve per supplier × part |
| `carbon.csv` | Scope 1 / 2 / 3 gCO2e per unit per supplier × part |
| `wages.csv` | Country labor rates + overhead multipliers |
| `labor_hours.csv` | Direct labor hours + SG&A % + target margin per part |
| `npi_gates.csv`, `npi_programs.csv` | NPI schedule templates (iPhone 16 Pro, MacBook Air M4) |

All numbers are synthetic and reference order-of-magnitude public teardowns (iFixit, TechInsights). Nothing here is real Apple supplier pricing.

---

## Tech stack

- **Python 3.9+**
- **Streamlit** for the UI
- **pandas** for the data model
- **PuLP** (with CBC solver, bundled) for the MILP optimizer
- **numpy** for the vectorised Monte Carlo
- **plotly** for every chart
- **pytest** for tests

No cloud dependencies, no credentials required. Runs on a laptop in one command.

---

## License

MIT — see `LICENSE`. Free to fork, port, or build on for real supplier data behind a firewall.

---

## Related docs

- `docs/FEATURES.md` — full feature spec organised by delivery wave
- `docs/PLAN.md` — phased build plan and risk register
- `docs/ARCHITECTURE.md` — module layout and layering rules
- `docs/CORRECTIONS.md` — review feedback and fixes applied
