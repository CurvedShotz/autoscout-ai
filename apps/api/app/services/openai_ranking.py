import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.models import AIRankingResult, VehicleListing
from app.services.ranking import (
    AIRankingService,
    RANKING_SYSTEM_GUIDANCE,
    RankingContext,
    ranking_input,
    validate_ranking_result,
)


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
        search_request: RankingContext,
        listings: list[VehicleListing],
    ) -> AIRankingResult:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": RANKING_SYSTEM_GUIDANCE,
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