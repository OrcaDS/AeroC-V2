"""
Trend domain objects.

Trend analysis is treated as a first-class domain capability. v1 compares two
adjacent time windows of equal length and reports pollutant-level summaries,
including explicit status when the available data is insufficient for a
defensible comparison.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class TrendWindow:
    current_start: datetime
    current_end: datetime
    baseline_start: datetime
    baseline_end: datetime


@dataclass(slots=True, frozen=True)
class TrendValue:
    value: float
    unit: str


@dataclass(slots=True, frozen=True)
class PollutantTrend:
    pollutant: str
    status: str
    current_average: TrendValue | None
    baseline_average: TrendValue | None
    absolute_change: TrendValue | None
    percent_change: float | None
    direction: str | None
    current_observation_count: int
    baseline_observation_count: int


@dataclass(slots=True, frozen=True)
class CityTrendAssessment:
    city: object
    window: TrendWindow
    trends: dict[str, PollutantTrend]
