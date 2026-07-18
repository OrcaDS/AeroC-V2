"""
Internal DTOs used during the data collection pipeline.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class PollutantReading:
    """
    Represents a single pollutant measurement.
    """

    value: float | None
    unit: str


@dataclass(slots=True, frozen=True)
class CollectedObservation:
    """
    Normalized observation returned by collectors.

    This DTO is independent of any external provider or database model.
    """

    source: str
    observed_at: datetime
    values: dict[str, PollutantReading]