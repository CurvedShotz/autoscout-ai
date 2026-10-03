from app.services.natural_search import (
    NaturalSearchParserError,
    NaturalSearchPlanningError,
    NaturalSearchProviderError,
    NaturalSearchRankingError,
    NaturalSearchRiskError,
)
from app.services.natural_search_provider import get_natural_search_service

QUERY = "Find me a Toyota Camry near Dallas under $20k"


def main() -> None:
    try:
        result = get_natural_search_service().search(QUERY)
    except NaturalSearchParserError:
        print("Live search failed: query parsing failed.")
        return
    except NaturalSearchPlanningError:
        print("Live search failed: search planning failed.")
        return
    except NaturalSearchProviderError:
        print("Live search failed: listing provider request failed.")
        return
    except NaturalSearchRankingError:
        print("Live search failed: ranking failed.")
        return
    except NaturalSearchRiskError:
        print("Live search failed: listing risk analysis failed.")
        return
    except Exception:
        print("Live search failed: service initialization failed.")
        return

    print(f"Query: {QUERY}")
    print(f"Planned searches: {len(result.planned_requests)}")
    print(f"Deduplicated listings: {len(result.listings)}")
    for item in result.ranked_listings[:10]:
        listing = item.listing
        vehicle = " ".join(
            str(value)
            for value in (listing.year, listing.make, listing.model)
            if value is not None
        )
        signals = ", ".join(item.risk.signals) if item.risk.signals else "none"
        print(
            f"#{item.rank} {vehicle or 'unknown vehicle'} | "
            f"price={listing.price if listing.price is not None else 'n/a'} | "
            f"mileage={listing.mileage if listing.mileage is not None else 'n/a'} | "
            f"ranking_score={item.score:g} | reason={item.reason} | "
            f"risk_score={item.risk.risk_score} | "
            f"risk_level={item.risk.risk_level.value} | "
            f"risk_signals={signals} | "
            f"risk_explanation={item.risk.explanation}"
        )


if __name__ == "__main__":
    main()
