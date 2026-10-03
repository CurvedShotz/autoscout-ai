import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    AIRankedListing,
    AIRankingResult,
    ListingRiskAssessment,
    ListingRiskLevel,
    SearchRankingContext,
    SearchRequest,
    UserSearchIntent,
)
from app.services.natural_search import NaturalSearchService
from app.services.natural_search import (
    NaturalSearchLocationError,
    NaturalSearchLocationProviderError,
    NaturalSearchRiskError,
)
from app.services.location_resolver import (
    LocationResolutionError,
    LocationResolver,
    LocationResolverUnavailable,
    ResolvedLocation,
)
from app.services.ranking import AIRankingService, ranking_input
from app.services.search_planner import SearchPlanner
from app.services.search_query_parser import SearchQueryParser

client = TestClient(app)


def provider_listing(
    vin: str,
    *,
    make: str = "Toyota",
    model: str = "Camry",
    price: int = 18_000,
    mileage: int = 40_000,
    body_style: str | None = None,
) -> dict:
    return {
        "vehicle": {
            "vin": vin,
            "year": 2021,
            "make": make,
            "model": model,
            "bodyStyle": body_style,
        },
        "retailListing": {"price": price, "miles": mileage},
    }


class FakeParser(SearchQueryParser):
    def __init__(self, intent: UserSearchIntent | None = None, error: Exception | None = None):
        self.intent = intent or UserSearchIntent(search_request=SearchRequest())
        self.error = error
        self.queries: list[str] = []

    def parse(self, query: str) -> UserSearchIntent:
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.intent


class FakeLocationResolver(LocationResolver):
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[str | None] = []

    def resolve(self, location: str | None) -> ResolvedLocation | None:
        self.calls.append(location)
        if self.error:
            raise self.error
        if location is None:
            return None
        if location.isdigit() and len(location) == 5:
            return ResolvedLocation(original_query=location, zip=location)
        city = location.split(",", maxsplit=1)[0]
        return ResolvedLocation(
            original_query=location,
            city=city,
            state="TX",
            zip="75201",
        )


