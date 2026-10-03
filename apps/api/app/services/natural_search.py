from dataclasses import dataclass

from app.models import (
    RankedVehicleSearchResult,
    SearchRankingContext,
    SearchRequest,
    VehicleListing,
)
from app.core.config import get_settings
from app.services.auto_dev_client import AutoDevClient
from app.services.location_resolver import (
    LocationResolutionError,
    LocationResolver,
    LocationResolverUnavailable,
)
from app.services.ranking import AIRankingService, validate_ranking_result
from app.services.listing_risk import ListingRiskAnalyzer
from app.services.search_planner import SearchPlanner
from app.services.search_query_parser import SearchQueryParser
from app.services.search_result_combiner import combine_ranked_results
from app.services.vehicle_listing_normalizer import normalize_listings


class NaturalSearchParserError(Exception):
    pass


class NaturalSearchPlanningError(Exception):
    pass


class NaturalSearchProviderError(Exception):
    pass


class NaturalSearchLocationError(Exception):
    pass


class NaturalSearchLocationProviderError(Exception):
    pass


class NaturalSearchRankingError(Exception):
    pass


class NaturalSearchRiskError(Exception):
    pass


@dataclass(frozen=True)
class NaturalSearchResult:
    planned_requests: list[SearchRequest]
    listings: list[VehicleListing]
    ranked_listings: list[RankedVehicleSearchResult]


class NaturalSearchService:
    """Run natural searches atomically: any planned provider-search failure fails the request."""

    def __init__(
        self,
        *,
        parser: SearchQueryParser,
        planner: SearchPlanner,
        auto_dev_client: AutoDevClient,
        location_resolver: LocationResolver,
        ranking_service: AIRankingService,
        risk_analyzer: ListingRiskAnalyzer,
    ) -> None:
        self.parser = parser
        self.planner = planner
        self.auto_dev_client = auto_dev_client
        self.location_resolver = location_resolver
        self.ranking_service = ranking_service
        self.risk_analyzer = risk_analyzer

    def search(self, query: str) -> NaturalSearchResult:
        if not query.strip():
            raise NaturalSearchParserError

        try:
            intent = self.parser.parse(query)
        except Exception:
            raise NaturalSearchParserError from None

        try:
            planned_requests = self.planner.plan(intent)
            if not planned_requests:
                raise ValueError("planner returned no search requests")
        except Exception:
            raise NaturalSearchPlanningError from None

        try:
            resolved_location = self.location_resolver.resolve(
                intent.search_request.location
            )
        except LocationResolutionError:
            raise NaturalSearchLocationError from None
        except LocationResolverUnavailable:
            raise NaturalSearchLocationProviderError from None
        except Exception:
            raise NaturalSearchLocationProviderError from None

        if resolved_location is not None:
            planned_requests = [
                request.model_copy(update={"location": resolved_location.zip})
                for request in planned_requests
            ]

        merged_listings: list[VehicleListing] = []
        try:
            for request in planned_requests:
                provider_params = request.model_dump()
                if resolved_location is not None and resolved_location.city is not None:
                    provider_params["distance"] = (
                        get_settings().auto_dev_search_distance_miles
                    )
                response = self.auto_dev_client.search_listings(
                    **provider_params,
                    limit=10,
                )
                merged_listings.extend(normalize_listings(response))
        except Exception:
            raise NaturalSearchProviderError from None

        listings = _deduplicate_by_vin(merged_listings)
        if not listings:
            return NaturalSearchResult(planned_requests, listings, [])

        try:
            context = SearchRankingContext.from_intent(intent)
            ranking_result = self.ranking_service.rank_listings(context, listings)
            validate_ranking_result(ranking_result, listings)
        except Exception:
            raise NaturalSearchRankingError from None

        try:
            risk_assessments = self.risk_analyzer.analyze(listings)
            ranked_listings = combine_ranked_results(
                ranking_result,
                risk_assessments,
                listings,
            )
        except Exception:
            raise NaturalSearchRiskError from None
        return NaturalSearchResult(planned_requests, listings, ranked_listings)


def _deduplicate_by_vin(listings: list[VehicleListing]) -> list[VehicleListing]:
    unique: list[VehicleListing] = []
    seen_vins: set[str] = set()
    for listing in listings:
        if listing.vin and listing.vin.strip():
            vin_key = listing.vin.strip().upper()
            if vin_key in seen_vins:
                continue
            seen_vins.add(vin_key)
        unique.append(listing)
    return unique
