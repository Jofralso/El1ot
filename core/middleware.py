"""
Request instrumentation middleware for Prometheus metrics.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.monitoring import request_count, request_duration


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Collect request count and duration for all routes."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        request_count.labels(method=method, endpoint=path, status=response.status_code).inc()
        request_duration.labels(method=method, endpoint=path).observe(elapsed)

        return response
