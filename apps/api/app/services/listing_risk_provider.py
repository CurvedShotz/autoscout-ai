from app.services.gemini_listing_risk_analyzer import GeminiListingRiskAnalyzer
from app.services.listing_risk import ListingRiskAnalyzer


def get_listing_risk_analyzer() -> ListingRiskAnalyzer:
    return GeminiListingRiskAnalyzer()
