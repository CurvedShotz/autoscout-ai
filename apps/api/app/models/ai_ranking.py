from pydantic import BaseModel, Field


class AIRankedListing(BaseModel):
    vin: str
    score: float = Field(ge=0, le=100)
    rank: int = Field(gt=0)
    reason: str


class AIRankingResult(BaseModel):
    rankings: list[AIRankedListing]