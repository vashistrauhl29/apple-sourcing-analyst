# Apple Global Sourcing Command Center — Features Spec

Reframe: the current repo is a single-SKU two-country TCO comparator. This spec upgrades it into a decision-support workbench for a Global Supply Sourcing Manager (GSSM) at Apple, covering the full decision surface — from BOM-level should-cost to NPI gate planning to portfolio-level award allocation, what-if scenarios, sustainability, trade compliance, and stakeholder briefings.

Each feature below lists: purpose, primary user, inputs, outputs, and acceptance criteria.

---

## Wave 0 — Foundation

### F0.1 Domain model
- **Purpose**: Replace flat CSV + ad-hoc variables with a typed data model that every downstream feature consumes.
- **Entities**: `Part`, `BOMLine`, `Supplier`, `SupplierSite`, `Quote`, `LogisticsLane`, `TariffSchedule`, `FXRate`, `NPIGate`, `CarbonProfile`, `YieldProfile`.
- **Inputs**: seed CSVs under `sourcing/data/`.
- **Outputs**: immutable `@dataclass(frozen=True)` objects loaded once into an in-memory `Catalog`.
- **Acceptance**: every record carries `as_of_date` and `source`; no field is silently defaulted.

### F0.2 Seed data
- **Purpose**: Credible sample data across ~15 parts, ~10 suppliers, ~5 origin countries, ~8 destination plants, tariff schedules, FX forwards, NPI gates, and carbon profiles.
- **Acceptance**: loads without error, rolls BOM → finished good, references only known supplier/part IDs.

### F0.3 TCO engine refactor
- **Purpose**: Replace hardcoded `if country == "Mexico"` with an FTA/tariff lookup keyed on (HTS, origin, destination, as_of_date).
- **Inputs**: `Quote`, `LogisticsLane`, `TariffSchedule`, `FXRate`, `YieldProfile`.
- **Outputs**: `TCOBreakdown` with FOB, freight, insurance, duty, 301/232, AD/CVD, inventory carrying, yield loss, NRE amortization, carbon shadow.
- **Acceptance**: three-way sanity tests (China/Vietnam/Mexico) match hand-computed numbers.

### F0.4 Audit trail
- **Purpose**: Every scenario saveable as JSON with author, timestamp, inputs, outputs, data `as_of_date`.
- **Acceptance**: load/save round-trips identically; SOX-style audit log appended.

---

## Wave 1 — GSSM daily workbench

### F1.1 N-way Portfolio Comparator
- **User**: Commodity GSSM.
- **Purpose**: Compare 2–N suppliers on the same part with per-supplier FOB, lane, yield, NRE.
- **Inputs**: part, list of supplier IDs, demand volume, time horizon.
- **Outputs**: side-by-side TCO stack chart + per-supplier delta table + driver decomposition.
- **Acceptance**: supports ≥5 suppliers simultaneously; FOB no longer shared across options.

### F1.2 Award-Split Optimizer
- **User**: Commodity GSSM, Commodity Manager.
- **Purpose**: MILP that allocates volume across suppliers to minimise (weighted) TCO + risk + carbon, subject to business rules.
- **Constraints**: `sum(shares)=1`; per-supplier `min_share`/`max_share`; per-supplier capacity ceiling; per-country max concentration; minimum # of suppliers; optional quality floor (max DPPM).
- **Objective**: `w_cost·TCO + w_carbon·carbon_cost + w_risk·risk_score`.
- **Outputs**: allocation (% + units + $), shadow prices on binding constraints, sensitivity to weight changes.
- **Acceptance**: returns provably optimal allocation via `pulp`; binding constraints explicitly surfaced.

### F1.3 Should-Cost Decomposition
- **User**: GSSM, Commodity Finance, Supplier Development.
- **Purpose**: Teardown quote into material + labor-hours × regional wage + overhead + SG&A + margin; flag variance vs quoted.
- **Inputs**: BOM, wage table, overhead rate, target margin band.
- **Outputs**: stacked waterfall chart quoted vs should-cost; variance $ and %.
- **Acceptance**: matches manual spreadsheet calc for one reference part to within $0.01.

### F1.4 Yield-adjusted unit economics
- **User**: GSSM, Quality.
- **Purpose**: Convert cost-per-shipped-unit to cost-per-good-unit using FPY, DPPM, warranty reserve.
- **Acceptance**: `cost_per_good = cost_per_shipped / FPY + warranty_reserve_per_unit`.

### F1.5 NRE / tooling amortization
- **Purpose**: Spread one-time NRE and tooling investment over committed volume horizon; flow per-unit charge into TCO.
- **Acceptance**: amortization table by quarter; toggles `include_nre` in TCO.

### F1.6 FX sensitivity
- **Purpose**: Show how TCO shifts when CNY/INR/VND/MXN/THB move ±X% against USD forward curve.
- **Acceptance**: sensitivity table + spark chart per currency.

