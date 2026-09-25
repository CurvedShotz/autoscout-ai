import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.models import AIRankingResult, SearchRequest, VehicleListing
from app.services.ranking import AIRankingService, ranking_input, validate_ranking_result


class GeminiRankingService(AIRankingService):
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        settings = get_settings()
        if client is None:
            if settings.gemini_api_key is None:
                raise ValueError("GEMINI_API_KEY is not configured")
            client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.client = client
        self.model = model or settings.gemini_ranking_model

    def rank_listings(
        self,
        search_request: SearchRequest,
        listings: list[VehicleListing],
    ) -> AIRankingResult:
        response = self.client.models.generate_content(
            model=self.model,
            contents=json.dumps(ranking_input(search_request, listings)),
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Compare each provided vehicle candidate against the user's original "
                    "search constraints and preferences. Use your judgment to weigh price, "
                    "mileage, year, accident history, owner history, overall value, and "
                    "tradeoffs. Rank only the provided candidates. Do not invent vehicles "
                    "or VINs."
                ),
                response_mime_type="application/json",
                response_schema=AIRankingResult,
            ),
        )

        parsed_result = response.parsed
        if not isinstance(parsed_result, (AIRankingResult, dict)):
            raise ValueError("Gemini returned no valid structured ranking result")
        try:
            ranking_result = AIRankingResult.model_validate(parsed_result)
        except ValidationError as exc:
            raise ValueError("Gemini returned a malformed ranking result") from exc

        return validate_ranking_result(ranking_result, listings)