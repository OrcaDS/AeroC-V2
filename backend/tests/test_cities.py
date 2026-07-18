def test_get_cities_returns_active_cities(client, seeded_city):
    response = client.get("/api/v1/cities")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": seeded_city.id,
            "code": "MNL",
            "timezone": "Asia/Manila",
            "name": "Manila",
            "country": "Philippines",
            "latitude": 14.5995,
            "longitude": 120.9842,
            "active": True,
        }
    ]


def test_get_city_returns_single_city(client, seeded_city):
    response = client.get(f"/api/v1/cities/{seeded_city.id}")

    assert response.status_code == 200
    assert response.json()["code"] == "MNL"
    assert response.json()["timezone"] == "Asia/Manila"


def test_get_city_returns_404_when_missing(client):
    response = client.get("/api/v1/cities/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "City not found"}
