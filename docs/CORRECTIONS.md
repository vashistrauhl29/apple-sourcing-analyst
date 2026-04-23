# Corrections from 2026-04-23 user review

Durable checklist of every issue raised. Each item has owner + status + acceptance criteria. Do NOT delete when done — mark with ✅ so history is preserved.

## Style rules applied across ALL pages

- **Page tagline**: single plain-English line right under the `st.title(...)` describing what this screen does and when a GSSM would open it. No jargon. Same tone as a colleague explaining it over coffee.
- **Inline control hints**: every slider / selectbox / checkbox gets a parenthetical `(what this does / realistic values)` either as the label suffix or a `st.caption` beneath it.
- **Acronym glossary — always expand on first use**:
  - TCO → Total Cost of Ownership (landed cost)
  - DPPM → Defective Parts Per Million
  - FPY → First Pass Yield
  - NRE → Non-Recurring Engineering (one-time setup cost)
  - LTB → Last-Time Buy
  - ECO → Engineering Change Order
  - NPI → New Product Introduction
  - EVT / DVT / PVT → Engineering / Design / Production Validation Test
  - MP → Mass Production
  - FCS → First Customer Ship
  - HTS → Harmonized Tariff Schedule
  - 301 / 232 → Section 301 / 232 US tariffs
  - AD/CVD → Anti-Dumping / Countervailing Duty
  - FTA → Free Trade Agreement
  - USMCA / CPTPP → specific FTAs
  - DPO → Days Payable Outstanding (payment-term float)
  - FX → Foreign Exchange
  - TTR → Time-to-Recover (weeks to restore supply after disruption)
  - Altman-Z → financial health score (>3 safe, 1.8–3 grey, <1.8 distress)
  - MILP → Mixed-Integer Linear Program
  - Scope 1/2/3 → direct emissions / purchased electricity / upstream tier-2+ emissions
  - BOM → Bill of Materials

## Corrections list

| # | Owner | Status | Page / file | Fix |
|---|---|---|---|---|
| C1 | engine | ✅ | `sourcing/engine/tco.py` + callsites | Bug — `ValueError: No lane found: China → China (Ocean)` when component is quoted into origin-country for assembly. Add `pick_best_mode(catalog, quote)` helper that prefers Truck for same-country, Ocean for cross-ocean, Truck for adjacent-NA. All pages must use this helper instead of `"Truck" if Mexico else "Ocean"`. |
| C2 | comparator | ✅ | `pages/1_Portfolio_Comparator.py` | Default "Focus View (exclude FOB)" = **True**. |
| C3 | all pages | ✅ | all `pages/*.py` + `app.py` | Add plain-English page tagline + inline `(…)` hints per Style Rules above. |
| C4 | optimizer | ✅ | `pages/2_Award_Split_Optimizer.py` | Replace raw `w_cost / w_risk / w_carbon` sliders with **decision-style presets**: "Cheapest wins", "Balanced (cost + modest risk hedge)", "De-risk (geo + quality first)", "Green (Apple 2030 track)", "Custom" (shows sliders). Each preset pre-fills the three weights and caption-explains *why*. |
| C5 | optimizer | ✅ | `pages/2_Award_Split_Optimizer.py` | "Max allowed DPPM" → "Max allowed DPPM (Defective Parts Per Million — 500 ≈ tight, 1000 ≈ loose)". Explain "Tariff override scenario" ("simulate a hypothetical duty rate ignoring the loaded tariff table"). |
| C6 | should-cost | ✅ | `pages/3_Should_Cost.py` | Add **"Negotiation Talking Points"** section — auto-generated bullets derived from the teardown: e.g. "Labor at ${wage} × {hrs}h ≈ ${labor} — challenge if quoted labor claim higher than BLS benchmark"; "Overhead multiplier {X} — ask for breakdown if >0.4"; "Target margin {Y}% vs Apple historical norm of 8-12% for this commodity"; etc. Also cite data sources (BLS wage, LME metals, supplier 10-K public margins). |
| C7 | what-if | ✅ | `pages/4_What_If_Scenarios.py` | Tagline + inline hints on each tab; explain P50/P90/P95 in a caption ("P90 = 90% of scenarios come in at or below this — the stress-budget number"). |
| C8 | npi | ✅ | `pages/5_NPI_Planner.py` | Fix table contrast — replace pale pastel backgrounds with stronger colors + bold health cell. Explain each gate in a side glossary (EVT / DVT / PVT / LTB). |
| C9 | sustaining | ✅ | `pages/6_Sustaining_Ops.py` | Tagline + explain second-source, ECO, LTB in plain words in each tab header. |
| C10 | sustainability | ✅ | `pages/7_Sustainability.py` | Fix metric label overflow — use markdown cards instead of `st.metric` for long labels like "36,407 g — Luxshare Pre". Add Scope 1/2/3 explainer at top. |
| C11 | trade | ✅ | `pages/8_Trade_Compliance.py` | Tagline + explain HTS, substantial transformation, FTA in plain words. |
| C12 | risk | ✅ | `pages/9_Supplier_Risk.py` | **Bug** — remove `background_gradient` (matplotlib dep). Use cell-colour via `.style.map` or skip gradient. Rename "TTR" → "Time-to-Recover (weeks)". Explain Altman-Z in caption. |
| C13 | ai | ✅ | `pages/10_AI_Analyst.py` | Briefing expanders: **all open by default**. Explain z-threshold in plain words ("how many standard deviations from the peer mean before flagging"). |
| C14 | exec | ✅ | `pages/11_Executive_Dashboard.py` | Tagline + expand acronyms (TTR → "Time-to-Recover (weeks)", etc.). |
| C15 | all | ✅ | all pages with tables | Tables self-adjust to content — keep `use_container_width=True` but wrap long text cols with `st.column_config.TextColumn(width="large")` where labels are long. |
| C16 | landing | ✅ | `app.py` | Module card blurbs match per-page taglines. |

## Validation

After every correction batch:
1. `pytest -q` (was 38 passing — must stay green).
2. `python3 -m streamlit run app.py` — no tracebacks on first load of any page.
3. Manually exercise: Portfolio Comparator with Camera Module (the crash part) and Award-Split Optimizer with any component.
