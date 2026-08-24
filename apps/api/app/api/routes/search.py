from fastapi import APIRouter, HTTPException

from app.models import SearchRequest
from app.services.auto_dev_client import AutoDevClient
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
        return {"data": normalize_listings(raw_response)}
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream listing service request failed") from None
