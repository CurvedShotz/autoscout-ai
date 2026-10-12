from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import SearchRateLimitMiddleware


def test_search_endpoints_share_a_configurable_rate_limit() -> None:
    app = FastAPI()
    app.add_middleware(
        SearchRateLimitMiddleware,
        max_requests=1,
        window_seconds=60,
    )

    @app.post("/search")
    def search() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search/natural")
    def natural_search() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)

    assert (
        client.post("/search", headers={"X-Forwarded-For": "198.51.100.7"}).status_code
        == 200
    )
    limited_response = client.post(
        "/search/natural",
        headers={"X-Forwarded-For": "198.51.100.7"},
    )

    assert limited_response.status_code == 429
    assert limited_response.json() == {
        "detail": "Search limit reached. Please wait before trying again."
    }
    assert limited_response.headers["Retry-After"] == "60"


def test_health_and_non_search_requests_are_not_rate_limited() -> None:
    app = FastAPI()
    app.add_middleware(
        SearchRateLimitMiddleware,
        max_requests=1,
        window_seconds=60,
    )
    app.add_api_route("/health", lambda: {"status": "healthy"}, methods=["GET"])

    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
