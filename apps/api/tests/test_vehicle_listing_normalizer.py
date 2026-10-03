import pytest

from app.services.vehicle_listing_normalizer import (
    InvalidListingResponseError,
    normalize_listing,
    normalize_listings,
)


def test_normalize_listing_maps_nested_auto_dev_fields() -> None:
    listing = normalize_listing(
        {
            "vehicle": {
                "vin": "1HGBH41JXMN109186",
                "year": 2022,
                "make": "Honda",
                "model": "Civic",
                "bodyStyle": "Sedan",
                "exteriorColor": "Blue",
            },
            "retailListing": {
                "price": 25000,
                "miles": 12000,
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "vdp": "https://example.test/listing",
            },
            "history": {"accidentCount": 0, "accidents": False},
            "createdAt": "2026-01-01T00:00:00Z",
            "api": {"version": "v2"},
        }
    )

    assert listing.vin == "1HGBH41JXMN109186"
    assert listing.body_style == "Sedan"
    assert listing.price == 25000
    assert listing.mileage == 12000
    assert listing.has_accidents is False
    assert listing.listing_url == "https://example.test/listing"
    assert listing.created_at == "2026-01-01T00:00:00Z"


def test_normalize_listings_reads_real_auto_dev_data_response() -> None:
    listings = normalize_listings(
        {
            "data": [
                {
                    "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022},
                    "retailListing": {"vdp": "https://example.test/camry", "price": 24000},
                    "history": {"accidents": True},
                }
            ],
            "api": {"version": "v2"},
        }
    )

    assert len(listings) == 1
    assert listings[0].make == "Toyota"
    assert listings[0].has_accidents is True
    assert listings[0].listing_url == "https://example.test/camry"


def test_normalize_listing_leaves_missing_fields_as_none() -> None:
    listing = normalize_listings({"data": [{"vehicle": {"make": "Honda"}}]})[0]

    assert listing.make == "Honda"
    assert listing.model is None
    assert listing.price is None
    assert listing.accident_count is None


@pytest.mark.parametrize("response", [{"data": []}, {"listings": []}, []])
def test_normalize_listings_accepts_valid_empty_results(response) -> None:
    assert normalize_listings(response) == []


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": [None]},
        {"unexpected": []},
    ],
)
def test_normalize_listings_rejects_unusable_response_shapes(response) -> None:
    with pytest.raises(InvalidListingResponseError):
        normalize_listings(response)