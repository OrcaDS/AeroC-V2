from datetime import UTC, datetime
from threading import Event

import httpx
import pytest

from app.ingestion.collectors.open_meteo import CollectionCancelledError
from app.ingestion.collectors.open_meteo import OpenMeteoCollector


def provider_payload():
    return {
        "hourly": {
            "time": [1_784_347_200],
            "pm2_5": [12.5],
            "pm10": [20.0],
            "carbon_monoxide": [100.0],
            "nitrogen_dioxide": [10.0],
            "sulphur_dioxide": [2.0],
            "ozone": [30.0],
        },
        "hourly_units": {
            "pm2_5": "ug/m3",
            "pm10": "ug/m3",
            "carbon_monoxide": "ug/m3",
            "nitrogen_dioxide": "ug/m3",
            "sulphur_dioxide": "ug/m3",
            "ozone": "ug/m3",
        },
    }


def test_collector_requests_and_normalizes_utc_unix_timestamps():
    collector = OpenMeteoCollector()

    params = collector._build_params(14.5995, 120.9842)
    observation = collector._normalize(
        provider_payload()
    )

    assert params["timeformat"] == "unixtime"
    assert "timezone" not in params
    assert observation.observed_at == datetime.fromtimestamp(1_784_347_200, UTC)
    assert observation.observed_at.tzinfo is UTC


def test_collector_retries_transient_status(monkeypatch):
    request = httpx.Request("GET", OpenMeteoCollector.BASE_URL)
    responses = iter(
        [
            httpx.Response(503, request=request),
            httpx.Response(200, request=request, json=provider_payload()),
        ]
    )
    calls = []

    def fake_get(self, url, params):
        calls.append(url)
        return next(responses)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    collector = OpenMeteoCollector(max_attempts=2, retry_base_seconds=0)

    result = collector.fetch(14.5995, 120.9842)

    assert result.source == "open-meteo"
    assert len(calls) == 2


def test_collector_does_not_retry_permanent_client_error(monkeypatch):
    request = httpx.Request("GET", OpenMeteoCollector.BASE_URL)
    calls = []

    def fake_get(self, url, params):
        calls.append(url)
        return httpx.Response(400, request=request)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    collector = OpenMeteoCollector(max_attempts=3, retry_base_seconds=0)

    with pytest.raises(httpx.HTTPStatusError):
        collector.fetch(14.5995, 120.9842)

    assert len(calls) == 1


def test_collector_honors_cooperative_cancellation():
    cancellation = Event()
    cancellation.set()
    collector = OpenMeteoCollector(cancellation_event=cancellation)

    with pytest.raises(CollectionCancelledError):
        collector.fetch(14.5995, 120.9842)
