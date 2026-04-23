"""Quote anomaly detector — flag quotes > k·σ away from should-cost or peer FOB."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from sourcing.data.catalog import Catalog
from sourcing.engine.should_cost import compute_should_cost


@dataclass(frozen=True)
class Anomaly:
    part_id: str
    supplier_id: str
    kind: str
    severity: float
    message: str


def detect(catalog: Catalog, z_threshold: float = 1.5) -> List[Anomaly]:
    anomalies: List[Anomaly] = []

    # Group quotes by part, compute z of FOB within peer set.
    rows = []
    for q in catalog.quotes:
        rows.append({"part_id": q.part_id, "supplier_id": q.supplier_id, "fob": q.fob_usd})
    df = pd.DataFrame(rows)
    for part_id, grp in df.groupby("part_id"):
        if len(grp) < 2:
            continue
        mu = grp["fob"].mean()
        sd = grp["fob"].std(ddof=0)
        if sd == 0 or pd.isna(sd):
            continue
        for _, r in grp.iterrows():
            z = (r["fob"] - mu) / sd
            if abs(z) >= z_threshold:
                anomalies.append(
                    Anomaly(
                        part_id=r["part_id"],
                        supplier_id=r["supplier_id"],
                        kind="peer-fob-outlier",
                        severity=abs(z),
                        message=(
                            f"FOB ${r['fob']:.2f} is {z:+.1f}σ vs peer set "
                            f"(mean ${mu:.2f}, σ ${sd:.2f})."
                        ),
                    )
                )

    # Quote vs should-cost variance on assemblies — only run where a BOM exists,
    # otherwise a labor-only should-cost makes the variance meaningless.
    parts_with_bom = {bl.parent_part_id for bl in catalog.bom}
    for part_id, part in catalog.parts.items():
        if part.category == "Component":
            continue
        if part_id not in catalog.labor or part_id not in parts_with_bom:
            continue
        for q in catalog.quotes_for(part_id):
            try:
                sc = compute_should_cost(catalog, part_id, q.supplier_id)
            except Exception:
                continue
            if sc.should_cost <= 0:
                continue
            var_pct = (q.fob_usd - sc.should_cost) / sc.should_cost
            if abs(var_pct) > 0.20:
                anomalies.append(
                    Anomaly(
                        part_id=part_id,
                        supplier_id=q.supplier_id,
                        kind="should-cost-gap",
                        severity=abs(var_pct),
                        message=(
                            f"Quote ${q.fob_usd:.2f} is {var_pct:+.0%} vs should-cost "
                            f"${sc.should_cost:.2f}."
                        ),
                    )
                )

    anomalies.sort(key=lambda a: a.severity, reverse=True)
    return anomalies
