import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.models import AIRankedListing, AIRankingResult, SearchRequest, VehicleListing
from app.services.openai_ranking import OpenAIRankingService
from app.services.ranking import validate_ranking_result


class FakeResponses:
    def __init__(self, result: AIRankingResult) -> None:
        self.result = result
        self.kwargs = {}

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"output_parsed": self.result})()


class FakeOpenAI:
    def __init__(self, result: AIRankingResult) -> None:
        self.responses = FakeResponses(result)


def candidate_listings() -> list[VehicleListing]:
    return [
        VehicleListing(vin="VIN-1", make="Honda", model="Civic"),
        VehicleListing(vin="VIN-2", make="Toyota", model="Camry"),
    ]


def test_openai_ranking_accepts_valid_structured_response(monkeypatch) -> None:
    fake_client = FakeOpenAI(
        AIRankingResult(
            rankings=[
                AIRankedListing(vin="VIN-1", score=92, rank=1, reason="Best fit"),
                AIRankedListing(vin="VIN-2", score=80, rank=2, reason="Good alternative"),
            ]
        )
    )
    monkeypatch.setattr(
        "app.services.openai_ranking.get_settings",
        lambda: Settings(AUTO_DEV_API_KEY="auto-key", OPENAI_RANKING_MODEL="configured-model"),
    )

    service = OpenAIRankingService(client=fake_client)
    result = service.rank_listings(SearchRequest(make="Honda"), candidate_listings())

    assert result.rankings[0].vin == "VIN-1"
    assert fake_client.responses.kwargs["model"] == "configured-model"
    assert fake_client.responses.kwargs["text_format"] is AIRankingResult
    system_prompt = fake_client.responses.kwargs["input"][0]["content"]
    assert "rank only by user fit and purchase tradeoffs" in system_prompt
    assert "leave formal anomaly and scam-risk judgments" in system_prompt
    for restricted_term in (
        "high-risk",
        "low-risk",
        "suspicious",
        "a scam",
        "fraudulent",
        "a fake listing",
        "anomaly risk",
    ):
        assert restricted_term in system_prompt
    assert "reported accidents reducing desirability" in system_prompt


@pytest.mark.parametrize(
    ("rankings", "message"),
    [
        ([AIRankedListing(vin="UNKNOWN", score=90, rank=1, reason="No")], "unknown VIN"),
        (
            [
                AIRankedListing(vin="VIN-1", score=90, rank=1, reason="One"),
                AIRankedListing(vin="VIN-1", score=80, rank=2, reason="Duplicate"),
            ],
            "duplicate VINs",
        ),
        (
            [
                AIRankedListing(vin="VIN-1", score=90, rank=1, reason="One"),
                AIRankedListing(vin="VIN-2", score=80, rank=3, reason="Gap"),
            ],
            "sequential",
        ),
    ],
)
def test_ranking_validation_rejects_invalid_results(rankings, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_ranking_result(AIRankingResult(rankings=rankings), candidate_listings())


def test_ranking_schema_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        AIRankedListing(vin="VIN-1", score=101, rank=1, reason="Invalid")


def test_openai_ranking_rejects_more_results_than_candidates() -> None:
    result = AIRankingResult(
        rankings=[AIRankedListing(vin="VIN-1", score=90, rank=1, reason="One")]
    )
    with pytest.raises(ValueError):
        validate_ranking_result(result, [])