from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    make: Optional[str] = Field(
        None,
        description="Vehicle make to search for",
    )
    model: Optional[str] = Field(
        None,
        description="Vehicle model to search for",
    )
    min_year: Optional[int] = Field(
        None,
        ge=1886,
        description="Minimum model year",
    )
    max_year: Optional[int] = Field(
        None,
        ge=1886,
        description="Maximum model year",
    )
    min_price: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum price",
    )
    max_price: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum price",
    )
    min_mileage: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum mileage",
    )
    max_mileage: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum mileage",
    )
    location: Optional[str] = Field(
        None,
        description="Location where the search should be performed",
    )
