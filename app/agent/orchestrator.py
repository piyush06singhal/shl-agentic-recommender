"""Agent orchestrator coordinates the routing of resolved ConversationState actions."""

import logging

from app.agent.action_executor import ActionExecutor
from app.agent.models import ChatResponse
from app.agent.state import ConversationState

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates system execution flows, delegating actions to the ActionExecutor."""

    def __init__(self, action_executor: ActionExecutor) -> None:
        self.executor = action_executor

    def route_action(self, state: ConversationState) -> ChatResponse:
        """Reads resolved action from state and triggers execution.

        Args:
            state: Precalculated ConversationState snapshot.

        Returns:
            A ChatResponse envelope.
        """
        logger.info("AgentOrchestrator: Routing action: %s", state.next_action)
        return self.executor.execute_action(state)
