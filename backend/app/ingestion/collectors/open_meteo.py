"""
Collector for Open-Meteo Air Quality API.

Fetches air quality data and normalizes it into AeroC's internal DTO format.
"""

from __future__ import annotations

import logging
import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from threading import Event

import httpx

from app.config.settings import settings
from app.domain.constants import (
    DATA_SOURCE_OPEN_METEO,
    SUPPORTED_POLLUTANTS,
)
from app.dto import CollectedObservation, PollutantReading

logger = logging.getLogger(__name__)


class CollectionCancelledError(RuntimeError):
    """Raised when shutdown cancellation interrupts provider collection."""


class OpenMeteoCollector:
    """
    Fetches air quality observations from Open-Meteo.
    """

    BASE_URL = settings.OPEN_METEO_BASE_URL
    TIMEOUT = settings.OPEN_METEO_TIMEOUT_SECONDS

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_attempts: int | None = None,
        retry_base_seconds: float | None = None,
        retry_max_seconds: float | None = None,
        cancellation_event: Event | None = None,
    ) -> None:
        self.base_url = base_url or self.BASE_URL
        self.timeout_seconds = timeout_seconds or self.TIMEOUT
        self.max_attempts = max_attempts or settings.OPEN_METEO_MAX_ATTEMPTS
        self.retry_base_seconds = (
            settings.OPEN_METEO_RETRY_BASE_SECONDS
            if retry_base_seconds is None
            else retry_base_seconds
        )
        self.retry_max_seconds = (
            settings.OPEN_METEO_RETRY_MAX_SECONDS
            if retry_max_seconds is None
            else retry_max_seconds
        )
        self.cancellation_event = cancellation_event or Event()

    # -------------------------
    # Public API
    # -------------------------
    def fetch(self, latitude: float, longitude: float) -> CollectedObservation:
        """
        Fetch and normalize air quality data for a location.
        """

        params = self._build_params(latitude, longitude)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            for attempt in range(1, self.max_attempts + 1):
                self._raise_if_cancelled()
                try:
                    response = client.get(self.base_url, params=params)
                    response.raise_for_status()
                    return self._normalize(response.json())
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == self.max_attempts:
                        raise
                    self._wait_before_retry(attempt, exc)
                except httpx.HTTPStatusError as exc:
                    if not self._is_transient_status(exc.response.status_code):
                        raise
                    if attempt == self.max_attempts:
                        raise
                    self._wait_before_retry(attempt, exc, exc.response)

        raise RuntimeError("Open-Meteo retry loop exited unexpectedly")

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

    def _wait_before_retry(
        self,
        attempt: int,
        exc: Exception,
        response: httpx.Response | None = None,
    ) -> None:
        delay = min(
            self.retry_max_seconds,
            self.retry_base_seconds * (2 ** (attempt - 1)),
        )
        retry_after = self._retry_after_seconds(response)
        if retry_after is not None:
            delay = min(self.retry_max_seconds, max(delay, retry_after))

        if delay > 0:
            delay = min(self.retry_max_seconds, delay + random.uniform(0, delay * 0.25))

        logger.warning(
            "event=provider_retry provider=open-meteo attempt=%s max_attempts=%s delay_seconds=%.3f error_type=%s",
            attempt,
            self.max_attempts,
            delay,
            type(exc).__name__,
            extra={
                "event": "provider_retry",
                "provider": "open-meteo",
                "attempt": attempt,
                "max_attempts": self.max_attempts,
                "delay_seconds": delay,
                "error_type": type(exc).__name__,
            },
        )

        if self.cancellation_event.wait(delay):
            raise CollectionCancelledError("collection cancelled during provider retry")

    def _raise_if_cancelled(self) -> None:
        if self.cancellation_event.is_set():
            raise CollectionCancelledError("collection cancelled before provider request")

    @staticmethod
    def _is_transient_status(status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code <= 599

    @staticmethod
    def _retry_after_seconds(response: httpx.Response | None) -> float | None:
        if response is None:
            return None
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None
