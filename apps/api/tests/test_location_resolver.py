import pytest

from app.services import location_resolver
from app.services.location_resolver import (
    AmbiguousLocationError,
    LocationNotFoundError,
    LocationResolverUnavailable,
    NominatimLocationResolver,
)


def place(name: str, state: str, *, field: str = "city", lat: str = "32.7", lon: str = "-96.8"):
    return {
        "lat": lat,
        "lon": lon,
        "address": {field: name, "state": state, "country_code": "us"},
    }


@pytest.fixture(autouse=True)
def clear_location_cache():
    location_resolver._resolve_city.cache_clear()
    location_resolver._resolve_location_to_zip.cache_clear()


def test_direct_zip_does_not_call_geocoder(monkeypatch) -> None:
    monkeypatch.setattr(
        location_resolver,
        "_resolve_city",
        lambda *_args: pytest.fail("ZIP lookup should bypass geocoding"),
    )

    resolved = NominatimLocationResolver().resolve("75001")

    assert resolved is not None
    assert (resolved.zip, resolved.city, resolved.state) == ("75001", None, None)


@pytest.mark.parametrize(
    ("query", "city", "state", "zip_code"),
    [
        ("Dallas", "Dallas", "TX", "75242"),
        ("Dallas, TX", "Dallas", "TX", "75242"),
        ("Denton", "Denton", "TX", "76201"),
        ("Denton, TX", "Denton", "TX", "76201"),
    ],
)
def test_city_search_resolves_to_reverse_geocoded_zip(
    monkeypatch,
    query: str,
    city: str,
    state: str,
    zip_code: str,
) -> None:
    calls = []

    def fake_get_json(url, params, user_agent):
        calls.append((url, params, user_agent))
        if url.endswith("/search"):
            return [place(city, "Texas")]
        return {"address": {"postcode": zip_code, "state": "Texas"}}

    monkeypatch.setattr(location_resolver, "_get_json", fake_get_json)

    resolved = NominatimLocationResolver(
        base_url="https://geocoder.example",
        user_agent="test-agent",
    ).resolve(query)

    assert resolved is not None
    assert (resolved.city, resolved.state, resolved.zip) == (city, state, zip_code)
    assert [call[0].rsplit("/", 1)[-1] for call in calls] == ["search", "reverse"]
    assert calls[0][1]["countrycodes"] == "us"
    assert calls[1][1]["lat"] == "32.7"
    assert all(call[2] == "test-agent" for call in calls)


def test_denton_prefers_exact_city_over_same_name_town(monkeypatch) -> None:
    monkeypatch.setattr(
        location_resolver,
        "_get_json",
        lambda url, _params, _user_agent: (
            [
                place("Denton", "Maryland", field="town", lat="38.8", lon="-75.8"),
                place("Denton", "Texas"),
            ]
            if url.endswith("/search")
            else {"address": {"postcode": "76201", "state": "Texas"}}
        ),
    )

    resolved = NominatimLocationResolver().resolve("Denton")

    assert resolved is not None
    assert (resolved.city, resolved.state, resolved.zip) == ("Denton", "TX", "76201")


def test_unknown_place_is_not_resolved(monkeypatch) -> None:
    monkeypatch.setattr(location_resolver, "_get_json", lambda *_args: [])

    with pytest.raises(LocationNotFoundError):
        NominatimLocationResolver().resolve("No Such Place")


def test_multiple_same_level_city_matches_are_rejected_as_ambiguous(monkeypatch) -> None:
    monkeypatch.setattr(
        location_resolver,
        "_get_json",
        lambda *_args: [
            place("Springfield", "Illinois"),
            place("Springfield", "Missouri", lat="37.2", lon="-93.3"),
        ],
    )

    with pytest.raises(AmbiguousLocationError):
        NominatimLocationResolver().resolve("Springfield")


def test_resolver_network_failure_has_sanitized_error(monkeypatch) -> None:
    def fail_request(*_args):
        raise RuntimeError("secret provider details")

    monkeypatch.setattr(location_resolver, "_get_json", fail_request)

    with pytest.raises(LocationResolverUnavailable) as exc_info:
        NominatimLocationResolver().resolve("Dallas")

    assert "secret provider details" not in str(exc_info.value)


def test_missing_location_does_not_call_geocoder(monkeypatch) -> None:
    monkeypatch.setattr(
        location_resolver,
        "_resolve_city",
        lambda *_args: pytest.fail("No location should skip geocoding"),
    )

    assert NominatimLocationResolver().resolve(None) is None
    assert NominatimLocationResolver().resolve("  ") is None


def test_successful_location_is_cached(monkeypatch) -> None:
    calls = []

    def fake_get_json(url, _params, _user_agent):
        calls.append(url)
        if url.endswith("/search"):
            return [place("Dallas", "Texas")]
        return {"address": {"postcode": "75242", "state": "Texas"}}

    monkeypatch.setattr(location_resolver, "_get_json", fake_get_json)
    resolver = NominatimLocationResolver()

    resolver.resolve("Dallas")
    resolver.resolve("Dallas")

    assert [url.rsplit("/", maxsplit=1)[-1] for url in calls] == ["search", "reverse"]
