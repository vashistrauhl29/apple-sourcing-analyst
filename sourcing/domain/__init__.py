"""Immutable domain dataclasses. No business logic, no IO."""
from sourcing.domain.part import Part, BOMLine
from sourcing.domain.supplier import Supplier, SupplierSite
from sourcing.domain.quote import Quote, YieldProfile
from sourcing.domain.logistics import LogisticsLane
from sourcing.domain.tariff import TariffSchedule, FTARule
from sourcing.domain.fx import FXRate
from sourcing.domain.npi import NPIGate, NPIProgram
from sourcing.domain.sustainability import CarbonProfile

__all__ = [
    "Part",
    "BOMLine",
    "Supplier",
    "SupplierSite",
    "Quote",
    "YieldProfile",
    "LogisticsLane",
    "TariffSchedule",
    "FTARule",
    "FXRate",
    "NPIGate",
    "NPIProgram",
    "CarbonProfile",
]
