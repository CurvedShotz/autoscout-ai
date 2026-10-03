from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.models import AIRankedListing, AIRankingResult, SearchRequest, VehicleListing
from app.services.gemini_ranking import GeminiRankingService


class FakeModels:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.call = None

    def generate_content(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(parsed=self.parsed)


class FakeGeminiClient:
    def __init__(self, parsed: object) -> None:
        self.models = FakeModels(parsed)


def candidates() -> list[VehicleListing]:
    return [
        VehicleListing(vin="VIN-1", make="Honda", model="Civic"),
        VehicleListing(vin="VIN-2", make="Toyota", model="Camry"),
    ]


def configured_settings() -> Settings:
    return Settings(
        AUTO_DEV_API_KEY="auto-key",
        GEMINI_API_KEY="gemini-test-key",
        GEMINI_RANKING_MODEL="gemini-test-model",
    )


def test_gemini_ranking_accepts_structured_result_and_uses_configured_model(monkeypatch) -> None:
    result = AIRankingResult(
        rankings=[
            AIRankedListing(vin="VIN-2", score=93, rank=1, reason="Strong value"),
            AIRankedListing(vin="VIN-1", score=84, rank=2, reason="Good alternative"),
        ]
    )
    client = FakeGeminiClient(result)
    monkeypatch.setattr("app.services.gemini_ranking.get_settings", configured_settings)

    ranked = GeminiRankingService(client=client).rank_listings(
        SearchRequest(make="Honda", max_price=25000), candidates()
    )

    assert ranked == result
    assert client.models.call["model"] == "gemini-test-model"
    config = client.models.call["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is AIRankingResult
    assert "rank only by user fit and purchase tradeoffs" in config.system_instruction
    assert "leave formal anomaly and scam-risk judgments" in config.system_instruction
    for restricted_term in (
        "high-risk",
        "low-risk",
        "suspicious",
        "a scam",
        "fraudulent",
        "a fake listing",
        "anomaly risk",
    ):
        assert restricted_term in config.system_instruction
    assert "very high mileage weakening fit" in config.system_instruction
    assert "unusually low listed price making value difficult to assess" in config.system_instruction
    assert "candidate_listings" in client.models.call["contents"]
    assert "max_price" in client.models.call["contents"]


def test_gemini_client_uses_key_from_settings(monkeypatch) -> None:
    captured = {}
    client = FakeGeminiClient(None)

    def fake_client(*, api_key: str):
        captured["api_key"] = api_key
        return client

    monkeypatch.setattr("app.services.gemini_ranking.get_settings", configured_settings)
    monkeypatch.setattr("app.services.gemini_ranking.genai.Client", fake_client)

    service = GeminiRankingService()

    assert service.client is client
    assert captured["api_key"] == "gemini-test-key"


@pytest.mark.parametrize(
    "rankings",
    [
        [AIRankedListing(vin="UNKNOWN", score=80, rank=1, reason="Unknown VIN")],
        [
            AIRankedListing(vin="VIN-1", score=90, rank=1, reason="First"),
            AIRankedListing(vin="VIN-1", score=80, rank=2, reason="Duplicate"),
        ],
    ],
)
def test_gemini_ranking_rejects_invalid_vins(monkeypatch, rankings) -> None:
    monkeypatch.setattr("app.services.gemini_ranking.get_settings", configured_settings)
    service = GeminiRankingService(
        client=FakeGeminiClient(AIRankingResult(rankings=rankings))
    )

    with pytest.raises(ValueError):
        service.rank_listings(SearchRequest(), candidates())


@pytest.mark.parametrize("parsed", [None, {"rankings": [{"vin": "VIN-1"}]}])
def test_gemini_ranking_rejects_malformed_result(monkeypatch, parsed) -> None:
    monkeypatch.setattr("app.services.gemini_ranking.get_settings", configured_settings)
    service = GeminiRankingService(client=FakeGeminiClient(parsed))

    with pytest.raises(ValueError, match="structured|malformed"):
        service.rank_listings(SearchRequest(), candidates())