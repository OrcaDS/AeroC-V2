def test_get_city_trends_returns_all_pollutants_with_status(client, trend_dataset):
    response = client.get(f"/api/v1/cities/{trend_dataset['city'].id}/trends?days=7")

    assert response.status_code == 200
    payload = response.json()

    assert payload["city"]["code"] == "MNL"
    assert payload["window"] == {
        "current_start": "2026-07-09T12:00:00Z",
        "current_end": "2026-07-16T12:00:00Z",
        "baseline_start": "2026-07-02T12:00:00Z",
        "baseline_end": "2026-07-09T12:00:00Z",
    }
    assert payload["trends"]["pm2_5"] == {
        "pollutant": "pm2_5",
        "status": "ok",
        "current_average": {"value": 35.0, "unit": "ug/m3"},
        "baseline_average": {"value": 22.5, "unit": "ug/m3"},
        "absolute_change": {"value": 12.5, "unit": "ug/m3"},
        "percent_change": 55.56,
        "direction": "up",
        "current_observation_count": 2,
        "baseline_observation_count": 2,
    }
    assert payload["trends"]["pm10"] == {
        "pollutant": "pm10",
        "status": "ok",
        "current_average": {"value": 33.0, "unit": "ug/m3"},
        "baseline_average": {"value": 31.5, "unit": "ug/m3"},
        "absolute_change": {"value": 1.5, "unit": "ug/m3"},
        "percent_change": 4.76,
        "direction": "flat",
        "current_observation_count": 2,
        "baseline_observation_count": 2,
    }
    assert payload["trends"]["ozone"]["status"] == "insufficient_data"
    assert payload["trends"]["carbon_monoxide"]["status"] == "insufficient_data"


def test_get_city_trends_returns_404_for_missing_city(client):
    response = client.get("/api/v1/cities/999/trends?days=7")

    assert response.status_code == 404
    assert response.json() == {"detail": "City not found"}


def test_get_city_trends_supports_custom_window_length(client, trend_dataset):
    response = client.get(f"/api/v1/cities/{trend_dataset['city'].id}/trends?days=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["window"] == {
        "current_start": "2026-07-13T12:00:00Z",
        "current_end": "2026-07-16T12:00:00Z",
        "baseline_start": "2026-07-10T12:00:00Z",
        "baseline_end": "2026-07-13T12:00:00Z",
    }
    assert payload["trends"]["pm2_5"]["status"] == "insufficient_data"
