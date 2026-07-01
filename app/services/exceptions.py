"""Custom exception hierarchy database definitions module."""

from typing import Any


class BaseApplicationException(Exception):
    """Base exception class for all custom exceptions in the system."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ConfigurationException(BaseApplicationException):
    """Exception thrown when configuration settings fail validation checks."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


class ValidationException(BaseApplicationException):
    """Exception thrown when incoming message payload schemas or roles fail validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=422, details=details)


class RetrieverException(BaseApplicationException):
    """Exception thrown when queries against vector stores or database indexes fail."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


class LLMException(BaseApplicationException):
    """Exception thrown when external Large Language Model completions calls fail or timeout."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=502, details=details)


class CatalogException(BaseApplicationException):
    """Exception thrown when offline ingestion checks or metadata parsing fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


class AgentException(BaseApplicationException):
    """Exception thrown when state machines or decision-making routing rules fail."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=400, details=details)
