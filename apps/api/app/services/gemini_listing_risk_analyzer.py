import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.models import (
    ListingRiskAnalysisResult,
    ListingRiskAssessment,
    VehicleListing,
)
from app.services.listing_risk import (
    ListingRiskAnalyzer,
    validate_risk_candidates,
    validate_listing_risk_result,
)


class GeminiListingRiskAnalyzer(ListingRiskAnalyzer):
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        settings = get_settings()
        if client is None:
            if settings.gemini_api_key is None:
                raise ValueError("GEMINI_API_KEY is not configured")
            client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.client = client
        self.model = model or settings.gemini_ranking_model

    def analyze(
        self,
        listings: list[VehicleListing],
    ) -> list[ListingRiskAssessment]:
        if not listings:
            return []
        validate_risk_candidates(listings)

        response = self.client.models.generate_content(
            model=self.model,
            contents=json.dumps(
                [listing.model_dump(mode="json") for listing in listings]
            ),
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Assess only observable listing anomalies and caution signals in "
                    "the supplied candidate set. Compare candidates with one another "
                    "where that helps identify outliers, especially unusually low prices. "
                    "Consider whether a price may be a placeholder, but state it only as "
                    "a possibility, not a fact. Consider year, mileage, accident and "
                    "owner history, usage type, and missing data. An older vehicle with "
                    "high mileage is not inherently suspicious; accident history alone "
                    "must not produce a high risk score. Missing history is uncertainty, "
                    "not evidence of wrongdoing. Do not infer seller intent, payment "
                    "terms, title legitimacy, or fraud status. Never label a vehicle "
                    "fraudulent, fake, or a scam. Return exactly one assessment for "
                    "each provided VIN and do not invent VINs. Scores are 0-100: 0 means "
                    "little or no suspicious evidence in available data; 100 means "
                    "highly anomalous and deserving strong caution. Use low for scores "
                    "0-29, medium for 30-69, and high for 70-100. Base every signal and "
                    "explanation only on the provided normalized listing fields."
                ),
                response_mime_type="application/json",
                response_schema=ListingRiskAnalysisResult,
            ),
        )

        parsed = response.parsed
        if not isinstance(parsed, (ListingRiskAnalysisResult, dict)):
            raise ValueError("Gemini returned no valid structured listing risk analysis")
        try:
            result = ListingRiskAnalysisResult.model_validate(parsed)
        except ValidationError as exc:
            raise ValueError("Gemini returned malformed listing risk analysis") from exc
        return validate_listing_risk_result(result.assessments, listings)
