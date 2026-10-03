from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models import (
    ListingRiskAnalysisResult,
    ListingRiskAssessment,
    ListingRiskLevel,
    VehicleListing,
)
from app.services.gemini_listing_risk_analyzer import (
    GeminiListingRiskAnalyzer,
    validate_listing_risk_result,
)


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
        VehicleListing(
            vin="VIN-1",
            year=2021,
            make="Toyota",
            model="Camry",
            price=21_000,
            mileage=35_000,
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
        ),
        VehicleListing(
            vin="VIN-2",
            year=2021,
            make="Toyota",
            model="Camry",
            price=22_000,
            mileage=42_000,
            accident_count=0,
            has_accidents=False,
            owner_count=2,
        ),
    ]


def assessment(
    vin: str,
    score: int,
    level: ListingRiskLevel,
    *,
    signals: list[str] | None = None,
    explanation: str = "No unusual pattern is evident in the provided data.",
) -> ListingRiskAssessment:
    return ListingRiskAssessment(
        vin=vin,
        risk_score=score,
        risk_level=level,
        signals=signals or [],
        explanation=explanation,
    )


def analyzer(parsed: object) -> tuple[GeminiListingRiskAnalyzer, FakeGeminiClient]:
    client = FakeGeminiClient(parsed)
    return GeminiListingRiskAnalyzer(client=client, model="risk-test-model"), client


def test_normal_listing_set_gets_one_structured_assessment_per_vin() -> None:
    expected = ListingRiskAnalysisResult(
        assessments=[
            assessment("VIN-1", 5, ListingRiskLevel.LOW),
            assessment("VIN-2", 10, ListingRiskLevel.LOW),
        ]
    )
    service, client = analyzer(expected)

    result = service.analyze(candidates())

    assert result == expected.assessments
    assert [item.vin for item in result] == ["VIN-1", "VIN-2"]
    assert client.models.call["model"] == "risk-test-model"
    assert client.models.call["config"].response_schema is ListingRiskAnalysisResult
    assert "Compare candidates with one another" in client.models.call["config"].system_instruction


def test_extreme_low_price_outlier_is_assessed_in_comparative_candidate_set() -> None:
    listings = candidates()
    listings.append(
        VehicleListing(
            vin="VIN-OUTLIER",
            year=2021,
            make="Toyota",
            model="Camry",
            price=225,
            mileage=35_000,
        )
    )
    expected = ListingRiskAnalysisResult(
        assessments=[
            assessment("VIN-1", 5, ListingRiskLevel.LOW),
            assessment("VIN-2", 8, ListingRiskLevel.LOW),
            assessment(
                "VIN-OUTLIER",
                90,
                ListingRiskLevel.HIGH,
                signals=["Price is dramatically below the other Camry candidates"],
                explanation=(
                    "At $225, the listed amount is an extreme outlier compared with "
                    "the other 2021 Camrys in this candidate set; it may be placeholder "
                    "pricing, but the available data cannot confirm that."
                ),
            ),
        ]
    )
    service, client = analyzer(expected)

    result = service.analyze(listings)

    assert result[-1].vin == "VIN-OUTLIER"
    assert result[-1].risk_score == 90
    assert '"price": 225' in client.models.call["contents"]
    assert '"price": 21000' in client.models.call["contents"]


def test_accident_history_alone_does_not_force_high_risk() -> None:
    listings = candidates()
    listings[0] = listings[0].model_copy(
        update={"has_accidents": True, "accident_count": 1}
    )
    expected = ListingRiskAnalysisResult(
        assessments=[
            assessment(
                "VIN-1",
                25,
                ListingRiskLevel.LOW,
                signals=["One accident is reported"],
                explanation=(
                    "One accident is recorded; that history warrants review but is "
                    "not, by itself, strong evidence of a listing anomaly."
                ),
            ),
            assessment("VIN-2", 5, ListingRiskLevel.LOW),
        ]
    )
    service, _ = analyzer(expected)

    result = service.analyze(listings)

    assert result[0].risk_level == ListingRiskLevel.LOW
    assert result[0].risk_score < 30


