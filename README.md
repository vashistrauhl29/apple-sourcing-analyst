# Apple Global Sourcing Command Center

Decision-support workbench for a Global Supply Sourcing Manager (GSSM) at Apple.
Upgraded from a two-country TCO comparator to an 11-page multi-module platform:
BOM-level should-cost, n-way award splits, Monte Carlo what-if, NPI gate planning,
Apple-2030 sustainability, trade compliance, supplier risk, AI analyst, and an
executive rollup.

## Run

```bash
pip install -r requirements.txt
streamlit run Overview.py
```

Then navigate the sidebar across 11 modules.

## Run tests

```bash
pytest -q
```

## Layout

- `Overview.py` — landing / navigation hub (sidebar label: "Overview").
- `pages/*.py` — one thin UI page per module.
- `sourcing/domain/*` — immutable dataclasses (Part, Supplier, Quote, …).
- `sourcing/data/*` — seed CSVs + `Catalog.load()` single-entry loader.
- `sourcing/engine/*` — pure-Python business logic: TCO, should-cost, MILP optimizer,
  Monte Carlo, NPI planner, carbon, trade, risk.
- `sourcing/ai/*` — rule-based NL query, anomaly detector, stakeholder briefing generator.
- `tests/*` — pytest suite covering catalog, TCO, optimizer, MC, NPI, trade/carbon/risk, AI.
- `docs/FEATURES.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md` — design spec and phased build plan.

## Feature map (see `docs/FEATURES.md` for detail)

| # | Module | Wave |
|---|---|---|
| 1 | Portfolio Comparator (n-way) | 0/1 |
| 2 | Award-Split Optimizer (MILP) | 1 |
| 3 | Should-Cost Teardown | 1 |
| 4 | What-If (Monte Carlo, tornado, shocks) | 2 |
| 5 | NPI Backward Planner | 3 |
| 6 | Sustaining Ops | 3 |
| 7 | Sustainability (Apple 2030) | 3 |
| 8 | Trade Compliance (FTA / substantial transformation) | 3 |
| 9 | Supplier Risk (Altman-Z, concentration, TTR) | 3 |
| 10 | AI Sourcing Analyst (NL query, anomaly, briefings) | 4 |
| 11 | Executive Dashboard (portfolio rollup, red flags) | 6 |

## Data

All seed data under `sourcing/data/*.csv` is **synthetic**. Each record carries
`as_of` and `source` fields. Swap in real RFQ / tariff / FX / carbon data by
overwriting the CSVs — `Catalog.load()` picks them up without code changes.

## Not included (design-only)

Wave 5 enterprise integrations — live USITC/WCO feeds, SAP/Agile BOM import,
SSO/RBAC, SOX audit log — are architecturally anticipated but not implemented.