class FakeAutoDevClient:
    def __init__(self, responses: list[object]):
        self.responses = responses
        self.calls: list[dict] = []

    def search_listings(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses[len(self.calls) - 1]
        if isinstance(response, Exception):
            raise response
        return response


class FakeRankingService(AIRankingService):
    def __init__(self, error: Exception | None = None):
        self.context: SearchRankingContext | None = None
        self.vins: list[str | None] = []
        self.error = error

    def rank_listings(self, search_context, listings):
        if self.error:
            raise self.error
        assert isinstance(search_context, SearchRankingContext)
        self.context = search_context
        self.vins = [listing.vin for listing in listings]
        rankings = [
            AIRankedListing(
                vin=listing.vin,
                score=90 if listing.vin == "VIN-DUP" else 35,
                rank=index,
                reason="Good match",
            )
            for index, listing in enumerate(listings, start=1)
            if listing.vin
        ]
        return AIRankingResult(rankings=rankings)


class FakeRiskAnalyzer:
    def __init__(self, error: Exception | None = None):
        self.vins: list[str | None] = []
        self.error = error
        self.call_count = 0

    def analyze(self, listings):
        self.call_count += 1
        if self.error:
            raise self.error
        self.vins = [listing.vin for listing in listings]
        return [
            ListingRiskAssessment(
                vin=listing.vin,
                risk_score=85 if listing.vin == "VIN-DUP" else 5,
                risk_level=(
                    ListingRiskLevel.HIGH
                    if listing.vin == "VIN-DUP"
                    else ListingRiskLevel.LOW
                ),
                signals=["Unusually low price"] if listing.vin == "VIN-DUP" else [],
                explanation=(
                    "Price is an outlier compared with peers."
                    if listing.vin == "VIN-DUP"
                    else "No unusual evidence in available listing data."
                ),
            )
            for listing in listings
        ]


def build_service(
    intent: UserSearchIntent,
    responses: list[object],
    *,
    parser_error: Exception | None = None,
    ranking_error: Exception | None = None,
    risk_error: Exception | None = None,
    planner: SearchPlanner | None = None,
    location_resolver: LocationResolver | None = None,
) -> tuple[
    NaturalSearchService,
    FakeParser,
    FakeAutoDevClient,
    FakeRankingService,
    FakeRiskAnalyzer,
]:
    parser = FakeParser(intent, parser_error)
    auto_dev = FakeAutoDevClient(responses)
    ranking = FakeRankingService(ranking_error)
    risk_analyzer = FakeRiskAnalyzer(risk_error)
    service = NaturalSearchService(
        parser=parser,
        planner=planner or SearchPlanner(),
        auto_dev_client=auto_dev,
        location_resolver=location_resolver or FakeLocationResolver(),
        ranking_service=ranking,
        risk_analyzer=risk_analyzer,
    )
    return service, parser, auto_dev, ranking, risk_analyzer


def test_simple_natural_query_runs_full_flow_once() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(
            make="Toyota",
            model="Camry",
            location="Dallas",
            max_price=20_000,
        )
    )
    service, parser, auto_dev, ranking, risk_analyzer = build_service(
        intent,
        [{"data": [provider_listing("VIN-1")]}],
    )

    result = service.search("Find me a Toyota Camry near Dallas under $20k")

    assert parser.queries == ["Find me a Toyota Camry near Dallas under $20k"]
    assert result.planned_requests == [
        intent.search_request.model_copy(update={"location": "75201"})
    ]
    assert len(auto_dev.calls) == 1
    assert auto_dev.calls[0]["make"] == "Toyota"
    assert auto_dev.calls[0]["model"] == "Camry"
    assert auto_dev.calls[0]["location"] == "75201"
    assert auto_dev.calls[0]["distance"] == 50
    assert len(result.listings) == 1
    assert result.ranked_listings[0].listing.vin == "VIN-1"
    assert result.ranked_listings[0].risk.vin == "VIN-1"
    assert risk_analyzer.vins == ["VIN-1"]
    assert risk_analyzer.call_count == 1
    assert ranking.context is not None
    assert ranking.context.search_request == intent.search_request


def test_natural_search_resolves_city_before_provider_and_keeps_filters() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(
            make="Toyota",
            model="Camry",
            max_price=20_000,
            location="Dallas",
        )
    )
    service, _, auto_dev, _, _ = build_service(
        intent,
        [{"data": []}],
    )

    service.search("Find me a Toyota Camry near Dallas under $20k")

    assert auto_dev.calls[0] == {
        "make": "Toyota",
        "model": "Camry",
        "body_style": None,
        "min_year": None,
        "max_year": None,
        "min_price": None,
        "max_price": 20_000,
        "min_mileage": None,
        "max_mileage": None,
        "location": "75201",
        "distance": 50,
        "limit": 10,
    }


@pytest.mark.parametrize(
    ("resolver_error", "expected_error"),
    [
        (LocationResolutionError("ambiguous"), NaturalSearchLocationError),
        (LocationResolverUnavailable("sensitive upstream text"), NaturalSearchLocationProviderError),
    ],
)
def test_natural_location_resolution_failures_are_classified(
    resolver_error: Exception,
    expected_error: type[Exception],
) -> None:
    service, _, auto_dev, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest(location="Springfield")),
        [],
        location_resolver=FakeLocationResolver(resolver_error),
    )

    with pytest.raises(expected_error) as exc_info:
        service.search("Find a car near Springfield")

    assert "sensitive upstream text" not in str(exc_info.value)
    assert auto_dev.calls == []


