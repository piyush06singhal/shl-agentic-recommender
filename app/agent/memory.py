"""In-memory session state storage manager for stateless or stateful tracking."""

import logging

from app.agent.state import ConversationState

logger = logging.getLogger(__name__)


class AgentMemory:
    """Manages tracking and retrieval of ConversationState snapshots for sessions.

    Useful when integrating the stateless engine with stateful application routers.
    """

    def __init__(self) -> None:
        self._memory: dict[str, list[ConversationState]] = {}

    def get_history(self, conversation_id: str) -> list[ConversationState]:
        """Retrieves state history snapshots list for a given conversation session ID.

        Args:
            conversation_id: Unique session identifier.

        Returns:
            List of previously saved states.
        """
        return self._memory.get(conversation_id, [])

    def get_latest_state(self, conversation_id: str) -> ConversationState | None:
        """Gets the most recently saved state snapshot for a session.

        Args:
            conversation_id: Unique session identifier.

        Returns:
            The latest ConversationState or None.
        """
        history = self.get_history(conversation_id)
        if history:
            return history[-1]
        return None

    def save_state(self, conversation_id: str, state: ConversationState) -> None:
        """Saves a new state snapshot to the session dialogue history.

        Args:
            conversation_id: Unique session identifier.
            state: ConversationState to save.
        """
        if conversation_id not in self._memory:
            self._memory[conversation_id] = []
        self._memory[conversation_id].append(state)
        logger.debug(
            "AgentMemory: Saved state for session '%s' (history_size=%d).",
            conversation_id,
            len(self._memory[conversation_id]),
        )

    def clear(self, conversation_id: str) -> None:
        """Purges stored session history.

        Args:
            conversation_id: Unique session identifier.
        """
        self._memory.pop(conversation_id, None)
        logger.info("AgentMemory: Cleared history memory for session '%s'.", conversation_id)

    def clear_all(self) -> None:
        """Purges all saved session memory."""
        self._memory.clear()
        logger.info("AgentMemory: Cleared all sessions memory.")
