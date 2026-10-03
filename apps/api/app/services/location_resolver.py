from __future__ import annotations

import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings

_ZIP_PATTERN = re.compile(r"^\d{5}$")
_STATE_NAMES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}
_STATE_CODES = {code.casefold(): code for code in _STATE_NAMES.values()}
_STATE_CODES.update({name: code for name, code in _STATE_NAMES.items()})
_RATE_LIMIT_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0
_MIN_REQUEST_INTERVAL_SECONDS = 1.0


class LocationResolutionError(ValueError):
    """Base exception for location input that cannot be resolved."""


class LocationNotFoundError(LocationResolutionError):
    pass


class AmbiguousLocationError(LocationResolutionError):
    pass


class LocationResolverUnavailable(RuntimeError):
    """Raised when the external location service is unavailable or unusable."""


@dataclass(frozen=True)
class ResolvedLocation:
    original_query: str
    zip: str
    city: str | None = None
    state: str | None = None


class LocationResolver(ABC):
    @abstractmethod
    def resolve(self, location: str | None) -> ResolvedLocation | None:
        """Resolve a user location to a ZIP, or return None when not specified."""


class NominatimLocationResolver(LocationResolver):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.location_geocoder_base_url).rstrip("/")
        self.user_agent = user_agent or settings.location_geocoder_user_agent

    def resolve(self, location: str | None) -> ResolvedLocation | None:
        if location is None or not location.strip():
            return None

        query = location.strip()
        if _ZIP_PATTERN.fullmatch(query):
            return ResolvedLocation(original_query=query, zip=query)

        try:
            city, state, zip_code = _resolve_location_to_zip(
                query,
                self.base_url,
                self.user_agent,
            )
        except (LocationResolutionError, LocationResolverUnavailable):
            raise
        except Exception:
            raise LocationResolverUnavailable from None

        return ResolvedLocation(
            original_query=query,
            zip=zip_code,
            city=city,
            state=state,
        )


def _requested_state(query: str) -> tuple[str, str | None]:
    parts = [part.strip() for part in query.rsplit(",", maxsplit=1)]
    if len(parts) == 2:
        state = _state_code(parts[1])
        if state is not None:
            return parts[0], state
    return query, None


def _state_code(value: str) -> str | None:
    return _STATE_CODES.get(value.strip().casefold())


@lru_cache(maxsize=256)
def _resolve_location_to_zip(
    query: str,
    base_url: str,
    user_agent: str,
) -> tuple[str, str, str]:
    city, state, latitude, longitude = _resolve_city(query, base_url, user_agent)
    try:
        reverse = _get_json(
            f"{base_url}/reverse",
            {
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 18,
            },
            user_agent,
        )
    except Exception:
        raise LocationResolverUnavailable from None

    address = reverse.get("address") if isinstance(reverse, dict) else None
    if not isinstance(address, dict):
        raise LocationResolverUnavailable

    zip_match = re.match(r"^(\d{5})", str(address.get("postcode", "")))
    if not zip_match or _state_code(str(address.get("state", ""))) != state:
        raise LocationNotFoundError

    return city, state, zip_match.group(1)


@lru_cache(maxsize=256)
def _resolve_city(
    query: str,
    base_url: str,
    user_agent: str,
) -> tuple[str, str, str, str]:
    place_query, requested_state = _requested_state(query)
    try:
        results = _get_json(
            f"{base_url}/search",
            {
                "q": f"{place_query}, United States",
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 10,
                "countrycodes": "us",
            },
            user_agent,
        )
    except Exception:
        raise LocationResolverUnavailable from None

    if not isinstance(results, list):
        raise LocationResolverUnavailable

    place_matches: list[tuple[str, str, str, str, str]] = []
    wanted = place_query.casefold()
    for result in results:
        if not isinstance(result, dict):
            continue
        address = result.get("address")
        if not isinstance(address, dict):
            continue

        city_field = next(
            (
                field
                for field in ("city", "municipality", "town", "village", "hamlet")
                if isinstance(address.get(field), str)
                and address[field].casefold() == wanted
            ),
            None,
        )
        if city_field is None:
            continue

        state_name = address.get("state")
        city = address[city_field]
        state = _state_code(state_name) if isinstance(state_name, str) else None
        if state is None or (requested_state is not None and state != requested_state):
            continue

        latitude = result.get("lat")
        longitude = result.get("lon")
        if not isinstance(latitude, str) or not isinstance(longitude, str):
            continue
        place_matches.append((city, state, city_field, latitude, longitude))

    if not place_matches:
        if requested_state is not None:
            raise LocationNotFoundError
        raise LocationNotFoundError

    # Prefer a city/municipality over a town or village when both share a name.
    city_matches = [
        match
        for match in place_matches
        if match[2] in {"city", "municipality"}
    ]
    candidates = city_matches or place_matches
    distinct_places = {(match[0].casefold(), match[1]) for match in candidates}
    if len(distinct_places) > 1:
        raise AmbiguousLocationError
    if len(candidates) != 1:
        raise AmbiguousLocationError

    city, state, _, latitude, longitude = candidates[0]
    return city, state, latitude, longitude


def _get_json(url: str, params: dict[str, Any], user_agent: str) -> Any:
    global _LAST_REQUEST_AT

    with _RATE_LIMIT_LOCK:
        elapsed = time.monotonic() - _LAST_REQUEST_AT
        if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        _LAST_REQUEST_AT = time.monotonic()
        response = httpx.get(
            url,
            params=params,
            headers={"User-Agent": user_agent},
            timeout=10.0,
        )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            raise LocationResolverUnavailable from None
