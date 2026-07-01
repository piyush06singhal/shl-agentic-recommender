"""Turn manager for counting and validating dialogue turns and checking boundaries."""

import logging
from typing import Any

from app.agent.models import TurnStatistics
from app.configs.settings import get_settings
from app.schemas.request import Message

logger = logging.getLogger(__name__)


class TurnManager:
    """Manages dialogue turn counting, sequence boundaries, and checks conversation limits."""

    def __init__(self, max_turns: int | None = None) -> None:
        settings = get_settings()
        # Fallback to 20 if settings doesn't have max_conversation_turns
        resolved_max: Any = max_turns or getattr(settings, "max_conversation_turns", 20)
        self.max_turns: int = int(resolved_max) if resolved_max is not None else 20

    def calculate_statistics(self, messages: list[Message]) -> TurnStatistics:
        """Counts user and assistant turns, and checks if conversation limit is reached.

        Args:
            messages: Sanitized message list.

        Returns:
            A TurnStatistics model.
        """
        user_turns = sum(1 for m in messages if m.role == "user")
        assistant_turns = sum(1 for m in messages if m.role == "assistant")
        total_turns = len(messages)

        # Enforce maximum turn limits
        is_at_limit = total_turns >= self.max_turns

        return TurnStatistics(
            user_turns=user_turns,
            assistant_turns=assistant_turns,
            total_turns=total_turns,
            is_at_limit=is_at_limit,
        )

    def check_turn_limit(self, stats: TurnStatistics) -> None:
        """Raises ValueError if maximum conversation turns has been exceeded.

        Args:
            stats: Precalculated TurnStatistics.

        Raises:
            ValueError: If turn limit is breached.
        """
        if stats.total_turns > self.max_turns:
            raise ValueError(
                f"Conversation turn limit exceeded. "
                f"Active turns: {stats.total_turns}, Maximum permitted: {self.max_turns}."
            )
