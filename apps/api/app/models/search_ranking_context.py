from pydantic import BaseModel, Field

from .search_request import SearchRequest
from .user_search_intent import UserSearchIntent


class SearchRankingContext(BaseModel):
    search_request: SearchRequest
    makes: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    body_styles: list[str] = Field(default_factory=list)
    target_price: int | None = None
    target_mileage: int | None = None
    preferences: list[str] = Field(default_factory=list)

    @classmethod
    def from_intent(cls, intent: UserSearchIntent) -> "SearchRankingContext":
        return cls(
            search_request=intent.search_request,
            makes=intent.makes,
            models=intent.models,
            body_styles=intent.body_styles,
            target_price=intent.target_price,
            target_mileage=intent.target_mileage,
            preferences=intent.preferences,
        )
