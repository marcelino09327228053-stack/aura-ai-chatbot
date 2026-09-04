"""Infrastructure monitoring middleware."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.monitoring import metrics


class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        metrics.record_request()
        start = time.time()
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                metrics.record_error(
                    f"HTTP {response.status_code}",
                    path=request.url.path,
                    status_code=response.status_code,
                )
            return response
        except Exception as exc:
            metrics.record_error(str(exc), path=request.url.path, status_code=500)
            raise
        finally:
            elapsed = time.time() - start
            if elapsed > 5.0:
                metrics.record_error(
                    f"Slow request ({elapsed:.1f}s)",
                    path=request.url.path,
                    status_code=408,
                )
