# Execution Plan — Phased Attack

This plan sequences the FEATURES.md scope so that each phase is shippable and unblocks the next. Phases are ordered by dependency, not by feature-wave number; some Wave 3/4 items land earlier because they reuse the Wave 1 engine.

## Guiding principles
1. **Data model first**. Every downstream feature reads the same typed catalog; thrashing the schema later is the single biggest risk.
2. **Engines before pages**. UI is thin; all logic lives in `sourcing/engine/*` and is unit-testable without Streamlit.
3. **Seed data is a deliverable**. Credible synthetic data is what makes the tool demo-able; it gets the same care as code.
4. **Every wave leaves a runnable app**. No phase ends with a broken `streamlit run app.py`.
5. **Dates and sources on every record.** Audit trail is non-negotiable for a compliance-adjacent tool.

## Phase sequence

### Phase A — Plan & scaffold (this phase)
- Save `docs/FEATURES.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`.
- Decide libraries: `pulp` (MILP), `numpy` (Monte Carlo), `scipy` (forward rates interp), `plotly`.
- Update `requirements.txt`.

### Phase B — Foundation (Wave 0)
1. `sourcing/domain/*.py` dataclasses.
2. `sourcing/data/*.csv` seed data (parts, suppliers, sites, quotes, bom, lanes, tariffs, fx, npi_gates, carbon, yield, wages).
3. `sourcing/data/catalog.py` loader.
4. `sourcing/engine/tco.py` — single authoritative TCO function.
5. Pytest: `tests/test_tco.py`, `tests/test_catalog.py`.
**Exit**: `python -c "from sourcing.data.catalog import Catalog; c=Catalog.load(); print(c.summary())"` works.

### Phase C — Portfolio Comparator (Wave 0/1)
- `pages/1_Portfolio_Comparator.py` — n-way comparator using the engine.
- Replaces current `app.py` two-country logic; `app.py` becomes the landing page.
**Exit**: visual parity or better with current tool, now n-way.

### Phase D — Award-Split Optimizer (Wave 1)
- `sourcing/engine/optimizer.py` (MILP).
- `pages/2_Award_Split_Optimizer.py`.
- `tests/test_optimizer.py`.
**Exit**: optimizer returns allocation + shadow prices on a demo problem with ≥4 suppliers.

### Phase E — Should-Cost + Yield + NRE (Wave 1)
- `sourcing/engine/should_cost.py`.
- `pages/3_Should_Cost.py` (waterfall chart).
- Integrate yield + NRE into the TCO engine (backward-compatible flags).
- `tests/test_should_cost.py`.
**Exit**: should-cost waterfall for a chosen part; optimizer re-run now uses yield-adjusted numbers.

### Phase F — What-if (Wave 2)
- `sourcing/engine/sensitivity.py` (tornado).
- `sourcing/engine/monte_carlo.py` (vectorised).
- `sourcing/engine/scenarios.py` (pre-loaded tariff/demand shocks + tree).
- `pages/4_What_If_Scenarios.py`.
- `tests/test_monte_carlo.py`, `tests/test_sensitivity.py`.
**Exit**: 10k-trial Monte Carlo runs in <2 s; tornado ranks drivers.

### Phase G — NPI Planner (Wave 3)
- `sourcing/engine/npi_planner.py` — backward schedule.
- `pages/5_NPI_Planner.py` (Gantt + gate health).
- `tests/test_npi_planner.py`.
**Exit**: given launch date & lead-time tree, latest-start-per-gate computed and colour-coded.

### Phase H — Cross-functional pages (Wave 3)
Parallelisable — single-page-per-feature pattern, all consume existing engines/catalog:
- `pages/6_Sustaining_Ops.py` (second-source, ECO, LTB).
- `sourcing/engine/carbon.py` + `pages/7_Sustainability.py` (gCO2e, recycled %, carbon shadow price hook into TCO).
- `sourcing/engine/trade.py` + `pages/8_Trade_Compliance.py` (FTA, substantial transformation).
- `sourcing/engine/risk.py` + `pages/9_Supplier_Risk.py` (Altman Z, concentration, TTR).
**Exit**: carbon shadow price toggled on changes optimizer allocation.

### Phase I — Intelligence & Executive (Wave 4/6)
- `sourcing/ai/nl_query.py` (rule-based DSL → pandas).
- `sourcing/ai/anomaly.py` (z-score vs should-cost).
- `sourcing/ai/briefing.py` (stakeholder-tailored markdown generator).
- `pages/10_AI_Analyst.py`.
- `pages/11_Executive_Dashboard.py` (heatmaps, red-flag list, portfolio rollup).
**Exit**: NL query "components where India …" returns a correct DataFrame; briefings render per persona.

### Phase J — Polish
- `app.py` → landing / navigation page describing each module.
- `README.md` updated with screenshots prompt list, run instructions.
- Final pass on `requirements.txt`, pytest green, ruff clean.

## Parallelism map
Phases B→G are serial on the critical path (shared data model, shared engines). Phase H items (6, 7, 8, 9) are independent and could be done in any order or by different engineers. Phase I NL-query can start once Phase F lands.

## Risk register
| Risk | Mitigation |
|---|---|
| MILP solver install friction | `pulp` default CBC ships in-wheel; no native build. |
| Scope creep on AI layer | Ship rule-based NL query; LLM hook is a stub. |
| Seed data credibility | Reference public Apple teardown costs (iFixit, TechInsights) order-of-magnitude only; mark synthetic. |
| Streamlit multipage routing quirks | Use `pages/` directory convention, not `st.Page` — works with older Streamlit. |
| Cross-page state | Persist scenarios via `sourcing/data/scenarios/*.json`, not `st.session_state` alone. |

## Definition of done
- `streamlit run app.py` lands on a nav hub linking to 11 pages.
- Each page loads without error on seed data.
- `pytest -q` passes.
- `docs/FEATURES.md` items all have a backing page or engine function.
- Carbon shadow price, yield, NRE, and FTA all observably move TCO and optimizer output.
