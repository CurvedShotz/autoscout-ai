from fastapi.testclient import TestClient

from app.models import AIRankedListing, AIRankingResult
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
                "vehicle": {"vin": "VIN-HONDA", "make": "Honda", "model": "Civic"},
                "retailListing": {
                    "price": 19000,
                    "miles": 12000,
                    "vdp": "https://example.test/civic",
                },
                "history": {"accidents": False},
            },
            {
                "vehicle": {"vin": "VIN-TOYOTA", "make": "Toyota", "model": "Camry"},
                "retailListing": {"price": 21000, "miles": 15000},
                "history": {"accidents": False},
            },
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

    class FakeRankingService:
        def rank_listings(self, search_request, listings):
            assert search_request.make == "Honda"
            assert [listing.vin for listing in listings] == ["VIN-HONDA", "VIN-TOYOTA"]
            return AIRankingResult(
                rankings=[
                    AIRankedListing(
                        vin="VIN-TOYOTA", score=91, rank=1, reason="Lower mileage value"
                    ),
                    AIRankedListing(
                        vin="VIN-HONDA", score=87, rank=2, reason="Matches requested model"
                    ),
                ]
            )

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fake_search_listings)
    monkeypatch.setattr("app.api.routes.search.get_ranking_service", lambda: FakeRankingService())

    response = client.post("/search", json=payload)

    assert response.status_code == 200
    data = response.json()["data"]
    assert [(item["rank"], item["score"], item["reason"]) for item in data] == [
        (1, 91.0, "Lower mileage value"),
        (2, 87.0, "Matches requested model"),
    ]
    assert data[0]["listing"]["vin"] == "VIN-TOYOTA"
    assert data[0]["listing"]["make"] == "Toyota"
    assert data[0]["listing"]["price"] == 21000
    assert data[1]["listing"]["vin"] == "VIN-HONDA"
    assert data[1]["listing"]["listing_url"] == "https://example.test/civic"


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
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: (_ for _ in ()).throw(AssertionError("ranking must be skipped for empty results")),
    )

    response = client.post("/search", json={})

    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_post_search_returns_clean_error_when_ranking_fails(monkeypatch) -> None:
    def fake_search_listings(self, **kwargs):
        return {
            "data": [
                {
                    "vehicle": {"vin": "VIN-HONDA", "make": "Honda", "model": "Civic"},
                    "retailListing": {"price": 19000},
                }
            ]
        }

    class BrokenRankingService:
        def rank_listings(self, search_request, listings):
            raise RuntimeError("provider internals must not leak")

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fake_search_listings)
    monkeypatch.setattr("app.api.routes.search.get_ranking_service", lambda: BrokenRankingService())

    response = client.post("/search", json={})

    assert response.status_code == 502
    assert response.json() == {"detail": "AI ranking service request failed"}


def test_post_search_preserves_upstream_failure_behavior(monkeypatch) -> None:
    def fail_search_listings(self, **kwargs):
        raise RuntimeError("upstream details must not leak")

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fail_search_listings)

    response = client.post("/search", json={})

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream listing service request failed"}


def test_post_search_returns_predictable_error_for_invalid_provider(monkeypatch) -> None:
    def fake_search_listings(self, **kwargs):
        return {
            "data": [
                {"vehicle": {"vin": "VIN-HONDA", "make": "Honda"}},
            ]
        }

    from app.services.ranking_provider import UnsupportedRankingProviderError

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fake_search_listings)
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: (_ for _ in ()).throw(UnsupportedRankingProviderError("internal provider name")),
    )

    response = client.post("/search", json={})

    assert response.status_code == 500
    assert response.json() == {"detail": "Unsupported AI ranking provider configured"}
