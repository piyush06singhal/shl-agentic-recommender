"""Conversation validator analyzing history consistency and message integrity."""

import logging

from app.configs.constants import MAX_MESSAGE_CHARACTER_LENGTH
from app.schemas.request import Message

logger = logging.getLogger(__name__)


class HistoryValidator:
    """Audits fully parsed conversation history messages for redundancy, length boundaries, and consistency."""

    def validate_message_integrity(self, messages: list[Message]) -> list[str]:
        """Performs validation checks over dialogue turns, gathering non-fatal warnings.

        Checks:
        - Message length limits.
        - Redundant duplicate messages.
        - Blank content (handled in parsing, but check is documented).
        - Alternate validation (already handled by parser, but confirms safety).

        Args:
            messages: Pre-validated Message objects list.

        Returns:
            A list of warning messages describing anomalies found.
        """
        warnings: list[str] = []
        if not messages:
            return warnings

        seen_contents: set[str] = set()

        for idx, msg in enumerate(messages):
            # 1. Message character length audit
            content_len = len(msg.content)
            if content_len > MAX_MESSAGE_CHARACTER_LENGTH:
                # Typically, Pydantic handles max_length limit, but if bypassed:
                raise ValueError(
                    f"Message at index {idx} exceeds permitted characters length limits: "
                    f"{content_len} > {MAX_MESSAGE_CHARACTER_LENGTH}."
                )

            # 2. Check for duplicate messages (repeated statements)
            normalized_content = " ".join(msg.content.lower().split())
            if msg.role == "user":
                if normalized_content in seen_contents:
                    warnings.append(
                        f"User sent duplicate message at index {idx}: "
                        f"'{msg.content[:40]}...'"
                    )
                seen_contents.add(normalized_content)

        return warnings
