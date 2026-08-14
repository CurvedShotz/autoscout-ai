import httpx

from app.services.auto_dev_client import AutoDevClient


def test_decode_vin_calls_auto_dev_with_bearer_token(monkeypatch) -> None:
    captured = {}

    def fake_get(url: str, *, headers: dict | None = None, timeout: float | None = None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        request = httpx.Request("GET", url, headers=headers or {})
        return httpx.Response(
            200,
            request=request,
            json={
                "vin": "1HGBH41JXMN109186",
                "make": "Honda",
                "model": "Civic",
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = AutoDevClient(api_key="test-secret-key")
    result = client.decode_vin("1HGBH41JXMN109186")

    assert result["make"] == "Honda"
    assert captured["url"] == "https://api.auto.dev/vin/1HGBH41JXMN109186"
    assert captured["headers"]["Authorization"] == "Bearer test-secret-key"
    assert captured["timeout"] == 15.0


def test_search_listings_maps_bounded_ranges_and_auth(monkeypatch) -> None:
    captured = {}

    def fake_get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float | None = None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        request = httpx.Request("GET", url, params=params or {}, headers=headers or {})
        return httpx.Response(
            200,
            request=request,
            json={
                "listings": [
                    {"make": "Toyota", "model": "Camry", "year": 2022, "price": 25000},
                ]
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = AutoDevClient(api_key="test-secret-key")
    result = client.search_listings(
        make="Toyota",
        model="Camry",
        min_year=2020,
        max_year=2024,
        min_price=20000,
        max_price=30000,
        min_mileage=10000,
        max_mileage=50000,
        location="Dallas, TX",
        limit=25,
    )

    assert result["listings"][0]["make"] == "Toyota"
    assert captured["url"] == "https://api.auto.dev/listings"
    assert captured["headers"]["Authorization"] == "Bearer test-secret-key"
    assert captured["params"] == {
        "vehicle.make": "Toyota",
        "vehicle.model": "Camry",
        "vehicle.year": "2020-2024",
        "retailListing.price": "20000-30000",
        "retailListing.miles": "10000-50000",
        "limit": 25,
    }
    assert captured["timeout"] == 15.0
    assert "location" not in captured["params"]
    assert "zip" not in captured["params"]


def test_search_listings_supports_min_only_and_max_only_ranges(monkeypatch) -> None:
    captured = {}

    def fake_get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float | None = None):
        captured["params"] = params
        captured["headers"] = headers
        request = httpx.Request("GET", url, params=params or {}, headers=headers or {})
        return httpx.Response(200, request=request, json={"listings": []})

    monkeypatch.setattr(httpx, "get", fake_get)

    client = AutoDevClient(api_key="test-secret-key")
    client.search_listings(
        min_year=2020,
        max_price=20000,
        max_mileage=100000,
        location="75001",
    )

    assert captured["params"] == {
        "vehicle.year": "2020-",
        "retailListing.price": "-20000",
        "retailListing.miles": "-100000",
        "zip": "75001",
    }
    assert captured["headers"]["Authorization"] == "Bearer test-secret-key"


def test_search_listings_omits_none_filters_and_keeps_zip_behavior(monkeypatch) -> None:
    captured = {}

    def fake_get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float | None = None):
        captured["params"] = params
        captured["headers"] = headers
        request = httpx.Request("GET", url, params=params or {}, headers=headers or {})
        return httpx.Response(200, request=request, json={"listings": []})

    monkeypatch.setattr(httpx, "get", fake_get)

    client = AutoDevClient(api_key="test-secret-key")
    client.search_listings(make="Honda", location="75001")

    assert captured["params"] == {
        "vehicle.make": "Honda",
        "zip": "75001",
    }
    assert captured["headers"]["Authorization"] == "Bearer test-secret-key"
