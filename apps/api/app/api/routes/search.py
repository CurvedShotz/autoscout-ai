from fastapi import APIRouter, HTTPException

from app.models import RankedVehicleListing, SearchRequest
from app.services.auto_dev_client import AutoDevClient
from app.services.ranking import validate_ranking_result
from app.services.ranking_provider import (
    UnsupportedRankingProviderError,
    get_ranking_service,
)
from app.services.vehicle_listing_normalizer import normalize_listings

router = APIRouter()


@router.post("/search", tags=["search"])
def search(request: SearchRequest) -> dict[str, object]:
    client = AutoDevClient()
    try:
        raw_response = client.search_listings(
            make=request.make,
            model=request.model,
            min_year=request.min_year,
            max_year=request.max_year,
            min_price=request.min_price,
            max_price=request.max_price,
            min_mileage=request.min_mileage,
            max_mileage=request.max_mileage,
            location=request.location,
            limit=10,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream listing service request failed") from None

    listings = normalize_listings(raw_response)
    if not listings:
        return {"data": []}

    try:
        ranking_service = get_ranking_service()
        ranking_result = ranking_service.rank_listings(request, listings)
        validate_ranking_result(ranking_result, listings)
        listings_by_vin = {listing.vin: listing for listing in listings if listing.vin is not None}
        ranked_listings = [
            RankedVehicleListing(
                rank=ranking.rank,
                score=ranking.score,
                reason=ranking.reason,
                listing=listings_by_vin[ranking.vin],
            )
            for ranking in ranking_result.rankings
        ]
        return {"data": ranked_listings}
    except UnsupportedRankingProviderError:
        raise HTTPException(
            status_code=500,
            detail="Unsupported AI ranking provider configured",
        ) from None
    except Exception:
        raise HTTPException(status_code=502, detail="AI ranking service request failed") from None
