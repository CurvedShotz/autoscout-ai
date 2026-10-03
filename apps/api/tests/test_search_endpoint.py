import pytest
from fastapi.testclient import TestClient

from app.models import (
    AIRankedListing,
    AIRankingResult,
    ListingRiskAssessment,
    ListingRiskLevel,
)
from app.services.location_resolver import (
    AmbiguousLocationError,
    LocationResolver,
    LocationResolverUnavailable,
    ResolvedLocation,
)
from app.main import app

client = TestClient(app)


class FakeRiskAnalyzer:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.listing_vins = []
        self.call_count = 0

    def analyze(self, listings):
        self.call_count += 1
        if self.error:
            raise self.error
        self.listing_vins = [listing.vin for listing in listings]
        return [
            ListingRiskAssessment(
                vin=listing.vin,
                risk_score=80 if listing.vin == "VIN-TOYOTA" else 10,
                risk_level=(
                    ListingRiskLevel.HIGH
                    if listing.vin == "VIN-TOYOTA"
                    else ListingRiskLevel.LOW
                ),
                signals=["Unusually low price"] if listing.vin == "VIN-TOYOTA" else [],
                explanation=(
                    "The listed price is unusually low compared with peer listings."
                    if listing.vin == "VIN-TOYOTA"
                    else "No unusual evidence in the available listing data."
                ),
            )
            for listing in listings
        ]


def test_post_search_returns_normalized_listing_data(monkeypatch) -> None:
    payload = {
        "make": "Honda",
        "model": "Civic",
        "min_year": 2018,
        "max_price": 20000,
        "location": "75001",
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

    def fake_search_listings(self, *, make, model, body_style, min_year, max_year, min_price, max_price, min_mileage, max_mileage, location, limit):
        assert make == payload["make"]
        assert model == payload["model"]
        assert body_style is None
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
    risk_analyzer = FakeRiskAnalyzer()
    monkeypatch.setattr(
        "app.api.routes.search.get_listing_risk_analyzer",
        lambda: risk_analyzer,
    )

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
    assert data[0]["risk"]["vin"] == "VIN-TOYOTA"
    assert data[0]["risk"]["risk_score"] == 80
    assert data[0]["score"] == 91
    assert data[1]["listing"]["vin"] == "VIN-HONDA"
    assert data[1]["listing"]["listing_url"] == "https://example.test/civic"
    assert data[1]["risk"]["vin"] == "VIN-HONDA"
    assert data[1]["risk"]["risk_score"] == 10
    assert data[1]["score"] == 87
    assert risk_analyzer.listing_vins == ["VIN-HONDA", "VIN-TOYOTA"]


def test_post_search_accepts_empty_request_body(monkeypatch) -> None:
    mock_response = {"listings": [], "discover": {}, "actions": {}}

    def fake_search_listings(self, *, make, model, body_style, min_year, max_year, min_price, max_price, min_mileage, max_mileage, location, limit):
        assert make is None
        assert model is None
        assert body_style is None
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
    risk_analyzer = FakeRiskAnalyzer()
    monkeypatch.setattr(
        "app.api.routes.search.get_listing_risk_analyzer",
        lambda: risk_analyzer,
    )
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: (_ for _ in ()).throw(AssertionError("ranking must be skipped for empty results")),
    )

    response = client.post("/search", json={})

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert risk_analyzer.listing_vins == []
    assert risk_analyzer.call_count == 0


def test_post_search_returns_success_for_empty_provider_data(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.search.AutoDevClient.search_listings",
        lambda self, **kwargs: {"data": []},
    )
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: (_ for _ in ()).throw(
            AssertionError("ranking must be skipped for empty results")
        ),
    )
    risk_analyzer = FakeRiskAnalyzer()
    monkeypatch.setattr(
        "app.api.routes.search.get_listing_risk_analyzer",
        lambda: risk_analyzer,
    )

    response = client.post("/search", json={"max_price": 500})

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert risk_analyzer.call_count == 0


