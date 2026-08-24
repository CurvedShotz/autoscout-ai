from abc import ABC, abstractmethod
from typing import Any

from app.models import AIRankingResult, SearchRequest, VehicleListing


class AIRankingService(ABC):
    @abstractmethod
    def rank_listings(
        self,
        search_request: SearchRequest,
        listings: list[VehicleListing],
    ) -> AIRankingResult:
        raise NotImplementedError


def validate_ranking_result(
    result: AIRankingResult,
    listings: list[VehicleListing],
) -> AIRankingResult:
    candidate_vins = {listing.vin for listing in listings if listing.vin is not None}
    returned_vins = [ranking.vin for ranking in result.rankings]

    if len(result.rankings) > len(listings):
        raise ValueError("Ranking result contains more cars than input candidates")
    if len(returned_vins) != len(set(returned_vins)):
        raise ValueError("Ranking result contains duplicate VINs")
    if any(vin not in candidate_vins for vin in returned_vins):
        raise ValueError("Ranking result contains an unknown VIN")

    ranks = [ranking.rank for ranking in result.rankings]
    if len(ranks) != len(set(ranks)) or sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise ValueError("Ranking result ranks must be unique and sequential starting at 1")

    return result


def ranking_input(search_request: SearchRequest, listings: list[VehicleListing]) -> list[dict[str, Any]]:
    return [
        {
            "search_request": search_request.model_dump(mode="json"),
            "candidate_listings": [listing.model_dump(mode="json") for listing in listings],
        }
    ]