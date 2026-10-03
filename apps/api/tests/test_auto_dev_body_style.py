import httpx

from app.services.auto_dev_client import AutoDevClient


def test_search_listings_maps_verified_body_style_filter(monkeypatch) -> None:
    captured = {}

    def fake_get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float | None = None):
        captured["params"] = params
        request = httpx.Request("GET", url, params=params or {}, headers=headers or {})
        return httpx.Response(200, request=request, json={"data": []})

    monkeypatch.setattr(httpx, "get", fake_get)

    AutoDevClient(api_key="test-secret-key").search_listings(
        body_style="sedan",
        max_mileage=60_000,
    )

    assert captured["params"] == {
        "vehicle.bodyStyle": "sedan",
        "retailListing.miles": "-60000",
    }
