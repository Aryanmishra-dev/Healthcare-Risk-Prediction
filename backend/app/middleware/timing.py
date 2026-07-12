"""
Middleware for request timing, error logging, and inference latency.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            # Log slow requests
            if process_time > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} took {process_time:.3f}s"
                )

            return response
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} after {process_time:.3f}s",
                exc_info=True,
            )
            # Structured JSON error
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "path": request.url.path,
                    "message": "An unexpected error occurred. Please try again later.",
                },
            )
