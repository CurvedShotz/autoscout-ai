from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_search_returns_normalized_listing_data(monkeypatch) -> None:
    payload = {
        "make": "Honda",
        "model": "Civic",
        "min_year": 2018,
        "max_price": 20000,
        "location": "Chicago, IL",
    }
    mock_response = {
        "api": {"version": "v2"},
        "links": {"self": "https://example.test/search"},
        "data": [
            {
                "vehicle": {"make": "Honda", "model": "Civic"},
                "retailListing": {
                    "price": 19000,
                    "miles": 12000,
                    "vdp": "https://example.test/civic",
                },
                "history": {"accidents": False},
            }
        ]
    }

    def fake_search_listings(self, *, make, model, min_year, max_year, min_price, max_price, min_mileage, max_mileage, location, limit):
        assert make == payload["make"]
        assert model == payload["model"]
        assert min_year == payload["min_year"]
        assert max_year is None
        assert min_price is None
        assert max_price == payload["max_price"]
        assert min_mileage is None
        assert max_mileage is None
        assert location == payload["location"]
        assert limit == 10
        return mock_response

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fake_search_listings)

    response = client.post("/search", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "vin": None,
                "year": None,
                "make": "Honda",
                "model": "Civic",
                "trim": None,
                "body_style": None,
                "drivetrain": None,
                "engine": None,
                "transmission": None,
                "exterior_color": None,
                "fuel": None,
                "price": 19000,
                "mileage": 12000,
                "city": None,
                "state": None,
                "zip": None,
                "dealer": None,
                "primary_image": None,
                "listing_url": "https://example.test/civic",
                "carfax_url": None,
                "accident_count": None,
                "has_accidents": False,
                "owner_count": None,
                "one_owner": None,
                "usage_type": None,
                "created_at": None,
            }
        ]
    }


def test_post_search_accepts_empty_request_body(monkeypatch) -> None:
    mock_response = {"listings": [], "discover": {}, "actions": {}}

    def fake_search_listings(self, *, make, model, min_year, max_year, min_price, max_price, min_mileage, max_mileage, location, limit):
        assert make is None
        assert model is None
        assert min_year is None
        assert max_year is None
        assert min_price is None
        assert max_price is None
        assert min_mileage is None
        assert max_mileage is None
        assert location is None
        assert limit == 10
        return mock_response

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fake_search_listings)

    response = client.post("/search", json={})

    assert response.status_code == 200
    assert response.json() == {"data": []}
