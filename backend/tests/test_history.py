def test_get_city_history_returns_time_ordered_snapshots(client, city_with_history):
    response = client.get(f"/api/v1/cities/{city_with_history.id}/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"]["code"] == "MNL"
    assert [item["observed_at"] for item in payload["observations"]] == [
        "2026-07-15T12:00:00Z",
        "2026-07-16T12:00:00Z",
    ]
    assert payload["observations"][0]["pollutants"]["pm2_5"]["value"] == 20.0
    assert payload["observations"][1]["pollutants"]["pm10"]["value"] == 38.2


def test_get_city_history_filters_by_date_range(client, city_with_history):
    response = client.get(
        f"/api/v1/cities/{city_with_history.id}/history?from=2026-07-16T00:00:00Z"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["observations"]) == 1
    assert payload["observations"][0]["observed_at"] == "2026-07-16T12:00:00Z"


def test_get_city_history_filters_by_pollutant(client, city_with_history):
    response = client.get(
        f"/api/v1/cities/{city_with_history.id}/history?pollutant=pm2_5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["observations"]) == 2
    assert payload["observations"][0]["pollutants"] == {
        "pm2_5": {"value": 20.0, "unit": "ug/m3"}
    }
    assert payload["observations"][1]["pollutants"] == {
        "pm2_5": {"value": 24.5, "unit": "ug/m3"}
    }


def test_get_city_history_returns_404_when_city_missing(client):
    response = client.get("/api/v1/cities/999/history")

    assert response.status_code == 404
    assert response.json() == {"detail": "City not found"}


def test_get_city_history_rejects_unsupported_pollutant(client, city_with_history):
    response = client.get(
        f"/api/v1/cities/{city_with_history.id}/history?pollutant=lead"
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported pollutant"}
