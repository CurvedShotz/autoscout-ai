"""Manual live Gemini natural-language search parser check; not pytest-collected."""

from pathlib import Path
import sys


API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.services.gemini_search_parser import GeminiSearchQueryParser  # noqa: E402


QUERIES = [
    "Find me a Toyota Camry near Dallas under $20k, newer than 2019 and under 100k miles",
    "I want a reliable Honda or Toyota for around $15,000",
    "Show me a sporty sedan under 60k miles",
    "Find a 2018 or newer RAV4 around Denton",
    "I need a cheap first car with low maintenance costs",
]


def main() -> None:
    parser = GeminiSearchQueryParser()
    for query in QUERIES:
        result = parser.parse(query)
        print(f"Query: {query}")
        print(f"Hard SearchRequest: {result.search_request.model_dump(exclude_none=True)}")
        print(f"Makes: {result.makes}")
        print(f"Models: {result.models}")
        print(f"Body styles: {result.body_styles}")
        print(f"Target price: {result.target_price}")
        print(f"Target mileage: {result.target_mileage}")
        print(f"Semantic preferences: {result.preferences}")
        print()


if __name__ == "__main__":
    main()
