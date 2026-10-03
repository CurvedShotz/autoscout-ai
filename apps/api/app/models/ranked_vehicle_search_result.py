from pydantic import BaseModel, Field

from .listing_risk import ListingRiskAssessment
from .vehicle_listing import VehicleListing


class RankedVehicleSearchResult(BaseModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=100)
    reason: str
    risk: ListingRiskAssessment
    listing: VehicleListing
