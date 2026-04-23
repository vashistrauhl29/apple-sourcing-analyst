# Architecture

## Layering
```
 UI (Streamlit pages/*)             thin, stateless, render-only
   │
   ▼
 Engines (sourcing/engine/*)        pure-Python, testable, no Streamlit imports
   │
   ▼
 Catalog + domain (sourcing/data, sourcing/domain)
                                    immutable dataclasses, CSV-backed
```

UI never computes; engines never render; domain never imports from either.

## Module tree
```
apple-sourcing-analyst-main/
├── app.py                            # landing / navigation hub
├── pages/
│   ├── 1_Portfolio_Comparator.py
│   ├── 2_Award_Split_Optimizer.py
│   ├── 3_Should_Cost.py
│   ├── 4_What_If_Scenarios.py
│   ├── 5_NPI_Planner.py
│   ├── 6_Sustaining_Ops.py
│   ├── 7_Sustainability.py
│   ├── 8_Trade_Compliance.py
│   ├── 9_Supplier_Risk.py
│   ├── 10_AI_Analyst.py
│   └── 11_Executive_Dashboard.py
├── sourcing/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── part.py                   # Part, BOMLine
│   │   ├── supplier.py               # Supplier, SupplierSite
│   │   ├── quote.py                  # Quote, YieldProfile
│   │   ├── logistics.py              # LogisticsLane
│   │   ├── tariff.py                 # TariffSchedule, FTARule
│   │   ├── fx.py                     # FXRate
│   │   ├── npi.py                    # NPIGate, NPIProgram
│   │   └── sustainability.py         # CarbonProfile
│   ├── data/
│   │   ├── __init__.py
│   │   ├── catalog.py                # Catalog.load() single entry point
│   │   ├── parts.csv
│   │   ├── suppliers.csv
│   │   ├── supplier_sites.csv
│   │   ├── quotes.csv
│   │   ├── bom.csv
│   │   ├── lanes.csv
│   │   ├── tariffs.csv
│   │   ├── fta.csv
│   │   ├── fx.csv
│   │   ├── npi_gates.csv
│   │   ├── carbon.csv
│   │   ├── yield.csv
│   │   ├── wages.csv
│   │   └── scenarios/                # saved scenario JSONs
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── tco.py                    # TCO + TCOBreakdown
│   │   ├── should_cost.py
│   │   ├── optimizer.py              # MILP award split (pulp)
│   │   ├── monte_carlo.py            # numpy vectorised
│   │   ├── sensitivity.py            # tornado
│   │   ├── scenarios.py              # tariff/demand shock presets
│   │   ├── npi_planner.py
│   │   ├── carbon.py                 # shadow price, Scope 1/2/3 rollup
│   │   ├── trade.py                  # FTA qualifier, substantial transform
│   │   └── risk.py                   # Altman Z, concentration, TTR
│   └── ai/
│       ├── __init__.py
│       ├── nl_query.py               # rule-based DSL over pandas
│       ├── anomaly.py                # z-score vs should-cost
│       └── briefing.py               # persona-tailored markdown
├── tests/
│   ├── __init__.py
│   ├── test_catalog.py
│   ├── test_tco.py
│   ├── test_should_cost.py
│   ├── test_optimizer.py
│   ├── test_monte_carlo.py
│   ├── test_sensitivity.py
│   ├── test_npi_planner.py
│   └── test_trade.py
├── docs/
│   ├── FEATURES.md
│   ├── PLAN.md
│   └── ARCHITECTURE.md
├── apple_products.csv                # legacy — kept for back-compat
├── requirements.txt
└── README.md
```

## Data flow (one request)
```
UI page
  └─▶ Catalog.load()  (cached via @st.cache_resource)
  └─▶ engine.tco.compute(quote, lane, tariff, fx, yield, carbon_shadow)
  └─▶ Plotly render
```

## Key types (abridged)
```python
@dataclass(frozen=True)
class Part:
    id: str
    name: str
    hts_code: str
    category: str                 # Component | Subassembly | Finished Good
    weight_kg: float

@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    country: str
    tier: int                     # 1/2/3
    altman_z: float
    esg_audit_status: str
    renewable_pct: float

@dataclass(frozen=True)
class Quote:
    supplier_id: str
    part_id: str
    destination: str
    fob_usd: float
    currency: str
    moq: int
    capacity_monthly: int
    nre_usd: float
    tooling_usd: float
    payment_terms_days: int
    valid_until: date
    as_of: date
    source: str

@dataclass(frozen=True)
class TCOBreakdown:
    fob: float
    freight: float
    insurance: float
    base_duty: float
    section_301: float
    section_232: float
    adcvd: float
    fta_savings: float
    inventory_carrying: float
    nre_per_unit: float
    yield_loss: float
    warranty_reserve: float
    carbon_shadow: float
    fx_adjustment: float
    dpo_benefit: float
    total: float
```

## Conventions
- **Dataclasses frozen**; never mutate — rebuild.
- **No Streamlit in `sourcing/`** — engines must remain importable from a plain Python script or a test.
- **PEP 8, type hints on every signature**, black-formatted.
- **All money in USD**; FX conversion happens at the engine boundary.
- **All dates absolute ISO** (`date(2026, 4, 23)`), never relative strings.
- **Seed data marked synthetic**; no real Apple supplier pricing.

## Caching
- `@st.cache_resource` on `Catalog.load()` so CSVs parse once.
- `@st.cache_data` on heavy deterministic engine calls (Monte Carlo with fixed seed).

## Testing
- `pytest` with `-m unit` marker for fast path.
- Golden-value tests for TCO (reference hand-calc).
- Property tests on optimizer: output shares sum to 1, respect min/max.
