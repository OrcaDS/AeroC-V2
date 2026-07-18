from datetime import UTC, datetime

from app.ingestion.collectors.open_meteo import OpenMeteoCollector


def test_collector_requests_and_normalizes_utc_unix_timestamps():
    collector = OpenMeteoCollector()

    params = collector._build_params(14.5995, 120.9842)
    observation = collector._normalize(
        {
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
    )

    assert params["timeformat"] == "unixtime"
    assert "timezone" not in params
    assert observation.observed_at == datetime.fromtimestamp(1_784_347_200, UTC)
    assert observation.observed_at.tzinfo is UTC

