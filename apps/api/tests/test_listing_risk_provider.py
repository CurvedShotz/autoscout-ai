from app.services.listing_risk import ListingRiskAnalyzer
from app.services.listing_risk_provider import get_listing_risk_analyzer


def test_factory_returns_configured_gemini_risk_analyzer(monkeypatch) -> None:
    expected = object()
    monkeypatch.setattr(
        "app.services.listing_risk_provider.GeminiListingRiskAnalyzer",
        lambda: expected,
    )

    assert get_listing_risk_analyzer() is expected