def test_post_search_maps_malformed_provider_response_to_sanitized_502(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.search.AutoDevClient.search_listings",
        lambda self, **kwargs: {"data": None},
    )

    response = client.post("/search", json={"max_price": 500})

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream listing service request failed"}


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


def test_post_search_returns_clean_error_when_risk_analysis_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.search.AutoDevClient.search_listings",
        lambda self, **kwargs: {
            "data": [
                {
                    "vehicle": {"vin": "VIN-HONDA", "make": "Honda", "model": "Civic"},
                    "retailListing": {"price": 19000},
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: type(
            "RankingService",
            (),
            {
                "rank_listings": lambda self, request, listings: AIRankingResult(
                    rankings=[
                        AIRankedListing(
                            vin="VIN-HONDA",
                            score=90,
                            rank=1,
                            reason="Strong match",
                        )
                    ]
                )
            },
        )(),
    )
    monkeypatch.setattr(
        "app.api.routes.search.get_listing_risk_analyzer",
        lambda: FakeRiskAnalyzer(RuntimeError("Gemini credentials/details")),
    )

    response = client.post("/search", json={})

    assert response.status_code == 502
    assert response.json() == {"detail": "Listing risk analysis failed"}


def test_post_search_preserves_upstream_failure_behavior(monkeypatch) -> None:
    def fail_search_listings(self, **kwargs):
        raise RuntimeError("upstream details must not leak")

    monkeypatch.setattr("app.api.routes.search.AutoDevClient.search_listings", fail_search_listings)

    response = client.post("/search", json={})

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream listing service request failed"}


def test_post_search_resolves_city_before_provider_request(monkeypatch) -> None:
    class DallasResolver(LocationResolver):
        def resolve(self, location):
            assert location == "Dallas"
            return ResolvedLocation(
                original_query=location,
                city="Dallas",
                state="TX",
                zip="75201",
            )

    captured = {}

    def fake_search_listings(self, **kwargs):
        captured.update(kwargs)
        return {"data": []}

    monkeypatch.setattr(
        "app.api.routes.search.get_location_resolver",
        lambda: DallasResolver(),
    )
    monkeypatch.setattr(
        "app.api.routes.search.AutoDevClient.search_listings",
        fake_search_listings,
    )
    monkeypatch.setattr(
        "app.api.routes.search.get_ranking_service",
        lambda: (_ for _ in ()).throw(AssertionError("ranking must be skipped")),
    )

    response = client.post(
        "/search",
        json={
            "make": "Toyota",
            "model": "Camry",
            "max_price": 20_000,
            "location": "Dallas",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert captured["location"] == "75201"
    assert captured["distance"] == 50
    assert captured["make"] == "Toyota"
    assert captured["model"] == "Camry"
    assert captured["max_price"] == 20_000


@pytest.mark.parametrize(
    ("resolver_error", "expected_status", "expected_detail"),
    [
        (
            AmbiguousLocationError("ambiguous"),
            422,
            "Location could not be resolved unambiguously",
        ),
        (
            LocationResolverUnavailable("private geocoder response"),
            502,
            "Location resolution service unavailable",
        ),
    ],
)
def test_post_search_sanitizes_location_resolution_errors(
    monkeypatch,
    resolver_error,
    expected_status,
    expected_detail,
) -> None:
    class FailedResolver(LocationResolver):
        def resolve(self, _location):
            raise resolver_error

    monkeypatch.setattr(
        "app.api.routes.search.get_location_resolver",
        lambda: FailedResolver(),
    )
    monkeypatch.setattr(
        "app.api.routes.search.AutoDevClient.search_listings",
        lambda *_args, **_kwargs: pytest.fail(
            "provider must not be called when location resolution fails"
        ),
    )

    response = client.post("/search", json={"location": "Springfield"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


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
