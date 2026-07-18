from datetime import datetime


def test_get_dashboard_returns_product_summary(client, dashboard_dataset):
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    payload = response.json()

    assert datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
    assert payload["summary"] == {
        "cities_monitored": 3,
        "cities_with_current_data": 2,
        "last_observed_at": "2026-07-16T12:00:00Z",
        "average_pm2_5": {"value": 30.0, "unit": "ug/m3"},
        "average_pm10": {"value": 35.0, "unit": "ug/m3"},
    }
    assert payload["leaders"] == {
        "highest_pm2_5": {
            "city_id": dashboard_dataset["quezon_city"].id,
            "city_name": "Quezon City",
            "value": 35.0,
            "unit": "ug/m3",
            "observed_at": "2026-07-16T12:00:00Z",
        },
        "highest_pm10": {
            "city_id": dashboard_dataset["manila"].id,
            "city_name": "Manila",
            "value": 40.0,
            "unit": "ug/m3",
            "observed_at": "2026-07-16T11:00:00Z",
        },
        "highest_ozone": {
            "city_id": dashboard_dataset["quezon_city"].id,
            "city_name": "Quezon City",
            "value": 150.0,
            "unit": "ug/m3",
            "observed_at": "2026-07-16T12:00:00Z",
        },
        "highest_aqi": {
            "city_id": dashboard_dataset["quezon_city"].id,
            "city_name": "Quezon City",
            "observed_at": "2026-07-16T12:00:00Z",
                "aqi": {
                    "standard": "epa_us",
                    "estimated": True,
                    "limitations": [
                        "Derived from available PM2.5 and PM10 model observations.",
                        "Not an official EPA AQI.",
                        "Does not apply EPA-required 24-hour or NowCast averaging.",
                        "Does not include gaseous pollutant sub-indices.",
                    ],
                    "value": 99,
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
                            "value": 99,
                            "category": {
                            "code": "moderate",
                            "label": "Moderate",
                            "color": "#FFFF00",
                        },
                    },
                        "pm10": {
                            "pollutant": "pm10",
                            "value": 28,
                            "category": {
                                "code": "good",
                                "label": "Good",
                                "color": "#00E400",
                            },
                        },
                    },
                },
            },
        }

    cities = {entry["city"]["code"]: entry for entry in payload["cities"]}
    assert cities["MNL"]["latest"]["pollutants"]["pm2_5"]["value"] == 25.0
    assert cities["QC"]["latest"]["pollutants"]["ozone"]["value"] == 150.0
    assert cities["MNL"]["latest"]["aqi"]["value"] == 81
    assert cities["QC"]["latest"]["aqi"]["value"] == 99
    assert cities["CEB"]["latest"] is None


def test_get_dashboard_handles_empty_network(client):
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"] == {
        "cities_monitored": 0,
        "cities_with_current_data": 0,
        "last_observed_at": None,
        "average_pm2_5": {"value": None, "unit": None},
        "average_pm10": {"value": None, "unit": None},
    }
    assert payload["leaders"] == {
        "highest_pm2_5": None,
        "highest_pm10": None,
        "highest_ozone": None,
        "highest_aqi": None,
    }
    assert payload["cities"] == []
