from app.models import (
    AIRankingResult,
    ListingRiskAssessment,
    RankedVehicleSearchResult,
    VehicleListing,
)
from app.services.listing_risk import validate_listing_risk_result
from app.services.ranking import validate_ranking_result


def combine_ranked_results(
    ranking_result: AIRankingResult,
    risk_assessments: list[ListingRiskAssessment],
    listings: list[VehicleListing],
) -> list[RankedVehicleSearchResult]:
    validate_ranking_result(ranking_result, listings)
    ordered_risk_assessments = validate_listing_risk_result(risk_assessments, listings)
    listings_by_vin = {
        listing.vin.strip().upper(): listing
        for listing in listings
        if listing.vin and listing.vin.strip()
    }
    risks_by_vin = {
        assessment.vin.strip().upper(): assessment
        for assessment in ordered_risk_assessments
    }

    combined: list[RankedVehicleSearchResult] = []
    for ranking in ranking_result.rankings:
        vin_key = ranking.vin.strip().upper()
        combined.append(
            RankedVehicleSearchResult(
                rank=ranking.rank,
                score=ranking.score,
                reason=ranking.reason,
                risk=risks_by_vin[vin_key],
                listing=listings_by_vin[vin_key],
            )
        )
    return combined
