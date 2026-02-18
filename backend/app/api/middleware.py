"""API middleware for request processing."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"Response: {response.status_code}",
                extra={
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s",
                },
            )

            # Add process time header
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s",
                },
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits and process request."""
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"

        # Get current time
        current_time = time.time()
        minute_ago = current_time - 60

        # Clean old requests
        if client_id in self.request_counts:
            self.request_counts[client_id] = [
                t for t in self.request_counts[client_id] if t > minute_ago
            ]
        else:
            self.request_counts[client_id] = []

        # Check rate limit
        if len(self.request_counts[client_id]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_id}")
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"},
            )

        # Add current request
        self.request_counts[client_id].append(current_time)

        # Process request
        response = await call_next(request)
        return response
