"""Conversation parser for validating, normalizing, and sanitizing dialogue history."""

import logging
from typing import Any

from app.schemas.request import Message

logger = logging.getLogger(__name__)


class ConversationParser:
    """Validates, sanitizes, and normalizes stateless conversation history."""

    def parse_and_validate(self, raw_messages: list[Any]) -> list[Message]:
        """Converts raw messages into validated Message models, checking schema and constraints.

        Args:
            raw_messages: A list of dicts or Message objects representing dialogue history.

        Returns:
            A list of sanitized and validated Message objects.

        Raises:
            ValueError: If the history is malformed, empty, or violates sequencing rules.
        """
        if not raw_messages:
            raise ValueError("Conversation history cannot be empty.")

        parsed: list[Message] = []

        for idx, raw in enumerate(raw_messages):
            # 1. Normalize object format
            if isinstance(raw, dict):
                role = raw.get("role")
                content = raw.get("content")
                if not role or content is None:
                    raise ValueError(f"Message at index {idx} is missing 'role' or 'content'.")
                msg = Message(role=str(role).strip(), content=str(content))
            elif hasattr(raw, "role") and hasattr(raw, "content"):
                msg = Message(role=raw.role.strip(), content=raw.content)
            else:
                raise ValueError(f"Message at index {idx} has an invalid type: {type(raw)}.")

            # 2. Normalize and sanitize content
            msg.content = msg.content.strip()

            # Reject empty message content (Pydantic validator does min_length=1 but we double check)
            if not msg.content:
                raise ValueError(f"Message at index {idx} has empty content after trimming.")

            # Ensure roles are allowed
            if msg.role not in {"user", "assistant"}:
                raise ValueError(f"Message at index {idx} has invalid role: '{msg.role}'.")

            parsed.append(msg)

        # 3. Validate message order and alternation sequence
        self.validate_alternation(parsed)

        return parsed

    def validate_alternation(self, messages: list[Message]) -> None:
        """Validates that messages alternate roles between user and assistant.

        Typically starts with a user message. Consecutive roles of the same type are rejected.

        Args:
            messages: List of parsed Message objects.

        Raises:
            ValueError: If the roles do not alternate correctly.
        """
        if not messages:
            return

        # Ensure the first message is a user message
        if messages[0].role != "user":
            raise ValueError("Conversation history must start with a 'user' message.")

        last_role = messages[0].role
        for idx in range(1, len(messages)):
            current_role = messages[idx].role
            if current_role == last_role:
                raise ValueError(
                    f"Consecutive messages of the same role detected. "
                    f"Index {idx-1} and {idx} both have role '{last_role}'."
                )
            last_role = current_role
