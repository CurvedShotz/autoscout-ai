from collections.abc import Mapping
from typing import Any

from app.models import VehicleListing


def _first_value(source: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in source:
            return source[name]
    return None


def normalize_listing(raw_listing: Mapping[str, Any]) -> VehicleListing:
    vehicle = raw_listing.get("vehicle") or {}
    retail_listing = raw_listing.get("retailListing") or raw_listing.get("retail_listing") or {}
    history = raw_listing.get("history") or {}

    return VehicleListing(
        vin=_first_value(vehicle, "vin") or _first_value(raw_listing, "vin"),
        year=_first_value(vehicle, "year") or _first_value(raw_listing, "year"),
        make=_first_value(vehicle, "make") or _first_value(raw_listing, "make"),
        model=_first_value(vehicle, "model") or _first_value(raw_listing, "model"),
        trim=_first_value(vehicle, "trim"),
        body_style=_first_value(vehicle, "bodyStyle", "body_style"),
        drivetrain=_first_value(vehicle, "drivetrain"),
        engine=_first_value(vehicle, "engine"),
        transmission=_first_value(vehicle, "transmission"),
        exterior_color=_first_value(vehicle, "exteriorColor", "exterior_color"),
        fuel=_first_value(vehicle, "fuel", "fuelType", "fuel_type"),
        price=_first_value(retail_listing, "price"),
        mileage=_first_value(retail_listing, "miles", "mileage"),
        city=_first_value(retail_listing, "city"),
        state=_first_value(retail_listing, "state"),
        zip=_first_value(retail_listing, "zip", "zipCode", "zip_code"),
        dealer=_first_value(retail_listing, "dealer"),
        primary_image=_first_value(retail_listing, "primaryImage", "primary_image"),
        listing_url=_first_value(retail_listing, "vdp", "listingUrl", "listing_url"),
        carfax_url=_first_value(retail_listing, "carfaxUrl", "carfax_url"),
        accident_count=_first_value(history, "accidentCount", "accident_count"),
        has_accidents=_first_value(history, "accidents", "hasAccidents", "has_accidents"),
        owner_count=_first_value(history, "ownerCount", "owner_count"),
        one_owner=_first_value(history, "oneOwner", "one_owner"),
        usage_type=_first_value(history, "usageType", "usage_type"),
        created_at=_first_value(raw_listing, "createdAt", "created_at"),
    )


def normalize_listings(raw_response: Any) -> list[VehicleListing]:
    if isinstance(raw_response, Mapping):
        raw_listings = raw_response.get("data", raw_response.get("listings", []))
    else:
        raw_listings = raw_response

    if not isinstance(raw_listings, list):
        return []

    return [normalize_listing(listing) for listing in raw_listings if isinstance(listing, Mapping)]