"""API middleware for request processing."""

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_STALE_CLIENT_THRESHOLD = 300  # seconds before a silent client's entry is evicted


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.monotonic()

        logger.info(
            "Request: %s %s",
            request.method,
            request.url.path,
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
            process_time = time.monotonic() - start_time

            logger.info(
                "Response: %s in %.3fs",
                response.status_code,
                process_time,
                extra={
                    "status_code": response.status_code,
                    "process_time_s": round(process_time, 3),
                },
            )

            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            return response

        except Exception as e:
            process_time = time.monotonic() - start_time
            logger.error(
                "Request failed after %.3fs: %s",
                process_time,
                e,
                extra={"process_time_s": round(process_time, 3)},
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiting middleware.

    Evicts stale client entries periodically to prevent unbounded memory growth.
    """

    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._request_counts: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    def _cleanup_stale_clients(self, now: float) -> None:
        """Remove entries for clients that have not sent requests recently."""
        if now - self._last_cleanup < _STALE_CLIENT_THRESHOLD:
            return
        cutoff = now - _STALE_CLIENT_THRESHOLD
        stale = [cid for cid, ts in self._request_counts.items() if not ts or ts[-1] < cutoff]
        for cid in stale:
            del self._request_counts[cid]
        self._last_cleanup = now

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits and process request."""
        client_id = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - 60

        # Evict expired timestamps for this client
        timestamps = self._request_counts[client_id]
        self._request_counts[client_id] = [t for t in timestamps if t > window_start]

        # Periodically evict idle clients
        self._cleanup_stale_clients(now)

        if len(self._request_counts[client_id]) >= self.requests_per_minute:
            logger.warning("Rate limit exceeded for %s", client_id)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": 60},
                headers={"Retry-After": "60"},
            )

        self._request_counts[client_id].append(now)
        return await call_next(request)
