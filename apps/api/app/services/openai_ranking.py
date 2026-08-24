import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.models import AIRankingResult, SearchRequest, VehicleListing
from app.services.ranking import AIRankingService, ranking_input, validate_ranking_result


class OpenAIRankingService(AIRankingService):
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        settings = get_settings()
        if client is None:
            if settings.openai_api_key is None:
                raise ValueError("OPENAI_API_KEY is not configured")
            client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.client = client
        self.model = model or settings.openai_ranking_model

    def rank_listings(
        self,
        search_request: SearchRequest,
        listings: list[VehicleListing],
    ) -> AIRankingResult:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Compare the candidate vehicles against the user's request. "
                        "Rank only candidates provided. Consider price, mileage, year, "
                        "accident history, owner count, one-owner status, overall value, "
                        "and tradeoffs. Do not invent cars or VINs."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(ranking_input(search_request, listings)),
                },
            ],
            text_format=AIRankingResult,
        )
        parsed_result = response.output_parsed
        if not isinstance(parsed_result, AIRankingResult):
            raise ValueError("OpenAI returned no valid structured ranking result")
        return validate_ranking_result(parsed_result, listings)