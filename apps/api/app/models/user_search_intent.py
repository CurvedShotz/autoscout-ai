from pydantic import BaseModel, Field

from .search_request import SearchRequest


class UserSearchIntent(BaseModel):
    search_request: SearchRequest
    makes: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    body_styles: list[str] = Field(default_factory=list)
    target_price: int | None = Field(default=None, ge=0)
    target_mileage: int | None = Field(default=None, ge=0)
    preferences: list[str] = Field(default_factory=list)