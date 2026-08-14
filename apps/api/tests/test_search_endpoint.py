from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_search_returns_request_data(monkeypatch) -> None:
    payload = {
        "make": "Honda",
        "model": "Civic",
        "min_year": 2018,
        "max_price": 20000,
        "location": "Chicago, IL",
    }
    mock_response = {
        "data": [
            {
                "vehicle": {"make": "Honda", "model": "Civic"},
                "retailListing": {"price": 19000},
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
    assert response.json() == mock_response


def test_post_search_accepts_empty_request_body(monkeypatch) -> None:
    mock_response = {"data": []}

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
    assert response.json() == mock_response
