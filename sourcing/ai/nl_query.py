"""Rule-based natural-language query DSL over the catalog.

Supported query fragments (case-insensitive):
    "iphone" / "macbook" / "ipad" / "watch" / "airpod"  — filter by product family
    "china" / "vietnam" / "india" / "mexico" / "thailand" / "taiwan" — origin filter
    "tariff > 10%" / "section 301"                      — tariff conditions
    "dppm > 500" / "yield < 0.97"                       — quality thresholds
    "lead > 6 weeks"                                    — lead-time
    "under $100" / "fob > 50"                           — price band
    "carbon > 5000"                                     — gCO2e/unit threshold
    "single-source"                                     — parts with < 2 suppliers
    "top 5 cheapest"                                    — limit / sort
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import pandas as pd

from sourcing.data.catalog import Catalog


@dataclass(frozen=True)
class QueryResult:
    echo: str
    dataframe: pd.DataFrame


def _family(name: str) -> str:
    n = name.lower()
    if "iphone" in n:
        return "iPhone"
    if "macbook" in n:
        return "MacBook"
    if "ipad" in n:
        return "iPad"
    if "watch" in n:
        return "Watch"
    if "airpod" in n:
        return "AirPods"
    return "Other"


def _flat_table(catalog: Catalog) -> pd.DataFrame:
    rows = []
    for q in catalog.quotes:
        sup = catalog.suppliers[q.supplier_id]
        part = catalog.parts[q.part_id]
        yp = catalog.yields.get((q.supplier_id, q.part_id))
        cp = catalog.carbon.get((q.supplier_id, q.part_id))
        tariff = catalog.tariff_for(part.hts_code, sup.country, q.destination_country)
        tariff_pct = 0.0
        if tariff is not None:
            tariff_pct = (
                tariff.base_duty_rate + tariff.section_301 + tariff.section_232 + tariff.adcvd
            )
        carbon = 0.0
        if cp is not None:
            carbon = cp.scope1_gco2e_per_unit + cp.scope2_gco2e_per_unit + cp.scope3_gco2e_per_unit
        rows.append(
            {
                "Part": part.name,
                "PartID": part.id,
                "Family": _family(part.name),
                "Category": part.category,
                "Supplier": sup.name,
                "SupplierID": sup.id,
                "Origin": sup.country,
                "Destination": q.destination_country,
                "FOB": q.fob_usd,
                "Tariff %": tariff_pct * 100,
                "Section 301": (tariff.section_301 if tariff else 0.0) * 100,
                "Lead wk": q.lead_time_weeks,
                "Capacity/mo": q.capacity_monthly,
                "DPPM": yp.dppm if yp else None,
                "Yield": yp.first_pass_yield if yp else None,
                "Carbon g/unit": carbon,
            }
        )
    return pd.DataFrame(rows)


def query(catalog: Catalog, text: str) -> QueryResult:
    df = _flat_table(catalog)
    t = text.lower()
    filters: List[str] = []

    for fam in ["iphone", "macbook", "ipad", "watch", "airpod"]:
        if fam in t:
            df = df[df["Family"].str.lower().str.contains(fam)]
            filters.append(f"family={fam}")

    for country in ["China", "Vietnam", "India", "Mexico", "Thailand", "Taiwan"]:
        if country.lower() in t:
            df = df[df["Origin"] == country]
            filters.append(f"origin={country}")

    if "section 301" in t or "301" in t:
        df = df[df["Section 301"] > 0]
        filters.append("has section 301")

    # Tariff threshold
    m = re.search(r"tariff\s*([<>])\s*(\d+(?:\.\d+)?)\s*%?", t)
    if m:
        op, val = m.group(1), float(m.group(2))
        df = df[df["Tariff %"] > val] if op == ">" else df[df["Tariff %"] < val]
        filters.append(f"tariff {op} {val}%")

    m = re.search(r"dppm\s*([<>])\s*(\d+)", t)
    if m:
        op, val = m.group(1), int(m.group(2))
        df = df[df["DPPM"] > val] if op == ">" else df[df["DPPM"] < val]
        filters.append(f"DPPM {op} {val}")

    m = re.search(r"yield\s*([<>])\s*(\d+(?:\.\d+)?)", t)
    if m:
        op, val = m.group(1), float(m.group(2))
        df = df[df["Yield"] > val] if op == ">" else df[df["Yield"] < val]
        filters.append(f"yield {op} {val}")

    m = re.search(r"lead\s*([<>])\s*(\d+(?:\.\d+)?)\s*(?:w|wk|weeks?)", t)
    if m:
        op, val = m.group(1), float(m.group(2))
        df = df[df["Lead wk"] > val] if op == ">" else df[df["Lead wk"] < val]
        filters.append(f"lead {op} {val} wk")

    m = re.search(r"(under|below)\s*\$?(\d+(?:\.\d+)?)", t)
    if m:
        df = df[df["FOB"] < float(m.group(2))]
        filters.append(f"FOB < ${m.group(2)}")

    m = re.search(r"(over|above)\s*\$?(\d+(?:\.\d+)?)", t)
    if m:
        df = df[df["FOB"] > float(m.group(2))]
        filters.append(f"FOB > ${m.group(2)}")

    m = re.search(r"fob\s*([<>])\s*\$?(\d+(?:\.\d+)?)", t)
    if m:
        op, val = m.group(1), float(m.group(2))
        df = df[df["FOB"] > val] if op == ">" else df[df["FOB"] < val]
        filters.append(f"FOB {op} ${val}")

    m = re.search(r"carbon\s*([<>])\s*(\d+(?:\.\d+)?)", t)
    if m:
        op, val = m.group(1), float(m.group(2))
        df = df[df["Carbon g/unit"] > val] if op == ">" else df[df["Carbon g/unit"] < val]
        filters.append(f"carbon {op} {val}")

    if "single-source" in t or "single source" in t or "single sourced" in t:
        part_counts = _flat_table(catalog).groupby("PartID").size()
        single = set(part_counts[part_counts < 2].index)
        df = df[df["PartID"].isin(single)]
        filters.append("single-source parts")

    m = re.search(r"top\s+(\d+)\s+(cheapest|expensive|longest|lowest|highest)?", t)
    if m:
        n = int(m.group(1))
        sort_key = m.group(2) or "cheapest"
        if sort_key in ("cheapest", "lowest"):
            df = df.sort_values("FOB", ascending=True).head(n)
        elif sort_key in ("expensive", "highest"):
            df = df.sort_values("FOB", ascending=False).head(n)
        elif sort_key == "longest":
            df = df.sort_values("Lead wk", ascending=False).head(n)
        filters.append(f"top {n} {sort_key}")

    echo = "No filters parsed — showing all rows." if not filters else " AND ".join(filters)
    return QueryResult(echo=echo, dataframe=df.reset_index(drop=True))
