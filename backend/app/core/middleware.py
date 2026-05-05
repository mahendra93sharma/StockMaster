"""Security middleware: request ID injection, security headers, rate limiting."""

import time
import uuid
from collections import defaultdict
from contextlib import suppress

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Remove server header if present
        with suppress(KeyError):
            del response.headers["server"]
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID for tracing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window rate limiter per IP.

    NOTE: For production multi-instance deployments, replace with Redis-backed limiter.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60.0

        # Clean old entries
        hits = self._hits[client_ip]
        self._hits[client_ip] = [t for t in hits if t > window_start]

        if len(self._hits[client_ip]) >= self.rpm:
            return Response(
                content='{"error":{"code":"RATE_LIMITED","message":"Too many requests"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        self._hits[client_ip].append(now)
        return await call_next(request)
