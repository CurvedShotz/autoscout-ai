import pytest
from pydantic import ValidationError

from app.models import SearchRequest


def test_search_request_accepts_valid_filters() -> None:
    request = SearchRequest(
        make="Toyota",
        model="Corolla",
        min_year=2015,
        max_year=2022,
        min_price=5000,
        max_price=15000,
        min_mileage=10000,
        max_mileage=60000,
        location="San Francisco, CA",
    )

    assert request.make == "Toyota"
    assert request.model == "Corolla"
    assert request.min_year == 2015
    assert request.max_price == 15000
    assert request.location == "San Francisco, CA"


def test_search_request_all_fields_optional() -> None:
    request = SearchRequest()

    assert request.make is None
    assert request.model is None
    assert request.min_year is None
    assert request.max_year is None
    assert request.min_price is None
    assert request.max_price is None
    assert request.min_mileage is None
    assert request.max_mileage is None
    assert request.location is None


@pytest.mark.parametrize("kwargs", [
    {"min_price": -1},
    {"max_price": -100},
    {"min_mileage": -5},
    {"max_mileage": -200},
])
def test_search_request_rejects_negative_price_or_mileage(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**kwargs)