def test_alternative_makes_merge_listings_and_pass_soft_intent_to_ranking() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_price=None),
        makes=["Honda", "Toyota"],
        target_price=15_000,
        preferences=["reliable"],
    )
    service, _, auto_dev, ranking, risk_analyzer = build_service(
        intent,
        [
            {"data": [provider_listing("VIN-DUP", make="Honda", price=14_500)]},
            {
                "data": [
                    provider_listing("vin-dup", make="Toyota", price=13_500),
                    provider_listing("VIN-2", make="Toyota"),
                ]
            },
        ],
    )

    result = service.search("I want a reliable Honda or Toyota around $15,000")

    assert [call["make"] for call in auto_dev.calls] == ["Honda", "Toyota"]
    assert len(result.listings) == 2
    assert result.listings[0].make == "Honda"
    assert [item.listing.vin for item in result.ranked_listings] == ["VIN-DUP", "VIN-2"]
    assert [item.risk.vin for item in result.ranked_listings] == ["VIN-DUP", "VIN-2"]
    assert risk_analyzer.vins == ["VIN-DUP", "VIN-2"]
    assert result.ranked_listings[0].score == 90
    assert result.ranked_listings[0].risk.risk_score == 85
    assert result.ranked_listings[1].score == 35
    assert result.ranked_listings[1].risk.risk_score == 5
    assert ranking.context is not None
    assert ranking.context.preferences == ["reliable"]
    assert ranking.context.target_price == 15_000
    assert ranking.context.makes == ["Honda", "Toyota"]


def test_semantic_body_style_and_hard_mileage_reach_correct_layers() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_mileage=60_000),
        body_styles=["sedan"],
        preferences=["sporty"],
    )
    service, _, auto_dev, ranking, _ = build_service(
        intent,
        [{"data": [provider_listing("VIN-1", body_style="Sedan")]}],
    )

    service.search("Show me a sporty sedan under 60k miles")

    assert auto_dev.calls[0]["max_mileage"] == 60_000
    assert auto_dev.calls[0]["body_style"] == "sedan"
    assert ranking.context is not None
    assert ranking.context.preferences == ["sporty"]
    assert ranking.context.body_styles == ["sedan"]


def test_ranking_payload_keeps_structured_shape_and_adds_separate_soft_intent() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_mileage=60_000),
        makes=["Honda", "Toyota"],
        body_styles=["sedan"],
        target_price=15_000,
        preferences=["reliable"],
    )
    structured_payload = ranking_input(SearchRequest(max_price=20_000), [])
    natural_payload = ranking_input(
        SearchRankingContext.from_intent(intent),
        [],
    )

    assert set(structured_payload[0]) == {"search_request", "candidate_listings"}
    assert natural_payload[0]["search_request"]["max_mileage"] == 60_000
    assert "target_price" not in natural_payload[0]["search_request"]
    assert natural_payload[0]["semantic_intent"] == {
        "makes": ["Honda", "Toyota"],
        "models": [],
        "body_styles": ["sedan"],
        "target_price": 15_000,
        "target_mileage": None,
        "preferences": ["reliable"],
    }


def test_empty_merged_results_skip_ranking() -> None:
    intent = UserSearchIntent(search_request=SearchRequest(make="Honda"))
    service, _, _, ranking, risk_analyzer = build_service(intent, [{"data": []}])

    result = service.search("Honda")

    assert result.listings == []
    assert result.ranked_listings == []
    assert ranking.context is None
    assert risk_analyzer.vins == []
    assert risk_analyzer.call_count == 0


def test_natural_endpoint_returns_success_for_empty_provider_data(monkeypatch) -> None:
    service, _, _, ranking, risk_analyzer = build_service(
        UserSearchIntent(search_request=SearchRequest(max_price=500)),
        [{"data": []}],
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Toyota under $500"})

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert ranking.context is None
    assert risk_analyzer.call_count == 0


def test_natural_search_malformed_provider_response_remains_sanitized_502(
    monkeypatch,
) -> None:
    service, _, _, ranking, risk_analyzer = build_service(
        UserSearchIntent(search_request=SearchRequest(max_price=500)),
        [{"data": None}],
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Toyota under $500"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream listing service request failed"}
    assert ranking.context is None
    assert risk_analyzer.call_count == 0


def test_natural_endpoint_returns_sanitized_error_for_location_provider_failure(
    monkeypatch,
) -> None:
    service, _, auto_dev, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest(location="Dallas")),
        [],
        location_resolver=FakeLocationResolver(
            LocationResolverUnavailable("private geocoder response")
        ),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Search near Dallas"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Location resolution service unavailable"}
    assert auto_dev.calls == []


