"""Pytest configuration settings and shared test fixtures."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.configs.settings import Settings, get_settings
from app.main import app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provides session settings parameters overrides for tests."""
    return get_settings()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture instance validating endpoint routings."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_chat_request_payload() -> dict[str, Any]:
    """Sample chat request JSON payload for schema tests."""
    return {
        "messages": [
            {"role": "user", "content": "Hello! I need a test for hiring developers."},
            {
                "role": "assistant",
                "content": "Sure, what candidate level seniority are you looking for?",
            },
            {"role": "user", "content": "They are entry-level graduates."},
        ]
    }


@pytest.fixture
def sample_invalid_role_payload() -> dict[str, Any]:
    """Invalid sequence request payload violating alternating roles rule."""
    return {
        "messages": [
            {"role": "user", "content": "I need a test."},
            {"role": "user", "content": "Hello?"},  # Consecutive user roles
        ]
    }