def test_missing_history_is_uncertainty_not_definitive_suspicion() -> None:
    listings = [
        VehicleListing(
            vin="VIN-NO-HISTORY",
            year=2018,
            make="Honda",
            model="Civic",
            price=14_000,
            mileage=65_000,
        )
    ]
    expected = ListingRiskAnalysisResult(
        assessments=[
            assessment(
                "VIN-NO-HISTORY",
                35,
                ListingRiskLevel.MEDIUM,
                signals=["Accident and ownership history are not available"],
                explanation=(
                    "Missing history limits verification from the supplied data, "
                    "but does not establish that anything is wrong."
                ),
            )
        ]
    )
    service, _ = analyzer(expected)

    result = service.analyze(listings)

    assert result[0].risk_level == ListingRiskLevel.MEDIUM
    assert "does not establish" in result[0].explanation


def test_unknown_vin_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown VIN"):
        validate_listing_risk_result(
            [assessment("UNKNOWN", 5, ListingRiskLevel.LOW)],
            candidates(),
        )


def test_duplicate_vin_assessment_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate VIN"):
        validate_listing_risk_result(
            [
                assessment("VIN-1", 5, ListingRiskLevel.LOW),
                assessment("vin-1", 5, ListingRiskLevel.LOW),
                assessment("VIN-2", 5, ListingRiskLevel.LOW),
            ],
            candidates(),
        )


@pytest.mark.parametrize(
    "assessment_data",
    [
        {
            "vin": "VIN-1",
            "risk_score": 101,
            "risk_level": "high",
            "signals": [],
            "explanation": "Out of range",
        },
        {
            "vin": "VIN-1",
            "risk_score": 40,
            "risk_level": "unknown",
            "signals": [],
            "explanation": "Invalid level",
        },
        {
            "vin": "VIN-1",
            "risk_score": 80,
            "risk_level": "low",
            "signals": [],
            "explanation": "Inconsistent level",
        },
        {
            "vin": "VIN-1",
            "risk_score": 50.5,
            "risk_level": "medium",
            "signals": [],
            "explanation": "Non-integer score",
        },
    ],
)
def test_malformed_score_or_level_is_rejected(assessment_data: dict) -> None:
    with pytest.raises(ValidationError):
        ListingRiskAssessment.model_validate(assessment_data)


def test_gemini_malformed_structured_output_is_rejected() -> None:
    service, _ = analyzer({"assessments": [{"vin": "VIN-1", "risk_score": 50}]})

    with pytest.raises(ValueError, match="malformed listing risk analysis"):
        service.analyze(candidates())


def test_incomplete_assessment_set_is_rejected() -> None:
    service, _ = analyzer(
        ListingRiskAnalysisResult(
            assessments=[assessment("VIN-1", 5, ListingRiskLevel.LOW)]
        )
    )

    with pytest.raises(ValueError, match="one assessment per candidate"):
        service.analyze(candidates())


def test_empty_candidate_set_skips_gemini_call() -> None:
    service, client = analyzer(None)

    assert service.analyze([]) == []
    assert client.models.call is None


def test_gemini_client_uses_configured_key(monkeypatch) -> None:
    captured = {}
    client = FakeGeminiClient(None)

    def fake_client(*, api_key: str):
        captured["api_key"] = api_key
        return client

    monkeypatch.setattr(
        "app.services.gemini_listing_risk_analyzer.get_settings",
        lambda: Settings(
            AUTO_DEV_API_KEY="auto-key",
            GEMINI_API_KEY="gemini-risk-key",
        ),
    )
    monkeypatch.setattr(
        "app.services.gemini_listing_risk_analyzer.genai.Client",
        fake_client,
    )

    service = GeminiListingRiskAnalyzer()

    assert service.client is client
    assert captured["api_key"] == "gemini-risk-key"
