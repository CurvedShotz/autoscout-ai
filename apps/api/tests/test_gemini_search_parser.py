from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.models import SearchRequest, UserSearchIntent
from app.services.gemini_search_parser import GeminiSearchQueryParser


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


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        (
            "Find me a Toyota Camry near Dallas under $20k, newer than 2019 and under 100k miles",
            UserSearchIntent(
                search_request=SearchRequest(
                    make="Toyota",
                    model="Camry",
                    location="Dallas",
                    min_year=2020,
                    max_price=20_000,
                    max_mileage=100_000,
                )
            ),
        ),
        (
            "I want a reliable Honda or Toyota for around $15,000",
            UserSearchIntent(
                search_request=SearchRequest(),
                makes=["Honda", "Toyota"],
                target_price=15_000,
                preferences=["reliable"],
            ),
        ),
        (
            "Show me a sporty sedan under 60k miles",
            UserSearchIntent(
                search_request=SearchRequest(max_mileage=60_000),
                body_styles=["sedan"],
                preferences=["sporty"],
            ),
        ),
        (
            "Find a 2018 or newer RAV4 around Denton",
            UserSearchIntent(
                search_request=SearchRequest(model="RAV4", min_year=2018, location="Denton")
            ),
        ),
        (
            "I need a cheap first car with low maintenance costs",
            UserSearchIntent(
                search_request=SearchRequest(),
                preferences=["cheap", "first-car suitability", "low maintenance costs"],
            ),
        ),
        (
            "I want a car around 50k miles",
            UserSearchIntent(search_request=SearchRequest(), target_mileage=50_000),
        ),
    ],
)
def test_gemini_parser_returns_rich_structured_intent(monkeypatch, query, intent) -> None:
    client = FakeGeminiClient(intent)
    monkeypatch.setattr(
        "app.services.gemini_search_parser.get_settings",
        lambda: Settings(
            AUTO_DEV_API_KEY="auto-key",
            GEMINI_API_KEY="gemini-test-key",
            GEMINI_RANKING_MODEL="configured-parser-model",
        ),
    )

    result = GeminiSearchQueryParser(client=client).parse(query)

    assert result == intent
    assert client.models.call["model"] == "configured-parser-model"
    assert client.models.call["contents"] == query
    config = client.models.call["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is UserSearchIntent
    assert "leave unknown hard-filter fields null" in config.system_instruction
    assert "Never guess missing makes" in config.system_instruction
    assert "Do not invent a tolerance band" in config.system_instruction
    assert "leave the corresponding singular search_request field null" in config.system_instruction
    assert "never pick just the first alternative" in config.system_instruction


def test_gemini_parser_rejects_malformed_structured_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.gemini_search_parser.get_settings",
        lambda: Settings(AUTO_DEV_API_KEY="auto-key", GEMINI_API_KEY="test-key"),
    )
    parser = GeminiSearchQueryParser(
        client=FakeGeminiClient({"search_request": {"min_year": 1800}})
    )

    with pytest.raises(ValueError, match="malformed structured search parse"):
        parser.parse("a car")


def test_gemini_parser_rejects_missing_parsed_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.gemini_search_parser.get_settings",
        lambda: Settings(AUTO_DEV_API_KEY="auto-key", GEMINI_API_KEY="test-key"),
    )
    parser = GeminiSearchQueryParser(client=FakeGeminiClient(None))

    with pytest.raises(ValueError, match="no valid structured search parse"):
        parser.parse("a car")


def test_gemini_parser_rejects_empty_query(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.gemini_search_parser.get_settings",
        lambda: Settings(AUTO_DEV_API_KEY="auto-key", GEMINI_API_KEY="test-key"),
    )
    parser = GeminiSearchQueryParser(client=FakeGeminiClient(None))

    with pytest.raises(ValueError, match="must not be empty"):
        parser.parse("  ")
