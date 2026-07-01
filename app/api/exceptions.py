"""FastAPI exception handlers registering application-specific error response formats."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.exceptions import BaseApplicationException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers mapping custom exceptions to standard responses.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(BaseApplicationException)
    async def app_exception_handler(request: Request, exc: BaseApplicationException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "Caught application exception [%s] (ID: %s): %s",
            exc.__class__.__name__,
            correlation_id,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error_type": exc.__class__.__name__,
                "correlation_id": correlation_id,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.warning(
            "Caught validation error (ID: %s): %s",
            correlation_id,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request body validation failed.",
                "error_type": "RequestValidationError",
                "correlation_id": correlation_id,
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.critical(
            "Caught unhandled server exception (ID: %s): %s",
            correlation_id,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "error_type": "InternalServerError",
                "correlation_id": correlation_id,
            },
        )
