"""
AQI domain objects.

AQI is treated as a first-class domain concept rather than a loose computed
field. The v1 implementation follows the U.S. EPA AQI category system, but it
currently computes sub-indices only for PM2.5 and PM10 because the current
Open-Meteo ingestion model persists gases in units that do not cleanly match
the EPA breakpoint tables used for ozone, CO, NO2, and SO2.
"""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AqiCategory:
    code: str
    label: str
    color: str


@dataclass(slots=True, frozen=True)
class AqiSubIndex:
    pollutant: str
    value: int
    category: AqiCategory


@dataclass(slots=True, frozen=True)
class AqiAssessment:
    standard: str
    estimated: bool
    limitations: tuple[str, ...]
    value: int | None
    category: AqiCategory | None
    primary_pollutant: str | None
    computed_pollutants: tuple[str, ...]
    sub_indices: dict[str, AqiSubIndex]
