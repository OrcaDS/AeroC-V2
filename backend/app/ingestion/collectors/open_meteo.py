"""
Collector for Open-Meteo Air Quality API.

Fetches air quality data and normalizes it into AeroC's internal DTO format.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.domain.constants import (
    DATA_SOURCE_OPEN_METEO,
    HTTP_TIMEOUT_SECONDS,
    SUPPORTED_POLLUTANTS,
)
from app.dto import CollectedObservation, PollutantReading


class OpenMeteoCollector:
    """
    Fetches air quality observations from Open-Meteo.
    """

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    TIMEOUT = HTTP_TIMEOUT_SECONDS

    # -------------------------
    # Public API
    # -------------------------
    def fetch(self, latitude: float, longitude: float) -> CollectedObservation:
        """
        Fetch and normalize air quality data for a location.
        """

        params = self._build_params(latitude, longitude)

        with httpx.Client(timeout=self.TIMEOUT) as client:
            response = client.get(self.BASE_URL, params=params)

        response.raise_for_status()
        payload = response.json()

        return self._normalize(payload)

    # -------------------------
    # Internal helpers
    # -------------------------
    def _build_params(self, latitude: float, longitude: float) -> dict:
        """
        Build Open-Meteo API query parameters.
        """

        return {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(SUPPORTED_POLLUTANTS),
            "timeformat": "unixtime",
            "forecast_hours": 1,
        }

    def _normalize(self, payload: dict) -> CollectedObservation:
        """
        Convert Open-Meteo JSON into AeroC DTO.
        """

        hourly = payload["hourly"]
        units = payload["hourly_units"]

        # We only requested 1 hour
        timestamp = hourly["time"][0]
        observed_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        values: dict[str, PollutantReading] = {}

        for pollutant in SUPPORTED_POLLUTANTS:
            values[pollutant] = PollutantReading(
                value=hourly[pollutant][0],
                unit=units[pollutant],
            )

        return CollectedObservation(
            source=DATA_SOURCE_OPEN_METEO,
            observed_at=observed_at,
            values=values,
        )
