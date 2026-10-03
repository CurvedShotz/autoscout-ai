from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.models import NaturalSearchRequest, SearchRequest
from app.services.auto_dev_client import AutoDevClient
from app.services.location_resolver import (
    LocationResolutionError,
    LocationResolverUnavailable,
)
from app.services.location_resolver_provider import get_location_resolver
from app.services.natural_search import (
    NaturalSearchLocationError,
    NaturalSearchLocationProviderError,
    NaturalSearchParserError,
    NaturalSearchPlanningError,
    NaturalSearchProviderError,
    NaturalSearchRankingError,
    NaturalSearchRiskError,
)
from app.services.natural_search_provider import get_natural_search_service
from app.services.listing_risk_provider import get_listing_risk_analyzer
from app.services.ranking import validate_ranking_result
from app.services.ranking_provider import (
    UnsupportedRankingProviderError,
    get_ranking_service,
)
from app.services.search_result_combiner import combine_ranked_results
from app.services.vehicle_listing_normalizer import normalize_listings

router = APIRouter()


@router.post("/search", tags=["search"])
def search(request: SearchRequest) -> dict[str, object]:
    client = AutoDevClient()
    try:
        resolved_location = get_location_resolver().resolve(request.location)
    except LocationResolutionError:
        raise HTTPException(
            status_code=422,
            detail="Location could not be resolved unambiguously",
        ) from None
    except LocationResolverUnavailable:
        raise HTTPException(
            status_code=502,
            detail="Location resolution service unavailable",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Location resolution service unavailable",
        ) from None

    provider_request = request
    if resolved_location is not None:
        provider_request = request.model_copy(
            update={"location": resolved_location.zip}
        )
    provider_params = provider_request.model_dump()
    if resolved_location is not None and resolved_location.city is not None:
        provider_params["distance"] = get_settings().auto_dev_search_distance_miles

    try:
        raw_response = client.search_listings(
            **provider_params,
            limit=10,
        )
        listings = normalize_listings(raw_response)
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream listing service request failed") from None

    if not listings:
        return {"data": []}

    try:
        ranking_service = get_ranking_service()
        ranking_result = ranking_service.rank_listings(request, listings)
        validate_ranking_result(ranking_result, listings)
    except UnsupportedRankingProviderError:
        raise HTTPException(
            status_code=500,
            detail="Unsupported AI ranking provider configured",
        ) from None
    except Exception:
        raise HTTPException(status_code=502, detail="AI ranking service request failed") from None

    try:
        risk_assessments = get_listing_risk_analyzer().analyze(listings)
        combined_results = combine_ranked_results(
            ranking_result,
            risk_assessments,
            listings,
        )
        return {"data": combined_results}
    except Exception:
        raise HTTPException(status_code=502, detail="Listing risk analysis failed") from None


@router.post("/search/natural", tags=["search"])
def natural_search(request: NaturalSearchRequest) -> dict[str, object]:
    try:
        service = get_natural_search_service()
    except UnsupportedRankingProviderError:
        raise HTTPException(
            status_code=500,
            detail="Unsupported AI ranking provider configured",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Natural-language search service unavailable",
        ) from None

    try:
        result = service.search(request.query)
        return {"data": result.ranked_listings}
    except NaturalSearchParserError:
        raise HTTPException(
            status_code=502,
            detail="Search query parsing failed",
        ) from None
    except NaturalSearchPlanningError:
        raise HTTPException(
            status_code=500,
            detail="Search planning failed",
        ) from None
    except NaturalSearchLocationError:
        raise HTTPException(
            status_code=422,
            detail="Location could not be resolved unambiguously",
        ) from None
    except NaturalSearchLocationProviderError:
        raise HTTPException(
            status_code=502,
            detail="Location resolution service unavailable",
        ) from None
    except NaturalSearchProviderError:
        raise HTTPException(
            status_code=502,
            detail="Upstream listing service request failed",
        ) from None
    except NaturalSearchRankingError:
        raise HTTPException(
            status_code=502,
            detail="AI ranking service request failed",
        ) from None
    except NaturalSearchRiskError:
        raise HTTPException(
            status_code=502,
            detail="Listing risk analysis failed",
        ) from None
