from app.models import ListingRiskAssessment, ListingRiskLevel
from scripts.evaluate_listing_risk_calibration import explanation_signal_mismatches


def test_expected_old_high_mileage_explanation_is_not_a_risk_signal() -> None:
    assessment = ListingRiskAssessment(
        vin="CAL-OLD",
        risk_score=0,
        risk_level=ListingRiskLevel.LOW,
        signals=[],
        explanation="An older vehicle with high mileage is expected and not inherently suspicious.",
    )

    assert explanation_signal_mismatches(assessment) == set()


def test_explicit_accident_risk_in_explanation_requires_matching_signal() -> None:
    assessment = ListingRiskAssessment(
        vin="CAL-ACCIDENT",
        risk_score=20,
        risk_level=ListingRiskLevel.LOW,
        signals=[],
        explanation="Minor accident history noted for review.",
    )

    assert explanation_signal_mismatches(assessment) == {"accident"}


def test_placeholder_price_in_explanation_requires_matching_signal() -> None:
    assessment = ListingRiskAssessment(
        vin="CAL-PRICE",
        risk_score=85,
        risk_level=ListingRiskLevel.HIGH,
        signals=["Unusually low price compared with peers"],
        explanation="The extreme outlier price could possibly be a placeholder.",
    )

    assert explanation_signal_mismatches(assessment) == set()
