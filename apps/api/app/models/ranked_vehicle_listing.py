from pydantic import BaseModel, Field

from .vehicle_listing import VehicleListing


class RankedVehicleListing(BaseModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=100)
    reason: str
    listing: VehicleListing