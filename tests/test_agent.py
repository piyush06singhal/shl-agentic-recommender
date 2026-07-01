"""Unit tests for models validation schemas and base configurations."""

import pytest
from pydantic import ValidationError

from app.schemas.request import Message


def test_valid_message_model() -> None:
    """Verifies Message Pydantic model parses valid structures successfully."""
    msg = Message(role="user", content="Hello!")
    assert msg.role == "user"
    assert msg.content == "Hello!"


def test_invalid_role_message() -> None:
    """Verifies Message model rejects unpermitted role values."""
    with pytest.raises(ValidationError):
        Message(role="system", content="System initialization")  # Roles must be user or assistant


def test_invalid_content_message() -> None:
    """Verifies Message model rejects empty content strings."""
    with pytest.raises(ValidationError):
        Message(role="user", content="")
