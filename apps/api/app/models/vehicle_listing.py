from pydantic import BaseModel


class VehicleListing(BaseModel):
    vin: str | None = None
    year: int | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    body_style: str | None = None
    drivetrain: str | None = None
    engine: str | None = None
    transmission: str | None = None
    exterior_color: str | None = None
    fuel: str | None = None
    price: int | float | None = None
    mileage: int | float | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    dealer: str | None = None
    primary_image: str | None = None
    listing_url: str | None = None
    carfax_url: str | None = None
    accident_count: int | None = None
    has_accidents: bool | None = None
    owner_count: int | None = None
    one_owner: bool | None = None
    usage_type: str | None = None
    created_at: str | None = None