def test_natural_endpoint_rejects_ambiguous_location(monkeypatch) -> None:
    service, _, auto_dev, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest(location="Springfield")),
        [],
        location_resolver=FakeLocationResolver(
            LocationResolutionError("private ambiguity data")
        ),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Search near Springfield"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Location could not be resolved unambiguously"}
    assert auto_dev.calls == []


def test_duplicate_vins_across_provider_responses_keep_first_listing() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        makes=["Honda", "Toyota"],
    )
    service, _, _, ranking, risk_analyzer = build_service(
        intent,
        [
            {"data": [provider_listing("VIN-1", make="Honda", price=12_000)]},
            {"data": [provider_listing("VIN-1", make="Toyota", price=17_000)]},
        ],
    )

    result = service.search("Honda or Toyota")

    assert len(result.listings) == 1
    assert result.listings[0].make == "Honda"
    assert ranking.vins == ["VIN-1"]
    assert risk_analyzer.vins == ["VIN-1"]
    assert risk_analyzer.call_count == 1


def test_parser_failure_returns_sanitized_endpoint_error(monkeypatch) -> None:
    service, _, _, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest()),
        [],
        parser_error=RuntimeError("Gemini API key and SDK details"),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "search"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Search query parsing failed"}


def test_auto_dev_failure_fails_entire_planned_search_cleanly(monkeypatch) -> None:
    intent = UserSearchIntent(search_request=SearchRequest(), makes=["Honda", "Toyota"])
    service, _, auto_dev, ranking, _ = build_service(
        intent,
        [{"data": [provider_listing("VIN-1")]}, RuntimeError("provider secret details")],
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Honda or Toyota"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream listing service request failed"}
    assert len(auto_dev.calls) == 2
    assert ranking.context is None


def test_ranking_failure_returns_sanitized_endpoint_error(monkeypatch) -> None:
    service, _, _, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest()),
        [{"data": [provider_listing("VIN-1")]}],
        ranking_error=RuntimeError("provider internals"),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "search"})

    assert response.status_code == 502
    assert response.json() == {"detail": "AI ranking service request failed"}


def test_natural_endpoint_returns_combined_result(monkeypatch) -> None:
    service, _, _, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest()),
        [{"data": [provider_listing("VIN-1")]}],
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Toyota"})

    assert response.status_code == 200
    result = response.json()["data"][0]
    assert result["rank"] == 1
    assert result["score"] == 35
    assert result["risk"]["vin"] == "VIN-1"
    assert result["risk"]["risk_score"] == 5
    assert result["listing"]["vin"] == "VIN-1"


def test_natural_risk_failure_returns_sanitized_endpoint_error(monkeypatch) -> None:
    service, _, _, _, risk_analyzer = build_service(
        UserSearchIntent(search_request=SearchRequest()),
        [{"data": [provider_listing("VIN-1")]}],
        risk_error=RuntimeError("Gemini API key and response internals"),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "Toyota"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Listing risk analysis failed"}
    assert risk_analyzer.call_count == 1


def test_planning_failure_returns_sanitized_endpoint_error(monkeypatch) -> None:
    class BrokenPlanner:
        def plan(self, intent):
            raise RuntimeError("planner internals")

    service, _, _, _, _ = build_service(
        UserSearchIntent(search_request=SearchRequest()),
        [],
        planner=BrokenPlanner(),
    )
    monkeypatch.setattr("app.api.routes.search.get_natural_search_service", lambda: service)

    response = client.post("/search/natural", json={"query": "search"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Search planning failed"}


def test_natural_search_rejects_blank_query() -> None:
    response = client.post("/search/natural", json={"query": "  \n "})

    assert response.status_code == 422
