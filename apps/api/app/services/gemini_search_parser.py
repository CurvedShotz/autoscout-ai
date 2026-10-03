from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.models import UserSearchIntent
from app.services.search_query_parser import SearchQueryParser


class GeminiSearchQueryParser(SearchQueryParser):
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        settings = get_settings()
        if client is None:
            if settings.gemini_api_key is None:
                raise ValueError("GEMINI_API_KEY is not configured")
            client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.client = client
        self.model = model or settings.gemini_ranking_model

    def parse(self, query: str) -> UserSearchIntent:
        if not query.strip():
            raise ValueError("Search query must not be empty")

        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Parse the user's free-form used-vehicle search into the supplied "
                    "structured response schema. Reuse search_request for hard provider "
                    "filters: make, model, min_year, max_year, min_price, max_price, "
                    "min_mileage, max_mileage, and location. If the user explicitly asks "
                    "for two or more alternative makes or models (for example, 'Honda or "
                    "Toyota'), put every alternative in makes/models respectively and leave "
                    "the corresponding singular search_request field null; never pick just "
                    "the first alternative as a hard filter. For one explicitly specified "
                    "make or model, use the singular search_request field and do not repeat "
                    "it in makes/models. "
                    "Use body_styles for explicitly requested body styles such as sedan or "
                    "SUV. Never guess missing makes, models, years, amounts, mileage, or "
                    "places; leave unknown hard-filter fields null. Convert explicit price "
                    "shorthand such as $20k to "
                    "20000 dollars and mileage shorthand such as 100k miles to 100000. "
                    "'Under' means the corresponding maximum; 'over' means the minimum. "
                    "For approximate amounts phrased as 'around', 'about', 'roughly', or "
                    "'approximately', extract the stated amount into target_price or "
                    "target_mileage as appropriate. Do not invent a tolerance band or "
                    "min/max hard bound for an approximate amount. "
                    "'2018 or newer' means min_year 2018. Strictly 'newer than 2019' "
                    "means min_year 2020 because model years are integers. Preserve city, "
                    "region, or other useful location wording as provided; never make up "
                    "a ZIP code. For a stated range, fill both bounds. Do not turn vague "
                    "words like 'cheap' or 'good value' into arbitrary numbers; preserve "
                    "those as semantic preferences. Keep genuinely semantic preferences "
                    "such as reliable, sporty, low maintenance, first-car suitability, "
                    "fuel efficient, and good value in preferences. Do not force them into "
                    "unrelated fields. If there are no such preferences, return an empty "
                    "preferences list."
                ),
                response_mime_type="application/json",
                response_schema=UserSearchIntent,
            ),
        )

        parsed = response.parsed
        if not isinstance(parsed, (UserSearchIntent, dict)):
            raise ValueError("Gemini returned no valid structured search parse")
        try:
            return UserSearchIntent.model_validate(parsed)
        except ValidationError as exc:
            raise ValueError("Gemini returned a malformed structured search parse") from exc