"""Catalog: one-stop loader for all seed data, returned as immutable dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from sourcing.domain import (
    BOMLine,
    CarbonProfile,
    FTARule,
    FXRate,
    LogisticsLane,
    NPIGate,
    NPIProgram,
    Part,
    Quote,
    Supplier,
    SupplierSite,
    TariffSchedule,
    YieldProfile,
)

_DATA_DIR = Path(__file__).parent


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value), "%Y-%m-%d").date()


@dataclass(frozen=True)
class Wage:
    country: str
    usd_per_hour: float
    overhead_multiplier: float
    as_of: date
    source: str


@dataclass(frozen=True)
class LaborHours:
    part_id: str
    direct_labor_hours: float
    overhead_material_multiplier: float
    sga_margin_pct: float
    target_margin_pct: float


@dataclass(frozen=True)
class Catalog:
    parts: Dict[str, Part]
    bom: List[BOMLine]
    suppliers: Dict[str, Supplier]
    sites: Dict[str, SupplierSite]
    quotes: List[Quote]
    lanes: List[LogisticsLane]
    tariffs: List[TariffSchedule]
    ftas: List[FTARule]
    fx: Dict[str, FXRate]
    yields: Dict[Tuple[str, str], YieldProfile]
    carbon: Dict[Tuple[str, str], CarbonProfile]
    npi_programs: Dict[str, NPIProgram]
    npi_gates: List[NPIGate]
    wages: Dict[str, Wage]
    labor: Dict[str, LaborHours]

    @staticmethod
    def load(data_dir: Optional[Path] = None) -> "Catalog":
        d = Path(data_dir) if data_dir else _DATA_DIR

        parts_df = pd.read_csv(d / "parts.csv")
        parts = {
            r.id: Part(
                id=r.id,
                name=r.name,
                hts_code=r.hts_code,
                category=r.category,
                weight_kg=float(r.weight_kg),
                unit_of_measure=r.unit_of_measure,
                description=r.description,
            )
            for r in parts_df.itertuples(index=False)
        }

        bom_df = pd.read_csv(d / "bom.csv")
        bom = [
            BOMLine(
                parent_part_id=r.parent_part_id,
                child_part_id=r.child_part_id,
                quantity=float(r.quantity),
                scrap_factor=float(r.scrap_factor),
            )
            for r in bom_df.itertuples(index=False)
        ]

        supp_df = pd.read_csv(d / "suppliers.csv")
        suppliers = {
            r.id: Supplier(
                id=r.id,
                name=r.name,
                country=r.country,
                tier=int(r.tier),
                altman_z=float(r.altman_z),
                esg_audit_status=r.esg_audit_status,
                renewable_pct=float(r.renewable_pct),
                geopolitical_risk=float(r.geopolitical_risk),
                years_of_relationship=int(r.years_of_relationship),
            )
            for r in supp_df.itertuples(index=False)
        }

        sites_df = pd.read_csv(d / "supplier_sites.csv")
        sites = {
            r.id: SupplierSite(
                id=r.id,
                supplier_id=r.supplier_id,
                city=r.city,
                country=r.country,
                monthly_capacity=int(r.monthly_capacity),
                certifications=r.certifications,
                time_to_recover_weeks=int(r.time_to_recover_weeks),
            )
            for r in sites_df.itertuples(index=False)
        }

        q_df = pd.read_csv(d / "quotes.csv")
        quotes = [
            Quote(
                supplier_id=r.supplier_id,
                part_id=r.part_id,
                site_id=r.site_id,
                destination_country=r.destination_country,
                fob_usd=float(r.fob_usd),
                currency=r.currency,
                moq=int(r.moq),
                capacity_monthly=int(r.capacity_monthly),
                lead_time_weeks=float(r.lead_time_weeks),
                nre_usd=float(r.nre_usd),
                tooling_usd=float(r.tooling_usd),
                payment_terms_days=int(r.payment_terms_days),
                valid_until=_parse_date(r.valid_until),
                as_of=_parse_date(r.as_of),
                source=r.source,
            )
            for r in q_df.itertuples(index=False)
        ]

        ln_df = pd.read_csv(d / "lanes.csv")
        lanes = [
            LogisticsLane(
                origin_country=r.origin_country,
                destination_country=r.destination_country,
                mode=r.mode,
                transit_days=int(r.transit_days),
                usd_per_kg=float(r.usd_per_kg),
                insurance_pct=float(r.insurance_pct),
                carbon_g_per_kg_km=float(r.carbon_g_per_kg_km),
                distance_km=float(r.distance_km),
                as_of=str(r.as_of),
                source=r.source,
            )
            for r in ln_df.itertuples(index=False)
        ]

        t_df = pd.read_csv(d / "tariffs.csv")
        tariffs = [
            TariffSchedule(
                hts_code=r.hts_code,
                origin_country=r.origin_country,
                destination_country=r.destination_country,
                base_duty_rate=float(r.base_duty_rate),
                section_301=float(r.section_301),
                section_232=float(r.section_232),
                adcvd=float(r.adcvd),
                effective_from=_parse_date(r.effective_from),
                source=r.source,
            )
            for r in t_df.itertuples(index=False)
        ]

        fta_df = pd.read_csv(d / "fta.csv")
        ftas = [
            FTARule(
                fta_name=r.fta_name,
                origin_country=r.origin_country,
                destination_country=r.destination_country,
                hts_prefix=r.hts_prefix,
                savings_pct=float(r.savings_pct),
                substantial_transformation_required=bool(r.substantial_transformation_required),
                min_regional_content_pct=float(r.min_regional_content_pct),
                source=r.source,
            )
            for r in fta_df.itertuples(index=False)
        ]

        fx_df = pd.read_csv(d / "fx.csv")
        fx = {
            r.currency: FXRate(
                currency=r.currency,
                usd_per_unit=float(r.usd_per_unit),
                forward_3m=float(r.forward_3m),
                forward_12m=float(r.forward_12m),
                volatility_annual=float(r.volatility_annual),
                as_of=_parse_date(r.as_of),
                source=r.source,
            )
            for r in fx_df.itertuples(index=False)
        }

        y_df = pd.read_csv(d / "yield.csv")
        yields = {
            (r.supplier_id, r.part_id): YieldProfile(
                supplier_id=r.supplier_id,
                part_id=r.part_id,
                first_pass_yield=float(r.first_pass_yield),
                dppm=int(r.dppm),
                warranty_reserve_usd=float(r.warranty_reserve_usd),
                as_of=_parse_date(r.as_of),
                source=r.source,
            )
            for r in y_df.itertuples(index=False)
        }

        c_df = pd.read_csv(d / "carbon.csv")
        carbon = {
            (r.supplier_id, r.part_id): CarbonProfile(
                supplier_id=r.supplier_id,
                part_id=r.part_id,
                scope1_gco2e_per_unit=float(r.scope1_gco2e_per_unit),
                scope2_gco2e_per_unit=float(r.scope2_gco2e_per_unit),
                scope3_gco2e_per_unit=float(r.scope3_gco2e_per_unit),
                recycled_content_pct=float(r.recycled_content_pct),
                renewable_energy_pct=float(r.renewable_energy_pct),
                apple2030_gap_pct=float(r.apple2030_gap_pct),
                as_of=str(r.as_of),
                source=r.source,
            )
            for r in c_df.itertuples(index=False)
        }

        prog_df = pd.read_csv(d / "npi_programs.csv")
        programs = {
            r.id: NPIProgram(
                id=r.id,
                product_name=r.product_name,
                launch_date=_parse_date(r.launch_date),
                target_volume_y1=int(r.target_volume_y1),
                ramp_start=_parse_date(r.ramp_start),
                mp_start=_parse_date(r.mp_start),
                description=r.description,
            )
            for r in prog_df.itertuples(index=False)
        }

        g_df = pd.read_csv(d / "npi_gates.csv")
        gates = [
            NPIGate(
                program_id=r.program_id,
                gate_name=r.gate_name,
                default_offset_weeks_before_launch=int(r.default_offset_weeks_before_launch),
                owner_role=r.owner_role,
                buffer_weeks=int(r.buffer_weeks),
                description=r.description,
            )
            for r in g_df.itertuples(index=False)
        ]

        w_df = pd.read_csv(d / "wages.csv")
        wages = {
            r.country: Wage(
                country=r.country,
                usd_per_hour=float(r.usd_per_hour),
                overhead_multiplier=float(r.overhead_multiplier),
                as_of=_parse_date(r.as_of),
                source=r.source,
            )
            for r in w_df.itertuples(index=False)
        }

        lh_df = pd.read_csv(d / "labor_hours.csv")
        labor = {
            r.part_id: LaborHours(
                part_id=r.part_id,
                direct_labor_hours=float(r.direct_labor_hours),
                overhead_material_multiplier=float(r.overhead_material_multiplier),
                sga_margin_pct=float(r.sga_margin_pct),
                target_margin_pct=float(r.target_margin_pct),
            )
            for r in lh_df.itertuples(index=False)
        }

        return Catalog(
            parts=parts,
            bom=bom,
            suppliers=suppliers,
            sites=sites,
            quotes=quotes,
            lanes=lanes,
            tariffs=tariffs,
            ftas=ftas,
            fx=fx,
            yields=yields,
            carbon=carbon,
            npi_programs=programs,
            npi_gates=gates,
            wages=wages,
            labor=labor,
        )

    def quotes_for(self, part_id: str) -> List[Quote]:
        return [q for q in self.quotes if q.part_id == part_id]

    def tariff_for(
        self, hts_code: str, origin: str, destination: str
    ) -> Optional[TariffSchedule]:
        for t in self.tariffs:
            if (
                t.hts_code == hts_code
                and t.origin_country == origin
                and t.destination_country == destination
            ):
                return t
        return None

    def fta_for(
        self, origin: str, destination: str, hts_code: str
    ) -> Optional[FTARule]:
        for f in self.ftas:
            if f.origin_country != origin or f.destination_country != destination:
                continue
            if f.hts_prefix == "*" or hts_code.startswith(f.hts_prefix):
                return f
        return None

    def lane_for(
        self, origin: str, destination: str, mode: str
    ) -> Optional[LogisticsLane]:
        for ln in self.lanes:
            if (
                ln.origin_country == origin
                and ln.destination_country == destination
                and ln.mode == mode
            ):
                return ln
        return None

    def summary(self) -> Dict[str, int]:
        return {
            "parts": len(self.parts),
            "suppliers": len(self.suppliers),
            "sites": len(self.sites),
            "quotes": len(self.quotes),
            "lanes": len(self.lanes),
            "tariffs": len(self.tariffs),
            "fx": len(self.fx),
            "yields": len(self.yields),
            "carbon": len(self.carbon),
            "npi_programs": len(self.npi_programs),
            "npi_gates": len(self.npi_gates),
        }
