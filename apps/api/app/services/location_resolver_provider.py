from app.services.location_resolver import LocationResolver, NominatimLocationResolver


def get_location_resolver() -> LocationResolver:
    return NominatimLocationResolver()
