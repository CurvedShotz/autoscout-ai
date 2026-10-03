from abc import ABC, abstractmethod

from app.models import ListingRiskAssessment, VehicleListing


class ListingRiskAnalyzer(ABC):
    @abstractmethod
    def analyze(
        self,
        listings: list[VehicleListing],
    ) -> list[ListingRiskAssessment]:
        raise NotImplementedError


def validate_listing_risk_result(
    assessments: list[ListingRiskAssessment],
    listings: list[VehicleListing],
) -> list[ListingRiskAssessment]:
    candidate_vins = validate_risk_candidates(listings)
    assessment_vins: dict[str, ListingRiskAssessment] = {}

    for assessment in assessments:
        vin_key = assessment.vin.strip().upper()
        if vin_key not in candidate_vins:
            raise ValueError("Risk analysis contains an unknown VIN")
        if vin_key in assessment_vins:
            raise ValueError("Risk analysis contains duplicate VIN assessments")
        assessment_vins[vin_key] = assessment

    if set(assessment_vins) != set(candidate_vins):
        raise ValueError("Risk analysis must contain one assessment per candidate")

    return [assessment_vins[listing.vin.strip().upper()] for listing in listings]


def validate_risk_candidates(listings: list[VehicleListing]) -> dict[str, str]:
    candidate_vins: dict[str, str] = {}
    for listing in listings:
        if not listing.vin or not listing.vin.strip():
            raise ValueError("Risk analysis candidates must have VINs")
        vin = listing.vin.strip()
        vin_key = vin.upper()
        if vin_key in candidate_vins:
            raise ValueError("Risk analysis candidates contain duplicate VINs")
        candidate_vins[vin_key] = vin
    return candidate_vins
