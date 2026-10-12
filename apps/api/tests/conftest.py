import pytest

from app.core.rate_limit import SearchRateLimitMiddleware


@pytest.fixture(autouse=True)
def reset_search_rate_limit_state():
    yield

    from app.main import app

    middleware = app.middleware_stack
    while middleware is not None:
        if isinstance(middleware, SearchRateLimitMiddleware):
            with middleware._lock:
                middleware._buckets.clear()
                middleware._request_count = 0
            break
        middleware = getattr(middleware, "app", None)
