"""FastAPI middlewares configuration for CORS, trusted hosts, timings, and request IDs."""

import logging
import time
import uuid
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)


def register_middlewares(app: FastAPI) -> None:
    """Registers global middlewares (CORS, trusted hosts, request ID, timing, logs).

    Args:
        app: FastAPI application instance.
    """
    # 1. CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Trusted Host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # Restrict in production setting
    )

    # 3. HTTP middleware for request ID correlation and performance timing
    @app.middleware("http")
    async def log_request_performance(request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start_time = time.monotonic()
        logger.info(
            "API: [Start] %s %s (Request ID: %s)",
            request.method,
            request.url.path,
            correlation_id,
        )

        response = cast(Response, await call_next(request))

        duration_ms = (time.monotonic() - start_time) * 1000.0
        response.headers["x-correlation-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{duration_ms:.2f}"

        logger.info(
            "API: [Finish] %s %s | Status %d | Timing %.2fms (Request ID: %s)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id,
        )

        return response
