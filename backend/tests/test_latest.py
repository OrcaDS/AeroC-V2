def test_get_latest_city_observation_returns_dashboard_shape(client, city_with_observation):
    response = client.get(f"/api/v1/cities/{city_with_observation.id}/latest")

    assert response.status_code == 200
    assert response.json() == {
        "city": {
            "id": city_with_observation.id,
            "code": "MNL",
            "timezone": "Asia/Manila",
            "name": "Manila",
            "country": "Philippines",
            "latitude": 14.5995,
            "longitude": 120.9842,
            "active": True,
        },
        "source": "open-meteo",
        "observed_at": "2026-07-16T12:00:00Z",
        "collected_at": "2026-07-16T12:05:00Z",
        "pollutants": {
            "pm2_5": {"value": 24.5, "unit": "ug/m3"},
            "pm10": {"value": 38.2, "unit": "ug/m3"},
        },
        "aqi": {
            "standard": "epa_us",
            "estimated": True,
            "limitations": [
                "Derived from available PM2.5 and PM10 model observations.",
                "Not an official EPA AQI.",
                "Does not apply EPA-required 24-hour or NowCast averaging.",
                "Does not include gaseous pollutant sub-indices.",
            ],
            "value": 80,
            "category": {
                "code": "moderate",
                "label": "Moderate",
                "color": "#FFFF00",
            },
            "primary_pollutant": "pm2_5",
            "computed_pollutants": ["pm2_5", "pm10"],
            "sub_indices": {
                "pm2_5": {
                    "pollutant": "pm2_5",
                    "value": 80,
                    "category": {
                        "code": "moderate",
                        "label": "Moderate",
                        "color": "#FFFF00",
                    },
                },
                "pm10": {
                    "pollutant": "pm10",
                    "value": 35,
                    "category": {
                        "code": "good",
                        "label": "Good",
                        "color": "#00E400",
                    },
                },
            },
        },
    }


def test_get_latest_city_observation_returns_404_when_city_missing(client):
    response = client.get("/api/v1/cities/999/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "City not found"}


def test_get_latest_city_observation_returns_404_when_city_has_no_observations(client, seeded_city):
    response = client.get(f"/api/v1/cities/{seeded_city.id}/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "No observations found for this city"}
