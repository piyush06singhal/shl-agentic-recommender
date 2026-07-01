"""Conversation manager orchestrating session state lifecycles and dialogue loops."""

import logging
from typing import Any

from app.agent.conversation import ConversationEngine
from app.agent.memory import AgentMemory
from app.agent.models import AgentAction, ChatResponse
from app.agent.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages dialogue session CRUD states and handles conversation lifetime flows."""

    def __init__(
        self,
        conversation_engine: ConversationEngine,
        orchestrator: AgentOrchestrator,
        memory: AgentMemory | None = None,
    ) -> None:
        self.engine = conversation_engine
        self.orchestrator = orchestrator
        self.memory = memory or AgentMemory()

    def start_conversation(self, session_id: str) -> ChatResponse:
        """Initializes a new dialogue session, preparing greeting responses.

        Args:
            session_id: Unique session identifier.

        Returns:
            A greeting ChatResponse.
        """
        self.memory.clear(session_id)
        reply = (
            "Hello! I am your SHL assessment hiring consultant. I can help you discover, "
            "recommend, and compare official SHL assessment products for recruitment. "
            "What role or job family are you hiring for?"
        )
        logger.info("ConversationManager: Started session '%s'.", session_id)
        return self.orchestrator.executor.response_builder.build_response(reply=reply)

    def continue_conversation(
        self,
        session_id: str,
        raw_messages: list[Any],
    ) -> ChatResponse:
        """Processes the next conversational step using the raw history provided.

        Args:
            session_id: Unique session identifier.
            raw_messages: Dialogue message turns list.

        Returns:
            The resolved ChatResponse.
        """
        # Reconstruct state from history
        state = self.engine.process_conversation(raw_messages, conversation_id=session_id)

        # Save state to memory history
        self.memory.save_state(session_id, state)

        # Route decided action to generate response
        response = self.orchestrator.route_action(state)

        # If next action is END_CONVERSATION, set completion flag
        if state.next_action == AgentAction.END_CONVERSATION or response.end_of_conversation:
            logger.info("ConversationManager: Session '%s' flagged as completed.", session_id)

        return response

    def restart_conversation(self, session_id: str) -> ChatResponse:
        """Resets the active constraints state and returns to starting welcome parameters.

        Args:
            session_id: Unique session identifier.

        Returns:
            Start conversation greeting response.
        """
        logger.info("ConversationManager: Restarting session '%s'...", session_id)
        return self.start_conversation(session_id)

    def end_conversation(self, session_id: str) -> ChatResponse:
        """Terminates the session, returning goodbye responses.

        Args:
            session_id: Unique session identifier.

        Returns:
            Exit ChatResponse.
        """
        logger.info("ConversationManager: Explicitly ending session '%s'.", session_id)
        self.memory.clear(session_id)
        reply = (
            "Thank you for consulting with me. I hope you found the right SHL assessments. "
            "Good luck with your hiring! Let me know if you would like to start a new search."
        )
        return self.orchestrator.executor.response_builder.build_response(
            reply=reply,
            end_of_conversation=True,
        )

    def get_session_summary(self, session_id: str) -> str:
        """Compiles a text summary overview of the current session dialogue progression.

        Args:
            session_id: Unique session identifier.

        Returns:
            Summary report text.
        """
        state = self.memory.get_latest_state(session_id)
        if not state:
            return "No active session history located."

        return (
            f"Active Session Summary ('{session_id}'):\n"
            f"  - Intent: {state.intent}\n"
            f"  - Job Family: {state.active_context.job_family}\n"
            f"  - Seniority: {state.active_context.candidate_level}\n"
            f"  - Skills: {state.active_context.skills}\n"
            f"  - Resolved Action: {state.next_action}"
        )
