"""Utility helper modules containing reusable functions."""

import contextlib
import json
import logging
import re
import time
from collections.abc import Callable, Generator
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=Callable[..., Any])
logger = logging.getLogger(__name__)


def safe_json_load(file_path: str) -> Any:
    """Reads a JSON file safely from the local filesystem.

    Args:
        file_path: Path to target JSON file.

    Returns:
        The loaded JSON data structure (Dict, List, etc.).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("JSON file not found: %s", file_path)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON content at %s: %s", file_path, e)
        raise


def safe_json_dump(file_path: str, data: Any, indent: int = 4) -> None:
    """Writes a JSON data structure safely to a local filesystem file.

    Args:
        file_path: Path to save target file.
        data: The payload data (Dict, List, etc.) to serialize.
        indent: JSON indentation spacing.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to dump data to JSON file %s: %s", file_path, e)
        raise


def normalize_text(input_text: str) -> str:
    """Normalizes case, whitespace, and formatting variables in user text inputs.

    Args:
        input_text: The raw input string.

    Returns:
        The cleaned, normalized string.
    """
    # Remove HTML formatting tags
    cleaned = re.sub(r"<[^>]+>", "", input_text)
    # Strip formatting characters and normalize whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


def slugify(input_text: str) -> str:
    """Converts input text into a URL-friendly slug pattern.

    Args:
        input_text: The string to slugify.

    Returns:
        The slugified alphanumeric string.
    """
    normalized = normalize_text(input_text)
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", normalized)
    # Trim leading/trailing hyphens
    return slug.strip("-")


@contextlib.contextmanager
def timer(label: str) -> Generator[None, None, None]:
    """Context manager measuring execution durations of code blocks.

    Args:
        label: Custom name for the measured code execution path.
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        logger.info("Timer [%s]: Completed execution in %.4f seconds", label, duration)


def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[T], T]:
    """Decorator retrying wrapped functions on catching specified exceptions with exponential backoffs.

    Args:
        retries: Maximum execution attempts.
        delay: Initial retry pause in seconds.
        backoff: Exponential backoff scaling factor.
        exceptions: Tuple of exceptions to intercept and trigger retries on.
    """

    def decorator(func: T) -> T:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            current_delay = delay
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= retries:
                        logger.error(
                            "Retry exhausted for function %s after %d attempts: %s",
                            func.__name__,
                            attempt,
                            e,
                        )
                        raise
                    logger.warning(
                        "Retry attempt %d/%d for %s caught exception: %s. Pausing %.2fs.",
                        attempt,
                        retries,
                        func.__name__,
                        e,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return cast(T, wrapper)

    return decorator
