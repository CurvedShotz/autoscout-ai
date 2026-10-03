from enum import StrEnum

from pydantic import BaseModel, Field, StrictInt, model_validator


class ListingRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ListingRiskAssessment(BaseModel):
    """A caution assessment, not a determination that a listing is fraudulent."""

    vin: str
    risk_score: StrictInt = Field(
        ge=0,
        le=100,
        description=(
            "0 means little or no suspicious evidence in the provided data; "
            "100 means highly anomalous and deserving strong caution."
        ),
    )
    risk_level: ListingRiskLevel = Field(
        description=(
            "low for scores 0-29, medium for scores 30-69, "
            "and high for scores 70-100"
        )
    )
    signals: list[str] = Field(
        description="Specific caution signals supported by the provided listing data"
    )
    explanation: str = Field(
        description="A concise, evidence-based explanation that avoids fraud claims"
    )

    @model_validator(mode="after")
    def validate_level_matches_score(self) -> "ListingRiskAssessment":
        if self.risk_score < 30:
            expected_level = ListingRiskLevel.LOW
        elif self.risk_score < 70:
            expected_level = ListingRiskLevel.MEDIUM
        else:
            expected_level = ListingRiskLevel.HIGH
        if self.risk_level != expected_level:
            raise ValueError("risk_level must match risk_score range")
        return self


class ListingRiskAnalysisResult(BaseModel):
    assessments: list[ListingRiskAssessment]