### F1.7 DPO / payment-terms NPV
- **Purpose**: Value the working-capital benefit of longer payment terms at the company cost of capital.
- **Acceptance**: per-unit NPV benefit computed; optional adjustment into TCO ranking.

---

## Wave 2 — What-if engine

### F2.1 Demand-shock simulator
- **User**: GSSM, NPI PM, S&OP.
- **Purpose**: ±X% demand → which supplier hits capacity wall? forces freight-mode upgrade? triggers expedite premium?
- **Outputs**: capacity-gap heatmap, triggered mitigations, cost overrun.

### F2.2 Tariff-scenario engine
- **Purpose**: Pre-loaded plausible shocks (Section 232 expansion, Mexico 25%, USMCA sunset, further China hikes) + ad-hoc.
- **Outputs**: delta TCO per shock, winners/losers in the supplier set, break-even share shift.

### F2.3 Monte Carlo
- **Purpose**: Joint distribution over demand, FX, freight, yield, tariff probability; N trials.
- **Outputs**: TCO distribution, P50/P90, Value at Risk.
- **Acceptance**: ≥10 000 trials in <2 s with `numpy` vectorisation.

### F2.4 Tornado / sensitivity
- **Purpose**: Rank drivers by contribution to TCO variance.
- **Outputs**: horizontal bar chart, one bar per input, sorted by swing magnitude.

### F2.5 Scenario tree
- **Purpose**: Conditional decision-analysis (e.g., tariff probability × pre-build inventory × freight-mode shift).
- **Outputs**: expected value rollup, optimal policy per branch.

---

## Wave 3 — Cross-functional modules

### F3.1 NPI Backward Planner
- **User**: NPI PM, GSSM, Sustaining.
- **Purpose**: From launch date work back through MP → PVT → DVT → EVT → tooling → LTB-raw-material with stage-margin buffers.
- **Outputs**: Gantt + red/amber/green per gate + identified long-lead risks.
- **Acceptance**: identifies latest-start date for each gate; flags overruns.

### F3.2 Sustaining Ops Console
- **User**: Sustaining Ops lead, GSSM.
- **Purpose**: Second-source qualification tracker, ECO cost-delta calculator, EOL/LTB trigger list.
- **Outputs**: qualification table with status, ECO impact stack, LTB recommendation with demand-tail assumption.

### F3.3 Sustainability / Carbon module
- **User**: Env Ops, Sustainability team, GSSM (Apple 2030).
- **Purpose**: gCO2e per unit (Scope 1/2/3), recycled content %, supplier renewable-energy %.
- **Features**: shadow carbon price injectable into TCO; progress bar vs Apple 2030 trajectory.
- **Acceptance**: toggling shadow price changes optimizer allocation.

### F3.4 Trade Compliance
- **User**: Trade Compliance, GSSM.
- **Purpose**: HTS classifier assist, substantial-transformation checker, FTA savings calculator (USMCA, CPTPP, UKFTA, India GSP remnants).
- **Outputs**: qualification verdict per lane, savings $, documentation checklist.

### F3.5 Supplier Risk Panel
- **User**: Supplier Development, GSSM, Legal.
- **Purpose**: Altman Z-score from 10-K (manual entry for seed data), geographic concentration, geopolitical index, ESG audit status, Time-to-Recover (TTR) estimate.
- **Outputs**: per-supplier risk card + portfolio concentration heatmap.

---

## Wave 4 — Intelligence

### F4.1 Natural-language query
- **Purpose**: DSL over the catalog — "components where India is ≤$0.30 cheaper but adds ≥3 wks lead time AND current China share > 80%".
- **Implementation**: rule-based parser → pandas filter; LLM hook reserved but not required.
- **Acceptance**: handles ≥20 query templates; returns DataFrame + natural-language echo.

### F4.2 Quote anomaly detector
- **Purpose**: Flag quotes deviating >2σ from should-cost or historical range.
- **Outputs**: flagged list + rationale.

### F4.3 Stakeholder briefing generator
- **Purpose**: Same decision, six tailored briefings (NPI, Design, Finance, Trade, Sustainability, Exec).
- **Acceptance**: each briefing surfaces only the fields relevant to that persona.

### F4.4 Negotiation playbook
- **Purpose**: Public-data benchmarks (LME metals, supplier 10-K margin) → talking points + BATNA.
- **Outputs**: markdown brief ready for QBR.

---

## Wave 5 — Enterprise integration (design-only placeholders)
Live USITC/WCO tariff feed, SAP/Agile BOM import, RFQ portal ingestion, SSO + RBAC, SOX audit log. Stubs shipped; real integrations out of scope.

---

## Wave 6 — Moonshots

### F6.1 Multi-tier supply graph
Apple → EMS → component → substrate → wafer → silicon; surfaces concentration risk beyond Tier 1.

### F6.2 Geopolitical heatmap
Supplier map overlaid with sanctions, election calendar, trade-action risk score.

### F6.3 Executive dashboard
Portfolio exposure heatmap, single-source red flags, YoY cost-down tracker, carbon trajectory, resilience score rollup.
