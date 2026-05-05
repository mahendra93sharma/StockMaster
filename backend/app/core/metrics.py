"""Lightweight metrics endpoint (no external dependency).

Exposes basic request counts and latency in Prometheus text format.
For production, consider integrating prometheus-fastapi-instrumentator.
"""

import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

router = APIRouter(tags=["infra"])

# In-memory counters (reset on restart — sufficient for single-instance)
_request_count: dict[str, int] = defaultdict(int)
_request_latency_sum: dict[str, float] = defaultdict(float)
_error_count: dict[str, int] = defaultdict(int)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect per-path request count and latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        method = request.method
        key = f"{method} {path}"

        _request_count[key] += 1
        _request_latency_sum[key] += elapsed

        if response.status_code >= 500:
            _error_count[key] += 1

        return response


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus-compatible text metrics."""
    lines = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
    ]
    for key, count in sorted(_request_count.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_requests_total{{method="{method}",path="{path}"}} {count}')

    lines.extend([
        "# HELP http_request_duration_seconds_sum Sum of request durations",
        "# TYPE http_request_duration_seconds_sum counter",
    ])
    for key, total in sorted(_request_latency_sum.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.4f}')

    lines.extend([
        "# HELP http_errors_total Total 5xx errors",
        "# TYPE http_errors_total counter",
    ])
    for key, count in sorted(_error_count.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_errors_total{{method="{method}",path="{path}"}} {count}')

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; charset=utf-8")
