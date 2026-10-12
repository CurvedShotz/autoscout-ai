from __future__ import annotations

from math import ceil
from threading import Lock
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SearchRateLimitMiddleware(BaseHTTPMiddleware):
    _SEARCH_PATHS = {"/search", "/search/natural"}
    _MAX_TRACKED_CLIENTS = 10_000

    def __init__(
        self,
        app,
        *,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = Lock()
        self._request_count = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "POST" or request.url.path not in self._SEARCH_PATHS:
            return await call_next(request)

        retry_after = self._record_search(self._client_key(request), monotonic())
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Search limit reached. Please wait before trying again."
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    def _record_search(self, client_key: str, now: float) -> int | None:
        with self._lock:
            self._request_count += 1
            if self._request_count % 256 == 0:
                self._remove_expired_buckets(now)

            bucket = self._buckets.get(client_key)
            if bucket is None:
                if len(self._buckets) >= self._MAX_TRACKED_CLIENTS:
                    self._remove_expired_buckets(now)
                    if len(self._buckets) >= self._MAX_TRACKED_CLIENTS:
                        return self.window_seconds
                self._buckets[client_key] = (now, 1)
                return None

            window_start, request_count = bucket
            elapsed = now - window_start
            if elapsed >= self.window_seconds:
                self._buckets[client_key] = (now, 1)
                return None

            if request_count >= self.max_requests:
                return max(1, ceil(self.window_seconds - elapsed))

            self._buckets[client_key] = (window_start, request_count + 1)
            return None

    def _remove_expired_buckets(self, now: float) -> None:
        expired_clients = [
            client
            for client, (window_start, _) in self._buckets.items()
            if now - window_start >= self.window_seconds
        ]
        for client in expired_clients:
            del self._buckets[client]

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            forwarded_client = forwarded_for.rsplit(",", maxsplit=1)[-1].strip()
            if forwarded_client:
                return forwarded_client

        return request.client.host if request.client is not None else "unknown"
