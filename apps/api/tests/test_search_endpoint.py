from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_search_returns_request_data() -> None:
    payload = {
        "make": "Honda",
        "model": "Civic",
        "min_year": 2018,
        "max_price": 20000,
        "location": "Chicago, IL",
    }

    response = client.post("/search", json=payload)

    assert response.status_code == 200
    assert response.json() == payload


def test_post_search_accepts_empty_request_body() -> None:
    response = client.post("/search", json={})

    assert response.status_code == 200
    assert response.json() == {}
