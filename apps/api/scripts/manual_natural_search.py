from app.services.natural_search import (
    NaturalSearchParserError,
    NaturalSearchPlanningError,
    NaturalSearchProviderError,
    NaturalSearchRankingError,
)
from app.services.natural_search_provider import get_natural_search_service

QUERIES = [
    "Find me a Toyota Camry near Dallas under $20k, newer than 2019 and under 100k miles",
    "I want a reliable Honda or Toyota around $15,000",
    "Show me a sporty sedan under 60k miles",
]


def main() -> None:
    try:
        service = get_natural_search_service()
    except Exception:
        print("Search failed: natural-search service could not be initialized")
        return
    for query in QUERIES:
        print(f"Query: {query}")
        try:
            result = service.search(query)
        except NaturalSearchParserError:
            print("Search failed: query parsing failed")
            continue
        except NaturalSearchPlanningError:
            print("Search failed: planning failed")
            continue
        except NaturalSearchProviderError:
            print("Search failed: listing provider request failed")
            continue
        except NaturalSearchRankingError:
            print("Search failed: ranking failed")
            continue

        print(f"Planned searches: {len(result.planned_requests)}")
        print(f"Merged/deduplicated listings: {len(result.listings)}")
        for ranked in result.ranked_listings[:5]:
            listing = ranked.listing
            year = listing.year if listing.year is not None else "n/a"
            make = listing.make or "n/a"
            model = listing.model or "n/a"
            price = listing.price if listing.price is not None else "n/a"
            mileage = listing.mileage if listing.mileage is not None else "n/a"
            print(
                f"  #{ranked.rank} {year} {make} {model} | "
                f"price={price} | mileage={mileage} | "
                f"score={ranked.score:g} | reason={ranked.reason}"
            )


if __name__ == "__main__":
    main()
