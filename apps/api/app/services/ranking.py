from abc import ABC, abstractmethod
from typing import Any

from app.models import (
    AIRankingResult,
    SearchRankingContext,
    SearchRequest,
    VehicleListing,
)

RankingContext = SearchRequest | SearchRankingContext

RANKING_SYSTEM_GUIDANCE = (
    "Compare each provided vehicle candidate against the user's request and rank "
    "only by user fit and purchase tradeoffs. Consider price and value, mileage, "
    "year, accident and owner history, user preferences, target price and mileage, "
    "body style, overall desirability, and other relevant tradeoffs. Do not invent "
    "vehicles or VINs. Keep ranking separate from listing-risk analysis: explain "
    "how facts affect fit or desirability, but leave formal anomaly and scam-risk "
    "judgments to the dedicated listing-risk analyzer. Do not characterize listings "
    "as high-risk, low-risk, suspicious, a scam, fraudulent, a fake listing, or an "
    "anomaly risk. You may state grounded tradeoffs, such as reported accidents "
    "reducing desirability, very high mileage weakening fit, or an unusually low "
    "listed price making value difficult to assess."
)


class AIRankingService(ABC):
    @abstractmethod
    def rank_listings(
        self,
        search_request: RankingContext,
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


def ranking_input(
    search_context: RankingContext,
    listings: list[VehicleListing],
) -> list[dict[str, Any]]:
    semantic_intent: SearchRankingContext | None = None
    if isinstance(search_context, SearchRequest):
        search_request = search_context
    else:
        semantic_intent = search_context
        search_request = semantic_intent.search_request

    ranking_payload: dict[str, Any] = {
        "search_request": search_request.model_dump(mode="json"),
        "candidate_listings": [listing.model_dump(mode="json") for listing in listings],
    }
    if semantic_intent is not None and any(
        (
            semantic_intent.makes,
            semantic_intent.models,
            semantic_intent.body_styles,
            semantic_intent.target_price is not None,
            semantic_intent.target_mileage is not None,
            semantic_intent.preferences,
        )
    ):
        ranking_payload["semantic_intent"] = {
            "makes": semantic_intent.makes,
            "models": semantic_intent.models,
            "body_styles": semantic_intent.body_styles,
            "target_price": semantic_intent.target_price,
            "target_mileage": semantic_intent.target_mileage,
            "preferences": semantic_intent.preferences,
        }
    return [ranking_payload]